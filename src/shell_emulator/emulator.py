"""Команды оболочки и цикл чтения команд."""

from __future__ import annotations

import getpass
import os
import posixpath
import shlex
import time
from datetime import datetime
from getopt import GetoptError, getopt

from .vfs import CommandError, VirtualFileSystem


SIZE_BASE = 1024
SIZE_UNITS = ("", "K", "M", "G", "T", "P", "E")


class ShellEmulator:
    """Хранит текущий каталог, команды и состояние сессии."""

    def __init__(self, file_system: VirtualFileSystem, log_writer) -> None:
        """Начинает сессию в корне загруженной VFS."""
        self.file_system = file_system
        self.current_dir = "/"
        self.log_writer = log_writer
        self.running = True
        self.error_count = 0
        self.username = getpass.getuser()
        try:
            self.terminal = os.path.basename(os.ttyname(0))
        except OSError:
            self.terminal = "console"
        self.login_time = datetime.now().astimezone()
        self.commands = {
            "ls": self._command_ls,
            "cd": self._command_cd,
            "head": self._command_head,
            "wc": self._command_wc,
            "who": self._command_who,
            "touch": self._command_touch,
        }

    def prompt(self) -> str:
        """Возвращает приглашение с именем VFS и текущим каталогом."""
        return f"{self.file_system.name}:{self.current_dir}$ "

    def execute_line(self, line: str) -> str:
        """Выполняет команду, записывает результат в CSV и считает ошибки."""
        command_name = "<parse>"
        arguments = [line]
        output = ""
        error_message = ""

        try:
            expanded_line = os.path.expandvars(line)
            command_parts = shlex.split(expanded_line, comments=True)
            if not command_parts:
                return ""
            command_name = command_parts[0]
            arguments = command_parts[1:]

            output = self._dispatch_command(command_name, arguments)
        except CommandError as error:
            error_message = str(error)
        except ValueError as error:
            error_message = f"ошибка синтаксиса: {error}"

        if error_message:
            self.error_count += 1
        command_time = datetime.now().astimezone().isoformat(timespec="seconds")
        self.log_writer.writerow((command_time, command_name,
                                  shlex.join(arguments), error_message))
        if output:
            print(output)
        return error_message

    def _dispatch_command(self, command_name: str, arguments: list[str]) -> str:
        """Вызывает обработчик команды или завершает сессию по exit."""
        if command_name == "exit":
            if arguments:
                raise CommandError("exit: команда не принимает аргументы")
            self.running = False
            return ""
        if command_name not in self.commands:
            raise CommandError(f"неизвестная команда: {command_name}")
        return self.commands[command_name](arguments)

    def _command_ls(self, arguments: list[str]) -> str:
        """Показывает один файл или содержимое каталога с ключами l, a, h."""
        options, paths = self._parse_options("ls", arguments, "lah")
        if len(paths) > 1:
            raise CommandError("ls: ожидается не более одного пути")
        flags = {option[1] for option, _ in options}
        requested_path = paths[0] if paths else "."
        folder_path = self.file_system.resolve(requested_path, self.current_dir)
        if self.file_system.entries[folder_path] is None:
            names = self.file_system.list_directory(folder_path, "a" in flags)
        else:
            names = [(posixpath.basename(folder_path), folder_path)]
        return "\n".join(
            self._format_ls_entry(name, path, flags) for name, path in names
        )

    @staticmethod
    def _parse_options(command_name, arguments, allowed_flags):
        """Разбирает короткие ключи, их комбинации и разделитель --."""
        try:
            return getopt(arguments, allowed_flags)
        except GetoptError as error:
            raise CommandError(f"{command_name}: неизвестный ключ: {error.opt}")

    def _format_ls_entry(self, name: str, path: str, flags: set[str]) -> str:
        """Формирует обычную или подробную строку списка файлов."""
        kind, byte_count, modified_at = self.file_system.metadata(path)
        display_name = name + "/" if kind == "d" else name
        if "l" not in flags:
            return display_name
        size = self._human_size(byte_count) if "h" in flags else str(byte_count)
        modified_time = datetime.fromtimestamp(modified_at)
        date = modified_time.strftime("%Y-%m-%d %H:%M")
        return f"{kind} {size} {date} {display_name}"

    @staticmethod
    def _human_size(byte_count: int) -> str:
        """Сокращает размер в байтах, используя единицы по 1024 байта."""
        size = float(byte_count)
        for unit in SIZE_UNITS:
            if size < SIZE_BASE or unit == SIZE_UNITS[-1]:
                return f"{size:.1f}{unit}" if unit else str(byte_count)
            size /= SIZE_BASE
        return str(byte_count)

    def _command_cd(self, arguments: list[str]) -> str:
        """Меняет текущий каталог после проверки пути."""
        if len(arguments) != 1:
            raise CommandError("cd: ожидается ровно один путь")
        self.current_dir = self.file_system.resolve(
            arguments[0], self.current_dir, directory=True,
        )
        return ""

    def _command_head(self, arguments: list[str]) -> str:
        """Возвращает первые строки текстовых файлов."""
        line_count, file_paths = self._parse_head_arguments(arguments)
        output_parts = []

        for file_path in file_paths:
            full_path = self.file_system.resolve(
                file_path, self.current_dir, directory=False,
            )
            file = self.file_system.entries[full_path]
            if file.binary:
                raise CommandError(f"head: двоичный файл: {full_path}")

            file_lines = file.content.decode("utf-8").splitlines()
            file_output = "\n".join(file_lines[:line_count])
            if len(file_paths) > 1:
                heading = f"==> {full_path} <=="
                if file_output:
                    file_output = heading + "\n" + file_output
                else:
                    file_output = heading
            output_parts.append(file_output)
        return "\n\n".join(output_parts)

    @staticmethod
    def _parse_head_arguments(arguments: list[str]) -> tuple[int, list[str]]:
        """Разбирает число строк в формах -n N и -N, затем пути файлов."""
        line_count = 10
        index = 0

        while index < len(arguments):
            argument = arguments[index]
            if argument == "--":
                index += 1
                break
            if not argument.startswith("-") or argument == "-":
                break

            line_count, index = ShellEmulator._read_head_count(arguments, index)

        file_paths = arguments[index:]
        if not file_paths:
            raise CommandError("head: требуется имя хотя бы одного файла")
        return line_count, file_paths

    @staticmethod
    def _read_head_count(arguments: list[str], index: int) -> tuple[int, int]:
        """Читает один ключ head и проверяет неотрицательное число строк."""
        argument = arguments[index]
        if argument == "-n":
            index += 1
            count_text = arguments[index] if index < len(arguments) else ""
        elif argument[1:].isdigit():
            count_text = argument[1:]
        else:
            raise CommandError(f"head: неизвестный ключ: {argument}")
        try:
            line_count = int(count_text)
        except ValueError:
            raise CommandError(f"head: ожидалось число строк: {count_text}")
        if line_count < 0:
            raise CommandError(f"head: отрицательное число строк: {count_text}")
        return line_count, index + 1

    def _command_wc(self, arguments: list[str]) -> str:
        """Считает переводы строк, слова и байты; для файлов выводит итог."""
        options, file_paths = self._parse_options("wc", arguments, "lwc")
        if not file_paths:
            raise CommandError("wc: требуется имя хотя бы одного файла")

        selected_counts = list(dict.fromkeys(
            option[1] for option, _ in options
        ))
        selected_counts = selected_counts or ["l", "w", "c"]

        results = []
        total_counts = {"l": 0, "w": 0, "c": 0}
        for file_path in file_paths:
            full_path = self.file_system.resolve(
                file_path, self.current_dir, directory=False,
            )
            file = self.file_system.entries[full_path]
            file_counts = {
                "l": file.content.count(b"\n"),
                "w": len(file.content.split()),
                "c": len(file.content),
            }
            for count_name in total_counts:
                total_counts[count_name] += file_counts[count_name]
            results.append((file_counts, full_path))

        if len(file_paths) > 1:
            results.append((total_counts, "итого"))

        return "\n".join(
            self._format_wc_result(counts, name, selected_counts)
            for counts, name in results
        )

    @staticmethod
    def _format_wc_result(counts, file_name, selected_counts) -> str:
        """Выводит выбранные счётчики в порядке ключей пользователя."""
        numbers = [str(counts[count_name]) for count_name in selected_counts]
        return " ".join(numbers) + " " + file_name

    def _command_who(self, arguments: list[str]) -> str:
        """Показывает пользователя и время начала этой сессии эмулятора."""
        if arguments:
            raise CommandError("who: команда не принимает аргументы")
        session_start = self.login_time.strftime("%Y-%m-%d %H:%M")
        return f"{self.username} {self.terminal} {session_start}"

    def _command_touch(self, arguments: list[str]) -> str:
        """Обновляет время всех указанных файлов одним значением."""
        _, file_paths = self._parse_options("touch", arguments, "")
        if not file_paths:
            raise CommandError("touch: требуется имя хотя бы одного файла")
        modified_time = time.time()
        for file_path in file_paths:
            self.file_system.touch(file_path, self.current_dir, modified_time)
        return ""

    def run(self, lines: list[str] | None = None) -> int:
        """Читает команды до exit или конца ввода и возвращает число ошибок."""
        script_lines = iter(enumerate(lines, 1)) if lines is not None else None
        previous_errors = self.error_count

        while self.running:
            try:
                line_number, line = self._read_line(script_lines)
            except (StopIteration, EOFError, KeyboardInterrupt):
                if script_lines is None:
                    print()
                break

            self._run_line(line, line_number, script_lines is not None)
        return self.error_count - previous_errors

    def _read_line(self, script_lines) -> tuple[int, str]:
        """Читает строку скрипта с номером или запрашивает ввод пользователя."""
        if script_lines is not None:
            return next(script_lines)
        return 0, input(self.prompt())

    def _run_line(self, line: str, line_number: int, show_input: bool) -> None:
        """Пропускает комментарии и показывает результат одной строки."""
        line = line.strip()
        if not line or line.startswith("#"):
            return
        if show_input:
            print(f"{self.prompt()}{line}")
        error_message = self.execute_line(line)
        if error_message:
            location = f" в строке {line_number}" if line_number else ""
            print(f"Ошибка{location}: {error_message}")
