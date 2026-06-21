# Resumão Técnico — `pncp_researcher_service`

## 1) O que é este serviço

`pncp_researcher_service` é um microserviço FastAPI focado em:

- consultar contratações no PNCP;
- manter um índice local em SQLite para busca rápida;
- oferecer busca de mercado em modo tradicional e inteligente;
- gerenciar sessões de pesquisa (cotações) no próprio SQLite do serviço.

Na arquitetura do projeto, o Django backend chama este serviço via proxy em `/api/pncp-research/*`.

---

## 2) Estrutura de arquivos

- `app/main.py` — ponto de entrada FastAPI (`app = create_app()`).
- `app/api.py` — rotas HTTP (health, busca, índice local, sessões).
- `app/schemas.py` — contratos Pydantic de request/response.
- `app/config.py` — variáveis de ambiente e defaults.
- `app/pncp_client.py` — cliente HTTP PNCP (retry, backoff, throttle).
- `app/local_index.py` — camada SQLite (DDL, upserts, backfill, buscas, sessões).
- `app/service.py` — lógica de busca/score/ranking inteligente.
- `requirements.txt` — dependências mínimas do serviço.
- `Dockerfile` — imagem e comando de execução por `uvicorn`.

---

## 3) Endpoints expostos

Base path efetivo no serviço: `/api/pncp-research`.

### Saúde

- `GET /health`

### Busca PNCP

- `POST /market-search`
  - versão síncrona (resultado final).
- `POST /market-search/stream`
  - streaming NDJSON com eventos por página + evento `final`.
- `POST /market-search/intelligent`
  - busca em base local de itens + score/ranking + top 3.

### Índice local SQLite

- `GET /local-index/stats`
  - estatísticas da base local.
- `POST /local-index/backfill`
  - ingestão histórica PNCP para SQLite.
- `POST /local-index/search`
  - busca em `pncp_contratos` (objeto da contratação).
- `POST /local-index/search-items`
  - busca em `pncp_itens` (descrição/material do item).

### Sessões de pesquisa (cotação)

- `POST /research/sessions`
- `POST /research/cotacoes` (alias)
- `GET /research/sessions`
- `GET /research/sessions/{sessao_id}`
- `POST /research/sessions/{sessao_id}/items`
- `POST /research/sessions/{sessao_id}/update`

---

## 4) Fluxos principais

## 4.1 Busca tradicional (`market_search`)

1. Divide o período em janelas de até 365 dias (`_pn_date_windows`) para evitar 422 do PNCP.
2. Consulta modalidades em paralelo controlado.
3. Faz match por termo (`_build_query_groups` + `_compute_match_score`).
4. Opcionalmente cruza com tabela de itens PNCP (quando habilitado).
5. Pode fazer auto-ingest do bruto em SQLite (`PNCP_LOCAL_AUTO_INGEST`).
6. Retorna itens com métricas (`valor_min`, `valor_max`, `valor_mediano`, etc.).

## 4.2 Busca inteligente (`market_search_intelligent`)

A versão inteligente usa `local_item_search` (FTS5 + tiers) como fonte principal e aplica curadoria.

**Modo qualidade** (`PNCP_SEARCH_QUALITY_FIRST=1`, rev. `2026-06-19-quality-qwen`): documentação em `docs/PNCP-BUSCA-INTELIGENTE-QUALIDADE.md`.

1. **Tiers FTS**: strict → core → flex (ratio default **0.78**); tier anchor (2 palavras) **desligado** por default.
2. **Pré-filtro forte**: `_is_strict_candidate_match`.
3. **Scoring composto** por:
   - semântica por tokens (`_compute_match_score`);
   - recência (`_score_recency`);
   - coerência de preço (`_score_value_coherence`);
   - clareza/unidade (`_score_clarity_and_unit`);
   - penalidade de contexto incompatível (`_context_penalty`);
   - aderência literal ao termo (`_literal_match_score`).
