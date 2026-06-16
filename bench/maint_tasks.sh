#!/usr/bin/env bash
# Runs all 4 maintainability tasks (3 runs each) for a given variant and
# records wall-clock seconds to data/<variant>_maint.csv automatically.
#
# Usage (from repo root): bash bench/maint_tasks.sh <variant>
#   variant: containerised | bare-metal
set -euo pipefail

VARIANT="${1:-containerised}"
OUT="data/${VARIANT}_maint.csv"
COMPOSE="stack/docker-compose.yml"

echo "variant,task,run,seconds" > "$OUT"

timed() {
    local task="$1"
    local run="$2"
    local start end secs
    start=$(date +%s%N)
    shift 2
    "$@"
    end=$(date +%s%N)
    secs=$(awk "BEGIN {printf \"%.1f\", ($end - $start) / 1000000000}")
    echo "$VARIANT,$task,$run,$secs" >> "$OUT"
    echo "    -> ${secs}s recorded"
}

wait_healthy() {
    until curl -s http://localhost:8096/health 2>/dev/null | grep -q Healthy; do
        sleep 2
    done
}

wait_unhealthy() {
    local i=0
    while curl -s http://localhost:8096/health 2>/dev/null | grep -q Healthy; do
        sleep 1
        i=$((i+1))
        [ $i -gt 30 ] && break
    done
}

# ---- Task functions ----

task_update_container() {
    docker compose -f "$COMPOSE" pull
    docker compose -f "$COMPOSE" up -d
}

task_update_baremetal() {
    sudo apt-get update -qq
    sudo apt-get upgrade -y jellyfin -qq
    sudo systemctl restart jellyfin
    wait_healthy
}

task_fault_container() {
    sed -i 's/8096:8096/9096:8096/' "$COMPOSE"
    docker compose -f "$COMPOSE" up -d
    wait_unhealthy
    docker compose -f "$COMPOSE" ps
    grep '9096' "$COMPOSE"
    sed -i 's/9096:8096/8096:8096/' "$COMPOSE"
    docker compose -f "$COMPOSE" up -d
    wait_healthy
}

task_fault_baremetal() {
    sudo sed -i 's/<HttpServerPortNumber>8096/<HttpServerPortNumber>9096/' \
        /etc/jellyfin/network.xml 2>/dev/null || true
    sudo systemctl restart jellyfin
    wait_unhealthy
    sudo grep '9096' /etc/jellyfin/network.xml || true
    sudo sed -i 's/9096/8096/' /etc/jellyfin/network.xml 2>/dev/null || true
    sudo systemctl restart jellyfin
    wait_healthy
}

task_recovery_container() {
    docker compose -f "$COMPOSE" down
    docker compose -f "$COMPOSE" up -d
    wait_healthy
}

task_recovery_baremetal() {
    sudo systemctl stop jellyfin
    sudo systemctl start jellyfin
    wait_healthy
}

task_reinstall_container() {
    docker compose -f "$COMPOSE" down -v
    docker compose -f "$COMPOSE" up -d
    wait_healthy
}

task_reinstall_baremetal() {
    sudo apt-get purge -y jellyfin -qq
    sudo apt-get install -y jellyfin -qq
    sudo systemctl enable --now jellyfin
    wait_healthy
}

# ---- Run all tasks ----

for task in update fault_diagnosis recovery clean_reinstall; do
    for run in 1 2 3; do
        echo ">>> $task — run $run/3"
        case "${VARIANT}_${task}" in
            containerised_update)       timed "$task" "$run" task_update_container ;;
            bare-metal_update)          timed "$task" "$run" task_update_baremetal ;;
            containerised_fault_diagnosis) timed "$task" "$run" task_fault_container ;;
            bare-metal_fault_diagnosis) timed "$task" "$run" task_fault_baremetal ;;
            containerised_recovery)     timed "$task" "$run" task_recovery_container ;;
            bare-metal_recovery)        timed "$task" "$run" task_recovery_baremetal ;;
            containerised_clean_reinstall) timed "$task" "$run" task_reinstall_container ;;
            bare-metal_clean_reinstall) timed "$task" "$run" task_reinstall_baremetal ;;
        esac
    done
done

echo ""
echo "=== Results saved to $OUT ==="
python3 -c "
import pandas as pd
d = pd.read_csv('$OUT')
print(d.groupby('task')['seconds'].agg(['mean','std']).round(1))
"
