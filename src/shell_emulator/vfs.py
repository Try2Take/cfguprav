"""Загрузка XML и работа с виртуальными файлами в памяти."""

from __future__ import annotations

import base64
import posixpath
import time
import xml.etree.ElementTree as xml_etree
from dataclasses import dataclass, field
from pathlib import Path


class CommandError(Exception):
    """Ошибка команды или обращения к узлу VFS."""


class VFSLoadError(Exception):
    """Ошибка чтения или проверки исходного XML."""


def validate_name(name: str) -> None:
    """Отклоняет имена, которые нельзя использовать как отдельный узел."""
    if not name or name in {".", ".."} or "/" in name or "\x00" in name:
        raise CommandError(f"недопустимое имя узла VFS: {name!r}")


@dataclass
class File:
    """Содержимое файла и время его последнего изменения в памяти."""

    content: bytes = b""
    binary: bool = False
    modified_at: float = field(default_factory=time.time, init=False)


@dataclass
class VirtualFileSystem:
    """Хранит узлы по абсолютным путям; None обозначает каталог."""

    name: str
    entries: dict[str, File | None]
    loaded_at: float = field(default_factory=time.time, init=False)

    @classmethod
    def load(cls, path: str | Path) -> "VirtualFileSystem":
        """Читает XML, проверяет структуру и создаёт независимую VFS."""
        try:
            xml_root = xml_etree.parse(path).getroot()
            if xml_root.tag != "vfs":
                raise CommandError("корневой элемент должен называться <vfs>")

            vfs_name = (xml_root.get("name") or Path(path).stem).strip()
            if not vfs_name:
                raise CommandError("имя VFS не может быть пустым")

            file_system = cls(vfs_name, {"/": None})
            file_system._load_children(xml_root, "/")
            return file_system
        except (OSError, xml_etree.ParseError, CommandError) as error:
            raise VFSLoadError(f"не удалось загрузить VFS {path}: {error}")

    def _load_children(
        self, xml_node: xml_etree.Element, parent_path: str,
    ) -> None:
        """Рекурсивно загружает детей каталога без повторяющихся имён."""
        for child in xml_node:
            node_name = child.get("name", "").strip()
            validate_name(node_name)
            node_path = posixpath.join(parent_path, node_name)

            if node_path in self.entries:
                raise CommandError(f"повторяющееся имя в каталоге: {node_name}")
            if child.tag == "directory":
                self.entries[node_path] = None
                self._load_children(child, node_path)
            elif child.tag == "file":
                self.entries[node_path] = self._load_file(child)
            else:
                raise CommandError(f"неизвестный элемент VFS: <{child.tag}>")

    @staticmethod
    def _load_file(xml_node: xml_etree.Element) -> File:
        """Преобразует текст или base64 из XML в байты файла."""
        if len(xml_node):
            raise CommandError("файл содержит вложенные элементы")

        encoding = xml_node.get("encoding", "text")
        file_text = xml_node.text or ""
        if encoding == "text":
            return File(file_text.encode("utf-8"))
        if encoding == "base64":
            encoded_data = "".join(file_text.split())
            try:
                file_data = base64.b64decode(encoded_data, validate=True)
                return File(file_data, binary=True)
            except ValueError:
                raise CommandError("неверные данные base64 в файле")
        raise CommandError(f"неизвестная кодировка файла: {encoding}")

    def resolve(self, path: str, current_dir="/", directory=None) -> str:
        """Разрешает путь с . и .., проверяя каждый промежуточный каталог."""
        if path.startswith("/"):
            resolved_path = "/"
        else:
            resolved_path = current_dir

        for path_part in path.split("/"):
            if self.entries[resolved_path] is not None:
                raise CommandError(f"не является каталогом: {path}")
            if path_part == "..":
                resolved_path = posixpath.dirname(resolved_path)
            elif path_part not in {"", "."}:
                resolved_path = posixpath.join(resolved_path, path_part)
                if resolved_path not in self.entries:
                    raise CommandError(f"нет такого файла или каталога: {path}")

        path_is_directory = self.entries[resolved_path] is None
        if directory is not None and path_is_directory != directory:
            if directory:
                raise CommandError(f"не является каталогом: {path}")
            raise CommandError(f"является каталогом: {path}")
        return resolved_path

    def list_directory(
        self, path: str, include_hidden: bool = False,
    ) -> list[tuple[str, str]]:
        """Возвращает имена и пути непосредственных детей каталога."""
        folder_path = self.resolve(path, directory=True)
        names = []
        if include_hidden:
            names.extend([
                (".", folder_path),
                ("..", posixpath.dirname(folder_path)),
            ])
        for entry_path in sorted(self.entries):
            if entry_path == folder_path:
                continue
            if posixpath.dirname(entry_path) != folder_path:
                continue
            entry_name = posixpath.basename(entry_path)
            if include_hidden or not entry_name.startswith("."):
                names.append((entry_name, entry_path))
        return names

    def metadata(self, path: str) -> tuple[str, int, float]:
        """Возвращает тип, размер в байтах и время изменения узла."""
        full_path = self.resolve(path)
        file = self.entries[full_path]
        if file is None:
            return "d", 0, self.loaded_at
        return "-", len(file.content), file.modified_at
