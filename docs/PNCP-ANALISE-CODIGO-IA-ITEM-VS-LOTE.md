# Análise de código — IA item isolado vs IA cotação inteira (lote)

Documento técnico (jun/2026). Parte do comportamento já validado em campo; aqui só o que o **código** faz e onde diverge.

**Sintoma alvo:** mesmo item da cotação → `?itemId=` devolve até 3 cotações; autostart / lote devolve **0** (ou menos).

**Endpoint único:** `POST /api/pncp-research/market-search/intelligent`  
**Função:** `pncp_researcher_service/app/service.py` → `market_search_intelligent`  
**UI:** `frontend-vue/src/views/BuscaInteligenteCotacoes.vue`

---

## 1. Bifurcação principal

Única flag que troca o motor:

```python
busca_lote = bool(getattr(payload, "busca_lote", False))
```

| Origem UI | `busca_lote` | O que acontece depois do `local_item_search` |
|-----------|--------------|-----------------------------------------------|
| `?itemId=` → `applyFilters` → `runSearchWithContext` (sem `bulkMode`) | `false` | Scoring multi-estágio, fallbacks, rerank local/Qwen, top3 misto literal/similar |
| `?autostart=1` / lote → `runBulkItemSearches` → `bulkMode: true` | `true` | **Return antecipado** em `await _finalize_busca_lote_top3_response(...)` — **não entra** no bloco `_score_candidates` (linha ~2609+) |

Trecho do early return (lote):

```2591:2607:pncp_researcher_service/app/service.py
    if busca_lote:
        return await _finalize_busca_lote_top3_response(
            payload=payload,
            search_payload=search_payload,
            ...
        )
```

O pipeline do item isolado (scoring, `scored_fallback_local_preco`, `fallback_relaxado`, rerank, `_select_top3_mixed_literal_similar`, etc.) **simplesmente não roda** no lote.

---

## 2. Frontend — mesma tela, payloads diferentes

### Item isolado

`CotacaoItemDetalhe.vue` → link `?itemId={id}`.

`onMounted` (`BuscaInteligenteCotacoes.vue` ~1529–1544):

- Carrega **um** item da sessão.
- Preenche `filtros.cidades` com a UF do item.
- Chama `applyFilters()` → `runSearchWithContext` **sem** `bulkMode`.

### Cotação inteira

`CotacaoDetalhe.vue` → `?autostart=1` ou busca em massa.

- `fetchAllItemsForBulkSearch` → lista de contextos.
- `runBulkItemSearches` → por item: `runSearchWithContext({ bulkMode: true, ... })`.

Payload enviado (`runSearchWithContext` ~1114–1122):

| Campo | Item isolado | Lote |
|-------|--------------|------|
| `busca_lote` | `false` | `true` |
| `max_paginas` | `500` | `3` |
| `tamanho_pagina` | `200` | `80` |
| `somente_homologados` | `true` | `true` |
| Timeout HTTP | default | `BULK_SEARCH_TIMEOUT_MS` = **95000** ms, 2 tentativas |

Lote adicional: `BULK_CONCURRENCY = 1` (fila serial), `BULK_ITEM_DELAY_MS = 50`.

**Geo:** ambos usam `buildRecortesGeograficosPayload(filtros.cidades)`. No item isolado a UF é **forçada** no mount; no autostart `filtros.cidades` pode estar vazio (cada item usa `context.uf_padrao` + fallback BR se 0 resultados). Se o usuário deixou recortes “errados” na tela, o lote aplica o **mesmo** recorte a **todos** os itens — item isolado não.

---

## 3. Backend — índice local (`local_item_search`)

Chamada em loop de termos (`_iter_search_term_fallbacks`) em `market_search_intelligent`.

### 3.1 Limite de linhas

```2380:2382:pncp_researcher_service/app/service.py
    limit = max(50, search_payload.max_paginas * search_payload.tamanho_pagina)
    if busca_lote:
        limit = min(limit, max(80, int(PNCP_BULK_SEARCH_SQL_LIMIT)))  # default 200
```

`local_item_search` usa `sql_limit = min(limit * 8, 20000)`:

| Modo | `limit` | `sql_limit` FTS |
|------|---------|-----------------|
| Item isolado | até 100 000 | **20 000** |
| Lote | **200** | **1 600** |

Os candidatos “perfeitos” podem existir no índice mas **ficar fora do top FTS** no lote.

### 3.2 Filtro de fornecedor na indexação

```2402:2402:pncp_researcher_service/app/service.py
            filtrar_fornecedor_para_exibicao=not busca_lote,
```

