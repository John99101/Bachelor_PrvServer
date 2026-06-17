#!/usr/bin/env bash
# Configuration-controlled HTTP benchmark for RQ1.
#
# Removes the packaging/tuning confound of the main run by holding the Jellyfin
# version and configuration identical across variants:
#   1. bare-metal       systemd Jellyfin, vendor-default config
#   2. container-bridge same Jellyfin version, fresh default config, Docker bridge net
#   3. container-host    same version/config, Docker host networking
#
# (1) vs (2) = abstraction + bridge overhead with version/config controlled.
# (2) vs (3) = bridge networking overhead alone.
#
# Usage (from repo root, on Machine A): bash bench/controlled_http.sh [trials]
set -euo pipefail

N="${1:-5}"
URL="http://localhost:8096/health"
OUT="data/controlled_http.csv"
CLIENT="$(dirname "$0")/bench_http.py"

# Record the bare-metal Jellyfin version and derive a matching image tag.
BM_VER="$(jellyfin --version 2>/dev/null | head -1 || true)"
[ -z "$BM_VER" ] && BM_VER="$(dpkg-query -W -f='${Version}' jellyfin-server 2>/dev/null || echo unknown)"
TAG="$(printf '%s' "$BM_VER" | grep -oE '10\.[0-9]+\.[0-9]+' | head -1 || true)"
[ -z "$TAG" ] && TAG="10.9.6"
echo "bare-metal Jellyfin version: $BM_VER   ->   container image tag: jellyfin/jellyfin:$TAG"

echo "variant,jellyfin_version,config,trial,p50_ms,p95_ms,req_s" > "$OUT"

wait_healthy() { until curl -s "$URL" 2>/dev/null | grep -q Healthy; do sleep 2; done; }

run5() {
    local variant="$1" ver="$2"
    for i in $(seq 1 "$N"); do
        H="$(python3 "$CLIENT" "$URL" 2000)"
        p50="$(echo "$H" | jq .p50_ms)"; p95="$(echo "$H" | jq .p95_ms)"; rs="$(echo "$H" | jq .req_per_s)"
        echo "$variant,$ver,default,$i,$p50,$p95,$rs" >> "$OUT"
        echo "  [$variant $i/$N] p50=${p50}ms p95=${p95}ms req/s=${rs}"
    done
}

# Make sure nothing else holds port 8096.
docker rm -f jf_ctrl 2>/dev/null || true
sudo systemctl stop jellyfin 2>/dev/null || true

echo ">>> 1/3 bare-metal (systemd, default config)"
sudo systemctl start jellyfin
wait_healthy
run5 bare-metal "$BM_VER"
sudo systemctl stop jellyfin

echo ">>> 2/3 container, bridge networking (same version, fresh default config)"
docker volume rm jf_ctrl_cfg 2>/dev/null || true
docker run -d --name jf_ctrl -p 8096:8096 -v jf_ctrl_cfg:/config "jellyfin/jellyfin:$TAG" >/dev/null
wait_healthy
run5 container-bridge "$TAG"
docker rm -f jf_ctrl >/dev/null

echo ">>> 3/3 container, host networking (same version/config)"
docker run -d --name jf_ctrl --network host -v jf_ctrl_cfg:/config "jellyfin/jellyfin:$TAG" >/dev/null
wait_healthy
run5 container-host "$TAG"
docker rm -f jf_ctrl >/dev/null
docker volume rm jf_ctrl_cfg >/dev/null

echo ""
echo "=== Results saved to $OUT ==="
python3 -c "
import pandas as pd
d = pd.read_csv('$OUT')
print(d.groupby('variant')[['p50_ms','p95_ms','req_s']].agg(['mean','std']).round(2))
"
