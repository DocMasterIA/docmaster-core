# Prometheus — DocMaster

## O que é scrapeado

| Job | Origem | Métricas |
|-----|--------|----------|
| `node` | [node_exporter](https://github.com/prometheus/node_exporter) no host (`:9100`) | CPU, RAM, disco, load, rede |
| `backend` | `https://api.docmasteria.com.br/metrics` | `docmaster_*`, `django_*` |

## Subir com Docker Compose

```bash
docker compose up -d node_exporter prometheus grafana
curl -s http://127.0.0.1:9100/metrics | head
curl -s http://127.0.0.1:9090/targets   # node e backend devem estar UP
```

## Produção (servidor da API)

Painéis Host **zerados** quase sempre = `up{job="node"}` é 0 (não é CPU/RAM a 0%).

**Mesmo servidor (Compose):**

```bash
docker compose up -d node_exporter prometheus
./scripts/check-host-metrics.sh
```

**Prometheus noutra máquina** (só scrape HTTPS da API hoje):

1. No servidor da API: `docker compose up -d node_exporter` (porta `9100` no host).
2. `cp config/prometheus.d/20-node-prod.yml.example config/prometheus.d/20-node-prod.yml` — edite o IP.
3. No `docker-compose.yml` do Prometheus, acrescente ao `command`:
   `--config.file=/etc/prometheus/prometheus.d/20-node-prod.yml`
4. `docker compose restart prometheus` — em `/targets` o job `node` deve ficar **UP**.

## Grafana

```bash
python3 scripts/build-grafana-dashboard.py
./scripts/grafana-reset-dashboard.sh   # tag layout-v41-host
```

Explore: queries em `config/prometheus/explore-queries.md`.
