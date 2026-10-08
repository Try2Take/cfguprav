from __future__ import annotations

import csv
from contextlib import redirect_stdout
import hashlib
import io
import os
import shlex
from datetime import datetime
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


PROJECT_DIR = Path(__file__).resolve().parents[1]
SOURCE_DIR = PROJECT_DIR / "src"
sys.path.insert(0, str(SOURCE_DIR))

from shell_emulator.emulator import ShellEmulator
from shell_emulator.vfs import File, VFSLoadError, VirtualFileSystem


VFS_FILE = PROJECT_DIR / "vfs" / "sample.xml"
SESSION_TIME = datetime(2026, 10, 4, 12, 30).astimezone()


LOG_COLUMNS = ("timestamp", "command", "arguments", "error")


def make_shell(log=None) -> ShellEmulator:
    log_buffer = log if log is not None else io.StringIO()
    shell = ShellEmulator(VirtualFileSystem.load(VFS_FILE),
                          csv.writer(log_buffer))
    shell.username = "student"
    shell.terminal = "pts-test"
    shell.login_time = SESSION_TIME
    return shell


def execute_ok(shell: ShellEmulator, line: str) -> str:
    output = io.StringIO()
    with redirect_stdout(output):
        error = shell.execute_line(line)
    if error:
        raise AssertionError(error)
    captured_output = output.getvalue()
    if captured_output.endswith("\n"):
        return captured_output[:-1]
    return captured_output


def execute_error(shell: ShellEmulator, line: str) -> str:
    with redirect_stdout(io.StringIO()):
        return shell.execute_line(line)


def run_startup_script(shell, path, output) -> tuple[int, bool]:
    with redirect_stdout(output):
        errors = shell.run(Path(path).read_text(encoding="utf-8").splitlines())
    return errors, not shell.running


def read_log(log_buffer) -> list[dict[str, str]]:
    log_buffer.seek(0)
    return list(csv.DictReader(log_buffer, fieldnames=LOG_COLUMNS))


class ParserTests(unittest.TestCase):

    def test_environment_quotes_and_comments(self) -> None:
        log = io.StringIO()
        shell = make_shell(log)
        with mock.patch.dict(
            os.environ,
            {"EMU_DIR": "/home/student/documents"},
        ):
            output = execute_ok(shell, 'head -n 2 "$EMU_DIR/notes.txt" # note')
        self.assertEqual(output, "alpha beta\ngamma delta epsilon")
        rows = read_log(log)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["command"], "head")
        self.assertEqual(shlex.split(rows[0]["arguments"]),
                         ["-n", "2", "/home/student/documents/notes.txt"])
        self.assertEqual(rows[0]["error"], "")

    def test_unclosed_quote_is_reported(self) -> None:
        error = execute_error(make_shell(), 'head "broken')
        self.assertIn("ошибка синтаксиса", error)


class VfsTests(unittest.TestCase):

    def test_text_binary_and_three_levels_are_loaded(self) -> None:
        file_system = VirtualFileSystem.load(VFS_FILE)
        student = file_system.resolve("/home/student", directory=True)
        text = file_system.entries[file_system.resolve("documents/notes.txt", student)]
        binary = file_system.entries[file_system.resolve("documents/data.bin", student)]
        self.assertIsInstance(text, File)
        self.assertEqual(
            text.content,
            b"alpha beta\ngamma delta epsilon\nlast line",
        )
        self.assertIsInstance(binary, File)
        self.assertEqual(binary.content, bytes([0, 1, 2, 3, 255]))

    def test_absolute_relative_parent_and_root_paths(self) -> None:
        file_system = VirtualFileSystem.load(VFS_FILE)
        documents = file_system.resolve(
            "/home/student/documents",
            "/",
            directory=True,
        )
        welcome = file_system.resolve("../welcome.txt", documents)
        self.assertEqual(
            welcome,
            "/home/student/welcome.txt",
        )
        self.assertEqual(file_system.resolve("../../../../..", documents), "/")

    def test_missing_malformed_and_duplicate_vfs_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            malformed = directory / "malformed.xml"
            duplicate = directory / "duplicate.xml"
            malformed.write_text("<vfs><directory></vfs>", encoding="utf-8")
            duplicate.write_text(
                '<vfs><file name="a"/><file name="a"/></vfs>',
                encoding="utf-8",
            )
            with self.assertRaises(VFSLoadError):
                VirtualFileSystem.load(directory / "missing.xml")
            with self.assertRaises(VFSLoadError):
                VirtualFileSystem.load(malformed)
            with self.assertRaises(VFSLoadError):
                VirtualFileSystem.load(duplicate)


