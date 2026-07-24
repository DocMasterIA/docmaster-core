# Análise refinada de código — merge federado IA vs busca manual

Foco: mesma configuração de fontes (PNCP + TCE-RS + Compras.gov), manual encontra muitos hits e IA poucos / mix impreciso.

---

## 1. Não é o mesmo produto

| | Manual | IA (multi-fonte) |
|--|--------|------------------|
| Flag | `lista_completa: true` | omitido / `busca_lote` |
| Entrada | `federated_search` → `_federated_lista_completa` | adapters paralelos → crosslink → dedup → Camada B |
| Por fonte | até **3000** FTS/local | TCE/Compras ≤ **50**; PNCP = **top-3 já fechado** |
| Scoring produto | quase nenhum | category/spec reject + literal + CNPJ + faixa + rerank |
| Saída | até **5000** linhas | **≤ 3** |

Frontend reforça isso:

- Manual (`BuscaManualCotacoes.vue`): `lista_completa: true`, `max_paginas: 500`, `tamanho_pagina: 200`
- IA (`BuscaInteligenteCotacoes.vue`): mesmas páginas/tamanho, **sem** `lista_completa` → cai no funil de top-3

Conclusão: “mesma configuração” na UI (fontes, UF, faixa) **não** significa o mesmo pipeline. A percepção de “travamento no merge” é em grande parte **assimetria estrutural** entre os dois caminhos, não só bug de ranking.

---

## 2. Fluxo IA multi-fonte (onde trava)

```
fontes = [pncp, tce_rs, compras_gov]
        │
        ├─ PncpAdapter.search
        │     └─ market_search_intelligent(...)  → já devolve ≤3
        │        (pool PNCP rico é DESCARTADO antes do merge)
        │
        ├─ TceRsAdapter.search
        │     └─ platform_item_search(limit=min(50, tamanho_pagina))
        │        FTS só 1º token · sem search_tier
        │
        └─ ComprasGovAdapter.search
              └─ idem ≤50
        │
        ▼
assign_canonical_keys (crosslink)
        │
        ▼
dedupe_hits  → vencedor = MAIOR preço (não melhor texto)
        │
        ▼
orchestrate_federated_hits
        └─ prepare_federated_candidate_rows
              origem = federated_{plat}  (sem search_tier)
        └─ orchestrate_merged_candidate_pool  ← 2º funil completo
              faixa → score → literal/similar pools → federal-first → top-3
```

Branch no código:

```258:307:pncp_researcher_service/app/adapters/federated.py
    if query.lista_completa and not query.busca_lote:
        return await _federated_lista_completa(query)
    ...
    if sources == ["pncp"]:
        ... search_raw ...
    ...
    linked = assign_canonical_keys(merged, persist=True)
    deduped = dedupe_hits(linked)
    return await orchestrate_federated_hits(...)
```

---

## 3. Travamentos ranqueados (impacto no merge)

### T1 — PNCP chega pré-colapsado (impacto alto)

```19:25:pncp_researcher_service/app/adapters/pncp_adapter.py
    async def search(self, query: FederatedSearchQuery) -> List[MarketPriceHit]:
        ...
        data = await market_search_intelligent(payload)
        itens = list(data.get("itens") or [])
        return [pncp_row_to_hit(row) for row in itens if isinstance(row, dict)]
```

No merge multi-fonte, o PNCP **não** contribui com o pool de candidatos locais (centenas). Contribui só com o resultado final do pipeline inteligente (≤3).

Efeito:

- Alternativas PNCP boas que perderiam para um TCE/Compras melhor **nunca entram** no pool unificado.
- As 3 do PNCP já foram escolhidas **sem ver** TCE/Compras.
- Camada B roda de novo sobre ~3 PNCP + ≤50+50 plataformas → mix “funcional” mas enviesado para o que o PNCP sozinho já elegeu.

Manual faz o oposto: `local_item_search(limit=per_source)` até 3000 + FTS plataforma até 3000, sem top-3.

---

### T2 — Cap hard 50 nas plataformas na IA (impacto alto)

```35:40:pncp_researcher_service/app/adapters/indexed_platform_adapter.py
        rows = platform_item_search(
            ...
            limit=min(50, max(10, int(query.tamanho_pagina or 50))),
        )
```

Mesmo com frontend mandando `tamanho_pagina: 200`, o adapter **corta em 50**.

Manual:

```91:95:pncp_researcher_service/app/adapters/federated.py
    requested = max(200, int(query.max_paginas or 1) * int(query.tamanho_pagina or 50))
    limit = max(200, min(5000, requested))
    per_source = max(200, min(3000, limit))
```

Ordem de magnitude: manual ~60× mais candidatos TCE/Compras que a IA antes de qualquer score.

Não há env `PNCP_FEDERATED_*_LIMIT` — o 50 é hardcoded.

---

### T3 — FTS de plataforma = 1º token (impacto alto em precisão)

```150:154:pncp_researcher_service/app/platform_index/search.py
    anchor = _first_token(termo)
    ...
    fts_query = f'"{anchor}"*'
```

