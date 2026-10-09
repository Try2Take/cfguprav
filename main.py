"""Запуск эмулятора с параметрами VFS, журнала и стартового скрипта."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from src.shell_emulator.emulator import ShellEmulator
from src.shell_emulator.vfs import VFSLoadError, VirtualFileSystem


def parse_options() -> argparse.Namespace:
    """Читает параметры запуска и преобразует пути в абсолютные."""
    parser = argparse.ArgumentParser(description="Оболочка, вариант 32")
    parser.add_argument("--vfs", type=Path, required=True,
                        help="путь к XML-файлу VFS")
    parser.add_argument("--log", type=Path, required=True,
                        help="путь к CSV-журналу")
    parser.add_argument("--script", type=Path,
                        help="путь к стартовому скрипту")
    options = parser.parse_args()
    options.vfs = options.vfs.expanduser().resolve()
    options.log = options.log.expanduser().resolve()
    if options.script is not None:
        options.script = options.script.expanduser().resolve()
    return options


def show_options(options: argparse.Namespace) -> None:
    """Показывает параметры перед началом диалога."""
    print("Параметры запуска:")
    print(f"  VFS: {options.vfs}")
    print(f"  Лог: {options.log}")
    print(f"  Стартовый скрипт: {options.script or 'не задан'}", flush=True)


def run_shell(options: argparse.Namespace) -> int:
    """Открывает журнал и выполняет скрипт, затем интерактивный ввод."""
    file_system = VirtualFileSystem.load(options.vfs)
    options.log.parent.mkdir(parents=True, exist_ok=True)
    with options.log.open("a", encoding="utf-8", newline="",
                          buffering=1) as log_file:
        log_writer = csv.writer(log_file)
        if log_file.tell() == 0:
            log_writer.writerow(
                ("timestamp", "command", "arguments", "error"),
            )
        shell = ShellEmulator(file_system, log_writer)
        if options.script is not None:
            commands = options.script.read_text(encoding="utf-8").splitlines()
            shell.run(commands)
        if shell.running:
            shell.run()
    return shell.error_count


def main() -> int:
    """Завершает программу с итогом ошибок и подходящим кодом возврата."""
    options = parse_options()
    show_options(options)
    error_count = 1
    status = 2

    try:
        error_count = run_shell(options)
        status = 1 if error_count else 0
    except VFSLoadError as error:
        print(f"Ошибка загрузки VFS: {error}", file=sys.stderr, flush=True)
    except (OSError, UnicodeError) as error:
        print(f"Ошибка: {error}", file=sys.stderr, flush=True)
    if error_count:
        print("Errors были во время исполнения", flush=True)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
