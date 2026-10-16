#!/usr/bin/env bash
set -u

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd -- "$script_dir/.." && pwd)"
mkdir -p "$project_dir/logs"

if EMU_HOME="/home/student" \
  python3 "$project_dir/main.py" \
    --vfs "$project_dir/vfs/sample.xml" \
    --log "$project_dir/logs/stage4.csv" \
    --script "$project_dir/startup_scripts/stage4_commands.txt"; then
  echo "ОШИБКА: отрицательные случаи сценария не повлияли на код возврата" >&2
  exit 1
else
  status=$?
  [[ $status -eq 1 ]] || exit "$status"
fi

echo "Команды четвертого этапа и обработка ошибок проверены"
