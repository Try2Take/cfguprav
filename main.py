"""Stage 2: configure the emulator, log commands, and run scripts."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from src.shell_emulator.emulator import ShellEmulator


def parse_options() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Оболочка, вариант 32")
    parser.add_argument("--vfs", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--script", type=Path)
    options = parser.parse_args()
    options.vfs = options.vfs.expanduser().resolve()
    options.log = options.log.expanduser().resolve()
    if options.script is not None:
        options.script = options.script.expanduser().resolve()
    return options


def show_options(options: argparse.Namespace) -> None:
    print("Параметры запуска:")
    print(f"  VFS: {options.vfs}")
    print(f"  Лог: {options.log}")
    print(f"  Стартовый скрипт: {options.script or 'не задан'}", flush=True)


def run_shell(options: argparse.Namespace) -> int:
    """Runs the script and REPL without loading the configured VFS yet."""
    options.log.parent.mkdir(parents=True, exist_ok=True)
    with options.log.open("a", encoding="utf-8", newline="",
                          buffering=1) as stream:
        writer = csv.writer(stream)
        if stream.tell() == 0:
            writer.writerow(("timestamp", "command", "arguments", "error"))
        shell = ShellEmulator("study-vfs", writer)
        if options.script is not None:
            shell.run(options.script.read_text(encoding="utf-8").splitlines())
        if shell.running:
            shell.run()
    return shell.error_count


def main() -> int:
    options = parse_options()
    show_options(options)
    try:
        error_count = run_shell(options)
    except (OSError, UnicodeError) as error:
        print(f"Ошибка: {error}", file=sys.stderr, flush=True)
        print("Errors были во время исполнения", flush=True)
        return 2
    if error_count:
        print("Errors были во время исполнения", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
