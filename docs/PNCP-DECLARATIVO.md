# PNCP — documento declarativo (estado do repositório)

**Atualizado:** junho/2026  
**Escopo:** tudo implementado no DocMaster ligado ao **Pesquisador PNCP** — ingestão do índice local, busca, homologados, cobertura de fornecedor (CNPJ), cotação, relatório PDF e operação em produção.

**Contexto IA (completo):** [`PNCP-CONTEXTO-IA.md`](PNCP-CONTEXTO-IA.md) — ingest + fornecedor + produção + anti-padrões.  
**Regras de referência (fornecedor/PDF/enrich):** [`PNCP-FORNECEDOR-RELATORIO-REGRAS.md`](PNCP-FORNECEDOR-RELATORIO-REGRAS.md).

**Planejamento fino (análise jun/2026):** [`PNCP-PLANEJAMENTO/00-INDICE.md`](PNCP-PLANEJAMENTO/00-INDICE.md) — objetivos, arquitetura, ingestão, gaps e roadmap em série de `.md`.

Este ficheiro é a **fonte declarativa** do estado do repositório. Comandos: [`deploy/PNCP-COMANDOS-OPERACAO.txt`](deploy/PNCP-COMANDOS-OPERACAO.txt).

---

## 1. Objetivos de produto

| Objetivo | Como é atendido |
|----------|-----------------|
| Índice local profundo (365 dias, 27 UFs, modalidades 6–10) | Ingestão 24/7 no SQLite + watermark por UF/modalidade |
| Busca rápida no índice | FTS5 (`pncp_itens_fts`) + fallback LIKE |
| Complemento quando o índice é raso | Busca híbrida (PNCP ao vivo) |
| Só preços de itens **homologados/adjudicados** | Filtro em `local_item_search` + flags no frontend/backend |
| Fornecedor (CNPJ + razão social) na cotação/PDF | Enriquecimento on-demand PNCP `/resultados` + BrasilAPI |
| Métricas operacionais | `/local-index/coverage`, `supplier_coverage_stats`, comandos `audit_*` |

**Meta de negócio (fornecedor):** 70–90% de identificação em itens **elegíveis** na cotação/relatório — não necessariamente no índice bruto de ~1M+ linhas.

---

## 2. Arquitetura — dois pipelines independentes

```
┌─────────────────────────────────────────────────────────────────────────┐
│  PIPELINE A — Ingestão 24/7 (volume de itens no SQLite)                 │
│                                                                         │
│  Planner (15 min) ──► Fila SQLite ──► Worker asyncio (2 s)            │
│       │                    │                    │                       │
│       │ catalog_page       │ contract_items     │ GET /itens (catálogo) │
│       ▼                    ▼                    ▼                       │
│  pncp_contratos ──────────────────────────► pncp_itens                  │
│  (sem CNPJ em massa — endpoint /itens não traz vencedor por linha)      │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  PIPELINE B — Homologados + CNPJ (qualidade na busca/cotação/PDF)       │
│                                                                         │
│  local_item_search ──► filtro homologado ──► enrich até 16 (PNCP+API)   │
│  adicionar fonte   ──► backend enrich (24 PNCP + 48 BrasilAPI)        │
│  gerar PDF         ──► enrich até 96 PNCP + 64 BrasilAPI                │
│  (GET /resultados por item/compra — não faz parte do Pipeline A)        │
└─────────────────────────────────────────────────────────────────────────┘
```

**Declaração:** drenar a fila de `contract_items` **melhora** a busca homologada (mais linhas com `situacao_*`), mas **não** preenche CNPJ em massa no índice. CNPJ continua **on-demand** até implementar Fase B (backfill `/resultados`).

---

## 3. Stack e deploy

| Item | Valor |
|------|-------|
| Serviço | `pncp_researcher_service` (FastAPI **1.1.0**) |
| Porta | `8012` (opcional no host via `docker-compose.pncp.noports.yml`) |
| Compose | `docker-compose.pncp.yml`, projeto `docmaster-pncp` |
| SQLite | `/data/pncp/pncp_researcher_local.db` |
| Volume produção (DESKTOP) | `docmaster-pncp_pncp_researcher_data` |
| Rede | `docmaster_net` (backend usa `PNCP_RESEARCHER_BASE_URL=http://pncp_researcher_service:8012`) |
| Restart | `always` |

