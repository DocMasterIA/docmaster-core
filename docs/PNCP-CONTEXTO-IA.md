# PNCP — contexto consolidado para IA

**Atualizado:** junho/2026  
**Audiência:** agentes de código, revisão e operação — leitura única antes de alterar PNCP ou fornecedor.  
**Humano:** [`PNCP-DECLARATIVO.md`](PNCP-DECLARATIVO.md) (estado repo) · [`deploy/PNCP-COMANDOS-OPERACAO.txt`](deploy/PNCP-COMANDOS-OPERACAO.txt) (comandos)

---

## 1. Mapa de documentos

| Documento | Uso |
|-----------|-----|
| **Este ficheiro** | Contexto completo ingest + fornecedor + produção + armadilhas |
| [`PNCP-DECLARATIVO.md`](PNCP-DECLARATIVO.md) | Estado declarativo do repositório |
| [`PLANO-MODULO-COBERTURA-FORNECEDOR-PNCP.md`](PLANO-MODULO-COBERTURA-FORNECEDOR-PNCP.md) | Plano fornecedor (fases R0–R5, B–F) |
| [`deploy/PNCP-COMANDOS-OPERACAO.txt`](deploy/PNCP-COMANDOS-OPERACAO.txt) | Todos os comandos (monitor, backup, deploy) |
| [`deploy/PNCP-INGESTAO-INDEX-24-7.md`](deploy/PNCP-INGESTAO-INDEX-24-7.md) | Ingestão (parcialmente pré-worker) |
| [`deploy/PNCP-RESEARCHER-24-7.md`](deploy/PNCP-RESEARCHER-24-7.md) | Stack isolada |
| [`deploy/PNCP-API-INDICE-LOCAL.md`](deploy/PNCP-API-INDICE-LOCAL.md) | Endpoints busca/FTS |
| [`PESQUISADOR_PNCP_FUNCIONAMENTO_ATUAL.md`](PESQUISADOR_PNCP_FUNCIONAMENTO_ATUAL.md) | Fluxo pesquisador |
| [`PNCP_BUSCA_INTELIGENTE_IA.md`](PNCP_BUSCA_INTELIGENTE_IA.md) | Busca com LLM |
| [`PNCP-TESTES-FORNECEDOR.md`](PNCP-TESTES-FORNECEDOR.md) | **Checklist de testes** homolog + CNPJ |
| [`PNCP-FORNECEDOR-RELATORIO-REGRAS.md`](PNCP-FORNECEDOR-RELATORIO-REGRAS.md) | **Regras invariantes** — enrich, PDF, busca lote (não regredir) |

---

## 2. Resumo executivo (facts)

1. **Dois pipelines independentes:** (A) ingestão volume via `GET /itens`; (B) fornecedor via `GET /resultados` on-demand ou futuro backfill.
2. **Ingest saudável ≠ CNPJ alto no índice.** ~1,5M `pncp_itens` pode coexistir com `cobertura_cnpj_pct` baixo.
3. **Meta fornecedor 70–90%** aplica-se a **itens homologados na cotação/PDF**, não ao SQLite bruto.
4. **Worker** é o modo 24/7 recomendado; **loop bash** = rajada (não paralelo com worker).
5. **`PNCP_INGEST_ITEMS_REFRESH_DAYS=7`** evita retrabalho de `GET /itens` (default no compose).
6. **DESKTOP/WSL:** usar `docker-compose.pncp.noports.yml` — porta 8012 no host falha; API via `docker exec`.
7. **`docker compose up --force-recreate` sem rebuild** restaura **imagem antiga** — usar `scripts/deploy-pncp-researcher-code.sh` após recreate.
8. **Fase B / R2 pendente:** backfill `/resultados` na ingestão para CNPJ no índice em massa.

---

## 3. Pipeline A — Ingestão 24/7

### 3.1 Arquitetura

```
Planner (900s) → pncp_ingest_queue → Worker (poll 2s)
  catalog_page     → search_contracts → upsert_contracts → enqueue contract_items
  contract_items   → get_contract_items → upsert_contract_items
```

| Módulo | Ficheiro |
|--------|----------|
| Janela 365d | `ingest_dates.py` |
| Fila SQLite | `ingest_queue.py` |
| Enfileirar | `ingest_planner.py` |
| Processar | `ingest_worker.py` |
| Métricas | `ingest_coverage.py` |

Lifespan FastAPI (`api.py` v1.1.0) inicia `ingest_worker_loop()` se `PNCP_INGEST_WORKER_ENABLED=1`.

### 3.2 Comportamento do worker

