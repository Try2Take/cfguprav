"""Stage 2 REPL, command stubs, script playback, and CSV events."""

from __future__ import annotations

import os
import shlex
from datetime import datetime


class ShellEmulator:
    def __init__(self, file_system, log_writer) -> None:
        self.file_system = file_system
        self.log_writer = log_writer
        self.running = True
        self.error_count = 0

    def prompt(self) -> str:
        return f"{self.file_system.name}:/$ "

    def execute_line(self, line: str) -> str:
        name, arguments = "<parse>", [line]
        error = ""
        try:
            parts = shlex.split(os.path.expandvars(line), comments=True)
            if not parts:
                return ""
            name, *arguments = parts
            if name == "exit":
                if arguments:
                    error = "exit: команда не принимает аргументы"
                else:
                    self.running = False
            elif name in {"ls", "cd"}:
                print(f"{name}: {' '.join(arguments)}")
            else:
                error = f"неизвестная команда: {name}"
        except ValueError as exc:
            error = f"ошибка синтаксиса: {exc}"
        if error:
            self.error_count += 1
        self.log_writer.writerow((datetime.now().astimezone().isoformat(timespec="seconds"),
                                  name, shlex.join(arguments), error))
        return error

    def run(self, lines: list[str] | None = None) -> int:
        previous_errors = self.error_count
        script_lines = iter(enumerate(lines, 1)) if lines is not None else None
        while self.running:
            try:
                if script_lines is None:
                    line_number, line = None, input(self.prompt())
                else:
                    line_number, line = next(script_lines)
            except (StopIteration, EOFError, KeyboardInterrupt):
                if script_lines is None:
                    print()
                break
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if script_lines is not None:
                print(f"{self.prompt()}{line}")
            error = self.execute_line(line)
            if error:
                location = f" в строке {line_number}" if line_number else ""
                print(f"Ошибка{location}: {error}")
        return self.error_count - previous_errors
