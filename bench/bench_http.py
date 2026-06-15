"""HTTP latency + throughput benchmark for a single endpoint.

Usage: python bench_http.py <url> [n_requests]

Prints a JSON object with p50/p95 latency (ms) and requests/sec, computed
from N concurrent GETs against the given URL.
"""
import json
import statistics
import sys
import time
import concurrent.futures as cf

import requests

URL = sys.argv[1]
N = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
CONCURRENCY = 32


def hit(_):
    start = time.perf_counter()
    try:
        requests.get(URL, timeout=10)
        return (time.perf_counter() - start) * 1000
    except Exception:
        return None


def main():
    wall_start = time.perf_counter()
    with cf.ThreadPoolExecutor(CONCURRENCY) as ex:
        latencies = [x for x in ex.map(hit, range(N)) if x is not None]
    wall_elapsed = time.perf_counter() - wall_start

    latencies.sort()
    result = {
        "n": len(latencies),
        "n_failed": N - len(latencies),
        "p50_ms": round(statistics.median(latencies), 2) if latencies else None,
        "p95_ms": round(latencies[int(len(latencies) * 0.95)], 2) if latencies else None,
        "req_per_s": round(len(latencies) / wall_elapsed, 1) if wall_elapsed > 0 else None,
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
