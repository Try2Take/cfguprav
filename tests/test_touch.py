"""Изменения файлов командой touch остаются в памяти."""

from datetime import datetime
import unittest
from unittest import mock

from test_emulator import execute_error, execute_ok, make_shell


class TouchTests(unittest.TestCase):
    def test_double_dash_is_a_separator_and_not_a_file(self):
        shell = make_shell()
        execute_ok(shell, "touch -- -draft")
        self.assertIn("/-draft", shell.file_system.entries)
        self.assertNotIn("/--", shell.file_system.entries)
        self.assertEqual(execute_ok(shell, "ls -- -draft"), "-draft")

    def test_separator_without_names_is_an_error(self):
        shell = make_shell()
        error = execute_error(shell, "touch --")
        self.assertIn("требуется имя", error)
        self.assertNotIn("/--", shell.file_system.entries)

    def test_unsupported_flag_does_not_create_a_file(self):
        shell = make_shell()
        error = execute_error(shell, "touch -z")
        self.assertIn("неизвестный ключ", error)
        self.assertNotIn("/-z", shell.file_system.entries)

    def test_time_is_updated_without_changing_existing_content(self):
        shell = make_shell()
        file = shell.file_system.entries["/etc/motd"]
        content = file.content
        changed_at = datetime(2026, 10, 9, 12, 30).timestamp()
        with mock.patch("shell_emulator.emulator.time.time",
                        return_value=changed_at):
            execute_ok(shell, "touch /etc/motd /new")
        self.assertEqual(file.content, content)
        self.assertEqual(file.modified_at, changed_at)
        self.assertEqual(shell.file_system.entries["/new"].modified_at,
                         changed_at)
        self.assertIn("2026-10-09 12:30 motd",
                      execute_ok(shell, "ls -l /etc/motd"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
