"""Stage 1: the interactive REPL and its command stubs."""

import os
import csv
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


PROJECT_DIR = Path(__file__).resolve().parents[1]


class ReplTests(unittest.TestCase):
    def run_repl(self, commands, env=None):
        with tempfile.TemporaryDirectory() as temp_dir:
            return subprocess.run(
                [sys.executable, str(PROJECT_DIR / "main.py"),
                 "--vfs", str(Path(temp_dir) / "not-loaded.xml"),
                 "--log", str(Path(temp_dir) / "commands.csv")],
                input=commands, text=True, capture_output=True,
                env=env, check=False,
            )

    def test_prompt_stubs_and_environment_expansion(self):
        env = os.environ.copy()
        env["EMU_TARGET"] = "/tmp/example"
        result = self.run_repl("ls $EMU_TARGET\ncd /tmp\nexit\n", env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("study-vfs:/$", result.stdout)
        self.assertIn("ls: /tmp/example", result.stdout)
        self.assertIn("cd: /tmp", result.stdout)

    def test_errors_and_exit(self):
        result = self.run_repl("unknown\nhead file\ntouch file\nexit\nls later\n")
        self.assertIn("неизвестная команда: unknown", result.stdout)
        self.assertIn("неизвестная команда: head", result.stdout)
        self.assertIn("неизвестная команда: touch", result.stdout)
        self.assertNotIn("ls: later", result.stdout)
        self.assertEqual(result.returncode, 1)

    def test_script_echo_comments_and_csv_errors(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            script = directory / "start.txt"
            log = directory / "commands.csv"
            script.write_text("# comment\nls $EMU_TARGET\nunknown\nexit\n",
                              encoding="utf-8")
            env = os.environ.copy()
            env["EMU_TARGET"] = "/from-env"
            result = subprocess.run(
                [sys.executable, str(PROJECT_DIR / "main.py"),
                 "--vfs", str(directory / "not-loaded.xml"),
                 "--log", str(log), "--script", str(script)],
                text=True, capture_output=True, env=env, check=False,
            )
            self.assertTrue(log.exists(), result.stderr)
            with log.open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("Параметры запуска:", result.stdout)
        self.assertIn("study-vfs:/$ ls $EMU_TARGET", result.stdout)
        self.assertIn("ls: /from-env", result.stdout)
        self.assertNotIn("# comment", result.stdout)
        self.assertIn("Errors были во время исполнения", result.stdout)
        self.assertEqual([row["command"] for row in rows], ["ls", "unknown", "exit"])
        self.assertEqual(rows[0]["error"], "")
        self.assertIn("неизвестная команда", rows[1]["error"])


if __name__ == "__main__":
    unittest.main()
