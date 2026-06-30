# Casos de falha e autocura

## 1. Matriz de falhas

| Sintoma | Causa provável | Autocura | Intervenção manual |
|---------|----------------|----------|-------------------|
| Loop `ingest worker encerrou com erro` 5s | Exception no startup (ex. IntegrityError dead) | Supervisor reinicia | Deploy fix maintenance |
| `IntegrityError` UNIQUE na fila | dead + pending mesma chave | `purge_redundant_dead_tasks` | Deploy jun/2026 |
| `pending` alto, `items_ok=0` | Só catálogo na fila | backpressure + topup + stall itens 600s | Deploy jun/2026 |
| Batch 20+ min sem log | HTTP PNCP preso | Task timeout 180s + batch 480s | Aguardar ou restart |
| `stalled=true` 900s+ | Sem progresso com fila cheia | stall recovery | Verificar PNCP/API |
| `items_stalled=true` | Catálogo OK mas `items_ok=0` 600s+ | stall `items_sem_progresso` + topup | Ver [10-SLA-ALIMENTACAO.md](./10-SLA-ALIMENTACAO.md) |
| `dead` subindo | 5 falhas por tarefa | revive após 1h | Investigar erro PNCP |
| Scope `paused_blocked` | 429/timeout/json | `resume_expired` + backoff | Aguardar |
| Contentor unhealthy | Crash uvicorn / DB | restart: always | `docker logs` |
| Porta 8012 host erro 500 | Docker Desktop WSL | noports | Usar docker exec |
| Coverage timeout 15s | COUNT em 5GB DB | — | timeout 120s ou queue_stats |
| Fornecedor `pncp_*` no PDF | Bug fonte + backend | — | Deploy researcher + backend |

---

## 2. Incidentes reais (jun/2026)

### 2.1 Crash loop IntegrityError

**Logs:**
```
sqlite3.IntegrityError: UNIQUE constraint failed: pncp_ingest_queue...
ingest worker encerrou com erro — reinício em 5s
```

**Causa:** `revive_dead_tasks` tentava reativar dead com mesma chave que pending existente, ou múltiplas dead com mesma chave.

**Fix:**
- `purge_redundant_dead_tasks()` antes de reviver
- try/except no self-heal startup
- Supervisor com traceback legível

**Verificação:** boot log `ingest self-heal (startup): ... dead_purged=N ...` sem IntegrityError.

### 2.2 Índice estagnado (~1,54M)

**Sintoma:** `catalog_ok=3`, `items_ok=0`, pending ~1300+ catálogo, 0 contract_items.

**Causa:** Worker consumia 100% em catálogo; planner alimentava só 200 itens/15min.

**Fix (fase 1):**
- `topup_contract_items_if_starved`
- Pausa catálogo quando items_backlog < 150
- Paralelo 10 itens, timeouts, defaults maiores

**Fix (fase 2 — anti-trava jun/2026):**
- `ingest_backpressure.py` — `catalog_heavy` quando ≥300 catalog pending e poucos itens
- `is_items_feed_stalled()` — stall em 600s sem `items_ok` (não confundir com `catalog_ok`)
- Heartbeat com `items_ok_1h`, stall recovery chama topup

### 2.3 Batch lento (~7–20 min)

**Causa:** 3 chamadas PNCP sequenciais × timeout 120s × retries.

**Mitigação:** task timeout 180s, batch timeout 480s, catalog batch 6, itens paralelos.

### 2.4 Docker recreate falhou porta 8012

**Causa:** Docker Desktop port forward 500.

**Fix:** `docker-compose.pncp.noports.yml` — contentor sobe com `8012/tcp` interno only.

---

## 3. Camadas de autocura (stack)

```
Camada 1 — Task level
  mark_task_failed + retry 120s
  task timeout 180s

Camada 2 — Batch level
  batch timeout 480s → requeue processing

Camada 3 — Periodic (300s)
  requeue stale processing
  revive dead
  resume scopes

Camada 4 — Stall
  items: 600s sem items_ok com trabalho de itens → recovery (items_sem_progresso)
  fila geral: 900s sem progresso + pending ≥ 100 → recovery (fila_sem_progresso)

Camada 5 — Supervisor
  worker crash → restart 5s

Camada 6 — Docker
  restart: always
  healthcheck 30s
```

---

## 4. Sinais nos logs

| Log | Significado |
|-----|-------------|
| `ingest worker iniciado poll=2.0s` | Worker OK |
| `ingest self-heal (startup):` | Boot heal OK |
| `ingest purge dead redundantes removidas=` | Dedup dead |
| `ingest topup itens enfileirados=` | Fila itens alimentada |
| `ingest batch catalog_ok=X items_ok=Y` | Progresso |
| `ingest heartbeat ... stalled=False` | Vivo |
| `ingest catálogo pausado (heavy)` | catalog_heavy — backpressure ativo |
| `ingest heartbeat ... items_ok_1h=` | Throughput itens última hora |
| `ingest PARADA detectada (items_sem_progresso` | Stall de alimentação de itens |
| `ingest batch timeout` | Batch liberado à força |
| `ingest catalog task N: timeout` | PNCP lento, task failed |

---

## 5. Playbook rápido

### Fila não anda (>30 min sem batch)

```bash
docker logs pncp_researcher_service 2>&1 | tail -40
docker restart pncp_researcher_service
# self-heal no boot devolve processing
```

### `dead` > 100

```bash
docker exec pncp_researcher_service python -c "
from pncp_researcher_service.app.ingest_maintenance import run_ingest_self_healing
print(run_ingest_self_healing(mode='startup'))
"
```

### Muitos scopes pausados

```bash
docker exec pncp_researcher_service python -c "
import urllib.request, json
d=json.loads(urllib.request.urlopen('http://127.0.0.1:8012/api/pncp-research/local-index/ingest-status',timeout=60).read())
print('paused', sum(1 for s in d.get('scopes',[]) if s.get('paused_until')))
"
```

Aguardar backoff ou reduzir concorrência se 429 persistente.

---

## 6. Garantias honestas

| Garantido | Não garantido |
|-----------|---------------|
| Worker reinicia após crash | Latência PNCP baixa |
| Dead duplicado não crasha boot | `pending` monotônico decrescente |
| Stall recovery em ~15 min entre batches | Zero 429 |
| Stall de itens em ~10 min (`items_stall=600s`) | Índice sobe X/hora fixo |
| Fila processing recuperada após timeout | Histórico > 365d automático |
| `catalog_heavy` evita dias só em catálogo | Cobertura total PNCP |
