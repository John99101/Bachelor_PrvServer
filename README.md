# private-server-thesis

Reproducible measurement scripts for the thesis "Private Multi-Service Server" study.

## Ground rules

- Every number in the thesis must come from a file produced by the scripts in
  this repo, under `data/` or `figures/`. Nothing is reverse-engineered or
  hand-typed from the old draft.
- The architecture comparison (RQ1/RQ3) targets a wiped spare machine
  ("Machine A"); the AI anomaly-detection pipeline (RQ2) runs continuously on
  a Windows daily driver via Docker Desktop / WSL2 ("Machine B").
- Energy/power measurement (RQ4) has been **dropped** for this run (decision
  C2c) — no smart plug or RAPL data is collected. RQ4 is reported as
  "not executed — proposed protocol / future work" in the thesis, except for
  the non-energy TCO terms (hardware cost, admin time, downtime), which are
  still computed from measured/assumed inputs in `econ/tco.py`.
- Service subset (decision C3, minimum set): **Jellyfin + Nextcloud +
  Prometheus/cAdvisor/node_exporter**. WireGuard and Home Assistant are out of
  scope for this run.
- Trials per benchmark variant (decision C4): **5**, reported as mean ± SD.

## Layout

```
hardware/        machine specs (C1) — fill in by hand from the real hardware
stack/           docker-compose + prometheus config + systemd units (bare-metal variant)
bench/           fio jobs, HTTP latency/throughput benchmark, RAM footprint, run-all script
ai/              fault injection, feature export, model training/evaluation
econ/            TCO calculation (energy terms removed)
data/            raw outputs — CSV/JSON/Parquet from every run (commit or archive)
figures/         regenerated figures for the thesis
```

## Day-1 checklist

1. Record Machine A's real specs into `hardware/machineA.txt` and Machine B's
   into `hardware/machineB.txt` (see templates).
2. On Machine B: `cd stack && docker compose up -d`, then start
   `ai/inject_faults.py` in a privileged sidecar container and leave both
   running for the full collection window (target 4–5 days).
3. On Machine A: install the first variant (bare-metal), run
   `bench/run_variant.sh bare-metal 5`, capture results into `data/`.
4. Continue per the day-by-day plan; relabel anything not actually executed as
   future work rather than inventing numbers.

## Data-availability statement (for the thesis)

> All raw measurement data, scripts, and figures referenced in this chapter
> are available in the `private-server-thesis` repository
> (commit hash to be filled in at submission time).
