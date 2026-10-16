"""Итог ошибок при запуске из командной строки."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


PROJECT_DIR = Path(__file__).resolve().parents[1]
SUMMARY = "Errors были во время исполнения"


class CliErrorTests(unittest.TestCase):
    def run_cli(self, commands="exit\n", script=None, invalid_vfs=False,
                vfs_text=None):
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            vfs_path = PROJECT_DIR / "vfs" / "sample.xml"
            if invalid_vfs:
                vfs_text = "<vfs>"
            if vfs_text is not None:
                vfs_path = directory / "broken.xml"
                vfs_path.write_text(vfs_text, encoding="utf-8")
            arguments = [
                sys.executable, str(PROJECT_DIR / "main.py"),
                "--vfs", str(vfs_path),
                "--log", str(directory / "commands.csv"),
            ]
            if script is not None:
                script_path = directory / "start.txt"
                script_path.write_text(script, encoding="utf-8")
                arguments.extend(["--script", str(script_path)])
            return subprocess.run(
                arguments, input=commands, text=True, encoding="utf-8",
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=10, check=False,
            )

    def test_success_ends_without_error_summary(self):
        result = self.run_cli("ls /etc\nexit\n")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn(SUMMARY, result.stdout)

    def test_interactive_errors_are_reported_once_at_the_end(self):
        result = self.run_cli("cd /missing\nls /absent\nls /etc\nexit\n")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertEqual(result.stdout.count(SUMMARY), 1)
        self.assertTrue(result.stdout.rstrip().endswith(SUMMARY))

    def test_script_errors_are_kept_after_successful_interactive_input(self):
        result = self.run_cli("ls /etc\nexit\n", "cd /missing\n")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertEqual(result.stdout.count(SUMMARY), 1)
        self.assertTrue(result.stdout.rstrip().endswith(SUMMARY))

    def test_invalid_vfs_has_error_summary(self):
        result = self.run_cli(invalid_vfs=True)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("Ошибка загрузки VFS", result.stdout)
        self.assertEqual(result.stdout.count(SUMMARY), 1)

    def test_unsupported_xml_encoding_has_error_summary(self):
        for encoding in ("unknown", "UTF-32"):
            with self.subTest(encoding=encoding):
                xml_text = (
                    f'<?xml version="1.0" encoding="{encoding}"?>'
                    '<vfs name="test"/>'
                )
                result = self.run_cli(vfs_text=xml_text)
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertEqual(result.stdout.count(SUMMARY), 1)
                self.assertNotIn("Traceback", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