| Modo | Durante `local_item_search` |
|------|----------------------------|
| Item isolado | `filter_items_for_search_display` — só entra quem tem preço + fornecedor válido |
| Lote | `filter_items_with_display_price` — mantém linhas **sem** fornecedor no pool bruto |

No lote o fornecedor é exigido **depois**, em `_finalize_busca_lote_top3_response` → `filter_items_for_search_display`. Se enrich PNCP não preencher CNPJ/nome, linha some → **0 exibíveis** mesmo com `local_homologados > 0`.

### 3.3 Parada antecipada de termos (só lote)

```2427:2435:pncp_researcher_service/app/service.py
        priced_n = sum(1 for x in itens if _row_price_for_faixa(x) > 0.0)
        if priced_n >= 3:
            break
        if busca_lote and priced_n >= 1:
            break
        if busca_lote and priced_n == 0 and i >= 2:
            break
```

Item isolado continua variantes de termo até `priced_n >= 3` (ou esgotar fallbacks).

Lote: **para no primeiro termo** com qualquer linha com preço (`priced_n >= 1`). Cenário de código que zera o top3:

1. Primeira variante de termo traz linhas com preço **fora da faixa** ou sem fornecedor.
2. Loop de termos **não** tenta outras âncoras que achariam os 3 bons.
3. `_build_bulk_manual_recall_pool` elimina tudo na faixa → `candidates_na_faixa = 0`.
4. Ou `filter_items_for_search_display` → `candidates_exibiveis = 0`.

### 3.4 Enrich PNCP no loop (só lote)

Até `PNCP_BULK_LOCAL_ENRICH_HOMOLOG_MAX` (default **6**) homologados sem CNPJ — `enrich_homolog_items_from_pncp` (só fornecedor, **sem** preço homologado).

Item isolado: enrich no top3 final (até `PNCP_SEARCH_ENRICH_HOMOLOG_MAX` = **16**), após scoring.

---

## 4. Híbrido PNCP ao vivo

```2458:2467:pncp_researcher_service/app/service.py
    if busca_lote:
        need_hybrid = local_priced == 0
    else:
        need_hybrid = len(itens) < hybrid_min or local_priced < hybrid_min  # hybrid_min default 8
```

| Modo | Dispara `market_search` ao vivo |
|------|----------------------------------|
| Item isolado | Se pool local &lt; 8 **com preço** |
| Lote | **Somente** se `local_priced == 0` |

No lote, **uma** linha local com preço (mesmo irrelevante) **bloqueia** o híbrido. Item isolado ainda complementa com ao vivo se &lt; 8 preços bons.

Lote também limita `live_pages` a **2** (vs até `PNCP_HYBRID_MAX_LIVE_PAGES` no individual).

---

## 5. Finalize do lote (`_finalize_busca_lote_top3_response`)

Sequência:

1. `_build_bulk_manual_recall_pool` — exige `_row_price_for_faixa > 0` e `_preco_dentro_faixa` quando faixa ativa.
2. `enrich_homolog_items_from_pncp` — cap `_bulk_recall_enrich_cap` (max de `PNCP_SEARCH_ENRICH_HOMOLOG_MAX` e `PNCP_BULK_ENRICH_HOMOLOG_MAX`).
3. `filter_items_for_search_display` — fornecedor + preço.
4. `_select_top3_prioritize_federal` + `_ensure_top3_from_pool`.

**Não há:** `_score_candidates` strict/relaxed/aggressive, `scored_fallback_local_preco`, `local_rerank`, Qwen rerank (bulk: `PNCP_IA_RERANK_BULK_ENABLED` default off), `fallback_relaxado`.

Funil exposto: `modo_resposta = "busca_lote_top3_parity"`.

---

## 6. Pipeline do item isolado (trecho que o lote pula)

Após híbrido, se `not busca_lote`:

1. `_score_candidates(..., mode="strict")` + eliminação faixa.
2. Se pool fraco: `relaxed` → `aggressive` (se não `PNCP_SEARCH_QUALITY_FIRST`).
3. Rede de segurança **sem faixa** (`scored_fallback_local_preco`) — repõe homologados com preço quando scoring zerou tudo.
4. Pools literal/similar → `apply_local_rerank_top3` / Qwen.
5. `_select_top3_mixed_literal_similar` com `PNCP_SEARCH_MAX_SIMILAR_IN_TOP3`.
6. Enrich top3 + `filter_items_for_search_display`.

É aqui que o item isolado recupera candidatos que o pool do lote nunca ranqueia.

---

## 7. Timeout (só lote)

`api.py`:

