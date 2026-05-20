# Observabilidade na VPS (fluxo real)

O `docker-compose.yml` e a pasta `config/` vêm **do repositório** e são **copiados** para a pasta de deploy na VPS (`DEPLOY`). O que importa é **onde o compose roda na VPS**, não o caminho do clone no PC.

## URLs públicas (api.docmasteria.com.br)

| Serviço | URL | Upstream local |
|---------|-----|----------------|
| **Prometheus** | https://api.docmasteria.com.br/prometheus/ | `127.0.0.1:9090` |
| **Grafana** | https://api.docmasteria.com.br/grafana/ | `127.0.0.1:3000` |
| **Métricas Django** | https://api.docmasteria.com.br/metrics | backend (job `backend` no Prometheus) |

Não use `http://IP_DA_VPS:3000` nem `:9090` na internet — só localhost + nginx.

Config nginx: [deploy/nginx-observability-api.conf.example](../../deploy/nginx-observability-api.conf.example)

## Na VPS (depois de copiar o pacote)

```bash
cd DEPLOY
# 1) Incluir bloco nginx no server api.docmasteria.com.br e: sudo nginx -t && sudo systemctl reload nginx
# 2) Subir stack
docker compose up -d node_exporter prometheus grafana
```

Confirme:

```bash
curl -sI https://api.docmasteria.com.br/prometheus/-/ready | head -1
curl -sI https://api.docmasteria.com.br/grafana/api/health | head -1
curl -s 'http://127.0.0.1:9090/prometheus/api/v1/query' --data-urlencode 'query=up{job="node"}'
```

## No PC (atualizar dashboard / datasource)

```bash
cd /caminho/do/docmaster-core
python3 scripts/build-grafana-dashboard.py
GRAFANA_SKIP_COMPOSE=1 ./scripts/grafana-reset-dashboard.sh
```

Defaults: `GRAFANA_URL=https://api.docmasteria.com.br/grafana`, datasource `https://api.docmasteria.com.br/prometheus`.

## Sincronizar ficheiros na VPS

```bash
rsync -av config/ docker-compose.yml DEPLOY_USER@VPS:DEPLOY/
ssh VPS 'cd DEPLOY && docker compose up -d --force-recreate prometheus grafana'
```

## Erros comuns

1. **404 em /prometheus/** — falta o bloco nginx; Django responde 404.
2. **Grafana sem dados** — datasource deve ser `https://api.docmasteria.com.br/prometheus`, não `http://prometheus:9090`.
3. **`docker compose` em `~` sem `config/`** — monta paths errados; use `cd DEPLOY`.
