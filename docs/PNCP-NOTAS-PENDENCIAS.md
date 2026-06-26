# PNCP — notas e pendências operacionais

Registro rápido de bugs/observações reportados em campo (não substitui issue tracker).

---

## 2026-06-22 — Preço estimado em vez de homologado (busca com IA)

**Reportado:** o Pesquisador de Preços PNCP está usando **valor unitário estimado** na cotação, em vez do **valor unitário homologado**, na **busca com IA**.

**Comportamento esperado (código):** prioridade homologado → unitário canônico → estimado (`pricing_display.py`, `pncpPricing.js`).

**Status:** investigado (jun/2026) — **causa provável confirmada no código + dados**; correção ainda não implementada.

**Escopo (comparação correta):**

| Fluxo | Como o usuário abre | Flags |
|-------|---------------------|-------|
| **IA item isolado** | Item da cotação → «Buscar preços com I.A para este item» → `/busca-inteligente?itemId=` | `busca_lote: false`, `max_paginas: 500` |
| **IA cotação inteira** | Cotação → autostart ou busca em massa na Busca Inteligente | `?autostart=1` / `bulkMode`, `busca_lote: true`, `max_paginas: 3` |

Não confundir com **busca manual** (`/busca-manual`) — escopo desta nota é só **IA item isolado vs IA cotação inteira**.

### Investigação (somente análise)

#### Conclusão em uma linha

O preço exibido na busca tende a ser **estimado do índice local** quando `valor_unitario_homologado` está vazio; o enrich da busca **não busca preço vencedor** em `/resultados` (só CNPJ/nome). O Django corrige **parcialmente no save**, se o lookup PNCP funcionar.

#### Cadeia de prioridade (código atual)

| Camada | Arquivo | Ordem de escolha do unitário |
|--------|---------|------------------------------|
| Backend resposta | `pricing_display.row_display_unit_price` | homologado → **`valor_unitario`** → estimado → total/qtd |
| Frontend exibição | `pncpPricing.displayPnCpUnitario` | homologado → (se homologado) `valor_unitario` → estimado → total/qtd |
| Save na cotação (UI) | `BuscaInteligenteCotacoes.vue` | `homUnit ?? valorUnitario` (display) |
| Enrich no save (Django) | `pncp_supplier_enrichment._merge_homologated_pricing_into_payload` | sobrescreve com homologado de `/resultados` |
| Relatório / média | `preco_unitario_cotacao_fonte` | homologado em `source` → `valor_unitario` ORM |

A prioridade **está correta quando `valor_unitario_homologado` existe**. O problema aparece quando esse campo **não veio no índice nem no enrich da busca**.

#### Causa 1 — Lacuna no índice SQLite (dados)

Na ingestão (`local_index.py`, upsert de `/itens`):

- `valor_unitario` = homologado **se** `/resultados` veio no batch; senão **`valorUnitarioEstimado`** do catálogo.
- `valor_unitario_homologado` só preenche quando há payload de `/resultados`.

Predicado de backlog (`_SQL_ITEM_NEEDS_RESULTADOS_PREDICATE`): linhas homologadas/elegíveis com `valor_unitario_homologado IS NULL` ainda são comuns enquanto o pipeline de `/resultados` não cobriu o item.

**Efeito:** item **homologado** na situação, mas preço exibido = estimado gravado em `valor_unitario`.

#### Causa 2 — Enrich da busca não traz preço homologado (assimetria researcher vs Django)

Durante busca inteligente/lote, `enrich_homolog_items_from_pncp` chama `get_contract_supplier_snapshot` no **researcher**, que retorna só fornecedor (`resolution_to_api_dict` — sem campos de preço).

No **Django**, `get_contract_supplier_snapshot_sync` chama `_homolog_pricing_from_resultados` e mescla `valorUnitarioHomologado` no payload.

**Efeito:** na tela de busca, mesmo após enrich PNCP, o usuário pode continuar vendo estimado; o homologado só entra de forma confiável **no save** (se lookup OK e dentro do cap `PNCP_ADD_SOURCE_MAX_PNCP_LOOKUPS`).

#### Causa 3 — Metadado confuso no save (frontend)

Em `BuscaInteligenteCotacoes.vue`, ao salvar:

```javascript
valor_unitario_estimado: r.sourceRaw?.valor_unitario_estimado ?? r.sourceRaw?.valor_unitario ?? null
```

Se o índice não tem `valor_unitario_estimado` explícito, o **`valor_unitario` canônico** (que pode ser estimado) é copiado para o campo `estimado` no `source`. Isso não muda o display imediato, mas **polui auditoria** e pode confundir quem inspeciona JSON/`source`.

