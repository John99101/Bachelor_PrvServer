# Bare-metal variant — systemd units

Maps the minimum service subset (Jellyfin, Nextcloud, Prometheus/cAdvisor/node_exporter)
onto Debian 12 + apt + systemd.

| Service | Source | Unit |
|---|---|---|
| Jellyfin | `apt install jellyfin` provides `jellyfin.service` | none needed |
| Nextcloud | apache2 + php-fpm + postgresql via apt; apache2/postgresql provide their own units | none needed |
| node_exporter | not packaged on Debian 12 — install binary manually | `node_exporter.service` (this dir) |
| cAdvisor | container-only tool; **no bare-metal equivalent** — for the bare-metal variant, collect the equivalent host metrics via node_exporter only and note this limitation in §3.1/§4.2 | n/a |
| Prometheus | `apt install prometheus` provides `prometheus.service` | none needed (point its config at `prometheus.yml` from this repo) |

Install `node_exporter.service` with:

```sh
sudo cp node_exporter.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now node_exporter
```
