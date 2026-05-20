# Prometheus + Grafana

## URLs (produção)

- Prometheus: **https://api.docmasteria.com.br/prometheus/**
- Grafana: **https://api.docmasteria.com.br/grafana/**
- Métricas app: **https://api.docmasteria.com.br/metrics**

Nginx: [deploy/nginx-observability-api.conf.example](../../deploy/nginx-observability-api.conf.example)

## Deploy na VPS

1. Copie `docker-compose.yml` + `config/` para `DEPLOY`.
2. Aplique o nginx na VPS e recarregue.
3. `cd DEPLOY && docker compose up -d node_exporter prometheus grafana`

## Métricas

| Job | Alvo | Conteúdo |
|-----|------|----------|
| `backend` | `https://api.docmasteria.com.br/metrics` | `docmaster_*`, Django |
| `node` | `node_exporter:9100` (mesmo compose) | CPU, RAM, disco |

Grafana datasource: `https://api.docmasteria.com.br/prometheus`

## Comandos

**Na VPS:**

```bash
curl -s 'http://127.0.0.1:9090/prometheus/api/v1/query' --data-urlencode 'query=up{job="node"}'
```

**No PC:**

```bash
python3 scripts/build-grafana-dashboard.py
GRAFANA_SKIP_COMPOSE=1 ./scripts/grafana-reset-dashboard.sh
```
