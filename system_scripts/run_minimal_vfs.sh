#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd -- "$script_dir/.." && pwd)"
mkdir -p "$project_dir/logs"

set +e
python3 "$project_dir/main.py" \
  --vfs "$project_dir/vfs/not-loaded-yet.xml" \
  --log "$project_dir/logs/minimal.csv" \
  --script "$project_dir/startup_scripts/stage2_commands.txt" \
  > "$project_dir/logs/minimal-stage2-output.txt"
status=$?
set -e

[[ $status -eq 1 ]]
grep -q "Параметры запуска:" "$project_dir/logs/minimal-stage2-output.txt"
grep -q "Стартовый скрипт:" "$project_dir/logs/minimal-stage2-output.txt"
echo "Все три параметра проверены вторым системным сценарием"
