# Stack principal — Cloudflare, erro 502 na API e boot

Sintomas tratados em produção (DESKTOP): **site 200**, **API 502**; ou erro **1033** no Cloudflare; segundo túnel `cloudflared` órfão a receber tráfego.

Relacionado: [BOOT-AUTOMATICO.md](./BOOT-AUTOMATICO.md), [ESTABILIDADE-E-CLOUDFLARE.md](./ESTABILIDADE-E-CLOUDFLARE.md), [CHANGELOG-OPERACOES-2026-06.md](./CHANGELOG-OPERACOES-2026-06.md)

---

## 1. Sintoma: site OK, API 502

### Causa

Dois processos/contentores **cloudflared** com o mesmo token:

- `cloudflared-tunnel` (compose) — correto, na rede Docker
- Contentor ou PID **órfão** (ex. cgroup `docker-ffbaca…` no Docker Desktop WSL)

O órfão pode ficar **sem** aparecer em `docker ps | grep cloudflared` da mesma forma que o túnel oficial; `pgrep cloudflared` mostra o processo extra.

O tráfego para `api.docmasteria.com.br` ia para o túnel errado → **502** no origin.

### Diagnóstico

```bash
docker ps -a --filter "ancestor=cloudflare/cloudflared"
pgrep -af cloudflared

# Com túnel do compose parado, site ainda 200 → órfão a receber tráfego
docker stop cloudflared-tunnel
curl -sI https://docmasteria.com.br   # ainda 200?
```

### Correção (manual)

```bash
# Remover todos os cloudflared
docker rm -f $(docker ps -aq --filter "ancestor=cloudflare/cloudflared") 2>/dev/null || true
pkill -f 'cloudflared.*tunnel' || true

# Subir só o do compose
cd ~
./scripts/ensure-docmaster-stack.sh
```

**Não** correr `systemctl restart docmaster-stack` imediatamente após `ensure` manual se isso reexecutar reset em duplicado — um fluxo de cada vez.

### Correção automática (código)

`scripts/ensure-docmaster-stack.sh` inclui:

| Função | O que faz |
|--------|-----------|
| `prune_orphan_cloudflared_containers` | `docker rm -f` em contentores `cloudflare/cloudflared` exceto `cloudflared-tunnel` |
| `prune_orphan_cloudflared_processes` | `kill -9` em PIDs `cloudflared` que **não** estão em `docker top cloudflared-tunnel` |
| `reset_cloudflared_before_compose` | Reset completo antes do `compose up` (contentor + PIDs) |

Ordem de subida:

1. Core: `ollama`, `llm_api`, `rag_service`, `backend`, `frontend-vue`, `cloudflared-tunnel`
2. Observabilidade: `node_exporter`, `prometheus`, `grafana` (falha na 9100 **não** bloqueia o site)

---

## 2. Django `ALLOWED_HOSTS`

O backend recebe `Host: backend` via rede Docker. Adicionado em `backend/mdlicitatech/settings.py`:

```python
ALLOWED_HOSTS = [..., "backend"]
```

Sem isto, pedidos internos ou via túnel com host de serviço podem falhar.

---

## 3. Erro 1033 Cloudflare

Túnel parado, token ausente, WSL dormindo, ou Docker não no boot.

| Verificação | Comando |
|-------------|---------|
| Token no `.env` | `grep CLOUDFLARE_TUNNEL_TOKEN ~/docmaster/.env` |
| Contentor | `docker ps \| grep cloudflared-tunnel` |
| Stack | `./scripts/ensure-docmaster-stack.sh` |

Ver [ESTABILIDADE-E-CLOUDFLARE.md](./ESTABILIDADE-E-CLOUDFLARE.md) e [WSL-BOOT-WINDOWS.md](./WSL-BOOT-WINDOWS.md).

---

## 4. `ensure-docmaster-stack.sh` — variáveis

| Variável | Default | Função |
|----------|---------|--------|
| `DOCMASTER_DEPLOY_DIR` | pasta do script/.. | Onde está `docker-compose.yml` |
| `DOCMASTER_ENV_FILE` | `$DEPLOY/.env` | Token e secrets |
| `DOCMASTER_NO_RECREATE` | `0` | `1` → `up -d --no-recreate` |
| `DOCMASTER_FORCE_RECREATE` | `0` | Recria contentores do stack principal |
| `DOCMASTER_BUILD` | `0` | `docker compose build` |
| `DOCMASTER_START_PNCP_INGEST` | `0` | `1` → chama `ensure-pncp-ingest-loop.sh` |

Fluxo:

```
wait docker → load .env → token → docmaster_net
→ compose up (core + cloudflared reset)
→ compose up (obs)
→ ensure-pncp-researcher.sh
→ [opcional] ensure-pncp-ingest-loop.sh
→ health checks
```

Health checks no host:

- `http://127.0.0.1:8001/metrics` — backend
- `http://127.0.0.1:8012/.../health` — PNCP (falha se **noports**; usar `docker exec`)
- `http://127.0.0.1:3000/api/health` — Grafana

---

## 5. PNCP no ensure

O stack principal **não** inclui `pncp_researcher_service`. O ensure chama:

```bash
DOCMASTER_DEPLOY_DIR="$DEPLOY" ./scripts/ensure-pncp-researcher.sh
```

PNCP usa projeto `docmaster-pncp` — `up` do backend **não** deve derrubar o PNCP se os projetos estiverem separados.

---

## 6. Checklist pós-correção

```bash
curl -sf https://docmasteria.com.br -o /dev/null -w "%{http_code}\n"
curl -sf https://api.docmasteria.com.br/api/health/ -w "%{http_code}\n"  # ou endpoint real

docker ps --format '{{.Names}}' | grep -E 'backend|cloudflared'
docker logs --tail 20 cloudflared-tunnel
```

Esperado: site e API **200**; um único túnel activo; métricas do `cloudflared-tunnel` com pedidos (não zero em contentor fantasma).

---

## 7. O que não fazer

- Dois `docker compose up` de stacks diferentes com o **mesmo** token Cloudflare manualmente
- `docker run cloudflare/cloudflared` solto com o token de produção
- Ignorar `pgrep cloudflared` quando API 502 e site 200
- Rotacionar token Cloudflare sem actualizar `.env` (token antigo ficou em `ps` / histórico — gerar token novo no dashboard)