| Regra | Valor default |
|-------|----------------|
| Ordem | **Itens antes de catálogo** |
| Pausa catálogo se | `backlog_by_task_type(contract_items) >= 3000` |
| Batch itens normal | 28 |
| Batch itens drenagem | 40 |
| Batch catálogo | 3 (0 se pausado) |
| Planner | 4 páginas/scope/15 min |
| Cap fila total | 5000 pending (planner para catálogo) |

**`items_backlog` (worker/logs):** `pending + processing` só de `contract_items`.  
**Armadilha:** coverage API `by_task_type.contract_items.pending` **não** inclui `processing` — usar SQL ou logs `items_backlog=`.

Logs saudáveis:
```
ingest batch catalog_ok=0 items_ok=40 errors=0 pending=... items_backlog=6500 catalog_paused=True
ingest batch catalog_ok=3 items_ok=28 errors=0 pending=... items_backlog=2700 catalog_paused=False
```

### 3.3 Skip retrabalho (`PNCP_INGEST_ITEMS_REFRESH_DAYS=7`)

- Função: `contract_needs_items_refresh()` em `local_index.py`
- Se contrato **já tem itens** e `MAX(updated_at)` &lt; 7 dias → **não** chama PNCP `/itens`
- Aplica: worker (enqueue + process), backfill bash
- Contratos **sem itens** → sempre busca
- **Efeito:** `itens tocados em 48h` >> `itens novos neto`; medir crescimento com delta de `COUNT(*)` no tempo

### 3.4 Loop bash (rajada — legado)

| | Worker | Loop bash |
|---|--------|-----------|
| Throughput | ~15–25k itens/h cruzeiro; 40/tick drenagem | ~25–35k itens/h pico |
| Paralelo itens | Sequencial (28–40) | 12× (`PNCP_BACKFILL_ITEM_CONCURRENCY`) |
| Páginas/UF | 4/15 min | 60/ciclo |
| 24/7 | Dentro contentor `restart: always` | `nohup` no host — morre no reboot |
| Com worker | **NUNCA paralelo** | Desligar worker: `PNCP_INGEST_WORKER_ENABLED=0` |

### 3.5 Watermark, autopause, json_invalid

- `pncp_ingest_state`: `last_page`, `paused_blocked`, `last_error_kind`
- UFs problemáticas recorrentes: **PR, SC, RO, RR** (`json_invalid`)
- Reset scopes: `UPDATE pncp_ingest_state SET status='active' ... WHERE status='paused_blocked'`
- Requeue fila: `UPDATE pncp_ingest_queue SET status='pending' WHERE status='processing'`
- Retry JSON: `PNCP_INGEST_JSON_INVALID_RETRIES=3`

### 3.6 Métricas — como interpretar

| Métrica | Bom | Ruim |
|---------|-----|------|
| `sem_itens` | &lt; 500 | &gt; 2000 crescendo |
| `pending` total | 2k–4k estável | &gt; 5k subindo |
| `items_backlog` worker | &lt; 3k cruzeiro; drenagem ok se &gt; 3k com catalog_paused | &gt; 6k + catalog_ok=3 |
| `scopes_paused` | 0–10 | &gt; 15 persistente |
| `total_itens` delta 5 min | qualquer + com skip | 0 por horas + pending alto |

### 3.7 Deploy código (DESKTOP)

```bash
~/docmaster-core/scripts/deploy-pncp-researcher-code.sh
```

Copia: `config.py`, `local_index.py`, `ingest_worker.py`, `ingest_planner.py`, `ingest_queue.py`.  
Confirma: `from ...local_index import contract_needs_items_refresh` → `skip_fn ok`.

Compose (3 ficheiros):
```bash
docker compose -f ~/docker-compose.pncp.yml \
  -f ~/docker-compose.pncp.override.yml \
  -f ~/docker-compose.pncp.noports.yml up -d pncp_researcher_service
```

### 3.8 Produção DESKTOP (jun/2026 — referência)

| Item | Valor observado |
|------|-----------------|
| Volume | `docmaster-pncp_pncp_researcher_data` |
| DB size | ~5 GB |
| `total_itens` | ~1,49M |
| Envs ativos | `REFRESH_DAYS=7`, `SEARCH_ONLY_HOMOLOGATED=1`, `ENRICH_HOMOLOG_MAX=16` |
| Incidente resolvido | Fila 7k + código antigo pós-recreate → deploy script + requeue processing |

---

## 4. Pipeline B — Itens homologados + fornecedor (CNPJ)

### 4.1 Problema de negócio

