# Configuração, deploy e operações

## 1. Compose e scripts

| Ficheiro | Função |
|----------|--------|
| `docker-compose.pncp.yml` | Stack isolada `docmaster-pncp` |
| `docker-compose.pncp.noports.yml` | Remove bind 8012 no host (WSL) |
| `docker-compose.pncp.override.yml` | Volume external DESKTOP |
| `scripts/ensure-pncp-researcher.sh` | Sobe/mantém researcher |
| `scripts/deploy-pncp-researcher-code.sh` | Hotfix código sem rebuild |
| `scripts/attach-pncp-volume.sh` | Anexa volume índice grande |
| `scripts/run-pncp-index-ingest-loop.sh` | Loop legado backfill |

---

## 2. Subir no DESKTOP (noports)

```bash
cp ~/docmaster-core/docker-compose.pncp.noports.yml.example ~/docker-compose.pncp.noports.yml

docker compose \
  -f ~/docker-compose.pncp.yml \
  -f ~/docker-compose.pncp.override.yml \
  -f ~/docker-compose.pncp.noports.yml \
  up -d pncp_researcher_service
```

Ou: `~/docmaster-core/scripts/ensure-pncp-researcher.sh`

**Nunca** confiar em `curl localhost:8012` com noports — usar `docker exec`.

---

## 3. Variáveis críticas de ingestão

### Master switches

```bash
PNCP_INGEST_QUEUE_ENABLED=1
PNCP_INGEST_WORKER_ENABLED=1
PNCP_INGEST_SELF_HEAL_ENABLED=1
PNCP_INGEST_STALL_RECOVERY_ENABLED=1
```

### Throughput (defaults código jun/2026)

```bash
PNCP_INGEST_WORKER_CATALOG_BATCH=6
PNCP_INGEST_WORKER_ITEMS_BATCH=32
PNCP_INGEST_WORKER_ITEMS_CONCURRENCY=10
PNCP_INGEST_TASK_TIMEOUT_SECONDS=180
PNCP_INGEST_BATCH_MAX_SECONDS=480
PNCP_INGEST_PLANNER_INTERVAL_SECONDS=300
PNCP_INGEST_PLANNER_PAGES_PER_SCOPE=8
PNCP_INGEST_QUEUE_MAX_PENDING=12000
PNCP_INGEST_ITEMS_STARVE_BACKLOG=150
PNCP_INGEST_CATALOG_HEAVY_PENDING=300
PNCP_INGEST_ITEMS_STALL_SECONDS=600
PNCP_INGEST_ITEMS_BACKLOG_PAUSE_CATALOG=3000
PNCP_INGEST_PLANNER_CONTRACTS_WITHOUT_ITEMS_MAX=1200
PNCP_INGEST_STALL_SECONDS=900
PNCP_INGEST_STALL_MIN_PENDING=100
PNCP_INGEST_HEARTBEAT_LOG_SECONDS=300
```

### Janela e escopo

```bash
PNCP_LOCAL_BACKFILL_DAYS=365
PNCP_MODALIDADES_DEFAULT=8,6,7,9,10
PNCP_UFS_DEFAULT=AC,AL,...  # 27 UFs
PNCP_INGEST_ITEMS_REFRESH_DAYS=7
```

### Backend

```bash
PNCP_RESEARCHER_BASE_URL=http://pncp_researcher_service:8012
```

---

## 4. Comandos de diagnóstico

### Saúde rápida

```bash
docker ps --filter name=pncp_researcher_service

docker exec pncp_researcher_service python -c \
  "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8012/api/pncp-research/health',timeout=15).read().decode())"
```

### Fila (rápido)

```bash
docker exec pncp_researcher_service python -c \
  "from pncp_researcher_service.app.ingest_queue import queue_stats; print(queue_stats())"
```

### Prova de vida ingestão

```bash
docker logs pncp_researcher_service 2>&1 | grep -E 'ingest batch|ingest heartbeat|topup itens|batch timeout' | tail -10
```

### Coverage (lento — 60–120s)

```bash
docker exec pncp_researcher_service python -c "
import urllib.request, json
u='http://127.0.0.1:8012/api/pncp-research/local-index/coverage'
print(json.dumps(json.loads(urllib.request.urlopen(u,timeout=120).read()), indent=2)[:2000])
"
```

### Contratos sem itens

```bash
docker exec pncp_researcher_service python -c \
  "from pncp_researcher_service.app.ingest_queue import count_contracts_without_items; print(count_contracts_without_items())"
```

### Watermark por scope

```bash
docker exec pncp_researcher_service python -c "
import urllib.request, json
u='http://127.0.0.1:8012/api/pncp-research/local-index/ingest-status'
d=json.loads(urllib.request.urlopen(u,timeout=60).read())
for s in (d.get('scopes') or [])[:5]:
    w=s.get('watermark') or {}
    print(s.get('uf'), s.get('modalidade'), 'next=', w.get('next_page'), 'paused=', s.get('paused_until'))
"
```

---

## 5. Deploy de código

### Hotfix (sem rebuild imagem)

```bash
cd ~/docmaster-core && git pull
~/docmaster-core/scripts/deploy-pncp-researcher-code.sh
```

Verifica `purge_redundant_dead_tasks` no contentor.

### Aplicar novos env defaults

Requer recreate **com noports**:

```bash
docker compose -f ... -f noports.yml up -d --force-recreate pncp_researcher_service
```

### Backend (PDF fornecedor)

```bash
docker compose up -d --no-recreate backend
```

---

## 6. O que **não** usar como healthcheck

| Ação | Por quê |
|------|---------|
| `POST /ingest/worker-tick` manual frequente | Bloqueia até 480s |
| `curl localhost:8012` com noports | Sempre falha |
| `grep` agressivo nos logs | Esconde tracebacks |

---

## 7. Tunagem se 429 frequente

Reduzir agressividade:

```bash
PNCP_INGEST_WORKER_CATALOG_BATCH=4
PNCP_INGEST_WORKER_ITEMS_CONCURRENCY=6
PNCP_BUCKET_REFILL_PER_SEC=16
```

---

## 8. Referência completa env

Ver `pncp_researcher_service/app/config.py` — ~80 variáveis `PNCP_*`.

Tabela ingestão detalhada: [03-INGESTAO-24-7.md](./03-INGESTAO-24-7.md)

Comandos operacionais: `docs/deploy/PNCP-COMANDOS-OPERACAO.txt`