PNCP local usa tiers `strict/core/flex` e tokenização rica. TCE/Compras na federação IA:

- âncora fraca (`fio`, `agua`, `cadeira`, `fita`) → recall genérico;
- sem `search_tier` no row → **tier_bonus = 0** no score (PNCP local leva +2…+10).

Isso explica mix “funciona mas impreciso”: entram muitos genéricos de plataforma e poucos alinhados ao termo completo.

---

### T4 — Literal pool favorece `base_local` + tier (impacto médio-alto)

```2843:2853:pncp_researcher_service/app/service.py
    def _is_literal_candidate(it: Dict[str, Any]) -> bool:
        ...
        if tier in ("strict", "core") and origem.startswith("base_local"):
            return True
        if bool(it.get("similaridade_encontrada")):
            return False
        return float(it.get("literal_match") or 0) >= 6.0
```

Hits federados:

- `origem = federated_tce_rs` / `federated_compras_gov` (orchestrator)
- **não** têm `search_tier`

Caminho rápido “literal de verdade” (tier strict/core + `base_local`) **não existe** para TCE/Compras. Eles só entram no pool literal se `literal_match >= 6`. Descrições curtas/genéricas de índice aberto frequentemente ficam abaixo → slot de similaridade (máx. 1 em quality-first) ou eliminação.

---

### T5 — Penalidade de fornecedor sem CNPJ (impacto médio)

```2671:2679:pncp_researcher_service/app/service.py
            if not cnpj_f:
                ...
                    supplier_pen = -35.0
                else:
                    supplier_pen = -18.0
```

Índices TCE/Compras nem sempre trazem CNPJ limpo → −18 (ou −35) no score. Manual **não** aplica isso na lista ampla (só display gate no front).

---

### T6 — Federal-first no top-3 (impacto médio, assimétrico TCE)

```1497:1533:pncp_researcher_service/app/service.py
def _select_top3_prioritize_federal(...):
    # Se ≥3 federais com score ≥80 → prioriza só federais
```

- Compras.gov / muitos PNCP: `esfera=federal`
- TCE-RS: `esfera=estadual`

Quando há 3 federais fortes, TCE some do top-3 mesmo com match de texto melhor. Sensação: “merge existe, mas TCE não aparece”.

---

### T7 — Dedup cross-platform por **maior preço** (impacto médio)

```32:48:pncp_researcher_service/app/adapters/dedup.py
def dedupe_hits(...):
    """Mantém o hit com maior valor_unitario_homologado ou valor_unitario."""
```

Se crosslink agrupa PNCP + Compras (ou TCE) na mesma `canonical_key`, vence o **mais caro**, não o melhor lexical. Pode eliminar o hit de plataforma que a manual mostraria como opção válida.

Manual usa chave por `plataforma_item_id` / `plataforma:pncp:item` — **não** colapsa cross-platform.

---

### T8 — Duplo funil + saída ≤3 (impacto alto na percepção “poucos”)

Mesmo que TCE e Compras sobrevivam ao score, `_ensure_top3_from_pool` / seleção final devolve no máximo 3. Manual devolve centenas.

Parte do “IA encontra poucos” é **intencional** (regra de negócio top-3). O problema de precisão é que esses 3 são escolhidos sobre um pool **já empobrecido e enviesado** (T1–T7).

---

### T9 — Timeouts e UF (impacto situacional)

- Timeout secundário ~20s → `hits=0` silencioso naquela fonte.
- Manual: UF ≠ RS → TCE `skipped: uf_fora_escopo`.
- IA adapter: `uf = query.uf or spec.uf_scope` → se UF vazio, TCE busca RS; se UF=SP, FTS com `uf=SP` pode zerar TCE.

---

## 4. Por que a manual “acha diversos” e a IA “trava”

Para o **mesmo** termo e fontes:

1. Manual varre milhares de linhas FTS/local e lista tudo na faixa de preço.
2. IA limita plataformas a 50, PNCP a 3 pré-escolhidos, aplica rejects/score/CNPJ/federal, e corta em 3.

O esquema federado **é funcional** (stats `fontes`, hits chegam, testes de merge passam), mas a **mescla não é isonômica**:

| Fonte na IA | O que entra no merge | Qualidade do sinal |
|-------------|----------------------|--------------------|
| PNCP | 3 já ranqueados | Alto (pipeline completo), mas pool cego às outras fontes |
| TCE-RS | ≤50 FTS 1º token | Baixo (sem tier, sem multi-token) |
| Compras.gov | ≤50 FTS 1º token | Baixo + federal (favorecido no top-3 se score alto) |

Isso não é “merge quebrado”; é **merge sobre contribuições desiguais**.

---

## 5. O que *não* é o gargalo principal

- Flag `PNCP_FEDERATED_SEARCH_ENABLED` (ligado por padrão).
- Ausência total de Compras/TCE no registry (existem e alimentam).
- Faixa regional sozinha (manual também filtra faixa quando BASE+VAR; diferença é volume pré-filtro).
- Multiplicador hardcoded `score *= 0.5` por plataforma — **não existe**; o viés é estrutural.

