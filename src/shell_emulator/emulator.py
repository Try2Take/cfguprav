from __future__ import annotations

import getpass
import os
import posixpath
import shlex
import time
from datetime import datetime
from getopt import GetoptError, getopt

from .vfs import CommandError, File, VirtualFileSystem, validate_name


class ShellEmulator:
    def __init__(self, file_system: VirtualFileSystem, log_writer) -> None:
        self.file_system = file_system
        self.current_dir = "/"
        self.log_writer = log_writer
        self.running = True
        self.username = getpass.getuser()
        try:
            self.terminal = os.path.basename(os.ttyname(0))
        except OSError:
            self.terminal = "console"
        self.login_time = datetime.now().astimezone()
        self.commands = {
            "ls": self._command_ls,
            "cd": self._command_cd,
            "head": self._command_head,
            "wc": self._command_wc,
            "who": self._command_who,
            "touch": self._command_touch,
        }

    def prompt(self) -> str:
        return f"{self.file_system.name}:{self.current_dir}$ "

    def execute_line(self, line: str) -> str:
        command_name = "<parse>"
        arguments = [line]
        output = ""
        error_message = ""

        try:
            expanded_line = os.path.expandvars(line)
            command_parts = shlex.split(expanded_line, comments=True)
            if not command_parts:
                return ""
            command_name = command_parts[0]
            arguments = command_parts[1:]

            if command_name == "exit":
                if arguments:
                    raise CommandError("exit: команда не принимает аргументы")
                self.running = False
            elif command_name in self.commands:
                output = self.commands[command_name](arguments)
            else:
                raise CommandError(f"неизвестная команда: {command_name}")
        except CommandError as error:
            error_message = str(error)
        except ValueError as error:
            error_message = f"ошибка синтаксиса: {error}"

        command_time = datetime.now().astimezone().isoformat(timespec="seconds")
        self.log_writer.writerow((command_time, command_name,
                                  shlex.join(arguments), error_message))
        if output:
            print(output)
        return error_message

    def _command_ls(self, arguments: list[str]) -> str:
        if len(arguments) > 1:
            raise CommandError("ls: ожидается не более одного пути")

        requested_path = arguments[0] if arguments else "."
        folder_path = self.file_system.resolve(requested_path, self.current_dir)
        if self.file_system.entries[folder_path] is not None:
            return posixpath.basename(folder_path)

        names = []
        for entry_path, entry in sorted(self.file_system.entries.items()):
            if posixpath.dirname(entry_path) != folder_path or entry_path == folder_path:
                continue
            entry_name = posixpath.basename(entry_path)
            if entry is None:
                entry_name += "/"
            names.append(entry_name)
        return "\n".join(names)

    def _command_cd(self, arguments: list[str]) -> str:
        if len(arguments) != 1:
            raise CommandError("cd: ожидается ровно один путь")
        self.current_dir = self.file_system.resolve(
            arguments[0], self.current_dir, directory=True,
        )
        return ""

    def _command_head(self, arguments: list[str]) -> str:
        line_count, file_paths = self._parse_head_arguments(arguments)
        output_parts = []

        for file_path in file_paths:
            full_path = self.file_system.resolve(file_path, self.current_dir,
                                                 directory=False)
            file = self.file_system.entries[full_path]
            if file.binary:
                raise CommandError(f"head: двоичный файл: {full_path}")

            file_lines = file.content.decode("utf-8").splitlines()
            file_output = "\n".join(file_lines[:line_count])
            if len(file_paths) > 1:
                heading = f"==> {full_path} <=="
                if file_output:
                    file_output = heading + "\n" + file_output
                else:
                    file_output = heading
            output_parts.append(file_output)
        return "\n\n".join(output_parts)

    @staticmethod
    def _parse_head_arguments(arguments: list[str]) -> tuple[int, list[str]]:
        line_count = 10
        index = 0

        while index < len(arguments):
            argument = arguments[index]
            if argument == "--":
                index += 1
                break
            if not argument.startswith("-") or argument == "-":
                break

            if argument == "-n":
                index += 1
                count_text = arguments[index] if index < len(arguments) else ""
            elif argument[1:].isdigit():
                count_text = argument[1:]
            else:
                raise CommandError(f"head: неизвестный ключ: {argument}")

            try:
                line_count = int(count_text)
            except ValueError:
                raise CommandError(f"head: ожидалось число строк: {count_text}")
            if line_count < 0:
                raise CommandError(f"head: отрицательное число строк: {count_text}")
            index += 1

        file_paths = arguments[index:]
        if not file_paths:
            raise CommandError("head: требуется имя хотя бы одного файла")
        return line_count, file_paths

    def _command_wc(self, arguments: list[str]) -> str:
        try:
            options, file_paths = getopt(arguments, "lwc")
        except GetoptError as error:
            raise CommandError(f"wc: неизвестный ключ: {error.opt}")
        if not file_paths:
            raise CommandError("wc: требуется имя хотя бы одного файла")

        selected_counts = []
        for option, _ in options:
            count_name = option[1]
            if count_name not in selected_counts:
                selected_counts.append(count_name)
        if not selected_counts:
            selected_counts = ["l", "w", "c"]

        results = []
        total_counts = {"l": 0, "w": 0, "c": 0}
        for file_path in file_paths:
            full_path = self.file_system.resolve(file_path, self.current_dir,
                                                 directory=False)
            file = self.file_system.entries[full_path]
            file_counts = {
                "l": file.content.count(b"\n"),
                "w": len(file.content.split()),
                "c": len(file.content),
            }
            for count_name in total_counts:
                total_counts[count_name] += file_counts[count_name]
            results.append((file_counts, full_path))

        if len(file_paths) > 1:
            results.append((total_counts, "итого"))

        output_lines = []
        for counts, file_name in results:
            numbers = [str(counts[count_name]) for count_name in selected_counts]
            output_lines.append(" ".join(numbers) + " " + file_name)
        return "\n".join(output_lines)

    def _command_who(self, arguments: list[str]) -> str:
        if arguments:
            raise CommandError("who: команда не принимает аргументы")
        session_start = self.login_time.strftime("%Y-%m-%d %H:%M")
        return f"{self.username} {self.terminal} {session_start}"

    def _command_touch(self, arguments: list[str]) -> str:
        if not arguments:
            raise CommandError("touch: требуется имя хотя бы одного файла")

        modified_time = time.time()
        for file_path in arguments:
            if not file_path or file_path.endswith("/"):
                raise CommandError(f"недопустимый путь файла: {file_path!r}")

            parent_path, _, file_name = file_path.rpartition("/")
            validate_name(file_name)
            if not parent_path:
                parent_path = "/" if file_path.startswith("/") else "."
            parent_path = self.file_system.resolve(parent_path, self.current_dir,
                                                   directory=True)
            full_path = posixpath.join(parent_path, file_name)

            if full_path not in self.file_system.entries:
                self.file_system.entries[full_path] = File()
            file = self.file_system.entries[full_path]
            if file is None:
                raise CommandError(f"touch: является каталогом: {file_path}")
            file.modified_at = modified_time
        return ""

    def run(self, lines: list[str] | None = None) -> int:
        script_lines = iter(enumerate(lines, 1)) if lines is not None else None
        error_count = 0

        while self.running:
            try:
                if script_lines is not None:
                    line_number, line = next(script_lines)
                else:
                    line_number = 0
                    line = input(self.prompt())
            except (StopIteration, EOFError, KeyboardInterrupt):
                if script_lines is None:
                    print()
                break

            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if script_lines is not None:
                print(f"{self.prompt()}{line}")

            error_message = self.execute_line(line)
            if error_message:
                error_count += 1
                if line_number:
                    print(f"Ошибка в строке {line_number}: {error_message}")
                else:
                    print(f"Ошибка: {error_message}")
        return error_count
