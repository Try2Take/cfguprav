"""Stage 1: the interactive REPL and its command stubs."""

import os
from pathlib import Path
import subprocess
import sys
import unittest


PROJECT_DIR = Path(__file__).resolve().parents[1]


class ReplTests(unittest.TestCase):
    def run_repl(self, commands, env=None):
        return subprocess.run(
            [sys.executable, str(PROJECT_DIR / "main.py")],
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


if __name__ == "__main__":
    unittest.main()