class CommandTests(unittest.TestCase):

    def setUp(self) -> None:
        self.shell = make_shell()

    def test_prompt_ls_and_cd(self) -> None:
        self.assertEqual(self.shell.prompt(), "study-vfs:/$ ")
        self.assertEqual(execute_ok(self.shell, "ls"), "etc/\nhome/")
        execute_ok(self.shell, "cd /home/student/documents")
        self.assertEqual(
            self.shell.prompt(),
            "study-vfs:/home/student/documents$ ",
        )
        self.assertEqual(
            execute_ok(self.shell, "ls"),
            "data.bin\nnotes.txt",
        )

    def test_ls_and_cd_argument_errors(self) -> None:
        ls_error = execute_error(self.shell, "ls a b")
        self.assertIn("не более одного", ls_error)
        self.assertIn("ровно один", execute_error(self.shell, "cd"))
        self.assertIn("не является каталогом",
                      execute_error(self.shell, "cd /etc/motd"))
        missing_error = execute_error(self.shell, "cd /missing")
        self.assertIn("нет такого", missing_error)

    def test_head_default_count_and_short_forms(self) -> None:
        execute_ok(self.shell, "cd /home/student")
        default = execute_ok(self.shell, "head welcome.txt")
        self.assertEqual(len(default.splitlines()), 3)
        one = execute_ok(self.shell, "head -1 welcome.txt")
        self.assertEqual(
            one,
            "Добро пожаловать в виртуальную файловую систему.",
        )
        zero = execute_ok(self.shell, "head -n 0 welcome.txt")
        self.assertEqual(zero, "")

    def test_head_multiple_files_and_errors(self) -> None:
        execute_ok(self.shell, "cd /home/student")
        output = execute_ok(
            self.shell,
            "head -n 1 welcome.txt documents/notes.txt",
        )
        self.assertIn("==> /home/student/welcome.txt <==", output)
        self.assertIn("==> /home/student/documents/notes.txt <==", output)
        error = execute_error(self.shell, "head documents/data.bin")
        self.assertIn("двоичный файл", error)
        self.assertIn("требуется имя", execute_error(self.shell, "head"))
        self.assertIn("неизвестный ключ",
                      execute_error(self.shell, "head -x welcome.txt"))

    def test_wc_default_flags_binary_and_total(self) -> None:
        output = execute_ok(self.shell, "wc /home/student/welcome.txt")
        self.assertTrue(output.startswith("2 16 196 "))
        binary = execute_ok(
            self.shell,
            "wc -c /home/student/documents/data.bin",
        )
        self.assertEqual(binary, "5 /home/student/documents/data.bin")
        total = execute_ok(
            self.shell,
            "wc -lw /etc/motd /home/student/documents/notes.txt",
        )
        self.assertTrue(total.splitlines()[-1].endswith("итого"))

    def test_wc_argument_errors(self) -> None:
        self.assertIn("требуется имя", execute_error(self.shell, "wc"))
        self.assertIn("неизвестный ключ",
                      execute_error(self.shell, "wc -z /etc/motd"))
        error = execute_error(self.shell, "wc /home/student")
        self.assertIn("является каталогом", error)

    def test_who_exit_and_unknown_command(self) -> None:
        self.assertEqual(
            execute_ok(self.shell, "who"),
            "student pts-test 2026-10-04 12:30",
        )
        self.assertIn("не принимает", execute_error(self.shell, "who x"))
        execute_ok(self.shell, "exit")
        self.assertFalse(self.shell.running)
        self.assertIn("неизвестная", execute_error(self.shell, "missing"))

    def test_touch_creates_and_updates_files_in_memory(self) -> None:
        execute_ok(self.shell, "cd /home/student/documents")
        execute_ok(self.shell, "touch empty.txt notes.txt")
        created = self.shell.file_system.entries[
            self.shell.file_system.resolve("empty.txt", self.shell.current_dir)
        ]
        self.assertIsInstance(created, File)
        self.assertEqual(created.content, b"")
        self.assertIn("empty.txt", execute_ok(self.shell, "ls"))
        self.assertEqual(execute_ok(self.shell, "wc empty.txt").split()[0:3],
                         ["0", "0", "0"])

    def test_touch_errors_and_xml_is_unchanged(self) -> None:
        before = hashlib.sha256(VFS_FILE.read_bytes()).digest()
        self.assertIn("требуется имя", execute_error(self.shell, "touch"))
        self.assertIn("является каталогом",
                      execute_error(self.shell, "touch /home"))
        self.assertIn("нет такого",
                      execute_error(self.shell, "touch /missing/a"))
        execute_ok(self.shell, "touch /created.txt")
        after = hashlib.sha256(VFS_FILE.read_bytes()).digest()
        self.assertEqual(before, after)
        reloaded = VirtualFileSystem.load(VFS_FILE)
        self.assertNotIn("/created.txt", reloaded.entries)


