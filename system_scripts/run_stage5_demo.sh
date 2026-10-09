#!/usr/bin/env bash
set -eu

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd -- "$script_dir/.." && pwd)"
vfs_file="$project_dir/vfs/sample.xml"
mkdir -p "$project_dir/logs"

vfs_hash() {
  python3 - "$vfs_file" <<'PY'
import hashlib
from pathlib import Path
import sys

print(hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest())
PY
}

before_hash="$(vfs_hash)"
if python3 "$project_dir/main.py" \
  --vfs "$vfs_file" \
  --log "$project_dir/logs/stage5.csv" \
  --script "$project_dir/startup_scripts/stage5_commands.txt"; then
  echo "ОШИБКА: отрицательные случаи touch не отражены в коде возврата" >&2
  exit 1
else
  status=$?
  [[ $status -eq 1 ]] || exit "$status"
fi
after_hash="$(vfs_hash)"

if [[ "$before_hash" != "$after_hash" ]]; then
  echo "ОШИБКА: исходный XML-файл был изменен" >&2
  exit 1
fi

echo "touch проверен; исходный XML не изменился"
