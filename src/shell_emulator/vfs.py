"""Stage 3: load an XML virtual filesystem into memory."""

from __future__ import annotations

import base64
import posixpath
import xml.etree.ElementTree as xml_etree
from dataclasses import dataclass
from pathlib import Path


class CommandError(Exception):
    """Invalid VFS node or command."""


class VFSLoadError(Exception):
    """The source XML cannot be loaded."""


def validate_name(name: str) -> None:
    if not name or name in {".", ".."} or "/" in name or "\x00" in name:
        raise CommandError(f"недопустимое имя узла VFS: {name!r}")


@dataclass
class File:
    content: bytes = b""
    binary: bool = False


@dataclass
class VirtualFileSystem:
    name: str
    entries: dict[str, File | None]

    @classmethod
    def load(cls, path: str | Path) -> "VirtualFileSystem":
        try:
            xml_root = xml_etree.parse(path).getroot()
            if xml_root.tag != "vfs":
                raise CommandError("корневой элемент должен называться <vfs>")
            name = (xml_root.get("name") or Path(path).stem).strip()
            if not name:
                raise CommandError("имя VFS не может быть пустым")
            file_system = cls(name, {"/": None})
            file_system._load_children(xml_root, "/")
            return file_system
        except (OSError, xml_etree.ParseError, CommandError, LookupError,
                ValueError) as error:
            raise VFSLoadError(f"не удалось загрузить VFS {path}: {error}")

    def _load_children(self, xml_node: xml_etree.Element,
                       parent_path: str) -> None:
        for child in xml_node:
            name = child.get("name", "").strip()
            validate_name(name)
            node_path = posixpath.join(parent_path, name)
            if node_path in self.entries:
                raise CommandError(f"повторяющееся имя в каталоге: {name}")
            if child.tag == "directory":
                self.entries[node_path] = None
                self._load_children(child, node_path)
            elif child.tag == "file":
                self.entries[node_path] = self._load_file(child)
            else:
                raise CommandError(f"неизвестный элемент VFS: <{child.tag}>")

    @staticmethod
    def _load_file(xml_node: xml_etree.Element) -> File:
        if len(xml_node):
            raise CommandError("файл содержит вложенные элементы")
        encoding = xml_node.get("encoding", "text")
        text = xml_node.text or ""
        if encoding == "text":
            return File(text.encode("utf-8"))
        if encoding == "base64":
            try:
                data = base64.b64decode("".join(text.split()), validate=True)
                return File(data, binary=True)
            except ValueError:
                raise CommandError("неверные данные base64 в файле")
        raise CommandError(f"неизвестная кодировка файла: {encoding}")
