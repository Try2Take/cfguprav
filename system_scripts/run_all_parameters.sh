#!/usr/bin/env bash
set -u

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd -- "$script_dir/.." && pwd)"
log_dir="$project_dir/logs"
mkdir -p "$log_dir"

if EMU_TARGET="/home/student/documents" \
  python3 "$project_dir/main.py" \
    --vfs "$project_dir/vfs/sample.xml" \
    --log "$log_dir/all-parameters.csv" \
    --script "$project_dir/startup_scripts/stage2_commands.txt"; then
  echo "ОШИБКА: сценарий с неизвестной командой должен завершаться кодом 1" >&2
  exit 1
else
  status=$?
  if [[ $status -ne 1 ]]; then
    echo "ОШИБКА: ожидался код 1, получен $status" >&2
    exit 1
  fi
fi

echo "Все параметры переданы, ошибка команды отражена в выводе и CSV-журнале"
