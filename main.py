"""Stage 1: launch the interactive shell emulator."""

from src.shell_emulator.emulator import ShellEmulator


def main() -> int:
    shell = ShellEmulator("study-vfs")
    shell.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