class LoggingAndScriptTests(unittest.TestCase):

    def test_csv_contains_success_and_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "commands.csv"
            with log_path.open("w+", encoding="utf-8", newline="") as log_buffer:
                shell = make_shell(log_buffer)
                execute_ok(shell, "ls /etc")
                execute_error(shell, "cd /missing")
                rows = read_log(log_buffer)
        self.assertEqual([row["command"] for row in rows], ["ls", "cd"])
        self.assertEqual(rows[0]["error"], "")
        self.assertIn("нет такого", rows[1]["error"])

    def test_script_shows_dialog_comments_errors_and_continues(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "start.txt"
            script.write_text(
                "# comment\nls /etc\ncd /missing\nwho\nexit\nwho\n",
                encoding="utf-8",
            )
            output = io.StringIO()
            errors, exit_requested = run_startup_script(
                make_shell(), script, output,
            )
        rendered = output.getvalue()
        self.assertEqual(errors, 1)
        self.assertTrue(exit_requested)
        self.assertIn("study-vfs:/$ ls /etc", rendered)
        self.assertIn("Ошибка в строке 3", rendered)
        self.assertIn("student pts-test", rendered)
        self.assertEqual(rendered.count("student pts-test"), 1)

    def test_missing_script_is_reported(self) -> None:
        output = io.StringIO()
        with self.assertRaises(OSError):
            run_startup_script(make_shell(), "/missing/script.txt", output)


class CliTests(unittest.TestCase):

    def test_cli_uses_all_parameters(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            script = directory / "start.txt"
            log = directory / "commands.csv"
            script.write_text("ls $EMU_PATH\nexit\n", encoding="utf-8")
            command = [
                sys.executable,
                str(PROJECT_DIR / "main.py"),
                "--vfs",
                str(VFS_FILE),
                "--log",
                str(log),
                "--script",
                str(script),
            ]
            environment = os.environ.copy()
            environment["EMU_PATH"] = "/etc"
            result = subprocess.run(
                command,
                text=True,
                encoding="utf-8",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=environment,
                timeout=10,
                check=False,
            )
            rows = list(csv.DictReader(log.open(encoding="utf-8")))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("Параметры запуска", result.stdout)
        self.assertIn("study-vfs:/$ ls $EMU_PATH", result.stdout)
        self.assertEqual([row["command"] for row in rows], ["ls", "exit"])

    def test_cli_rejects_invalid_vfs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            invalid = directory / "invalid.xml"
            invalid.write_text("<vfs><directory></vfs>", encoding="utf-8")
            command = [
                sys.executable, str(PROJECT_DIR / "main.py"),
                "--vfs", str(invalid),
                "--log", str(directory / "commands.csv"),
            ]
            result = subprocess.run(
                command, text=True, encoding="utf-8",
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=10, check=False,
            )
        self.assertEqual(result.returncode, 2)
        self.assertIn("Ошибка загрузки VFS", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
