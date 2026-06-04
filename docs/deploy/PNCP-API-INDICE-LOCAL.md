# PNCP — API do índice local, FTS e busca

Base URL no contentor: `http://127.0.0.1:8012/api/pncp-research`  
Prefixo router: `/pncp-research`

Deploy V2: [PNCP-V2-DEPLOY.md](./PNCP-V2-DEPLOY.md) · Ingestão: [PNCP-INGESTAO-INDEX-24-7.md](./PNCP-INGESTAO-INDEX-24-7.md)

---

## 1. Health

### `GET /health`

| Campo | Significado |
|-------|-------------|
| `ok` | Serviço no ar |
| `db_path` | Caminho SQLite |
| `db_bytes` | Tamanho do ficheiro |
| `db_on_data_volume` | `true` se path em `/data/pncp/` |
| `index_hint` | Aviso se DB em `/tmp` ou índice suspeito |

```bash
docker exec pncp_researcher_service python -c "
import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8012/api/pncp-research/health', timeout=10).read().decode())
"
```

---

## 2. Estatísticas do índice

### `GET /local-index/stats`

Contagens globais, por UF, por modalidade, caminhos do DB.

---

## 3. Ingestão operacional

### `GET /local-index/ingest-status?uf=AC` (UF opcional)

Estado por UF/modalidade em `pncp_ingest_state`:

| Campo em `scopes[]` | Significado |
|---------------------|-------------|
| `status` | `active`, `paused_blocked`, `degraded` |
| `watermark.last_page` | Última página processada |
| `watermark.next_page` | Próxima página na corrida com watermark |
| `watermark.resume_enabled` | `PNCP_INGEST_WATERMARK_RESUME` |
| `error_streak`, `paused_until` | Autopause |

Resposta global: `overall_status`, `scopes_paused`, `scopes_degraded`.

---

## 4. Status operacional agregado (V2)

### `GET /local-index/operational-status`

Combina num único JSON:

```json
{
  "ok": true,
  "index": { "...stats..." },
  "ingest": { "...ingest-status..." },
  "fts": { "...fts-status..." }
}
```

Útil para dashboards e verificação pós-deploy.

---

## 5. FTS5

### `GET /local-index/fts-status`

| Campo | Significado |
|-------|-------------|
| `enabled` | `PNCP_FTS5_ENABLED` |
| `ready` | Tabela FTS existe |
| `items_total` | Linhas em `pncp_itens` |
| `fts_rows` | Linhas em `pncp_itens_fts` |
| `needs_rebuild` | `true` se FTS &lt; ~85% dos itens |

### `POST /local-index/fts-rebuild`

Reconstrói `pncp_itens_fts` (`INSERT … VALUES('rebuild')`). Pode demorar **horas** em bases com centenas de milhares / milhões de itens.

```bash
docker exec pncp_researcher_service python -c "
import urllib.request
req = urllib.request.Request('http://127.0.0.1:8012/api/pncp-research/local-index/fts-rebuild', method='POST', data=b'')
print(urllib.request.urlopen(req, timeout=3600).read().decode())
"
```

Correr após upgrades grandes ou quando `needs_rebuild: true`.

---

## 6. Backfill (ingestão HTTP)

### `POST /local-index/backfill`

Body JSON (`LocalBackfillRequest`):

| Campo | Tipo | Default | Notas |
|-------|------|---------|-------|
| `months` | int | 12 | Janela histórica |
| `max_paginas` | int ou null | null | `null` ou ≤0 = sem teto interno (perigoso em país inteiro) |
| `tamanho_pagina` | int | 50 | Máx. 50 (API PNCP) |
| `uf` | string ou null | null | Filtro UF |
| `codigo_municipio_ibge` | string ou null | null | Filtro município |
| `include_items` | bool | true | GET itens por contrato |

Resposta inclui: `paginas_processadas`, `upserts_executados`, `upserts_itens_executados`, `watermark_resume`, `ingestao_operacional`, stats atualizados.

