"""Сценарий touch работает без Linux-утилиты sha256sum."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


PROJECT_DIR = Path(__file__).resolve().parents[1]


class SystemScriptTests(unittest.TestCase):
    def test_stage5_uses_only_portable_hash_check(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tools_dir = Path(temp_dir)
            for name in ("bash", "dirname", "mkdir"):
                (tools_dir / name).symlink_to(shutil.which(name))
            (tools_dir / "python3").symlink_to(sys.executable)
            environment = os.environ.copy()
            environment["PATH"] = str(tools_dir)
            result = subprocess.run(
                [str(tools_dir / "bash"), str(
                    PROJECT_DIR / "system_scripts" / "run_stage5_demo.sh",
                )],
                env=environment, text=True, encoding="utf-8",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=10, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertIn("исходный XML не изменился", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
