# Ingestão 24/7 — fila, worker, planner

## 1. Modelo mental

A ingestão é uma **fila de trabalho em 2 fases**:

```
catalog_page  →  descobre contratos (GET publicação)
contract_items →  busca linhas de item (GET /itens)
```

Contratos vão para `pncp_contratos`. Itens vão para `pncp_itens` (+ FTS5 via triggers).

**Só `contract_items` aumenta `total_itens`.** Processar catálogo sem enfileirar/processar itens = índice estagnado.

---

## 2. Tabela de fila (`pncp_ingest_queue`)

| Campo | Uso |
|-------|-----|
| `task_type` | `catalog_page` ou `contract_items` |
| `status` | `pending` → `processing` → `done` / `dead` |
| `uf`, `modalidade`, `pagina`, `data_inicial`, `data_final` | Chave catálogo |
| `numero_pncp` | Chave itens |
| `priority` | Menor = mais urgente |
| `attempts` / `max_attempts` | Retry (default 5) → `dead` |

**Índices UNIQUE parciais:** só 1 `pending`/`processing` por chave lógica. Dead duplicadas causavam `IntegrityError` no revive — corrigido com `purge_redundant_dead_tasks()`.

---

## 3. Planner (`ingest_planner.py`)

Executado:
- No boot do worker
- A cada `PNCP_INGEST_PLANNER_INTERVAL_SECONDS` (default **300s**)
- No stall recovery

### 3.1 Enfileira catálogo

Para cada **UF × modalidade** (27 × 5 = 135 scopes):

1. Lê watermark `pncp_ingest_state`
2. Se scope pausado (`paused_until` > now) → skip
3. Calcula `start_page = last_page + 1` (se mesma janela de datas)
4. Enfileira até `PNCP_INGEST_PLANNER_PAGES_PER_SCOPE` páginas (default **8**)

**Pausas de catálogo** (via `compute_ingest_backpressure()` em `ingest_backpressure.py`):

- `pending >= PNCP_INGEST_QUEUE_MAX_PENDING` (default 12000)
- `items_backlog >= PNCP_INGEST_ITEMS_BACKLOG_PAUSE_CATALOG` (3000)
- `items_backlog < PNCP_INGEST_ITEMS_STARVE_BACKLOG` (150) — **starve: prioriza itens**
- `catalog_pending >= PNCP_INGEST_CATALOG_HEAVY_PENDING` (300) **e** `items_backlog < 500` — **catalog_heavy**

### 3.2 Enfileira itens (gap-fill)

SQL: contratos em `pncp_contratos` **sem** linha em `pncp_itens`:

```sql
SELECT c.numero_pncp FROM pncp_contratos c
WHERE NOT EXISTS (SELECT 1 FROM pncp_itens i WHERE i.numero_pncp = c.numero_pncp LIMIT 1)
ORDER BY c.updated_at DESC
LIMIT ?
```

Default **400** por plano; até **1200** quando fila de itens está baixa.

### 3.3 Topup no worker

`topup_contract_items_if_starved()` — chamado no início de cada batch quando `items_backlog < 150`, no máximo a cada 30s.

---

## 4. Worker (`ingest_worker.py`)

### 4.1 Loop principal

```
a cada ~2s:
  1. self-heal (a cada 300s)
  2. planner (a cada 300s)
  3. stall recovery se necessário
  4. process_ingest_batch() [timeout 480s]
  5. heartbeat log (a cada 300s)
  6. sleep
```

### 4.2 Um batch

1. Topup itens se starved (`items_backlog < 150`)
2. `compute_ingest_backpressure()` — se `pause_catalog`, log `catalog_heavy` quando aplicável
3. **Claim itens primeiro** (até 32, paralelo 10; até 48 se catálogo pausado)
4. **Claim catálogo** (até 6) — **0 se `pause_catalog`**
5. HTTP via `pncp_client`
6. `mark_task_done` / `mark_task_failed`

### 4.3 Timeouts (anti-trava)

