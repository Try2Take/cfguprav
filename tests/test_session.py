"""Проверки ошибок за всю сессию REPL."""

from contextlib import redirect_stdout
import io
import unittest
from unittest import mock

from test_emulator import make_shell


class SessionTests(unittest.TestCase):
    def test_errors_are_kept_between_script_and_repl(self):
        shell = make_shell()
        with redirect_stdout(io.StringIO()):
            script_errors = shell.run(["cd /missing", "ls /etc"])
            commands = ["ls /absent", "exit"]
            with mock.patch("builtins.input", side_effect=commands):
                repl_errors = shell.run()
        self.assertEqual(script_errors, 1)
        self.assertEqual(repl_errors, 1)
        self.assertEqual(getattr(shell, "error_count", 0), 2)

    def test_parse_and_command_errors_are_counted(self):
        shell = make_shell()
        with redirect_stdout(io.StringIO()):
            commands = ['head "broken', "unknown", "exit extra", "exit"]
            errors = shell.run(commands)
        self.assertEqual(errors, 3)
        self.assertEqual(getattr(shell, "error_count", 0), 3)
        self.assertFalse(shell.running)

    def test_empty_lines_comments_and_eof_are_not_errors(self):
        shell = make_shell()
        output = io.StringIO()
        with redirect_stdout(output):
            errors = shell.run(["", " # comment", "ls /etc"])
            with mock.patch("builtins.input", side_effect=EOFError):
                repl_errors = shell.run()
        self.assertEqual((errors, repl_errors), (0, 0))
        self.assertNotIn("Ошибка", output.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
