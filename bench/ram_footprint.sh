#!/usr/bin/env bash
# Captures RAM usage before and after a load run.
#
# Usage: ram_footprint.sh <variant> <load-command...>
#   e.g. ram_footprint.sh containerised python3 bench_http.py http://localhost:8096/health 2000
#
# Appends one row to data/<variant>_ram.csv: phase,used_kb
set -euo pipefail

VARIANT="$1"; shift
OUT="data/${VARIANT}_ram.csv"

if [ ! -f "$OUT" ]; then
    echo "phase,used_kb" > "$OUT"
fi

echo "idle,$(free -k | awk '/Mem:/{print $3}')" >> "$OUT"

"$@"

echo "loaded,$(free -k | awk '/Mem:/{print $3}')" >> "$OUT"
