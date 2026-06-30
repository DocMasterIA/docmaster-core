# SLA de alimentação do índice (anti-trava)

**Objetivo:** garantir que a ingestão **nunca fique dias processando só catálogo** enquanto o índice de itens (`pncp_itens`) para de crescer. **Não** promete cobrir os ~800M de linhas do PNCP nacional.

---

## 1. O que é inaceitável

| Cenário | Por que é bug |
|---------|----------------|
| 48h+ com `items_ok=0` e contratos sem itens no SQLite | Worker preso em `catalog_page`; índice não alimenta cotações |
| ~2.000 itens em 2 dias com fila saudável e PNCP respondendo | Throughput abaixo do mínimo arquitetural — indica desbalanceamento ou trava |
| `contract_items` pending = 0 por horas com milhares de contratos sem linhas em `pncp_itens` | Planner/worker não estão fazendo gap-fill |
| Fila 100% catálogo (>300 pending) e zero trabalho de itens | **catalog_heavy** — deve pausar catálogo automaticamente |

**Aceitável:** fila grande de catálogo **desde que** `items_ok > 0` regularmente e `items_ok_1h` suba quando há backlog de itens.

---

## 2. Garantias operacionais (código jun/2026)

Estas são garantias de **software**, não de latência PNCP:

| Garantia | Mecanismo | Threshold default |
|----------|-----------|-------------------|
| Catálogo não monopoliza worker com fila desbalanceada | `compute_ingest_backpressure()` + pause no worker/planner | `catalog_pending ≥ 300` e `items_backlog < 500` |
| Fila de itens alimentada quando baixa | `topup_contract_items_if_starved()` | `items_backlog < 150` → até 1200 contratos/rodada |
| Detecção de parada de **itens** (não só fila geral) | `is_items_feed_stalled()` | `items_ok=0` por **600s** com trabalho de itens pendente |
| Autocura agressiva | `run_stall_recovery_if_needed()` | topup + self-heal + replan; cooldown 120s |
| Batch não preso em HTTP | `asyncio.wait_for` task 180s, batch 480s | requeue `processing` |
| Boot não crasha por dead duplicada | `purge_redundant_dead_tasks()` | antes de `revive_dead_tasks` |

---

## 3. SLA mínimo mensurável

Use estas métricas no DESKTOP/servidor. **Falhar qualquer linha da tabela "deve"** com PNCP saudável (sem 429 massivo) indica regressão ou tunagem necessária.

### Heartbeat (`ingest heartbeat` nos logs)

| Métrica | Deve | Alerta |
|---------|------|--------|
| `items_ok_1h` | **> 0** se existem contratos sem itens ou `contract_items` pending/processing | = 0 por 2h com gap no SQLite |
| `items_stalled` | `False` na maior parte do tempo | `True` por > 20 min |
| `since_items_progress` | < 600s quando há trabalho de itens | > 900s repetido |
| `stalled` | `False` ou recovery dispara em ≤ 15 min | `True` por > 30 min |
| Log `ingest batch` ou `heartbeat` | a cada ≤ 20 min | silêncio > 30 min |

### Fila (`queue_stats()`)

| Métrica | Deve | Alerta |
|---------|------|--------|
| `dead` | ≈ 0 | > 50 sustentado |
| `contract_items` pending+processing | > 0 quando gap SQLite grande | 0 por > 1h com gap |
| Mix catálogo/itens | catálogo pausa quando `catalog_heavy=true` nos logs | só `catalog_ok`, nunca `items_ok` |

### Índice (`local-index/coverage` ou COUNT)

| Métrica | Deve | Alerta |
|---------|------|--------|
| `total_itens` | sobe ao longo de **horas** (não exige a cada 15 min) | flat por **48h** com worker healthy |
| Throughput ordem de grandeza | **dezenas a centenas de itens/hora** com defaults atuais | < 50 itens/dia por 2+ dias |

---

## 4. Módulo `ingest_backpressure.py`

Centraliza regras de pause de catálogo:

```
starving          = items_backlog < 150
catalog_heavy     = catalog_pending ≥ 300 AND items_backlog < 500
pause_high_items  = items_backlog ≥ 3000
pause_catalog     = starving OR catalog_heavy OR pause_high_items
```

Usado por:
- `ingest_planner.py` — não enfileira páginas se `pause_catalog`
- `ingest_worker.py` — `catalog_limit = 0`, boost batch itens para 48

---

## 5. Detecção de stall de itens vs fila geral

**Problema anterior:** stall só olhava `catalog_ok + items_ok` ou queda de `pending`. Worker podia processar catálogo (`catalog_ok=3`) indefinidamente com `items_ok=0` — falso negativo.

**Correção:** `is_items_feed_stalled()` — se há `contract_items` pending/processing ou `items_backlog > 0`, e `seconds_since_items_progress ≥ PNCP_INGEST_ITEMS_STALL_SECONDS` (600s), dispara stall recovery com motivo `items_sem_progresso`.

Heartbeat expõe: `items_ok_1h`, `gap_contratos` (amostra SQLite), `since_items_progress`, `items_stalled`.

---

## 6. Comandos de verificação

```bash
# Fila por tipo
docker exec pncp_researcher_service python -c "
from pncp_researcher_service.app.ingest_queue import queue_stats
print(queue_stats())
"

# Backpressure atual
docker exec pncp_researcher_service python -c "
from pncp_researcher_service.app.ingest_backpressure import compute_ingest_backpressure
print(compute_ingest_backpressure())
"

# Runtime / stall
docker exec pncp_researcher_service python -c "
from pncp_researcher_service.app.ingest_runtime import ingest_runtime_status
print(ingest_runtime_status())
"

# Logs anti-trava
docker logs pncp_researcher_service 2>&1 | grep -E 'heartbeat|catalog_heavy|topup|PARADA|items_ok' | tail -20
```

---

## 7. O que **não** entra neste SLA

- Cobertura de **todo** o PNCP (~800M itens)
- Histórico > 365 dias sem planner multi-janela
- Throughput fixo ignorando 429 da API externa
- Fornecedor em massa na ingestão (Pipeline B on-demand continua separado)

Ver [01-OBJETIVOS-E-ESCOPO.md](./01-OBJETIVOS-E-ESCOPO.md) e [09-GAPS-E-ROADMAP.md](./09-GAPS-E-ROADMAP.md).