O stack principal (`docmaster`) **não** deve recriar o contentor PNCP.

---

## 4. Ingestão — Fase 1 (fila + worker)

Substitui o loop bash como **mecanismo principal** quando `PNCP_INGEST_WORKER_ENABLED=1` (default no compose).

### 4.1 Módulos novos

| Ficheiro | Responsabilidade |
|----------|------------------|
| `pncp_researcher_service/app/ingest_dates.py` | Janela **365 dias** (`resolve_backfill_window`) |
| `pncp_researcher_service/app/ingest_queue.py` | Tabela `pncp_ingest_queue`, enqueue/claim/done/fail |
| `pncp_researcher_service/app/ingest_planner.py` | Enfileira catálogo + backlog de contratos sem itens |
| `pncp_researcher_service/app/ingest_worker.py` | Worker asyncio; processa lote a cada poll |
| `pncp_researcher_service/app/ingest_coverage.py` | Agrega métricas para `/local-index/coverage` |

### 4.2 Tipos de tarefa na fila

| `task_type` | Origem | Ação HTTP |
|-------------|--------|-----------|
| `catalog_page` | Planner | `search_contracts` → `upsert_contracts` → enfileira `contract_items` |
| `contract_items` | Planner (backlog) ou catálogo | `get_contract_items` → `upsert_contract_items` |

Estados: `pending` → `processing` → `done` | `failed` | `dead` (após `max_attempts`).

### 4.3 Comportamento do worker (declarado)

1. **Itens antes de catálogo** — reduz `contratos_sem_itens` e backlog.
2. Pausa catálogo se **`backlog_by_task_type(contract_items) >= 3000`** (`pending + processing`, não só pending).
3. Se pausado: `catalog_ok = 0`, `items_ok` até **40**; planner não enfileira catálogo.
4. Planner a cada **900 s**; no máximo **4** páginas por scope (UF × modalidade).
5. Fila total cap: **5000** pending antes de planner parar catálogo.
6. Logs incluem `items_backlog` e `catalog_paused` por batch.
7. Lifespan FastAPI inicia `ingest_worker_loop()` se worker habilitado.

### 4.3.1 Skip de retrabalho (`PNCP_INGEST_ITEMS_REFRESH_DAYS`)

Com **N > 0**, contratos que **já têm itens** no SQLite e `MAX(updated_at)` dentro de N dias **não** disparam GET `/itens` (worker, catálogo e backfill). Default **7** no compose e no código (`0` = sempre busca, legado).

### 4.4 Watermark e autopause (legado mantido)

- `pncp_ingest_state`: `last_page`, pausas `paused_blocked`, `last_error_kind`.
- `PNCP_INGEST_WATERMARK_RESUME=1`: retoma em `last_page + 1`.
- Autopause em rate limit / timeout / `json_invalid` com backoff configurável.
- **`pncp_client.py`:** retry dedicado em corpo JSON inválido (**3** tentativas, backoff 2 s).

### 4.5 Loop bash (legado)

| Script | Estado |
|--------|--------|
| `scripts/run-pncp-index-ingest-loop.sh` | Ainda existe; POST `/local-index/backfill` com `days: 365` |
| Com worker ativo | **Não correr em paralelo** — duplica carga e infla `pending` |

### 4.6 SQLite — WAL e tabelas relevantes

- `PRAGMA journal_mode=WAL` em conexões de fila e índice.
- `pncp_contratos`, `pncp_itens`, `pncp_ingest_state`, `pncp_ingest_queue`, `pncp_itens_fts`, `pesquisador_sessoes`.
- Colunas de fornecedor em `pncp_itens`: `cnpj_fornecedor`, `fornecedor`, `fornecedor_elegivel` (preenchimento principal via enrich, não via ingest `/itens`).

### 4.7 Testes unitários (ingest)

| Ficheiro | Cobertura |
|----------|-----------|
| `pncp_researcher_service/tests/test_ingest_dates.py` | Janela 365 dias |
| `pncp_researcher_service/tests/test_ingest_queue.py` | CRUD da fila |
| `pncp_researcher_service/tests/test_ingest_refresh.py` | Skip `REFRESH_DAYS` |

### 4.8 Deploy hotfix

| Script | Função |
|--------|--------|
| `scripts/deploy-pncp-researcher-code.sh` | Copia app PNCP para contentor + restart + valida `skip_fn` |