| Timeout | Default | Efeito |
|---------|---------|--------|
| `PNCP_INGEST_TASK_TIMEOUT_SECONDS` | 180s | Falha tarefa individual |
| `PNCP_INGEST_BATCH_MAX_SECONDS` | 480s | Requeue all `processing`, continua loop |

### 4.4 Após catálogo bem-sucedido

Se `PNCP_LOCAL_INCLUDE_ITEMS=1` e backlog itens < 3000:
- Para cada contrato na página: `enqueue_contract_items` se `contract_needs_items_refresh()`

Refresh skip: itens buscados há < `PNCP_INGEST_ITEMS_REFRESH_DAYS` (7) dias.

---

## 5. Watermark (`pncp_ingest_state`)

Por `(uf, modalidade)`:

| Campo | Significado |
|-------|-------------|
| `last_page` | Última página completa processada |
| `last_data_inicial/final` | Janela em curso |
| `paused_until` | Autopause após 429/timeout/JSON inválido |
| `error_streak` | Backoff exponencial |
| `total_upserts` / `total_item_upserts` | Contadores acumulados |

**Fim de catálogo:** resposta com `< 10` contratos → `last_page = 0` (recomeça do topo na próxima varredura).

**Mudança de janela de datas** (ex.: novo dia, rolling 365d) → watermark reinicia página 1.

---

## 6. Autocura

### `ingest_maintenance.py`

| Função | Quando |
|--------|--------|
| `requeue_processing_tasks` | Startup: all; periodic: stale > 900s |
| `purge_redundant_dead_tasks` | Antes de reviver dead |
| `revive_dead_tasks` | Dead antigas → pending |
| `resume_expired_ingest_scopes` | Scopes pausados expirados |

### `ingest_runtime.py`

| Função | Quando |
|--------|--------|
| `maybe_log_heartbeat` | Prova de vida; expõe `items_ok_1h`, `items_stalled` |
| `is_items_feed_stalled` | `items_ok=0` por 600s com trabalho de itens pendente |
| `run_stall_recovery_if_needed` | Stall de itens **ou** fila ≥100 sem progresso 900s |

**Limitação conhecida:** stall recovery só corre **entre batches**. Batch preso dentro de HTTP > 480s é tratado pelo batch timeout.

---

## 7. Backpressure (diagrama)

```
items_backlog < 150              → STARVE: pausa catálogo, topup até 1200 itens
catalog_pending ≥ 300            → CATALOG_HEAVY (se items_backlog < 500): pausa catálogo
items_backlog 150–2999           → normal: catálogo + itens
items_backlog ≥ 3000             → pausa catálogo, só itens (batch até 48)
pending ≥ 12000                  → planner para de enfileirar catálogo
```

Detalhe completo: [10-SLA-ALIMENTACAO.md](./10-SLA-ALIMENTACAO.md)

---

## 8. Throughput esperado (ordem de grandeza)

Com defaults atuais (pós jun/2026):

- **Itens:** até 32/batch × 10 paralelos, batch a cada ~2–8 min → dezenas a centenas de itens/hora (depende PNCP)
- **Catálogo:** 6 páginas × ~50 contratos/página por batch → centenas de contratos/hora
- **Gargalo real:** rate limit PNCP (429), latência HTTP, fila grande de catálogo sem itens correspondentes

**Sintoma "índice não sobe":** fila só com `catalog_page`, `contract_items` pending = 0, `items_ok=0` por horas. Ver `catalog_heavy`, topup, stall `items_sem_progresso`.

---

## 9. Ficheiros e testes

| Ficheiro | Testes |
|----------|--------|
| `ingest_worker.py` | — |
| `ingest_planner.py` | `test_ingest_planner.py` |
| `ingest_queue.py` | `test_ingest_queue.py` |
| `ingest_maintenance.py` | `test_ingest_maintenance.py` |
| `ingest_runtime.py` | `test_ingest_runtime.py` |
| `ingest_backpressure.py` | `test_ingest_backpressure.py` |
| `ingest_dates.py` | `test_ingest_dates.py` |

Deploy hotfix: `scripts/deploy-pncp-researcher-code.sh`
