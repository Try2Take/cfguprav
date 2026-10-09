"""Запускает модульные тесты и выводит число ошибок и провалов."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest


def main() -> int:
    """Находит тесты в этой папке и возвращает код результата проверки."""
    tests_directory = Path(__file__).resolve().parent
    suite = unittest.defaultTestLoader.discover(
        str(tests_directory),
        pattern="test_*.py",
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(
        f"\nИтог: {result.testsRun} тестов, "
        f"ошибок: {len(result.errors)}, "
        f"провалов: {len(result.failures)}."
    )
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
