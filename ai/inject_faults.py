"""Fault injection for the AI anomaly-detection pipeline (RQ2).

Runs inside a privileged sidecar container:

    docker rm -f fault-injector
    docker run -d --name fault-injector --pid=host --network=host \\
        --cap-add=NET_ADMIN --cap-add=SYS_RESOURCE \\
        -v /path/to/repo/ai:/ai:ro \\
        -v /path/to/repo/data:/data \\
        debian:12 bash -c "
            apt-get update &&
            apt-get install -y stress-ng iproute2 python3 &&
            python3 /ai/inject_faults.py >> /data/inject_faults.log 2>&1"

40 episodes with shorter gaps (~6-8 hours total) to fit the deadline.
Writes ground-truth labels to /data/fault_labels.csv.
"""
import csv
import datetime as dt
import os
import random
import subprocess
import sys
import tempfile
import threading
import time

EPISODES = 40
MIN_GAP = 300    # 5 min minimum between episodes
MAX_GAP = 600    # 10 min maximum
DUR_MIN = 120    # 2 min minimum fault duration
DUR_MAX = 240    # 4 min maximum
IFACE = "eth0"


def stress_cpu(duration):
    """Stress CPU using 2 workers at 80% load — reliable in WSL2."""
    subprocess.run(
        ["stress-ng", "--cpu", "2", "--cpu-load", "80", "--timeout", f"{duration}s"],
        check=False
    )


def stress_memory(duration):
    """Stress memory by allocating a large array in Python."""
    size_mb = 512
    print(f"  memory stress: allocating {size_mb}MB for {duration}s", flush=True)
    end = time.time() + duration
    data = bytearray(size_mb * 1024 * 1024)
    # Touch pages to ensure they're actually allocated
    for i in range(0, len(data), 4096):
        data[i] = 1
    remaining = end - time.time()
    if remaining > 0:
        time.sleep(remaining)
    del data


def stress_io(duration):
    """Stress I/O by repeatedly writing and reading a temp file."""
    print(f"  io stress: write/read loop for {duration}s", flush=True)
    end = time.time() + duration
    tmp = tempfile.mktemp(prefix="stress_io_", dir="/tmp")
    chunk = b"0" * (1024 * 1024)  # 1 MB
    try:
        while time.time() < end:
            with open(tmp, "wb") as f:
                for _ in range(200):  # 200 MB
                    f.write(chunk)
                    if time.time() >= end:
                        break
            if os.path.exists(tmp):
                os.unlink(tmp)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def net_loss(on):
    """Apply or remove 20% packet loss via tc netem."""
    if on:
        r = subprocess.run(
            ["tc", "qdisc", "add", "dev", IFACE, "root", "netem", "loss", "20%"],
            capture_output=True
        )
        if r.returncode != 0:
            print(f"  tc add warning: {r.stderr.decode().strip()}", flush=True)
    else:
        subprocess.run(
            ["tc", "qdisc", "del", "dev", IFACE, "root", "netem"],
            capture_output=True
        )


FAULT_RUNNERS = {
    "cpu": stress_cpu,
    "memory": stress_memory,
    "io": stress_io,
    "network": None,  # handled separately
}


def run_fault(ftype, duration):
    if ftype == "network":
        net_loss(True)
        time.sleep(duration)
        net_loss(False)
    else:
        FAULT_RUNNERS[ftype](duration)


def main():
    out_path = "/data/fault_labels.csv"
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["start_utc", "end_utc", "type", "duration_s"])

        for i in range(EPISODES):
            gap = random.randint(MIN_GAP, MAX_GAP)
            print(f"[{i + 1}/{EPISODES}] sleeping {gap}s before next fault...", flush=True)
            time.sleep(gap)

            ftype = random.choice(list(FAULT_RUNNERS.keys()))
            dur = random.randint(DUR_MIN, DUR_MAX)
            start = dt.datetime.utcnow().isoformat()
            print(f"[{i + 1}/{EPISODES}] START {ftype} fault for {dur}s", flush=True)

            run_fault(ftype, dur)

            end = dt.datetime.utcnow().isoformat()
            actual = (dt.datetime.fromisoformat(end) - dt.datetime.fromisoformat(start)).seconds
            print(f"[{i + 1}/{EPISODES}] END   {ftype} actual={actual}s", flush=True)

            w.writerow([start, end, ftype, actual])
            f.flush()

    print("All episodes complete.", flush=True)


if __name__ == "__main__":
    main()