**Armadilha:** `docker compose up --force-recreate` repõe **imagem** antiga — sempre correr deploy script ou rebuild após recreate.

---

## 5. Homologados e fornecedor (Fase A+)

### 5.1 Filtro homologado

| Camada | Config / flag | Default |
|--------|---------------|---------|
| Researcher | `PNCP_SEARCH_ONLY_HOMOLOGATED` | `true` |
| API busca | `somente_homologados` em `MarketSearchRequest` | omissão → config do serviço |
| Frontend manual/IA | `somente_homologados: true` | fixo nas views de cotação |
| Backend adicionar fonte | `PNCP_ADD_SOURCE_ONLY_HOMOLOGATED` | `true` |

Lógica: `item_homologado_para_busca`, `_row_passes_homolog_filter`, situações elegíveis (`homolog`, `adjudic`, `encerr`).

### 5.2 Enriquecimento de CNPJ (on-demand)

| Momento | Limites (defaults) | Módulo |
|---------|-------------------|--------|
| Busca local (`local_item_search`) | **16** homologados sem CNPJ | `_enrich_homolog_items_from_pncp_sync` |
| Adicionar fonte à cotação | **48** PNCP + **48** BrasilAPI | `pncp_supplier_enrichment.py` |
| PDF relatório | **96** PNCP + **64** BrasilAPI | `enrich_missing_supplier_fields_for_cotacao` |

Desligar enrich no PDF: `PNCP_RELATORIO_PDF_SKIP_ENRICH=true`.

### 5.3 Módulos de fornecedor (researcher)

| Ficheiro | Função |
|----------|--------|
| `supplier_resolver.py` | Extração CNPJ/nome de payloads PNCP |
| `fornecedor_cache.py` | Cache BrasilAPI no SQLite |
| `supplier_probe.py` | Diagnóstico de gaps |
| `pncp_client.py` | `get_contract_supplier_snapshot`, `get_contract_items` |

### 5.4 Backend Django

| Ficheiro | Função |
|----------|--------|
| `backend/app/services/pncp_supplier_enrichment.py` | Enrich síncrono (espelho da lógica PNCP) |
| `backend/app/services/pncp_supplier_gap_audit.py` | Auditoria de gaps por fonte |
| `backend/app/services/pncp_relatorio_itens.py` | Montagem de linhas do PDF |
| `backend/app/pncp_cotacao_api.py` | CRUD cotação, persistência `source` |
| `backend/app/pncp_relatorio_api.py` | Geração PDF com enrich prévio |
| `backend/app/pncp_research_proxy.py` | Proxy para researcher |

### 5.5 Comandos de auditoria

```bash
# Homologados com CNPJ numa cotação (métrica de produto)
python manage.py audit_pncp_homologados_coverage --cotacao-id <ID>

# Cobertura geral de fornecedor
python manage.py audit_pncp_supplier_coverage
```

### 5.6 Métricas no índice

`GET /api/pncp-research/local-index/stats` inclui bloco `fornecedor`:

- `itens_com_cnpj_fornecedor`, `itens_elegiveis`, `itens_elegiveis_com_cnpj_e_nome`
- `cobertura_cnpj_pct`, `cobertura_elegivel_pct`

**Expectativa:** `cobertura_cnpj_pct` no índice total permanece **baixa** sem Fase B.

### 5.7 O que **não** está implementado (Fase B+)

- Backfill em massa de `/resultados` na ingestão 24/7.
- Job noturno de reprocessamento de fornecedor em registros antigos.
- Unificação total researcher ↔ backend num único pacote compartilhado.

Plano detalhado: [`docs/PLANO-MODULO-COBERTURA-FORNECEDOR-PNCP.md`](PLANO-MODULO-COBERTURA-FORNECEDOR-PNCP.md) (secções B–F pendentes; secção 2.1 desatualizada quanto a colunas `fornecedor` — já existem no código).

---

## 6. Busca e IA