#### Correções (homologado — referência)

| Prioridade | Ação | Onde |
|------------|------|------|
| A | Mesclar preço de `/resultados` no enrich do researcher | paridade com `pncp_supplier_enrichment._homolog_pricing_from_resultados` |
| B | Backfill `/resultados` no índice | `ingest` / planner |
| C | Badge “estimado” na UI | `CotacaoItemDetalhe.vue` |
| D | Fallback `valor_unitario_estimado ?? valor_unitario` no save | `BuscaInteligenteCotacoes.vue` |

#### Veredito (homologado)

Prioridade de código correta quando `valor_unitario_homologado` existe. Gap: índice + enrich researcher sem preço de `/resultados`. **Tema separado** do recall 0 vs 3 (seção seguinte).

**Análise de código (homologado):** causas 1–3 acima; correções A–D na tabela.

---

## 2026-06-22 — IA item isolado: 3 cotações; cotação inteira (lote): 0

**Sintoma (campo confirmado):** mesmo item — `?itemId=` até **3** cotações; autostart / lote **0** (ou menos).

**Não é** preço estimado vs homologado; é **dois motores no mesmo endpoint**.

**Análise completa (código):** [`PNCP-ANALISE-CODIGO-IA-ITEM-VS-LOTE.md`](PNCP-ANALISE-CODIGO-IA-ITEM-VS-LOTE.md)

### Resumo do que o código faz

| | Item isolado | Lote |
|---|--------------|------|
| Flag | `busca_lote: false` | `busca_lote: true` |
| Após índice local | Scoring + fallbacks + rerank + top3 inteligente | **Return** em `_finalize_busca_lote_top3_response` (linha ~2591) |
| SQL FTS | `sql_limit` até **20 000** | `sql_limit` até **1 600** (`PNCP_BULK_SEARCH_SQL_LIMIT`=200) |
| Termos | até `priced_n >= 3` | **para** em `priced_n >= 1` |
| Híbrido ao vivo | se local &lt; 8 com preço | **só** se `local_priced == 0` |
| IA rerank / resumo | ligado (defaults) | **desligado** |

### Causas no código que explicam 0 no lote (mapa §9 do doc de análise)

1. Early return — pipeline do `?itemId=` **não roda** no lote.  
2. Cap SQL 200 → candidatos fora do top FTS.  
3. `priced_n >= 1` → para variantes de termo antes de achar os 3 na faixa.  
4. Faixa em `_build_bulk_manual_recall_pool` + `filter_items_for_search_display` no finalize.  
5. Híbrido bloqueado por qualquer preço local irrelevante.  
6. Sem `scored_fallback_local_preco` / fallbacks relaxed.  
7. Timeout `asyncio.wait_for` 90s só no lote (`api.py`).

### Trabalho derivado do código

- **Estrutural:** lote usar o mesmo ramo pós-índice que `busca_lote=false` (com caps timeout/enrich) — [`PNCP-PLANO-PARIDADE-BUSCA.md`](PNCP-PLANO-PARIDADE-BUSCA.md) Fase B; runbook: [`PNCP-IMPLEMENTACAO-PARIDADE-LOTE.md`](PNCP-IMPLEMENTACAO-PARIDADE-LOTE.md).  
- **Paliativo:** rever `priced_n >= 1` break; alinhar `need_hybrid`; teste regressão em `test_bulk_search_lote.py` (mesmos `numero_pncp` isolado vs lote).

**Status:** aberto — implementação pendente.

---

## 2026-06-22 — Regressão geral do autostart (velocidade + trade-offs)

**Reportado (campo):** autostart **mais lento** (~2×+); em alguns itens **ganhou** recall que antes não tinha, em outros **perdeu** os 3 do item isolado (ver seção acima).

**Hipótese técnica (resumo):** `busca_lote: true`, fila serial, enrich duplicado, pipeline `busca_lote_top3_parity` vs motor completo do `?itemId=`.

**Status:** aberto — ver plano de paridade e [`PNCP-ANALISE-CODIGO-IA-ITEM-VS-LOTE.md`](PNCP-ANALISE-CODIGO-IA-ITEM-VS-LOTE.md).

---

## 2026-06-22 — Outras plataformas de preços (TCE, BNC, BLL, …)

**Ideia:** conectar fontes além do PNCP para completar cotações (Art. 5º) quando o índice federal não cobre item/região.

**Status:** planejamento — ver [`PLANO-FONTES-PRECOS-MULTIPLAS-PLATAFORMAS.md`](PLANO-FONTES-PRECOS-MULTIPLAS-PLATAFORMAS.md).
