# Observabilidade na VPS (sem mexer no nginx)

O `docker-compose.yml` e `config/` são **copiados** para a pasta de deploy (`DEPLOY`). Comandos: **`cd DEPLOY`**, nunca só `docker compose` em `~` sem a pasta `config/`.

## Não precisa de sites-available / nginx custom

O **api.docmasteria.com.br** continua só com o Django (como hoje). Grafana e Prometheus **não** entram nesse domínio por padrão.

Por isso **https://api.docmasteria.com.br/grafana/** dá **404** — é o Django, não o Grafana. Isso é normal **sem** configurar proxy no nginx (que não é obrigatório).

## Como acessar o Grafana (recomendado)

### Na própria VPS (SSH)

```bash
cd DEPLOY
docker compose up -d node_exporter prometheus grafana
curl -s http://127.0.0.1:3000/api/health
```

No browser **na VPS** (ou com túnel): **http://127.0.0.1:3000**

Dashboard: **http://127.0.0.1:3000/d/docmaster-backend**

Login: `admin` + senha do `.env` (`GRAFANA_ADMIN_PASSWORD`, default `changeme`).

### Do seu PC (túnel SSH — o mais simples)

```bash
ssh -L 3000:127.0.0.1:3000 docmaster@SUA_VPS
```

No PC: **http://127.0.0.1:3000/d/docmaster-backend**

Nada de nginx, Cloudflare ou `sites-enabled`.

### WSL / máquina local (docmaster-core no desktop)

```bash
cd ~/docmaster-core
docker compose up -d node_exporter prometheus grafana
```

**http://127.0.0.1:3000/d/docmaster-backend**

## Prometheus

- Na VPS: `http://127.0.0.1:9090` (só localhost)
- Métricas da API: o Prometheus **já** scrape `https://api.docmasteria.com.br/metrics` (job `backend`) — isso **não** muda o nginx do site.

## Atualizar dashboard

```bash
python3 scripts/build-grafana-dashboard.py
cd DEPLOY && docker compose restart grafana
```

## Opcional (só se um dia quiser URL pública)

Ficheiro de referência **não aplicado automaticamente**: [nginx-observability-api.conf.example](../../deploy/nginx-observability-api.conf.example)

Só use se souber **onde** o nginx do servidor define `api.docmasteria.com.br` (painel do host, `/etc/nginx/nginx.conf`, etc.). Erro no nginx pode derrubar o site — por isso o padrão do projeto é **túnel SSH**, não mexer no proxy.

## Erros comuns

| Problema | Causa |
|----------|--------|
| 404 em `api.docmasteria.com.br/grafana` | Esperado sem nginx; use `127.0.0.1:3000` ou túnel |
| Conflito `container name prometheus` | Dois `docker compose` em pastas diferentes; use só `cd DEPLOY` |
| Grafana sem dados | Datasource deve ser `http://host.docker.internal:9090` (já no provisioning) |
