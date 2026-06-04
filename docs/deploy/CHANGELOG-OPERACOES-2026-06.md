# Changelog operacional — junho 2026 (DESKTOP / docmaster)

Alterações feitas na sessão de produção que **não** estavam todas documentadas nos guias antigos. Use com [README.md](./README.md).

---

## PNCP — ingestão e performance

| Alteração | Ficheiros | Efeito |
|-----------|-----------|--------|
| Watermark resume (`last_page+1`) | `local_index.py`, `PNCP_INGEST_WATERMARK_RESUME` | Crawl profundo; `next_page` em `ingest-status` |
| Paralelo de GET itens no backfill | `PNCP_BACKFILL_ITEM_CONCURRENCY` (default 12) | ~5–10× mais rápido por página |
| Fix HTTP 500 no backfill | `local_index.py` — `state["last_page"]` vs `Row.get()` | Loop deixa de falhar com exit 1 imediato |
| Loop via `docker exec` automático | `run-pncp-index-ingest-loop.sh` | Funciona com `noports` (sem 8012 no host) |
| JSON do backfill em ficheiro separado | `~/pncp-ingest-responses.jsonl` | `pncp-ingest.log` legível |
| Defaults do loop: 60 páginas, sleeps 10s/180s | `run-pncp-index-ingest-loop.sh` | Mais throughput 24/7 |
| `DOCMASTER_DEPLOY_DIR` + detecção contentor | loop script | `~/docmaster` vs `~/docmaster-core` |

Documentação: [PNCP-INGESTAO-INDEX-24-7.md](./PNCP-INGESTAO-INDEX-24-7.md)

---

## PNCP — stack isolada V2

| Alteração | Documentação |
|-----------|----------------|
| FTS5 + `fts-rebuild` | [PNCP-V2-DEPLOY.md](./PNCP-V2-DEPLOY.md) |
| Busca híbrida (`PNCP_HYBRID_*`) | [PNCP-API-INDICE-LOCAL.md](./PNCP-API-INDICE-LOCAL.md) |
| `GET /local-index/operational-status` | Agrega stats + ingest + FTS |
| Ingestão resiliente (autopause, `ingest-status`) | `pncp_ingest_state` |

---

## Stack principal — Cloudflare 502

| Alteração | Ficheiros |
|-----------|-----------|
| Remoção de `cloudflared` órfão (contentor + PID) | `ensure-docmaster-stack.sh` |
| `reset_cloudflared_before_compose` antes do `up` | idem |
| Core sobe antes de observabilidade (porta 9100) | `main_compose_up` |
| `ALLOWED_HOSTS` inclui `"backend"` | `backend/mdlicitatech/settings.py` |

Documentação: [STACK-E-CLOUDFLARE-502.md](./STACK-E-CLOUDFLARE-502.md)

---

## Boot e systemd

| Alteração | Ficheiros |
|-----------|-----------|
| `ensure-docmaster-stack.sh` unificado | chama `ensure-pncp-researcher.sh` |
| `DOCMASTER_START_PNCP_INGEST=1` opcional no ensure | env |
| `install-docmaster-boot-service.sh --with-pncp-ingest` | `docmaster-pncp-ingest.service` |
| `deploy/docmaster-stack.service.example` | template systemd |
| WSL: tarefa Windows + `vmIdleTimeout` | [WSL-BOOT-WINDOWS.md](./WSL-BOOT-WINDOWS.md) |

---

## Scripts e utilitários PNCP

| Script | Estado |
|--------|--------|
| `scripts/lib/pncp-compose-args.sh` | `noports`, health via `docker exec` |
| `scripts/ensure-pncp-ingest-loop.sh` | PID file + flock + espera health |
| `docker-compose.pncp.noports.yml` | Sem bind 8012 no host |
| Entrypoint `chown` em `/data/pncp` | `docker-entrypoint.sh` |

Referência: [PNCP-SCRIPTS-REFERENCIA.md](./PNCP-SCRIPTS-REFERENCIA.md)

---

## Volumes e dados (DESKTOP)

| Facto | Notas |
|-------|--------|
| Volume em uso | `docmaster-pncp_pncp_researcher_data` |
| `docmaster_pncp_researcher_data` (underscore) | Pode existir **sem** `.db` válido — não montar sem verificar |
| `find-pncp-db-volumes.sh` | Pode falhar no WSL se imagem `alpine` não correr — ver alternativa no guia de scripts |
| Crescimento observado | ~300k itens / ~10h após paralelo + 60 páginas |

---

## Backend (menor)

| Alteração | Ficheiro |
|-----------|----------|
| `Prefeitura.__str__` só `nome_municipio` | `backend/app/models/prefeitura.py` |

Sem impacto na ingestão PNCP.

---

## Deploy recomendado após `git pull`

```bash
cd ~/docmaster-core && git pull
cp ~/docmaster-core/docker-compose.pncp.yml ~/docker-compose.pncp.yml

# PNCP código (hotfix ou rebuild)
docker cp ~/docmaster-core/pncp_researcher_service/app/local_index.py \
  pncp_researcher_service:/app/pncp_researcher_service/app/local_index.py
docker cp ~/docmaster-core/pncp_researcher_service/app/config.py \
  pncp_researcher_service:/app/pncp_researcher_service/app/config.py
docker restart pncp_researcher_service

# Loop
export DOCMASTER_DEPLOY_DIR=/home/docmaster
pkill -f run-pncp-index-ingest-loop || true
rm -f ~/.pncp-index-ingest.lock
nohup ~/docmaster-core/scripts/run-pncp-index-ingest-loop.sh >> ~/pncp-ingest.log 2>&1 &
```
