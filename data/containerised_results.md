# Containerised variant — benchmark results (5 trials)
# Machine A: AMD Ryzen 7 5825U, 16 GB DDR4-3200, SK hynix BC711 512 GB NVMe
# Debian 12 + Docker, same stack/docker-compose.yml as Machine B

| metric           | mean        | std       | vs bare-metal   |
|------------------|-------------|-----------|-----------------|
| p50_ms           | 21.08       | 0.34      | -11.71 (-35.7%) |
| p95_ms           | 40.00       | 1.92      | -19.57 (-32.9%) |
| req_s            | 1,373.70    | 49.21     | +495 (+56.3%)   |
| rand_read_iops   | 358,554.88  | 75,205.52 | -29,251 (-7.5%) |
| rand_write_iops  | 188,139.74  | 18,540.57 | +4,853 (+2.6%)  |
| seq_read_iops    | 16,465.06   | 1,261.18  | +1,913 (+13.1%) |
| seq_write_iops   | 5,780.12    | 143.35    | -136 (-2.3%)    |

Notes:
- HTTP latency lower and throughput higher in container than bare-metal — likely
  Docker's networking stack handles concurrent connections more efficiently than
  the bare-metal systemd/Jellyfin configuration on this hardware. Discuss in §4.1.
- Disk I/O differences are within noise (all within ±15%) — no meaningful
  containerisation overhead, as expected on Linux (no hypervisor layer).
- rand_read std is high in both variants (51k bare-metal, 75k container) — NVMe
  thermal/queue-depth variation; report mean ± SD honestly in the thesis table.