| Funcionalidade | Config / endpoint |
|----------------|-------------------|
| FTS5 | `PNCP_FTS5_ENABLED=1`, `POST /local-index/fts-rebuild` |
| Busca híbrida | `PNCP_HYBRID_*` — complementa com PNCP ao vivo se local &lt; 8 |
| Busca inteligente | `POST /market-search/intelligent` → FTS tiers + scoring + top 3 |
| Modo qualidade | `PNCP_SEARCH_QUALITY_FIRST=1`, flex 0.78, rev. `2026-06-19-quality-qwen` — ver [`PNCP-BUSCA-INTELIGENTE-QUALIDADE.md`](PNCP-BUSCA-INTELIGENTE-QUALIDADE.md) |
| Rerank / resumo IA | `PNCP_IA_*` → **`qwen_llm_service:8015`** (fallback recall: `llm_api:8002`) |
| Bloqueio serviços | `PNCP_BLOCK_SERVICE_ITEMS=true` |

Frontend: `frontend-vue/src/views/PncpResearcher.vue`, `BuscaManualCotacoes.vue`, `BuscaInteligenteCotacoes.vue`, `CotacaoDetalhe.vue`, `services/pncpResearch.js`.

---

## 7. API — endpoints principais

Prefixo: `/api/pncp-research`

| Método | Path | Descrição |
|--------|------|-----------|
| GET | `/health` | Saúde + tamanho do `.db` |
| GET | `/local-index/stats` | Totais + `fornecedor` |
| GET | `/local-index/ingest-status` | Estado por UF/modalidade |
| GET | `/local-index/coverage` | Janela 365d + fila + gaps |
| GET | `/local-index/operational-status` | Agregado stats + ingest + FTS |
| POST | `/local-index/ingest/plan` | Dispara planner (debug/manual) |
| POST | `/local-index/ingest/worker-tick` | Um lote do worker (debug) |
| POST | `/local-index/backfill` | Backfill monolítico (loop bash) |
| POST | `/local-index/search-items` | Busca FTS com homolog + enrich |
| POST | `/market-search` | Busca ao vivo PNCP |
| POST | `/market-search/intelligent` | Busca inteligente |
| POST | `/research/sessions` | Cotação no SQLite do serviço |

---

## 8. Variáveis de ambiente (ingest + worker)

Defaults em `docker-compose.pncp.yml` e `pncp_researcher_service/app/config.py`:

| Variável | Default | Efeito |
|----------|---------|--------|
| `PNCP_LOCAL_BACKFILL_DAYS` | `365` | Janela de ingestão |
| `PNCP_INGEST_QUEUE_ENABLED` | `1` | Fila SQLite |
| `PNCP_INGEST_WORKER_ENABLED` | `1` | Worker em background |
| `PNCP_INGEST_WORKER_CATALOG_BATCH` | `3` | Páginas catálogo por tick |
| `PNCP_INGEST_WORKER_ITEMS_BATCH` | `28` | Contratos itens por tick |
| `PNCP_INGEST_WORKER_ITEMS_BATCH_MAX` | `40` | Boost com backlog alto |
| `PNCP_INGEST_WORKER_POLL_SECONDS` | `2` | Intervalo entre lotes |
| `PNCP_INGEST_PLANNER_INTERVAL_SECONDS` | `900` | Intervalo do planner |
| `PNCP_INGEST_PLANNER_PAGES_PER_SCOPE` | `4` | Páginas novas por scope |
| `PNCP_INGEST_PLANNER_CONTRACTS_WITHOUT_ITEMS` | `200` | Backlog sem itens por plan |
| `PNCP_INGEST_QUEUE_MAX_PENDING` | `5000` | Teto antes de pausar catálogo |
| `PNCP_INGEST_ITEMS_BACKLOG_PAUSE_CATALOG` | `3000` | Pausa catálogo se itens ≥ N |
| `PNCP_INGEST_JSON_INVALID_RETRIES` | `3` | Retries JSON inválido |
| `PNCP_INGEST_ITEMS_REFRESH_DAYS` | `7` | Skip GET `/itens` se buscado há &lt; N dias (`0` = legado, sempre busca) |
| `PNCP_BACKFILL_ITEM_CONCURRENCY` | `12` | Paralelo no backfill HTTP |
| `PNCP_INGEST_WATERMARK_RESUME` | `1` | Watermark `last_page+1` |
| `PNCP_SEARCH_ONLY_HOMOLOGATED` | `true` | Só homologados na busca |
| `PNCP_SEARCH_ENRICH_HOMOLOG_MAX` | `16` | Enrich na busca |