---

## 6. Patches de união justa (2026-07-24)

Objetivo: **pesquisa de preços justa** — nenhuma fonte habilitada some no merge por assimetria estrutural.

| Patch | O que mudou | Efeito |
|-------|-------------|--------|
| P1 chave top-3 | `_ia_item_key` com `plataforma` + id | TCE gêmeos não colapsam em 1 |
| P2 fill similar | Completa top-3 quando literal é escasso | Não fica em 1 cotação com pool rico |
| P3 cap plataforma | Limit FTS IA 50→**200** (env) | Mais candidatos TCE/Compras |
| **M1 pool PNCP** | `PncpAdapter.search` usa `local_item_search` (pool), não top-3 intelligent | PNCP compete em igualdade |
| **M5 dedup** | Dedup **por plataforma**; não apaga TCE vs PNCP no mesmo canon; vence identidade, não preço alto | Fontes permanecem até o scoring |
| **M6 diversidade** | Federal-first reserva slot estadual; top-3 mono-fonte troca 1 slot | TCE/Compras não somem do trio |
| **M7 CNPJ** | Penalidade suave em `federated_*` / TCE / Compras | Score justo para índice aberto |
| **M4 literal** | Federado com `literal_match≥5` conta como literal | Menos empurrão para “similaridade” |

Testes: `test_fair_source_union.py`, `test_safe_federated_top3_patches.py`, adapters/crosslink atualizados.

### Ainda aberto (próxima leva)

| # | Patch | Nota |
|---|-------|------|
| M3 | FTS multi-token nas plataformas | Precisão do recall TCE (genéricos 1º token) |
| — | Family/product filters | Produto errado ≠ união de fontes |

---

## 7. Direções legadas (parcialmente cobertas)

Ordenadas pelo que mais desbloqueia precisão do merge sem abandonar top-3:

| # | Patch | Arquivo | Efeito |
|---|-------|---------|--------|
| M1 | PNCP no merge multi-fonte deve exportar **pool de candidatos** (ex. scored pré-top3 ou `local_item_search` limit N), não só `itens` finais | `pncp_adapter.py` + ponto de saída em `orchestrate_merged_candidate_pool` / `market_search_intelligent` | Merge isonômico: todas as fontes competem no mesmo pool |
| M2 | ~~Subir cap IA plataformas~~ **feito** via `PNCP_FEDERATED_PLATFORM_SEARCH_LIMIT=200` | `indexed_platform_adapter.py` | Recall TCE/Compras maior |
| M3 | FTS multi-token / tiers leves no `platform_item_search` (ou passar `search_tier` aproximado por bm25) | `platform_index/search.py` | Menos genéricos “fio/água/cadeira” |
| M4 | Tratar `origem.startswith("federated_")` como elegível a literal se FTS/bm25 forte (ou injetar tier) | `service.py` `_is_literal_candidate` | Plataformas não ficam só no slot similaridade |
| M5 | Dedup por melhor score textual (ou preferir hit com CNPJ + match), não maior preço | `dedup.py` | Não matar match bom barato |
| M6 | Federal-first só após pool misturado com piso de diversidade de plataforma (ex. ≥1 não-federal se score ≥ min_ok) | `_select_top3_prioritize_federal` | TCE deixa de sumir quando há 3 federais ≥80 |
| M7 | Suavizar `supplier_pen` em `federated_*` quando nome de fornecedor existe | `_score_candidates` | Menos punição artificial a índices abertos |

**Não confundir com** patches de família/produto (oxigenada≠boricada): aqueles melhoram precisão do que sobra no top-3; estes (M1–M7) melhoram **como** as fontes chegam e competem.

---

## 8. Como validar no funil (já exposto em stats)

Olhar `stats.fontes` / `funil_busca` numa busca IA multi-fonte:

| Sinal | Interpretação |
|-------|----------------|
| `tce_rs.hits` ≈ 50 e manual centenas | T2 ativo |
| `pncp.hits` ≤ 3 no merge | T1 ativo |
| `literal_pool` quase só PNCP | T3+T4 |
| top-3 só `plataforma=pncp`/`compras_gov` com TCE hits>0 | T6 |
| `total_hits` >> `total_apos_dedup` e sumiço de fonte | T7 |

Instrumentação útil (patch observabilidade): contagem por plataforma em `scored`, `literal_pool`, `top3_final`.

---

## 8. Síntese

A sensação de travamento no merge TCE-RS + Compras.gov é correta no código:

1. Manual e IA **divergem de propósito** (`lista_completa` vs top-3).
2. No caminho IA, o merge **não recebe pools equivalentes**: PNCP já fechou; plataformas chegam pobres (50 × 1º token × sem tier).
3. Scoring e seleção (literal, CNPJ, federal-first, dedup por preço) **comprimem ainda mais** o que as plataformas trouxeram.
4. O resultado final ≤3 amplifica qualquer viés anterior.

Correção de precisão do federado começa em **isonomia de candidatos (M1+M2+M3)**; filtros de família/produto são camada seguinte sobre um pool que finalmente representa as três fontes.
