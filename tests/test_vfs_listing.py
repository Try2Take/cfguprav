"""Чтение каталогов и сведений об узлах VFS."""

import unittest

from test_emulator import make_shell
from shell_emulator.vfs import File


class VfsListingTests(unittest.TestCase):
    def setUp(self):
        self.file_system = make_shell().file_system
        self.file_system.entries["/.secret"] = File(b"hidden")

    def test_listing_selects_only_visible_direct_children(self):
        self.assertTrue(hasattr(self.file_system, "list_directory"))
        entries = self.file_system.list_directory("/")
        self.assertEqual(entries, [("etc", "/etc"), ("home", "/home")])

    def test_all_listing_includes_hidden_and_parent_entries(self):
        self.assertTrue(hasattr(self.file_system, "list_directory"))
        entries = self.file_system.list_directory("/", include_hidden=True)
        self.assertEqual(entries, [
            (".", "/"), ("..", "/"), (".secret", "/.secret"),
            ("etc", "/etc"), ("home", "/home"),
        ])
        children = self.file_system.list_directory(
            "/home/student", include_hidden=True,
        )
        self.assertEqual(children[:2], [
            (".", "/home/student"), ("..", "/home"),
        ])

    def test_metadata_uses_byte_size_and_file_modification_time(self):
        file = File("привет".encode("utf-8"))
        file.modified_at = 123.0
        self.file_system.entries["/message"] = file
        self.assertTrue(hasattr(self.file_system, "metadata"))
        self.assertEqual(self.file_system.metadata("/message"),
                         ("-", 12, 123.0))
        kind, size, modified_at = self.file_system.metadata("/home")
        self.assertEqual((kind, size), ("d", 0))
        self.assertGreater(modified_at, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
