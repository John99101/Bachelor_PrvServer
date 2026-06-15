#!/usr/bin/env bash
# Runs HTTP + fio benchmarks N times (decision C4: default 5 trials) for one
# architecture variant and writes data/<variant>_bench.csv.
#
# Usage: run_variant.sh <variant> [n_trials] [http_url]
#   variant   e.g. bare-metal | proxmox-vm | containerised
#   n_trials  default 5
#   http_url  default http://localhost:8096/health (Jellyfin)
set -euo pipefail

VARIANT="$1"
N="${2:-5}"
URL="${3:-http://localhost:8096/health}"
OUT="data/${VARIANT}_bench.csv"
FIO_DIR="$(dirname "$0")/fio"

echo "trial,p50_ms,p95_ms,req_s,rand_read_iops,rand_write_iops,seq_read_iops,seq_write_iops" > "$OUT"

for i in $(seq 1 "$N"); do
    H=$(python3 "$(dirname "$0")/bench_http.py" "$URL")
    RR=$(fio --output-format=json "$FIO_DIR/randread.fio"  | jq '.jobs[0].read.iops')
    RW=$(fio --output-format=json "$FIO_DIR/randwrite.fio" | jq '.jobs[0].write.iops')
    SR=$(fio --output-format=json "$FIO_DIR/seqread.fio"   | jq '.jobs[0].read.iops')
    SW=$(fio --output-format=json "$FIO_DIR/seqwrite.fio"  | jq '.jobs[0].write.iops')

    p50=$(echo "$H" | jq .p50_ms)
    p95=$(echo "$H" | jq .p95_ms)
    rs=$(echo "$H" | jq .req_per_s)

    echo "$i,$p50,$p95,$rs,$RR,$RW,$SR,$SW" >> "$OUT"
    echo "[$i/$N] p50=${p50}ms p95=${p95}ms req/s=${rs} randread=${RR}iops randwrite=${RW}iops"
done

python3 - "$OUT" <<'EOF'
import sys
import pandas as pd
d = pd.read_csv(sys.argv[1])
print(d.describe().loc[["mean", "std"]])
EOF
