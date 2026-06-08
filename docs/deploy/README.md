# Deploy DocMaster — índice da documentação

Guias operacionais para produção (servidor DESKTOP / `/home/docmaster`, WSL + Docker).

## Por onde começar

| Objetivo | Documento |
|----------|-----------|
| Site + API no ar, túnel Cloudflare, erro 502/1033 | [STACK-E-CLOUDFLARE-502.md](./STACK-E-CLOUDFLARE-502.md) |
| Boot após reboot (systemd + WSL Windows) | [BOOT-AUTOMATICO.md](./BOOT-AUTOMATICO.md), [WSL-BOOT-WINDOWS.md](./WSL-BOOT-WINDOWS.md) |
| PNCP API 24/7 (contentor isolado) | [PNCP-RESEARCHER-24-7.md](./PNCP-RESEARCHER-24-7.md) |
| **Estado declarativo PNCP** (ingest + homolog + CNPJ — tudo num doc) | [PNCP-DECLARATIVO.md](../PNCP-DECLARATIVO.md) |
| **Alimentar índice PNCP** (loop, watermarks, paralelo) | [PNCP-INGESTAO-INDEX-24-7.md](./PNCP-INGESTAO-INDEX-24-7.md) |
| Scripts PNCP (referência) | [PNCP-SCRIPTS-REFERENCIA.md](./PNCP-SCRIPTS-REFERENCIA.md) |
| API índice local + FTS + busca V2 | [PNCP-API-INDICE-LOCAL.md](./PNCP-API-INDICE-LOCAL.md), [PNCP-V2-DEPLOY.md](./PNCP-V2-DEPLOY.md) |
| Grafana / Prometheus | [OBSERVABILIDADE-VPS.md](./OBSERVABILIDADE-VPS.md) |
| Estabilidade geral / WSL idle | [ESTABILIDADE-E-CLOUDFLARE.md](./ESTABILIDADE-E-CLOUDFLARE.md) |
| Entrega de módulos (checklist) | [ENTREGA-MODULOS.md](./ENTREGA-MODULOS.md) |
| Alterações recentes (changelog ops) | [CHANGELOG-OPERACOES-2026-06.md](./CHANGELOG-OPERACOES-2026-06.md) |

## Dois stacks Docker

| Stack | Compose | Projeto Compose | Contentores críticos |
|-------|---------|-----------------|----------------------|
| Principal | `~/docker-compose.yml` | `docmaster` | `backend`, `frontend-vue`, `cloudflared-tunnel`, LLM, RAG… |
| PNCP isolado | `~/docker-compose.pncp.yml` + override + noports | `docmaster-pncp` | `pncp_researcher_service` |

O `docker compose up` do stack **principal** não deve recriar o PNCP (projeto separado).

## Scripts principais (`scripts/`)

| Script | Função |
|--------|--------|
| `ensure-docmaster-stack.sh` | Sobe app + túnel + PNCP API + observabilidade |
| `ensure-pncp-researcher.sh` | Mantém só o contentor PNCP |
| `run-pncp-index-ingest-loop.sh` | Loop de ingestão do índice |
| `ensure-pncp-ingest-loop.sh` | Idempotente: garante um loop (cron/systemd) |
| `attach-pncp-volume.sh` | Liga volume Docker com `.db` existente |
| `find-pncp-db-volumes.sh` | Lista volumes com SQLite PNCP |
| `install-docmaster-boot-service.sh` | Instala systemd no boot |

## Regra de ouro (produção)

1. **Nunca** `docker compose -f docker-compose.pncp.yml down -v`
2. **Um** loop de ingestão (`nohup` ou `docmaster-pncp-ingest.service`)
3. Volume PNCP: `docmaster-pncp_pncp_researcher_data` (confirmar com `sqlite3` / stats)
4. Após reboot WSL: `ensure-docmaster-stack.sh` + relançar ingest se não usar `--with-pncp-ingest`