Backend (`settings.py`): `PNCP_RELATORIO_PDF_MAX_PNCP_LOOKUPS=96`, `PNCP_RELATORIO_PDF_MAX_BRASILAPI_LOOKUPS=64`, `PNCP_ADD_SOURCE_*`.

---

## 9. Operação em produção (DESKTOP)

### 9.1 Sinais de ingestão saudável

| Sinal | Bom | Ruim |
|-------|-----|------|
| Logs `ingest batch` | `items_ok` 28–40, `catalog_ok` 0–3 | `INGEST OK` em 2–4 s sem trabalho |
| `items_pending` | Caindo ~40/tick | Crescendo sem limite |
| `paused` em coverage | `0` | Muitos scopes `json_invalid` parados |
| `sem_itens` | Estável ou caindo | Só sobe (catálogo &gt;&gt; itens) |

### 9.2 Comandos úteis

```bash
# Cobertura agregada
docker exec pncp_researcher_service python -c "
import urllib.request, json
print(json.dumps(json.loads(urllib.request.urlopen(
  'http://127.0.0.1:8012/api/pncp-research/local-index/coverage', timeout=120).read()), indent=2))
"

# Logs do worker
docker logs pncp_researcher_service 2>&1 | grep 'ingest batch'

# Reativar scopes pausados por json_invalid (SQLite no volume)
docker exec pncp_researcher_service sqlite3 /data/pncp/pncp_researcher_local.db "
UPDATE pncp_ingest_state SET status='active', paused_until=NULL, last_error_kind=NULL
WHERE last_error_kind='json_invalid' AND status='paused_blocked';
"

# Requeue tarefas presas em processing (após restart)
docker exec pncp_researcher_service sqlite3 /data/pncp/pncp_researcher_local.db "
UPDATE pncp_ingest_queue SET status='pending' WHERE status='processing';
"
```

### 9.3 Hotfix sem rebuild (padrão usado em produção)

```bash
docker cp ~/docmaster-core/pncp_researcher_service/app/ingest_worker.py \
  pncp_researcher_service:/app/pncp_researcher_service/app/
docker cp ~/docmaster-core/pncp_researcher_service/app/ingest_planner.py \
  pncp_researcher_service:/app/pncp_researcher_service/app/
docker cp ~/docmaster-core/pncp_researcher_service/app/ingest_queue.py \
  pncp_researcher_service:/app/pncp_researcher_service/app/
docker cp ~/docmaster-core/pncp_researcher_service/app/config.py \
  pncp_researcher_service:/app/pncp_researcher_service/app/
docker restart pncp_researcher_service
```

Homologados/CNPJ exigem também **backend** e **frontend-vue** alinhados ao repositório.

### 9.4 Incidentes já resolvidos (registro)

| Problema | Resolução |
|----------|-----------|
| `paused_blocked` + `json_invalid` parando ingest | Reset SQL + retry no client |
| `INGEST OK` rápido sem crescimento | Worker + pausa catálogo com backlog |
| `processing` preso após restart | `UPDATE` → `pending` |
| `reativados: 0` no reset de pausa | Comparar datas ISO com `Z` vs SQLite `datetime('now')` |
| `/coverage` timeout | `count_contracts_without_items()` otimizado (COUNT direto) |
| Pending &gt; 8k, índice parado | Priorizar itens; planner conservador (4 páginas/15 min) |

---

## 10. Índice de ficheiros PNCP no repositório

### Researcher (`pncp_researcher_service/`)

- `app/api.py`, `app/config.py`, `app/local_index.py`, `app/pncp_client.py`, `app/service.py`
- `app/ingest_*.py` (5 módulos)
- `app/supplier_resolver.py`, `app/fornecedor_cache.py`, `app/supplier_probe.py`
- `app/schemas.py`
- `tests/test_ingest_*.py`, `tests/test_supplier_resolver.py`
- `RESUMAO_PNCP_RESEARCHER_SERVICE.md`

### Backend

- `app/pncp_cotacao_api.py`, `app/pncp_relatorio_api.py`, `app/pncp_research_proxy.py`
- `app/services/pncp_supplier_enrichment.py`, `pncp_relatorio_*.py`
- `app/management/commands/audit_pncp_*.py`
- `app/models/pncp_cotacao.py`, migrations `0031`–`0036`

### Frontend

