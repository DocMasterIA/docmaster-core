# Prometheus + Grafana

## Access (default — no nginx)

| What | URL |
|------|-----|
| Grafana | http://127.0.0.1:3000 |
| Dashboard | http://127.0.0.1:3000/d/docmaster-backend |
| Prometheus | http://127.0.0.1:9090 |
| API metrics | https://api.docmasteria.com.br/metrics (automatic scrape) |

From your PC to the VPS: `ssh -L 3000:127.0.0.1:3000 user@vps` and open http://127.0.0.1:3000

## Deploy / after restarting the PC

```bash
cd DEPLOY
./scripts/ensure-observability.sh
```

Or: `docker compose up -d node_exporter prometheus grafana` (containers with `restart: always`).

Details: [docs/deploy/OBSERVABILIDADE-VPS.md](../../docs/deploy/OBSERVABILIDADE-VPS.md)

## Metrics

| Job | Target |
|-----|--------|
| `backend` | `https://api.docmasteria.com.br/metrics` |
| `node` | `node_exporter:9100` |

Grafana datasource (provisioning): `http://host.docker.internal:9090`
