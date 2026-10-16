"""Stage 3: XML VFS loading and error reporting."""

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


PROJECT_DIR = Path(__file__).resolve().parents[1]


class VfsTests(unittest.TestCase):
    def test_nested_text_and_binary_are_loaded_without_changing_xml(self):
        sys.path.insert(0, str(PROJECT_DIR))
        try:
            from src.shell_emulator.vfs import VirtualFileSystem
        except ImportError:
            self.fail("VFS loader is unavailable")
        source = PROJECT_DIR / "vfs" / "sample.xml"
        before = hashlib.sha256(source.read_bytes()).digest()
        file_system = VirtualFileSystem.load(source)
        self.assertEqual(file_system.name, "study-vfs")
        deep = VirtualFileSystem.load(PROJECT_DIR / "vfs" / "deep.xml")
        self.assertIn("/level1/level2/level3/deep.txt", deep.entries)
        self.assertEqual(file_system.entries["/home/student/documents/data.bin"].content,
                         bytes([0, 1, 2, 3, 255]))
        self.assertIn(b"alpha beta", file_system.entries[
            "/home/student/documents/notes.txt"].content)
        self.assertEqual(hashlib.sha256(source.read_bytes()).digest(), before)

    def test_cli_uses_xml_name_and_rejects_malformed_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log = str(Path(temp_dir) / "log.csv")
            valid = subprocess.run(
                [sys.executable, str(PROJECT_DIR / "main.py"), "--vfs",
                 str(PROJECT_DIR / "vfs" / "minimal.xml"), "--log", log],
                input="exit\n", text=True, capture_output=True, check=False,
            )
            malformed = Path(temp_dir) / "broken.xml"
            malformed.write_text("<vfs>", encoding="utf-8")
            invalid = subprocess.run(
                [sys.executable, str(PROJECT_DIR / "main.py"), "--vfs",
                 str(malformed), "--log", log],
                input="exit\n", text=True, capture_output=True, check=False,
            )
        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertIn("minimal-vfs:/$", valid.stdout)
        self.assertEqual(invalid.returncode, 2)
        self.assertIn("Ошибка загрузки VFS", invalid.stderr)
        self.assertNotIn("Traceback", invalid.stderr)


if __name__ == "__main__":
    unittest.main()
