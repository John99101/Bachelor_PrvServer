"""Fault injection for the AI anomaly-detection pipeline (RQ2).

Runs inside a privileged sidecar container with stress-ng and iproute2
installed, e.g.:

    docker run --rm -it --pid=host --network=host --cap-add=NET_ADMIN \\
        -v "$(pwd)/data:/data" debian:12 bash
    apt-get update && apt-get install -y stress-ng iproute2 python3
    python3 inject_faults.py

Schedules randomised fault episodes (CPU, memory, I/O, network loss) over the
collection window and writes ground-truth labels to data/fault_labels.csv.

Decision: 60 episodes (down from the draft's 200) to fit a 4-5 day window.
"""
import csv
import datetime as dt
import random
import subprocess
import time

EPISODES = 60
MIN_GAP, MAX_GAP = 600, 1800  # seconds between episodes
DUR_MIN, DUR_MAX = 180, 420   # episode length in seconds
IFACE = "eth0"                # adjust to the container's interface

FAULTS = {
    "cpu": ["stress-ng", "--cpu", "0", "--cpu-load", "90"],
    "memory": ["stress-ng", "--vm", "2", "--vm-bytes", "75%"],
    "io": ["stress-ng", "--hdd", "2", "--hdd-bytes", "1G"],
}


def net_loss(on):
    if on:
        subprocess.run(["tc", "qdisc", "add", "dev", IFACE, "root", "netem", "loss", "20%"])
    else:
        subprocess.run(["tc", "qdisc", "del", "dev", IFACE, "root", "netem"])


def main():
    with open("/data/fault_labels.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["start_utc", "end_utc", "type"])
        for i in range(EPISODES):
            time.sleep(random.randint(MIN_GAP, MAX_GAP))
            ftype = random.choice(list(FAULTS) + ["network"])
            start = dt.datetime.utcnow().isoformat()
            dur = random.randint(DUR_MIN, DUR_MAX)
            if ftype == "network":
                net_loss(True)
                time.sleep(dur)
                net_loss(False)
            else:
                p = subprocess.Popen(FAULTS[ftype] + ["--timeout", f"{dur}s"])
                p.wait()
            end = dt.datetime.utcnow().isoformat()
            w.writerow([start, end, ftype])
            f.flush()
            print(f"[{i + 1}/{EPISODES}] {ftype} {dur}s")


if __name__ == "__main__":
    main()
