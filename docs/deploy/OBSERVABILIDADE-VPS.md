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

## Subir sozinho após reboot / queda

Os três serviços usam `restart: always` no `docker-compose.yml` (Docker recria o contentor se cair).

**1. Docker tem de arrancar com o sistema**

- **VPS Linux:** `sudo systemctl enable docker`
- **WSL / Windows:** Docker Desktop → Settings → **Start Docker Desktop when you sign in**

**2. Uma vez por máquina (ou após `docker compose down`):**

```bash
cd DEPLOY
chmod +x scripts/ensure-observability.sh
./scripts/ensure-observability.sh
```

**3. VPS — opcional (systemd no boot):** [docmaster-observability.service.example](../../deploy/docmaster-observability.service.example)

`unless-stopped` não voltava se o contentor tinha sido parado à mão; `always` + passo 2 garante a stack após ligar o PC/servidor.

## Grafana “down” ou sem dados por horas

Rode na pasta do compose (`DEPLOY` ou `~/docmaster-core`):

```bash
docker ps -a --format 'table {{.Names}}\t{{.Status}}' | grep -E 'grafana|prometheus|node_exporter'
curl -sf --max-time 5 http://127.0.0.1:3000/api/health && echo " grafana OK" || echo " grafana OFF"
curl -sf --max-time 5 http://127.0.0.1:9090/-/ready && echo " prometheus OK" || echo " prometheus OFF"
docker logs prometheus --tail 40
docker logs grafana --tail 40
df -h /var/lib/docker
```

| Sintoma | Causa provável | Ação |
|---------|----------------|------|
| `grafana` / `prometheus` **Exited** | Não subiu após reboot ou `compose up` sem esses serviços | `./scripts/ensure-observability.sh` |
| Prometheus **Restarting** | Disco cheio no volume `prometheus_data` | `df -h`; compose já limita retenção 30d — se volume antigo enorme: ver nota abaixo |
| Grafana abre, painéis vazios / loading | Datasource não alcançava Prometheus | Provisioning usa `http://prometheus:9090` (rede Docker) |
| Demora 10–15 min e aparece | Prometheus a recompactar TSDB ou 1º scrape após cold start | Normal após longa queda; espere ou `docker compose restart prometheus grafana` |
| Só no DESKTOP, backend vazio | Scrape aponta para `api.docmasteria.com.br` (produção) | Normal localmente; métricas de host (`node`) ainda devem aparecer |

Recuperação rápida:

```bash
cd DEPLOY   # ou ~/docmaster-core
docker compose up -d node_exporter prometheus grafana
docker compose restart prometheus grafana
sleep 20
curl -s http://127.0.0.1:9090/-/ready
curl -s http://127.0.0.1:3000/api/health
```

Se Prometheus não voltar por disco (logs `no space left`):

```bash
docker compose stop prometheus
docker volume rm $(docker volume ls -q | grep prometheus_data)   # APAGA histórico de métricas
docker compose up -d prometheus grafana
```

## Erros comuns

| Problema | Causa |
|----------|--------|
| 404 em `api.docmasteria.com.br/grafana` | Esperado sem nginx; use `127.0.0.1:3000` ou túnel |
| Conflito `container name prometheus` | Dois `docker compose` em pastas diferentes; use só `cd DEPLOY` |
| Grafana sem dados | Datasource: `http://prometheus:9090` (provisioning) |
