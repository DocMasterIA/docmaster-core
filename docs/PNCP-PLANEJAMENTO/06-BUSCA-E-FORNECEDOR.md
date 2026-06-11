# Busca e fornecedor

## 1. Fluxos de busca

### 1.1 Busca inteligente (produto principal)

**Rota:** `POST /api/pncp-research/market-search/intelligent`  
**Código:** `service.market_search_intelligent()`  
**UI:** `BuscaInteligenteCotacoes.vue`

```
1. local_item_search(termo, filtros UF/modalidade/geo)
2. Se len(local) < PNCP_HYBRID_MIN_LOCAL_RESULTS (8):
     market_search() ao vivo (até 6 páginas)
     merge fornecedor de live → local
3. Filtro serviços (PNCP_BLOCK_SERVICE_ITEMS)
4. Scoring multi-estágio (literal, preço ref, unidade, recência)
5. Top 3 + regra federal-first
6. enrich_homolog_items_from_pncp (async, top 3)
7. Opcional: LLM rerank + resumo item
8. Retorna exatamente 3 itens
```

### 1.2 Busca manual / ao vivo

**Rota:** `POST /market-search` ou `/market-search/stream`

Consulta PNCP publicação em tempo real, scoring objeto + tabela de itens, sem depender do índice local (pode upsert se `PNCP_LOCAL_AUTO_INGEST`).

### 1.3 Busca local direta

**Rota:** `POST /local-index/search-items`

FTS5/LIKE + enrich wrapper. Usado internamente e para diagnóstico.

### 1.4 Diagnóstico

**Rota:** `POST /market-search/intelligent/diagnose`

Funil completo sem persistir — útil para debug de termos difíceis.

---

## 2. Scoring e filtros

| Regra | Config |
|-------|--------|
| Só homologados/adjudicados | `PNCP_SEARCH_ONLY_HOMOLOGATED=1` |
| Score mínimo aprovação | `PNCP_SEARCH_MIN_SCORE_APROVACAO=50` |
| Bloqueio itens serviço | `PNCP_BLOCK_SERVICE_ITEMS=1` |
| Anchor termo longo | `PNCP_SEARCH_ANCHOR_*` |

Homologação: `supplier_resolver.item_homologado_para_busca()` — situações elegíveis vs skip.

---

## 3. Fallback híbrido

| Variável | Default |
|----------|---------|
| `PNCP_HYBRID_FALLBACK_ENABLED` | true |
| `PNCP_HYBRID_MIN_LOCAL_RESULTS` | 8 |
| `PNCP_HYBRID_MAX_LIVE_PAGES` | 6 |

Quando índice local retorna poucos hits, complementa com PNCP ao vivo. Erro PNCP → mantém só local (silencioso).

**Distinto de:** FTS fallback (LIKE quando FTS5 vazio).

---

## 4. Fornecedor — resolução

### 4.1 Módulo `supplier_resolver.py`

```python
SupplierResolution:
  cnpj_fornecedor
  fornecedor          # razão social
  fornecedor_fonte    # metadado: pncp_resultado_item, brasilapi, ...
  fornecedor_elegivel
  fornecedor_cadastro
```

**Ordem offline** (`resolve_item_supplier_offline`):
1. Payload `/resultados` item
2. Payload `/resultados` compra
3. Payload contratos
4. Linha catálogo

**Guards (jun/2026):**
- `_fonte_sufixada()` — evita `pncp_resultado_item_item`
- `nome_fornecedor_e_util()` — rejeita strings `pncp_*`

### 4.2 Live (`pncp_client.get_contract_supplier_snapshot`)

HTTP chain + `merge_with_cadastro` + BrasilAPI fallback.

### 4.3 Onde enriquece

| Contexto | Limite |
|----------|--------|
| Ingestão massiva | Não — GET /itens |
| `local_item_search` | Sync, homologados sem CNPJ |
| `/search-items` | `enrich_local_search_result` |
| Busca inteligente top 3 | Async PNCP |
| PDF Django | `pncp_relatorio_itens.py`, `pncp_relatorio_pdf.py` |

Config: `PNCP_SEARCH_ENRICH_HOMOLOG_MAX=16`

### 4.4 Bug corrigido (jun/2026)

**Sintoma:** PDF/cotação mostrava `FORNECEDOR: pncp_resultado_item_item` com CNPJ válido.

**Causa:**
- Typo sufixo em `fonte_prefix`
- Chaves metadado tratadas como nome
- Backend não filtrava `pncp_*` na exibição

**Deploy:** researcher (`supplier_resolver.py`) + **backend Django** (`pncp_relatorio_itens.py`).

---

## 5. IA opcional

| Feature | Config | Timeout |
|---------|--------|---------|
| Rerank top candidatos | `PNCP_IA_RERANK_ENABLED` | 4.5s |
| Resumo item | `PNCP_IA_ITEM_RESUMO_ENABLED` | 3.5s |

Chama `llm_api` via `PNCP_IA_BASE_URL`.

---

## 6. Sessões de cotação

| Camada | Rota |
|--------|------|
| Django (prod) | `/api/pncp/cotacoes/research/sessions/*` |
| FastAPI (legado) | `/api/pncp-research/research/sessions/*` |

Frontend usa Django para persistência; researcher para busca.

---

## 7. Casos de teste recomendados

1. Termo curto comum → 3 itens, scores > 50
2. Termo longo descritivo → anchor funciona
3. UF filtrada → só resultados da UF
4. CNPJ conhecido problemático (ex. `57.836.642/0001-42`) → nome legível, não `pncp_*`
5. Índice vazio para termo → hybrid fallback ativa
6. PDF gerado → capa/listagem fornecedor OK

Ver também: `docs/PNCP-TESTES-FORNECEDOR.md`
