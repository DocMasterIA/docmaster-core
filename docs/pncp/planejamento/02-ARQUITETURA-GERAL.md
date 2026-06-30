# Arquitetura geral

## 1. Visão de componentes

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Host (DESKTOP / WSL)                                                      │
│                                                                           │
│  ┌─────────────────┐     docmaster_net      ┌──────────────────────────┐ │
│  │ backend Django  │ ─────────────────────► │ pncp_researcher_service  │ │
│  │ :8000 / :8001   │  PNCP_RESEARCHER_BASE  │ FastAPI :8012            │ │
│  └────────┬────────┘  _URL=...service:8012  └───────────┬──────────────┘ │
│           │                                              │                │
│  ┌────────▼────────┐                          volume: /data/pncp/       │
│  │ frontend Vue    │                          pncp_researcher_local.db  │
│  │ (nginx/static)  │                                                     │
│  └─────────────────┘                                                     │
│                                                                           │
│  Projeto Compose isolado: docmaster-pncp (docker-compose.pncp.yml)       │
└──────────────────────────────────────────────────────────────────────────┘
         │ HTTPS                              │ HTTPS
         ▼                                    ▼
   pncp.gov.br/api/consulta            pncp.gov.br/pncp-api
   (catálogo / publicação)             (itens, resultados, contratos)
```

---

## 2. Serviços e portas

| Serviço | Contentor | Porta | Rede |
|---------|-----------|-------|------|
| PNCP Researcher | `pncp_researcher_service` | 8012 (interno) | `docmaster_net` |
| Backend Django | `backend` | 8000 | `docmaster_net` |
| Frontend | servido pelo backend ou Vite dev | 5173 dev | — |

**Docker Desktop + WSL:** porta `127.0.0.1:8012` no host frequentemente falha (erro 500). Usar `docker-compose.pncp.noports.yml` — API só via `docker exec` ou rede Docker (`pncp_researcher_service:8012`).

---

## 3. Rotas HTTP

### Frontend → Django

| Prefixo | Destino |
|---------|---------|
| `/api/pncp-research/*` | Proxy → FastAPI researcher |
| `/api/pncp/cotacoes/*` | Django ORM (sessões cotação) |

### FastAPI (`/api/pncp-research/`)

Ver lista completa em [06-BUSCA-E-FORNECEDOR.md](./06-BUSCA-E-FORNECEDOR.md) e [07-CONFIGURACAO-DEPLOY-OPS.md](./07-CONFIGURACAO-DEPLOY-OPS.md).

Principais:
- `GET /health` — saúde + runtime ingest
- `POST /market-search/intelligent` — busca inteligente (produto)
- `GET /local-index/coverage` — fila + gaps
- `POST /local-index/backfill` — backfill síncrono (legado/ops)

---

## 4. Persistência

| Recurso | Local |
|---------|-------|
| SQLite índice + fila | `/data/pncp/pncp_researcher_local.db` |
| Volume Docker | `docmaster-pncp_pncp_researcher_data` (nome pode variar) |
| Sessões cotação | PostgreSQL/SQLite Django (`backend`) |

**Crítico:** o volume PNCP **não** deve ser apagado com `docker compose down -v` no stack principal.

---

## 5. Ciclo de vida do researcher

```python
# api.py — lifespan FastAPI
if PNCP_INGEST_WORKER_ENABLED:
    worker_task = asyncio.create_task(_supervised_ingest_worker())
```

1. Uvicorn sobe FastAPI
2. Supervisor inicia `ingest_worker_loop()`
3. Startup: self-heal + planner boot
4. Loop infinito: heal periódico → planner → stall check → batch → sleep 2s
5. Crash → supervisor reinicia em 5s

---

## 6. Modos de ingestão

| Modo | Quando usar | Característica |
|------|-------------|----------------|
| **Worker 24/7** (default) | Produção | Fila SQLite, 2 fases, resiliente |
| **POST /local-index/backfill** | Ops pontual | Síncrono, bloqueia até terminar |
| **run-pncp-index-ingest-loop.sh** | Legado DESKTOP | Loop bash → POST backfill |
| **POST /ingest/plan** + **worker-tick** | Debug manual | Disparo explícito |

**Recomendado:** apenas worker 24/7 com `PNCP_INGEST_WORKER_ENABLED=1`.

---

## 7. Integração backend

```python
# settings.py
PNCP_RESEARCHER_BASE_URL = "http://pncp_researcher_service:8012"
```

```python
# pncp_research_proxy.py — repassa sessão Django autenticada
GET/POST → {BASE}/api/pncp-research/{path}
```

Timeouts proxy: GET 60s, POST 600s, stream 900s.

---

## 8. Frontend

| Ficheiro | Função |
|----------|--------|
| `services/pncpResearch.js` | Cliente HTTP |
| `views/BuscaInteligenteCotacoes.vue` | UI busca inteligente + sessão |

Fluxo típico:
1. `POST /api/pncp-research/market-search/intelligent`
2. Usuário seleciona itens → `POST /api/pncp/cotacoes/research/sessions/...`
3. Gera PDF via backend Django (usa `pncp_relatorio_itens.py`)
