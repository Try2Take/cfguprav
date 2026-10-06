#!/usr/bin/env python3

import argparse
import csv
import sys
from pathlib import Path

from src.shell_emulator.emulator import ShellEmulator
from src.shell_emulator.vfs import VFSLoadError, VirtualFileSystem


def main() -> int:
    parser = argparse.ArgumentParser(description="Оболочка, вариант 32")
    parser.add_argument("--vfs", type=Path, required=True,
                        help="путь к XML-файлу VFS")
    parser.add_argument("--log", type=Path, required=True,
                        help="путь к CSV-журналу")
    parser.add_argument("--script", type=Path,
                        help="путь к стартовому скрипту")
    options = parser.parse_args()

    vfs_path = options.vfs.expanduser().resolve()
    log_path = options.log.expanduser().resolve()
    script_path = None
    if options.script is not None:
        script_path = options.script.expanduser().resolve()

    print("Параметры запуска:")
    print(f"  VFS: {vfs_path}")
    print(f"  Лог: {log_path}")
    print(f"  Стартовый скрипт: {script_path or 'не задан'}")

    try:
        file_system = VirtualFileSystem.load(vfs_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8", newline="",
                           buffering=1) as log_file:
            log_writer = csv.writer(log_file)
            if log_file.tell() == 0:
                log_writer.writerow(("timestamp", "command", "arguments", "error"))

            shell = ShellEmulator(file_system, log_writer)
            script_errors = 0
            if script_path is not None:
                commands = script_path.read_text(encoding="utf-8").splitlines()
                script_errors = shell.run(commands)
            if shell.running:
                shell.run()

        return 1 if script_errors else 0
    except VFSLoadError as error:
        print(f"Ошибка загрузки VFS: {error}", file=sys.stderr)
    except (OSError, UnicodeError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