4. **Sem reescala inflacionada** (35–100) em modo qualidade — scores absolutos.
5. Relaxamento de termos só se pool &lt; 2; fallback agressivo desligado.
6. Pools **literal** / **similar**; rerank IA também no pool **misto** (`PNCP_IA_RERANK_MIXED_POOL`).
7. Top 3: `_select_top3_mixed_literal_similar` — máx. **1** similar no top 3 (`PNCP_SEARCH_MAX_SIMILAR_IN_TOP3`).
8. **Rerank Qwen** (`PNCP_IA_BASE_URL`, timeout 22s) + **resumo** por item (18s).

### Blindagens atuais de estabilidade

- Prompt de IA exige score variável (`0-100`) e JSON estrito.
- Se IA devolver score muito baixo para item já forte (`ia<=15`, `base>=70`, `literal>=45`), o score base é preservado.
- `confiabilidade`/`risco` sempre recalculados a partir do score final.
- `stats.funil_busca` expõe pools, rerank e flags de qualidade para diagnose.

---

## 5) Modelo de dados local (SQLite)

`local_index.py` cria e mantém:

- `pncp_contratos`
  - contratação por `numero_pncp` (PK), com `raw_json` completo.
- `pncp_itens`
  - linhas de itens das contratações, com `UNIQUE(numero_pncp, item_fingerprint)`.
- `pesquisador_sessoes`
  - metadados da cotação (título, termo, status, modelo, filtros).
- `pesquisador_sessao_itens`
  - itens adicionados na sessão, incluindo `source_json_zlib`.

### Estratégia de persistência

- Contratos: `upsert_contracts` (ON CONFLICT UPDATE).
- Itens de contrato: `upsert_contract_items`.
- Sessões/itens de sessão: INSERT/UPDATE simples.

---

## 6) Backfill local (ingestão PNCP -> SQLite)

Função: `backfill_local_index(...)`.

Parâmetros relevantes:

- `months`: janela histórica (default de config).
- `max_paginas`: `null` ou `<=0` significa sem teto interno.
- `tamanho_pagina`: 10–50.
- `uf` e `codigo_municipio_ibge`: recorte opcional.
- `include_items`: inclui ou não tabela de itens da contratação.

Retorno inclui:

- `paginas_processadas`
- `upserts_executados`
- `upserts_itens_executados`
- `erros_modalidade`
- estatísticas atuais do índice (`local_index_stats`).

---

## 7) Cliente PNCP (`pncp_client.py`)

O cliente implementa robustez para API pública:

- `httpx.AsyncClient` com limites de conexão;
- retry em `429/500/502/503/504`;
- backoff exponencial + suporte a `Retry-After`;
- throttle configurável:
  - `bucket` (padrão, melhor para concorrência),
  - `interval` (serializado),
  - `off`.

Principais funções:

- `search_contracts(...)` -> endpoint de consulta pública;
- `get_contract_items(...)` -> endpoint PNCP API de itens (`pncp-api`);
- `create_pncp_http_client()` -> fábrica padrão.

---

## 8) Variáveis de ambiente mais importantes

Em `config.py`:

### Conectividade PNCP

- `PNCP_BASE_URL`
- `PNCP_PNCP_API_BASE_URL`
- `PNCP_TIMEOUT`

### Retry/Rate limit

- `PNCP_MAX_RETRIES`
- `PNCP_RETRY_BACKOFF_SECONDS`
- `PNCP_THROTTLE_MODE`
- `PNCP_BUCKET_CAPACITY`
- `PNCP_BUCKET_REFILL_PER_SEC`
- `PNCP_MIN_REQUEST_INTERVAL_SECONDS`
- `PNCP_RATE_LIMIT_EXTRA_ATTEMPTS`
- `PNCP_RATE_LIMIT_BACKOFF_CAP_SECONDS`

### Busca

- `PNCP_DEFAULT_LOOKBACK_DAYS`
- `PNCP_MAX_PAGINAS_PER_REQUEST`
- `PNCP_MODALIDADES_DEFAULT`

### Lookup de itens

- `PNCP_ENABLE_ITEM_TABLE_LOOKUP`
- `PNCP_ITEM_LOOKUP_PER_PAGE`
- `PNCP_ITEM_LOOKUP_CONCURRENCY`
- `PNCP_ITEM_LOOKUP_TIMEOUT_SECONDS`
- `PNCP_ITEM_LOOKUP_MAX_SECONDS_PER_PAGE`
- `PNCP_FETCH_ITEMS_ALWAYS`
- `PNCP_REQUIRE_TABLE_MATCH_WHEN_ITENS_EXIST`