```131:136:pncp_researcher_service/app/api.py
        if body.busca_lote and float(PNCP_BULK_SEARCH_MAX_SECONDS or 0) > 0:
            tmo = max(8.0, float(PNCP_BULK_SEARCH_MAX_SECONDS))  # default 90s
            try:
                data = await asyncio.wait_for(market_search_intelligent(body), timeout=tmo)
            except asyncio.TimeoutError:
                data = _bulk_search_timeout_response(body)
```

Resposta timeout: `itens: []`, `busca_lote_timeout: true`. Frontend ainda tem 95s no axios — dois tetos.

Item isolado: **sem** `wait_for` no endpoint.

---

## 8. IA desligada no lote

```1991:2006:pncp_researcher_service/app/service.py
def _ia_rerank_on_for_request(busca_lote: bool) -> bool:
    ...
    if busca_lote:
        return bool(_cfg.PNCP_IA_RERANK_BULK_ENABLED)  # default False
    return True

def _ia_resumo_on_for_request(busca_lote: bool) -> bool:
    ...
    return not busca_lote
```

---

## 9. Mapa de causas → código (0 no lote, 3 no item isolado)

| # | Mecanismo | Arquivo / símbolo | Efeito |
|---|-----------|-------------------|--------|
| 1 | Early return lote | `service.py:2591` | Motor completo do item isolado **não executa** |
| 2 | SQL cap 200 vs 100k | `config.py` `PNCP_BULK_SEARCH_SQL_LIMIT`, `service.py:2380` | Candidatos fora do top ~1600 FTS |
| 3 | `priced_n >= 1` break | `service.py:2431` | Para variantes de termo cedo |
| 4 | Faixa no recall pool | `_build_bulk_manual_recall_pool` | `eliminados_faixa_preco_recall` |
| 5 | Filtro fornecedor no finalize | `filter_items_for_search_display` | `candidates_exibiveis = 0` |
| 6 | Híbrido só se 0 preço local | `service.py:2459-2461` | Não complementa quando há lixo local |
| 7 | Sem fallbacks scoring | bloco `2609–2830` ignorado no lote | Sem `scored_fallback_local_preco` |
| 8 | Timeout 90s | `api.py:131` | `itens: []` sob carga/enrich |
| 9 | Geo global no autostart | `BuscaInteligenteCotacoes.vue` `filtros.cidades` | Recorte único para todos os itens |

---

## 10. Trabalho recomendado (derivado do código)

### Correção estrutural (Fase B do plano de paridade)

**Opção preferida:** no ramo `busca_lote`, **não** chamar `_finalize_busca_lote_top3_response`; reutilizar o mesmo caminho pós-`local_item_search` do item isolado, com caps:

- `skip_ia_resumo=True`
- `skip_qwen=True` ou `PNCP_IA_RERANK_BULK_ENABLED` temporário
- `enrich_max=3`
- manter `wait_for` / timeout

**Opção mínima (paliativo):** ajustes pontuais no lote atual:

1. Remover ou condicionar `if busca_lote and priced_n >= 1: break` — só parar se `candidates_na_faixa >= 3` após simulação de pool.
2. Alinhar `need_hybrid` do lote ao individual (`local_priced < 8`) ou híbrido quando `top3_final < 3` após finalize.
3. Subir `PNCP_BULK_SEARCH_SQL_LIMIT` (custo tempo) ou ordenar FTS igual ao item isolado.
4. `filtrar_fornecedor_para_exibicao=True` também no lote **ou** enrich de preço+fornecedor antes do pool.

### Testes a adicionar

Estender `tests/test_bulk_search_lote.py`:

- Fixture com ≥5 linhas indexadas; item isolado retorna 3 PNCP conhecidos; assert **mesmos** `numero_pncp` no lote.
- Caso `priced_n >= 1` com linha fora da faixa → hoje lote 0; após fix ≥1.

### Homologado vs estimado

Tema **ortogonal** (ver seção homologado em `PNCP-NOTAS-PENDENCIAS.md`). Mesma `displayPnCpUnitario` nos dois fluxos; 0 vs 3 é **recall/seleção**, não tipo de preço.

---

## 11. Arquivos de referência

```
frontend-vue/src/views/BuscaInteligenteCotacoes.vue   # bulkMode, payloads, autostart
frontend-vue/src/views/CotacaoItemDetalhe.vue         # link ?itemId=
pncp_researcher_service/app/service.py                # market_search_intelligent, finalize lote
pncp_researcher_service/app/local_index.py            # local_item_search, filtros
pncp_researcher_service/app/pricing_display.py        # preço canônico resposta
pncp_researcher_service/app/config.py                 # PNCP_BULK_*, PNCP_HYBRID_*
pncp_researcher_service/app/api.py                    # timeout lote
pncp_researcher_service/tests/test_bulk_search_lote.py
```

---

*Última atualização: 2026-06-22 — análise estática do repositório.*
