"""Export 5-minute-resampled host/container metrics from Prometheus to Parquet.

Usage: python export_features.py [days]

Pulls the last `days` (default 5) of data ending now and writes
data/features.parquet. Adjust the window to whatever was actually collected.
"""
import sys
import time

import pandas as pd
import requests

PROM = "http://localhost:9090"
STEP = "300s"  # 5-minute resample

QUERIES = {
    "cpu_user": 'rate(node_cpu_seconds_total{mode="user"}[5m])',
    "cpu_system": 'rate(node_cpu_seconds_total{mode="system"}[5m])',
    "cpu_iowait": 'rate(node_cpu_seconds_total{mode="iowait"}[5m])',
    "mem_committed": "node_memory_Committed_AS_bytes",
    "disk_read": "rate(node_disk_read_bytes_total[5m])",
    "disk_write": "rate(node_disk_written_bytes_total[5m])",
    "net_in": "rate(node_network_receive_bytes_total[5m])",
    "net_out": "rate(node_network_transmit_bytes_total[5m])",
    "runqueue": "node_load1",
    "procs_running": "node_procs_running",
}


def query(expr, start, end):
    r = requests.get(
        f"{PROM}/api/v1/query_range",
        params={"query": expr, "start": start, "end": end, "step": STEP},
    ).json()
    result = r["data"]["result"]
    if not result:
        return pd.Series(dtype=float)
    frames = [
        pd.Series({int(float(t)): float(v) for t, v in series["values"]})
        for series in result
    ]
    return pd.concat(frames, axis=1).sum(axis=1)


def main():
    days = float(sys.argv[1]) if len(sys.argv) > 1 else 5
    end = time.time()
    start = end - days * 24 * 3600

    df = pd.DataFrame({name: query(expr, start, end) for name, expr in QUERIES.items()})
    df.index = pd.to_datetime(df.index, unit="s")
    df = df.sort_index().ffill().dropna()

    df.to_parquet("data/features.parquet")
    print(df.shape, "saved to data/features.parquet")
    print(f"window: {df.index.min()} -> {df.index.max()} ({days} days requested)")


if __name__ == "__main__":
    main()
