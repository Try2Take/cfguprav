"""Режимы ls и размеры виртуальных файлов."""

from datetime import datetime
from itertools import permutations
import unittest

from test_emulator import execute_error, execute_ok, make_shell
from shell_emulator.vfs import File


class LsTests(unittest.TestCase):
    def setUp(self):
        self.shell = make_shell()
        entries = self.shell.file_system.entries
        entries["/home/student/.secret"] = File(b"hidden")
        entries["/home/student/.cache"] = None
        entries["/home/student/large.bin"] = File(b"x" * 1536)
        entries["/-odd"] = File(b"hello")
        entries["/home/student/large.bin"].modified_at = datetime(
            2026, 10, 9, 12, 30,
        ).timestamp()

    def test_default_hides_dot_entries(self):
        output = execute_ok(self.shell, "ls /home/student")
        self.assertEqual(output, "documents/\nlarge.bin\nwelcome.txt")

    def test_all_shows_hidden_entries_and_parent(self):
        output = execute_ok(self.shell, "ls -a /home/student")
        self.assertEqual(output, (
            "./\n../\n.cache/\n.secret\ndocuments/\nlarge.bin\nwelcome.txt"
        ))
        self.assertEqual(execute_ok(self.shell, "ls -a /etc"),
                         "./\n../\nmotd")

    def test_long_output_shows_type_bytes_time_and_name(self):
        output = execute_ok(self.shell, "ls -l /home/student/large.bin")
        self.assertEqual(output, "- 1536 2026-10-09 12:30 large.bin")
        directory = execute_ok(self.shell, "ls -l /home")
        self.assertRegex(directory, r"^d 0 \d{4}-\d{2}-\d{2} .* student/$")

    def test_human_size_boundaries(self):
        cases = [(0, "0"), (1023, "1023"), (1024, "1.0K"),
                 (1536, "1.5K"), (1048576, "1.0M")]
        for size, expected in cases:
            with self.subTest(size=size):
                self.shell.file_system.entries["/sized"] = File(b"x" * size)
                output = execute_ok(self.shell, "ls -lh /sized")
                self.assertEqual(output.split()[1], expected)

    def test_every_flag_combination_and_order(self):
        flags = ["".join(order) for count in (1, 2, 3)
                 for order in permutations("lah", count)]
        for combination in flags:
            with self.subTest(flags=combination):
                combined = f"ls -{combination} /home/student"
                separate = "ls " + " ".join(f"-{flag}" for flag in combination)
                output = execute_ok(self.shell, combined)
                self.assertEqual(output, execute_ok(
                    self.shell, separate + " /home/student",
                ))
                names = [line.split()[-1] for line in output.splitlines()]
                self.assertEqual(".secret" in names, "a" in combination)
                self.assertEqual("./" in names, "a" in combination)
                large = next(line for line in output.splitlines()
                             if line.endswith("large.bin"))
                if "l" in combination:
                    size = "1.5K" if "h" in combination else "1536"
                    self.assertEqual(large.split()[:2], ["-", size])
                else:
                    self.assertEqual(large, "large.bin")

    def test_h_without_l_keeps_the_name_listing(self):
        self.assertEqual(execute_ok(self.shell, "ls -h /home/student"),
                         "documents/\nlarge.bin\nwelcome.txt")

    def test_explicit_hidden_file_is_shown_without_a(self):
        self.assertEqual(execute_ok(self.shell, "ls /home/student/.secret"),
                         ".secret")

    def test_double_dash_accepts_a_name_starting_with_dash(self):
        self.assertEqual(execute_ok(self.shell, "ls -- -odd"), "-odd")

    def test_invalid_flag_and_extra_paths_are_errors(self):
        self.assertIn("неизвестный ключ", execute_error(self.shell, "ls -z"))
        self.assertIn("не более одного", execute_error(self.shell, "ls -l a b"))
        self.assertIn("нет такого", execute_error(self.shell, "ls -lah /none"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
