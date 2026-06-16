# Bare-metal variant — benchmark results (5 trials)
# Machine A: AMD Ryzen 7 5825U, 16 GB DDR4-3200, SK hynix BC711 512 GB NVMe
# Debian 12, Jellyfin installed via apt, services via systemd

| metric           | mean        | std       |
|------------------|-------------|-----------|
| p50_ms           | 32.79       | 1.92      |
| p95_ms           | 59.57       | 4.19      |
| req_s            | 878.66      | 66.88     |
| rand_read_iops   | 387,805.61  | 51,047.29 |
| rand_write_iops  | 183,286.84  | 6,988.31  |
| seq_read_iops    | 14,552.28   | 1.83      |
| seq_write_iops   | 5,915.77    | 389.87    |

Notes:
- HTTP benchmark target: http://localhost:8096/health (Jellyfin)
- fio directory: /var/lib/benchdir (NVMe)
- seq_write_iops × 128 KB ≈ 758 MB/s — consistent with BC711 spec (~800 MB/s seq write)
- rand_read_iops unusually high variance (std 51k); likely NVMe thermal/queue-depth variation