### Índice local

- `PNCP_LOCAL_DB_PATH`
- `PNCP_LOCAL_AUTO_INGEST`
- `PNCP_LOCAL_BACKFILL_MONTHS`
- `PNCP_LOCAL_INCLUDE_ITEMS`

### Busca inteligente — qualidade

- `PNCP_SEARCH_QUALITY_FIRST`
- `PNCP_SEARCH_TIER_FLEX_RATIO`
- `PNCP_SEARCH_ANCHOR_TIER_ENABLED`
- `PNCP_SEARCH_MAX_SIMILAR_IN_TOP3`
- `PNCP_SEARCH_MIN_SCORE_APROVACAO`
- `PNCP_SEARCH_CODE_REV`

### Rerank / resumo IA (Qwen)

- `PNCP_IA_RERANK_ENABLED`
- `PNCP_IA_RERANK_MIXED_POOL`
- `PNCP_IA_BASE_URL` (default `http://qwen_llm_service:8015`)
- `PNCP_IA_GENERATE_PATH`
- `PNCP_IA_MODEL`
- `PNCP_IA_TIMEOUT_SECONDS`
- `PNCP_IA_ITEM_RESUMO_ENABLED`
- `PNCP_IA_ITEM_RESUMO_TIMEOUT_SECONDS`
- `PNCP_IA_MAX_CANDIDATES`

---

## 9) Contratos de request

`schemas.py` define:

- `MarketSearchRequest`
  - termo, UF, município, período, modalidade, paginação.
- `MarketSearchResponse`
  - `ok`, `filtros`, `stats`, `itens`.
- `LocalBackfillRequest`
  - janela/paginação/filtros/include_items.
- `ResearchSessionCreateRequest`
- `ResearchSessionAddItemsRequest`
- `ResearchSessionUpdateRequest`

---

## 10) Operação e comandos úteis

### Rodar local (fora Docker)

```bash
uvicorn pncp_researcher_service.app.main:app --host 0.0.0.0 --port 8012
```

### Health

```bash
curl -sS "http://localhost:8012/api/pncp-research/health"
```

### Backfill

```bash
curl -sS -X POST "http://localhost:8012/api/pncp-research/local-index/backfill" \
  -H "Content-Type: application/json" \
  -d '{
    "months": 12,
    "max_paginas": null,
    "tamanho_pagina": 50,
    "uf": null,
    "codigo_municipio_ibge": null,
    "include_items": true
  }'
```

### Acompanhar estatísticas em tempo real

```bash
watch -n 5 'curl -sS "http://localhost:8012/api/pncp-research/local-index/stats" | jq .'
```

(ou loop `while true` com `clear` caso `watch` não esteja disponível)

---

## 11) Dependências e container

Dependências mínimas:

- `fastapi`
- `uvicorn`
- `httpx`
- `pydantic`

Dockerfile:

- base `python:3.12-slim`;
- instala requirements do serviço;
- sobe com `uvicorn pncp_researcher_service.app.main:app` na porta `8012`.

---

## 12) Limitações atuais e observações práticas

- Serviço usa SQLite local (bom para simplicidade e persistência em volume, mas sem características de banco distribuído).
- Backfill pode ser demorado para janelas amplas sem recorte geográfico.
- Em picos de 429 no PNCP, o serviço tende a degradar com retries/backoff (esperado).
- Busca inteligente depende da qualidade da descrição PNCP; itens ambíguos podem exigir refinamento no termo.
- Rerank IA é opcional e com fallback heurístico (não bloqueia a resposta quando IA falha).

---

## 13) Resumo executivo

`pncp_researcher_service` é o motor de pesquisa PNCP do sistema: coleta, indexa e ranqueia contratações/itens com foco em uso operacional de cotações. O núcleo técnico combina:

- ingestão resiliente da API PNCP,
- índice local SQLite para performance e autonomia,
- ranking heurístico com curadoria literal,
- rerank IA opcional com guardrails de estabilidade,
- e APIs dedicadas para o fluxo de sessão/cotação.