Teto por pedido: `PNCP_MAX_PAGINAS_PER_REQUEST` (default 120).

O loop usa `max_paginas=60` por UF.

---

## 7. Busca no índice local

### `POST /local-index/search`

Busca em contratos (objeto, etc.).

### `POST /local-index/search-items`

Busca em itens com FTS5 (ou LIKE se FTS desactivado/vazio). Suporta filtros UF, modalidade, município, recortes.

---

## 8. Busca de mercado (PNCP ao vivo + índice)

### `POST /market-search`

Consulta PNCP com paginação.

### `POST /market-search/intelligent`

Fluxo usado pelo DocMaster:

1. `local_item_search` (FTS5)
2. Se resultados &lt; `PNCP_HYBRID_MIN_LOCAL_RESULTS` → complemento via PNCP ao vivo (`PNCP_HYBRID_MAX_LIVE_PAGES`)
3. Opcional: rerank LLM, bloqueio de itens de serviço (`PNCP_BLOCK_SERVICE_ITEMS`)

### `POST /market-search/stream`

Versão streaming (NDJSON).

---

## 9. Sessões de pesquisa (cotações)

Persistência local em `pesquisador_sessoes` / `pesquisador_sessao_itens`:

| Método | Path |
|--------|------|
| POST | `/research/sessions` |
| POST | `/research/cotacoes` |
| GET | `/research/sessions` |
| GET | `/research/sessions/{id}` |
| POST | `/research/sessions/{id}/items` |
| POST | `/research/sessions/{id}/update` |

---

## 10. Variáveis de ambiente (serviço)

### Índice e backfill

| Variável | Default |
|----------|---------|
| `PNCP_LOCAL_DB_PATH` | `/data/pncp/pncp_researcher_local.db` |
| `PNCP_LOCAL_BACKFILL_MONTHS` | 12 |
| `PNCP_INGEST_WATERMARK_RESUME` | true |
| `PNCP_BACKFILL_ITEM_CONCURRENCY` | 12 |
| `PNCP_BACKFILL_ITEM_TIMEOUT_SECONDS` | 45 |
| `PNCP_INGEST_AUTOPAUSE_*` | ver `config.py` |

### PNCP HTTP client

| Variável | Função |
|----------|--------|
| `PNCP_THROTTLE_MODE` | `bucket` (default) ou `interval` |
| `PNCP_BUCKET_CAPACITY` / `PNCP_BUCKET_REFILL_PER_SEC` | Rate limit interno |
| `PNCP_MAX_RETRIES`, `PNCP_RATE_LIMIT_*` | Retries em 429/5xx |

### Busca

| Variável | Default |
|----------|---------|
| `PNCP_FTS5_ENABLED` | true |
| `PNCP_HYBRID_FALLBACK_ENABLED` | true |
| `PNCP_HYBRID_MIN_LOCAL_RESULTS` | 8 |
| `PNCP_HYBRID_MAX_LIVE_PAGES` | 6 |
| `PNCP_IA_RERANK_ENABLED` | true |
| `PNCP_BLOCK_SERVICE_ITEMS` | true |

Lista completa: `pncp_researcher_service/app/config.py` e [RESUMAO_PNCP_RESEARCHER_SERVICE.md](../../pncp_researcher_service/RESUMAO_PNCP_RESEARCHER_SERVICE.md).

---

## 11. Tabelas SQLite principais

| Tabela | Função |
|--------|--------|
| `pncp_contratos` | Contratações |
| `pncp_itens` | Itens normalizados |
| `pncp_itens_fts` | FTS5 (content= `pncp_itens`) |
| `pncp_ingest_state` | Watermarks e autopause |
| `pesquisador_sessoes` | Sessões de cotação |

---

## 12. Modalidades default no backfill

`PNCP_MODALIDADES_DEFAULT`: `[8, 6, 7, 9, 10]` (pregão eletrônico, inexigibilidade, dispensa, etc.).

Override: env `PNCP_MODALIDADES_DEFAULT=8,6,7,9,10`.
