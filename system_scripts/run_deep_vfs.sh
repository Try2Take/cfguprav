#!/usr/bin/env bash
set -eu

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd -- "$script_dir/.." && pwd)"
mkdir -p "$project_dir/logs"

if python3 "$project_dir/main.py" \
  --vfs "$project_dir/vfs/deep.xml" \
  --log "$project_dir/logs/deep.csv" \
  --script "$project_dir/startup_scripts/stage3_commands.txt"; then
  echo "ОШИБКА: сценарий должен содержать зарегистрированную ошибку" >&2
  exit 1
else
  status=$?
  [[ $status -eq 1 ]] || exit "$status"
fi

if ! PYTHONPATH="$project_dir" python3 - "$project_dir/vfs/deep.xml" <<'PYCODE'
import sys
from src.shell_emulator.vfs import VirtualFileSystem

file_system = VirtualFileSystem.load(sys.argv[1])
assert "/level1/level2/level3/deep.txt" in file_system.entries
PYCODE
then
  echo "ОШИБКА: в глубокой VFS нет файла третьего уровня" >&2
  exit 1
fi

echo "Трехуровневая VFS загружена, ошибка сценария обработана"
