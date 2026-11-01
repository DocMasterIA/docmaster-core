# DocMaster Deploy — documentation index

Operational guides for production (DESKTOP server / `/home/docmaster`, WSL + Docker).

## Where to start

| Goal | Document |
|------|----------|
| Site + API up, Cloudflare tunnel, 502/1033 errors | [STACK-E-CLOUDFLARE-502.md](./STACK-E-CLOUDFLARE-502.md) |
| Boot after reboot (systemd + Windows WSL) | [BOOT-AUTOMATICO.md](./BOOT-AUTOMATICO.md), [WSL-BOOT-WINDOWS.md](./WSL-BOOT-WINDOWS.md) |
| PNCP API 24/7 (isolated container) | [PNCP-RESEARCHER-24-7.md](./PNCP-RESEARCHER-24-7.md) |
| **PNCP AI context** (ingest + supplier + ops) | [PNCP-CONTEXTO-IA.md](../pncp/PNCP-CONTEXTO-IA.md) |
| **PNCP declarative state** | [PNCP-DECLARATIVO.md](../pncp/PNCP-DECLARATIVO.md) |
| **Feed the PNCP index** (loop, watermarks, parallel) | [PNCP-INGESTAO-INDEX-24-7.md](./PNCP-INGESTAO-INDEX-24-7.md) |
| PNCP scripts (reference) | [PNCP-SCRIPTS-REFERENCIA.md](./PNCP-SCRIPTS-REFERENCIA.md) |
| **PNCP operations commands** (monitor, backup, deploy) | [PNCP-COMANDOS-OPERACAO.txt](./PNCP-COMANDOS-OPERACAO.txt) |
| Local index API + FTS + V2 search | [PNCP-API-INDICE-LOCAL.md](./PNCP-API-INDICE-LOCAL.md), [PNCP-V2-DEPLOY.md](./PNCP-V2-DEPLOY.md) |
| **Intelligent search quality + Qwen** | [PNCP-BUSCA-INTELIGENTE-QUALIDADE.md](../pncp/PNCP-BUSCA-INTELIGENTE-QUALIDADE.md) |
| Qwen integration (DocMaster) | [QWEN-INTEGRACAO-DOCMASTER.md](../integracao/QWEN-INTEGRACAO-DOCMASTER.md) |
| Grafana / Prometheus | [OBSERVABILIDADE-VPS.md](./OBSERVABILIDADE-VPS.md) |
| Overall stability / WSL idle | [ESTABILIDADE-E-CLOUDFLARE.md](./ESTABILIDADE-E-CLOUDFLARE.md) |
| Module delivery (checklist) | [ENTREGA-MODULOS.md](./ENTREGA-MODULOS.md) |
| **Cloudflare R2 backup** (DBs + media + cron) | [MODULO-BACKUP-R2.md](./MODULO-BACKUP-R2.md) |
| Recent changes (ops changelog) | [CHANGELOG-OPERACOES-2026-06.md](./CHANGELOG-OPERACOES-2026-06.md) |

## Two Docker stacks

| Stack | Compose | Compose project | Critical containers |
|-------|---------|-----------------|---------------------|
| Main | `~/docker-compose.yml` | `docmaster` | `backend`, `frontend-vue`, `cloudflared-tunnel`, LLM, RAG… |
| Isolated PNCP | `~/docker-compose.pncp.yml` + override + noports | `docmaster-pncp` | `pncp_researcher_service` |

`docker compose up` on the **main** stack must not recreate PNCP (separate project).

## Main scripts (`scripts/`)

| Script | Role |
|--------|------|
| `ensure-docmaster-stack.sh` | Brings up the app + tunnel + PNCP API + observability |
| `ensure-pncp-researcher.sh` | Keeps only the PNCP container running |
| `run-pncp-index-ingest-loop.sh` | Index ingestion loop |
| `ensure-pncp-ingest-loop.sh` | Idempotent: ensures one loop (cron/systemd) |
| `attach-pncp-volume.sh` | Attaches a Docker volume to an existing `.db` |
| `find-pncp-db-volumes.sh` | Lists volumes that contain the PNCP SQLite database |
| `install-docmaster-boot-service.sh` | Installs systemd at boot |

## Golden rule (production)

1. **Never** run `docker compose -f docker-compose.pncp.yml down -v`
2. **One** ingestion loop (`nohup` or `docmaster-pncp-ingest.service`)
3. PNCP volume: `docmaster-pncp_pncp_researcher_data` (confirm with `sqlite3` / stats)
4. After a WSL reboot: `ensure-docmaster-stack.sh` + relaunch ingest if you are not using `--with-pncp-ingest`