- `frontend-vue/src/views/PncpResearcher.vue`, `BuscaManualCotacoes.vue`, `BuscaInteligenteCotacoes.vue`, `CotacaoDetalhe.vue`
- `frontend-vue/src/services/pncpResearch.js`

### Deploy / scripts

- `docker-compose.pncp.yml`, `docker-compose.pncp.noports.yml.example`, `docker-compose.pncp.override.yml.example`
- `scripts/ensure-pncp-researcher.sh`, `run-pncp-index-ingest-loop.sh`, `ensure-pncp-ingest-loop.sh`
- `scripts/attach-pncp-volume.sh`, `find-pncp-db-volumes.sh`, `lib/pncp-compose-args.sh`
- `deploy/docmaster-pncp-ingest.service.example`

### Documentação relacionada

| Documento | Conteúdo |
|-----------|----------|
| [`docs/deploy/README.md`](deploy/README.md) | Índice deploy |
| [`docs/deploy/PNCP-INGESTAO-INDEX-24-7.md`](deploy/PNCP-INGESTAO-INDEX-24-7.md) | Guia ingestão (parcialmente pré-worker) |
| [`docs/deploy/PNCP-RESEARCHER-24-7.md`](deploy/PNCP-RESEARCHER-24-7.md) | Stack isolada |
| [`docs/deploy/PNCP-V2-DEPLOY.md`](deploy/PNCP-V2-DEPLOY.md) | FTS5 + híbrido |
| [`docs/deploy/PNCP-API-INDICE-LOCAL.md`](deploy/PNCP-API-INDICE-LOCAL.md) | Endpoints |
| [`docs/deploy/CHANGELOG-OPERACOES-2026-06.md`](deploy/CHANGELOG-OPERACOES-2026-06.md) | Changelog ops DESKTOP |
| [`docs/PLANO-MODULO-COBERTURA-FORNECEDOR-PNCP.md`](PLANO-MODULO-COBERTURA-FORNECEDOR-PNCP.md) | Plano fornecedor |
| [`docs/PESQUISADOR_PNCP_FUNCIONAMENTO_ATUAL.md`](PESQUISADOR_PNCP_FUNCIONAMENTO_ATUAL.md) | Fluxo pesquisador |
| [`docs/PNCP_BUSCA_INTELIGENTE_IA.md`](PNCP_BUSCA_INTELIGENTE_IA.md) | Busca inteligente + IA |
| [`docs/PNCP-BUSCA-INTELIGENTE-QUALIDADE.md`](PNCP-BUSCA-INTELIGENTE-QUALIDADE.md) | Modo qualidade + Qwen rerank |
| [`docs/QWEN-INTEGRACAO-DOCMASTER.md`](QWEN-INTEGRACAO-DOCMASTER.md) | Integração Qwen no DocMaster |

### RAG (módulo separado)

`rag_service/app/pncp_*.py` — scraping/ingest PNCP para RAG; **não** alimenta o índice do researcher.

---

## 11. Estado declarado (jun/2026)

| Área | Status |
|------|--------|
| Fila + worker ingest (365d, 27 UFs) | **Implementado** no repositório; worker é o modo recomendado 24/7 |
| Loop bash backfill | **Legado** — manter desligado com worker ativo |
| FTS5 + busca híbrida | **Implementado** |
| Busca inteligente modo qualidade + Qwen | **Implementado** (jun/2026) — deploy requer `QWEN_API_KEY` |
| Filtro homologados | **Implementado** (researcher + frontend + backend) |
| CNPJ on-demand (busca/cotação/PDF) | **Implementado** com limites configuráveis |
| CNPJ em massa no índice (Fase B) | **Não implementado** |
| Testes ingest | **5** testes (`ingest_dates`, `ingest_queue`) |
| Produção DESKTOP | Volume `docmaster-pncp_pncp_researcher_data`; deploy frequente via `docker cp` + restart |

---

## 12. Regras operacionais (não negociáveis)

1. **Nunca** `docker compose -f docker-compose.pncp.yml down -v` em produção.
2. **Um** mecanismo de ingest contínuo: worker **ou** loop bash, não ambos.
3. Confirmar volume correto antes de stats (`attach-pncp-volume.sh` / health hint).
4. Auditar homolog/CNPJ na **cotação**, não só no índice bruto.
5. Após `git pull`, sincronizar compose + hotfix/rebuild do researcher e, se mudou fornecedor, backend + frontend.
