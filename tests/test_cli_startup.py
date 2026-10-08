from pathlib import Path
import subprocess
import sys
import unittest


PROJECT_DIR = Path(__file__).resolve().parents[1]


class CliStartupTests(unittest.TestCase):
    def test_help_starts_without_loading_a_vfs(self):
        result = subprocess.run(
            [sys.executable, str(PROJECT_DIR / "main.py"), "--help"],
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("--vfs", result.stdout)
        self.assertIn("--log", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
