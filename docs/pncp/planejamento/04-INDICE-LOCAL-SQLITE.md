# Índice local SQLite

## 1. Localização

```
PNCP_LOCAL_DB_PATH=/data/pncp/pncp_researcher_local.db
```

Volume Docker persistente. Tamanho típico DESKTOP jun/2026: **~5 GB**, **~1,5M+ itens**.

---

## 2. Tabelas principais

### `pncp_contratos`

Catálogo de contratações (uma linha por `numero_pncp`).

| Coluna | Uso |
|--------|-----|
| `numero_pncp` | PK (`numeroControlePNCP`) |
| `objeto`, `orgao`, `uf`, `municipio` | Busca/filtro |
| `modalidade_codigo`, `modalidade_nome` | Filtro |
| `data_publicacao` | Recência |
| `raw_json` | Payload completo PNCP |

### `pncp_itens`

Linhas de item (preço unitário, descrição, quantidade).

| Coluna | Uso |
|--------|-----|
| `numero_pncp` + `item_fingerprint` | UNIQUE |
| `descricao`, `material_servico` | FTS5 |
| `valor_unitario`, `valor_total` | Cotação |
| `cnpj_fornecedor`, `fornecedor` | Preenchidos parcialmente na ingestão; enriquecidos na busca |
| `raw_json_zlib` | Item PNCP comprimido |

### `pncp_itens_fts` (virtual FTS5)

Índice full-text em `descricao` + `material_servico`. Sincronizado por triggers.

Rebuild: `POST /local-index/fts-rebuild` (pode levar horas).

### `pncp_ingest_queue`

Fila de ingestão — ver [03-INGESTAO-24-7.md](./03-INGESTAO-24-7.md).

### `pncp_ingest_state`

Watermark + autopause por UF/modalidade.

### `pesquisador_sessoes` / `pesquisador_sessao_itens`

Sessões legadas no SQLite researcher (supersedidas por Django ORM para cotações).

---

## 3. Métricas

### `GET /local-index/stats`

```json
{
  "total_contratos": N,
  "total_itens": N,
  "por_uf": [...],
  "por_modalidade": [...],
  "fornecedor": { ... }
}
```

**Lento** em DB grande (COUNT full table). Timeout comum: 15–120s sob carga.

### `GET /local-index/coverage`

Agrega:
- Janela 365d
- `contratos_sem_itens`
- Fila (`queue`)
- Runtime ingest
- `cobertura_itens_contratos_pct`

### Gap de itens

```python
count_contracts_without_items()
# ≈ COUNT(contratos) - COUNT(DISTINCT numero_pncp em itens)
```

Indica quantos contratos indexados ainda precisam de GET `/itens`.

---

## 4. Busca local

### FTS5 (preferido)

`local_item_search()` → `pncp_itens_fts` MATCH + BM25 + pós-filtro tokens.

Config: `PNCP_FTS5_ENABLED=1`

### Fallback LIKE

Se FTS vazio/desligado: `descricao LIKE %anchor%`

### Filtros

- UF, município, recortes geográficos (OR, max 30)
- Modalidade
- Homologados: `PNCP_SEARCH_ONLY_HOMOLOGATED=1`

### Anchor

Termos longos de cotação são truncados para tokens âncora (`derive_anchor_search_term`).

---

## 5. Upsert e deduplicação

- **Contratos:** upsert por `numero_pncp`
- **Itens:** fingerprint por conteúdo → evita duplicatas na mesma contratação
- **Refresh:** `contract_needs_items_refresh()` — skip se itens atualizados < 7 dias

---

## 6. Backfill síncrono (`backfill_local_index`)

Caminho alternativo ao worker:

1. Loop UF × modalidade × páginas
2. `search_contracts` + `upsert_contracts`
3. Itens em paralelo (`PNCP_BACKFILL_ITEM_CONCURRENCY=12`)

Usado por `POST /local-index/backfill` e script bash legado. **Não recomendado** concorrente com worker 24/7 (contention SQLite).

---

## 7. Fornecedor no índice vs na busca

| Momento | CNPJ/nome no SQLite |
|---------|---------------------|
| Ingestão GET /itens | Parcial — nem sempre há vencedor por linha |
| Busca `/search-items` | Enriquecimento sync limitado (homologados) |
| Busca inteligente top 3 | Enriquecimento async PNCP `/resultados` |
| PDF Django | `pncp_relatorio_itens.py` + guards `pncp_*` |

Meta de negócio: 70–90% fornecedor identificado em itens **elegíveis na cotação**, não no índice bruto.
