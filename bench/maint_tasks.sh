#!/usr/bin/env bash
# Runs all 4 maintainability tasks (3 runs each) for a given variant and
# records wall-clock seconds to data/<variant>_maint.csv automatically.
#
# Usage: bash bench/maint_tasks.sh <variant>
#   variant: containerised | bare-metal
set -euo pipefail

VARIANT="${1:-containerised}"
OUT="data/${VARIANT}_maint.csv"
COMPOSE="stack/docker-compose.yml"

echo "variant,task,run,seconds" > "$OUT"

run_timed() {
    local task="$1"; shift
    for run in 1 2 3; do
        echo ">>> $task — run $run/3"
        local start end secs
        start=$(date +%s%N)
        "$@"
        end=$(date +%s%N)
        secs=$(awk "BEGIN {printf \"%.1f\", ($end - $start) / 1000000000}")
        echo "$VARIANT,$task,$run,$secs" >> "$OUT"
        echo "    recorded: ${secs}s"
    done
}

# ---- Task 1: routine update ----
if [ "$VARIANT" = "containerised" ]; then
    run_timed update bash -c "docker compose -f $COMPOSE pull -q && docker compose -f $COMPOSE up -d"
else
    run_timed update bash -c "sudo apt-get update -qq && sudo apt-get upgrade -y jellyfin -qq && sudo systemctl restart jellyfin"
fi

# ---- Task 2: fault diagnosis ----
# Introduce a deliberate misconfiguration, measure time until service confirmed broken + root cause found
if [ "$VARIANT" = "containerised" ]; then
    run_timed fault_diagnosis bash -c "
        # Break it: wrong port env var
        sed -i 's/8096:8096/9096:8096/' $COMPOSE
        docker compose -f $COMPOSE up -d -q
        # Diagnose: check health, inspect config, find the port mismatch
        until ! curl -s http://localhost:8096/health >/dev/null 2>&1; do sleep 1; done
        docker compose -f $COMPOSE ps
        grep '9096' $COMPOSE
        # Fix it
        sed -i 's/9096:8096/8096:8096/' $COMPOSE
        docker compose -f $COMPOSE up -d -q
        until curl -s http://localhost:8096/health | grep -q Healthy; do sleep 2; done
    "
else
    run_timed fault_diagnosis bash -c "
        sudo sed -i 's/8096/9096/' /etc/jellyfin/network.xml 2>/dev/null || true
        sudo systemctl restart jellyfin
        until ! curl -s http://localhost:8096/health >/dev/null 2>&1; do sleep 1; done
        sudo systemctl status jellyfin | grep -i port || true
        sudo grep '9096' /etc/jellyfin/network.xml
        sudo sed -i 's/9096/8096/' /etc/jellyfin/network.xml
        sudo systemctl restart jellyfin
        until curl -s http://localhost:8096/health | grep -q Healthy; do sleep 2; done
    "
fi

# ---- Task 3: recovery (restart from known-good state) ----
if [ "$VARIANT" = "containerised" ]; then
    run_timed recovery bash -c "
        docker compose -f $COMPOSE down -q
        docker compose -f $COMPOSE up -d -q
        until curl -s http://localhost:8096/health | grep -q Healthy; do sleep 2; done
    "
else
    run_timed recovery bash -c "
        sudo systemctl stop jellyfin
        sudo systemctl start jellyfin
        until curl -s http://localhost:8096/health | grep -q Healthy; do sleep 2; done
    "
fi

# ---- Task 4: clean reinstall ----
if [ "$VARIANT" = "containerised" ]; then
    run_timed clean_install bash -c "
        docker compose -f $COMPOSE down -v -q
        docker compose -f $COMPOSE up -d -q
        until curl -s http://localhost:8096/health | grep -q Healthy; do sleep 2; done
    "
else
    run_timed clean_install bash -c "
        sudo apt-get purge -y jellyfin -qq
        sudo apt-get install -y jellyfin -qq
        sudo systemctl enable --now jellyfin
        until curl -s http://localhost:8096/health | grep -q Healthy; do sleep 2; done
    "
fi

echo ""
echo "=== Results saved to $OUT ==="
python3 -c "
import pandas as pd
d = pd.read_csv('$OUT')
print(d.groupby('task')['seconds'].agg(['mean','std']).round(1))
"
