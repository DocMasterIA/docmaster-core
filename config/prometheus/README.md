# Prometheus + Grafana

## Acesso (padrão — sem nginx)

| O quê | URL |
|-------|-----|
| Grafana | http://127.0.0.1:3000 |
| Dashboard | http://127.0.0.1:3000/d/docmaster-backend |
| Prometheus | http://127.0.0.1:9090 |
| Métricas API | https://api.docmasteria.com.br/metrics (scrape automático) |

Do PC para a VPS: `ssh -L 3000:127.0.0.1:3000 user@vps` e abra http://127.0.0.1:3000

## Deploy

```bash
cd DEPLOY   # pasta com docker-compose.yml + config/ copiados do repo
docker compose up -d node_exporter prometheus grafana
```

Detalhes: [docs/deploy/OBSERVABILIDADE-VPS.md](../../docs/deploy/OBSERVABILIDADE-VPS.md)

## Métricas

| Job | Alvo |
|-----|------|
| `backend` | `https://api.docmasteria.com.br/metrics` |
| `node` | `node_exporter:9100` |

Grafana datasource (provisioning): `http://host.docker.internal:9090`