Relatório de Pesquisa de Preços precisa **razão social + CNPJ** em linhas PNCP homologadas. Histórico ~20% cobertura. Meta **70–90%** (plano: 100% no subconjunto homologado quando PNCP publicar vencedor).

### 4.2 O que ingest NÃO faz

- `upsert_contract_items` usa só **`/itens`** (catálogo)
- Preenche: descrição, valores, `situacao_item`, `situacao_compra`, `fornecedor_elegivel`
- **Não** preenche `cnpj_fornecedor` / `fornecedor` em massa

### 4.3 Colunas SQLite `pncp_itens` (fornecedor)

Migradas em `local_index.py` (`_migrate_pncp_itens_supplier_columns`):

| Coluna | Uso |
|--------|-----|
| `cnpj_fornecedor` | CNPJ vencedor |
| `fornecedor` | Razão social |
| `fornecedor_fonte` | ex. `pncp_resultado_item`, `brasilapi` |
| `situacao_item`, `situacao_compra` | Filtro homolog |
| `fornecedor_elegivel` | 0/1 — elegível para relatório |

Índice: `idx_pncp_itens_fornecedor_elegivel`.

### 4.4 Filtro homologados (implementado)

| Camada | Config |
|--------|--------|
| Researcher | `PNCP_SEARCH_ONLY_HOMOLOGATED=1` |
| Busca API | `somente_homologados` (default → config) |
| Frontend | `somente_homologados: true` em manual/IA |
| Backend add source | `PNCP_ADD_SOURCE_ONLY_HOMOLOGATED=1` |

Funções: `item_homologado_para_busca`, `_row_passes_homolog_filter`, tokens `homolog`, `adjudic`, `encerr`.

### 4.5 Enriquecimento on-demand (camadas)

Ordem típica de resolução (`supplier_resolver.py`, `pncp_client.py`, `pncp_supplier_enrichment.py`):

1. Campos já no índice / `source` da cotação
2. Parse `raw_json_zlib` / resultado inline
3. `GET .../itens/{n}/resultados` → fallback `GET .../resultados`
4. BrasilAPI por CNPJ (`fornecedor_cache.py`, TTL ~90d)
5. Propagação CNPJ→nome dentro da mesma cotação (`pncp_relatorio_itens.py`)

| Momento | Limites (settings) |
|---------|-------------------|
| Busca `local_item_search` | 16 (`PNCP_SEARCH_ENRICH_HOMOLOG_MAX`) |
| Adicionar fonte | 48 PNCP + 48 BrasilAPI |
| PDF relatório | 96 PNCP + 64 BrasilAPI |

Desligar PDF enrich: `PNCP_RELATORIO_PDF_SKIP_ENRICH=true`.

### 4.6 Limitações reais (não são bugs)

- PNCP **HTTP 204** em `/resultados` → sem CNPJ mesmo homologado
- Lógica **duplicada** researcher ↔ backend — risco divergência
- Granularidade: enrich por **`numero_item`** melhorou; ingest em massa por item **não**
- Tetos HTTP: busca 16 vs PDF 96 — cotação grande pode precisar PDF para completar

### 4.7 Auditoria (métrica de produto)

```bash
docker exec backend python manage.py audit_pncp_homologados_coverage --cotacao-id <ID>
docker exec backend python manage.py audit_pncp_supplier_coverage --cotacao-id <ID> --only-missing
docker exec backend python manage.py audit_pncp_supplier_coverage --cotacao-id <ID> --json
```

Índice bruto:
```bash
docker exec pncp_researcher_service python -c "
import urllib.request, json
d=json.loads(urllib.request.urlopen(
  'http://127.0.0.1:8012/api/pncp-research/local-index/stats', timeout=120).read())
print(json.dumps(d.get('fornecedor'), indent=2))
"
```

**Não** usar `cobertura_cnpj_pct` total como KPI de produto sem Fase B.

### 4.8 Fases pendentes (fornecedor)

| Fase | Entrega | Prioridade sugerida |
|------|---------|---------------------|
| **R1** | Fallback contratos sem `/resultados` | Média |
| **R2 / Fase B** | Backfill `/resultados` na ingestão/worker | **Alta** se audit &lt; meta |
| **R3** | Job reprocessamento homologados antigos | Média |
| **R4** | UI badge `gap_reason` ao adicionar fonte | UX |
| **R5** | PDF texto «Não publicado PNCP (204)» | Jurídico |

Detalhe: [`PLANO-MODULO-COBERTURA-FORNECEDOR-PNCP.md`](PLANO-MODULO-COBERTURA-FORNECEDOR-PNCP.md).

---

## 5. Índice de ficheiros (alterar PNCP / fornecedor)

