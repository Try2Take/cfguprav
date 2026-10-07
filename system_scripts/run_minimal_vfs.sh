#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd -- "$script_dir/.." && pwd)"
mkdir -p "$project_dir/logs"

printf 'ls\nexit\n' | python3 "$project_dir/main.py" \
  --vfs "$project_dir/vfs/minimal.xml" \
  --log "$project_dir/logs/minimal.csv"
