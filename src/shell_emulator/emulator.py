"""The stage 1 REPL, with placeholder commands."""

import os
import shlex


class ShellEmulator:
    def __init__(self, vfs_name: str) -> None:
        self.vfs_name = vfs_name
        self.running = True

    def prompt(self) -> str:
        return f"{self.vfs_name}:/$ "

    def execute_line(self, line: str) -> None:
        try:
            parts = shlex.split(os.path.expandvars(line))
        except ValueError as error:
            print(f"Ошибка синтаксиса: {error}")
            return
        if not parts:
            return

        command, *arguments = parts
        if command == "exit":
            if arguments:
                print("Ошибка: exit не принимает аргументы")
            else:
                self.running = False
        elif command in {"ls", "cd"}:
            print(f"{command}: {' '.join(arguments)}")
        else:
            print(f"Ошибка: неизвестная команда: {command}")

    def run(self) -> None:
        while self.running:
            try:
                line = input(self.prompt())
            except (EOFError, KeyboardInterrupt):
                print()
                break
            self.execute_line(line)