### Researcher
```
pncp_researcher_service/app/
  api.py, config.py, local_index.py, pncp_client.py, service.py, schemas.py
  ingest_dates.py, ingest_queue.py, ingest_planner.py, ingest_worker.py, ingest_coverage.py
  supplier_resolver.py, fornecedor_cache.py, supplier_probe.py
tests/test_ingest_*.py, tests/test_ingest_refresh.py, tests/test_supplier_resolver.py
```

### Backend
```
backend/app/services/pncp_supplier_enrichment.py
backend/app/services/pncp_supplier_gap_audit.py
backend/app/services/pncp_relatorio_itens.py, pncp_relatorio_pdf.py
backend/app/pncp_cotacao_api.py, pncp_relatorio_api.py, pncp_research_proxy.py
backend/app/management/commands/audit_pncp_*.py
backend/mdlicitatech/settings.py  (PNCP_ADD_SOURCE_*, PNCP_RELATORIO_PDF_*)
```

### Frontend
```
frontend-vue/src/views/BuscaManualCotacoes.vue, BuscaInteligenteCotacoes.vue, CotacaoDetalhe.vue
frontend-vue/src/services/pncpResearch.js
```

### Deploy / ops
```
docker-compose.pncp.yml
docker-compose.pncp.noports.yml.example
scripts/deploy-pncp-researcher-code.sh
scripts/ensure-pncp-researcher.sh
scripts/run-pncp-index-ingest-loop.sh
docs/deploy/PNCP-COMANDOS-OPERACAO.txt
```

---

## 6. Anti-padrões (não fazer)

| Erro | Consequência |
|------|--------------|
| Worker + loop bash 24/7 | Fila 8k+, `sem_itens` inflado |
| `docker compose down -v` no PNCP | Apaga índice |
| `force-recreate` sem `deploy-pncp-researcher-code.sh` | Código antigo, skip/pause quebrados |
| `curl localhost:8012` com noports | Falso negativo |
| Medir ingest só com `updated_at 48h` | Conta re-upsert, não neto |
| Reset pausas em loop sem reduzir carga | `json_invalid` infinito PR/SC |
| Esperar CNPJ alto em 1,5M itens sem Fase B | Expectativa errada |

---

## 7. Decisões de desenho (para IA não reverter sem motivo)

1. **Worker vs rajada:** worker = estabilidade 24/7; bash = campanha volume.
2. **Pausa catálogo em 3000:** evita catálogo >> itens (`sem_itens`).
3. **Skip 7d:** reduz carga PNCP; refresh semanal suficiente para homologação.
4. **Fornecedor on-demand:** entrega valor antes de Fase B; Fase B é evolução, não pré-requisito do worker.
5. **Só homologados na busca:** decisão produto jun/2026 — não expor «Em andamento» na pesquisa de preços.
6. **backlog = pending + processing:** fix jun/2026 — não usar só pending para pausar catálogo.

---

## 8. Próximo trabalho sugerido (fornecedor)

1. `audit_pncp_homologados_coverage` em cotações reais no DESKTOP.
2. Classificar gaps (`pncp_supplier_gap_audit`: 204, sem resultado, timeout).
3. Implementar **R2/Fase B:** após `upsert_contract_items`, fetch `/resultados` por item elegível (com rate limit e fila separada).
4. Unificar extração researcher ↔ backend (pacote compartilhado ou researcher como SOA).
5. Opcional: paralelo itens no worker (aproximar rajada sem bash).

**Checklist de testes manuais:** [`PNCP-TESTES-FORNECEDOR.md`](PNCP-TESTES-FORNECEDOR.md).

---

## 9. Envs compose (`docker-compose.pncp.yml` — defaults produção)

```
PNCP_INGEST_WORKER_ENABLED=1
PNCP_INGEST_QUEUE_ENABLED=1
PNCP_INGEST_ITEMS_REFRESH_DAYS=7
PNCP_INGEST_ITEMS_BACKLOG_PAUSE_CATALOG=3000
PNCP_INGEST_QUEUE_MAX_PENDING=5000
PNCP_SEARCH_ONLY_HOMOLOGATED=1
PNCP_SEARCH_ENRICH_HOMOLOG_MAX=16
PNCP_LOCAL_BACKFILL_DAYS=365
```

Backend (stack principal): `PNCP_RELATORIO_PDF_MAX_PNCP_LOOKUPS=96`, `PNCP_ADD_SOURCE_MAX_PNCP_LOOKUPS=48`, etc.

---

*Manter este ficheiro atualizado quando mudar ingest, fornecedor ou lições de produção.*
