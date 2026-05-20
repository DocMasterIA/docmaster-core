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

1. Instale node_exporter no **mesmo host** que roda o backend (systemd ou container com `/proc`, `/sys` montados).
2. Em `config/prometheus.yml`, adicione o target `SEU_IP:9100` no job `node` (veja exemplo comentado).
3. Garanta que o Prometheus alcança a porta 9100 (firewall).

## Grafana

```bash
python3 scripts/build-grafana-dashboard.py
./scripts/grafana-reset-dashboard.sh   # tag layout-v41-host
```

Explore: queries em `config/prometheus/explore-queries.md`.
