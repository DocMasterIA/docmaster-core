# Análise interna completa — modificações e funcionamento atual

Data de referência: 2026-07-24  
Escopo: união justa de fontes na pesquisa de preços (PNCP + TCE-RS + Compras.gov)  
Serviço: `pncp_researcher_service`

---

## 1. Problema que motivou as mudanças

Sintomas observados em produção/QA:

1. **Manual** (mesmas fontes, faixa, termo) listava dezenas/centenas de hits.
2. **IA** devolvia **1** (às vezes 2) cotação, mesmo com TCE “cheio” na faixa.
3. Mix de fontes **enviesado**: PNCP dominava; TCE/Compras sumiam ou entravam fracos.
4. Faixa de preço (±VAR) estava ok; o gargalo era **isonomia de candidatos + seleção do top-3**.

Causa estrutural (antes):

| Camada | Comportamento antigo | Efeito |
|--------|----------------------|--------|
| PNCP multi-fonte | `PncpAdapter.search` → `market_search_intelligent` → **≤3** | Pool PNCP rico descartado antes do merge |
| TCE/Compras | Cap hard **50** FTS | Recall artificialmente baixo |
| Dedup | `canonical_key` cross-platform; vencedor = **maior preço** | Uma fonte apagava a outra |
| Top-3 key | Sem `plataforma` | Vários TCE com mesma desc → **1 chave** |
| Federal-first | 3 federais ≥80 → só federal | TCE estadual excluído |
| Score CNPJ | −18/−35 sem CNPJ | Índice aberto penalizado demais |
| Similar cap | máx. 1 similar no top-3 | Top incompleto com 1 literal |

---

## 2. Inventário das modificações

### 2.1 Arquivos alterados (produção)

| Arquivo | Papel |
|---------|--------|
| `app/adapters/pncp_adapter.py` | Pool local PNCP no multi-fonte |
| `app/adapters/indexed_platform_adapter.py` | Cap FTS configurável (default 200) |
| `app/adapters/dedup.py` | Dedup por plataforma + identidade |
| `app/adapters/federated.py` | Timeout PNCP alinhado ao pool local |
| `app/config.py` | `PNCP_FEDERATED_PLATFORM_SEARCH_LIMIT` |
| `app/service.py` | Chave top-3, fill similar, federal/diversidade, CNPJ, literal federado |

### 2.2 Testes novos/ajustados

| Arquivo | Cobertura |
|---------|-----------|
| `tests/test_fair_source_union.py` | Pool PNCP, dedup cross-fonte, federal reserva TCE, swap mono-fonte |
| `tests/test_safe_federated_top3_patches.py` | Chave anti-collapse, fill 3, cap 200 |
| `tests/test_federated_adapters.py` | Dedup identidade / não preço alto |
| `tests/test_platform_index_crosslink.py` | Canon igual PNCP+TCE → **2 hits** |

### 2.3 Documentação

- `docs/pncp/ANALISE-MERGE-FEDERADO-IA-VS-MANUAL.md` — diagnóstico + patches
- `docs/pncp/ANALISE-AUDITORIA-BUSCA-IA-COT138.md` — qualidade produto (família) — **escopo separado**

---

## 3. Funcionamento atual — três caminhos

```
POST /market-search/federated
        │
        ├─ lista_completa=true  → MANUAL (lista ampla, sem top-3 IA)
        │
        ├─ fontes == ["pncp"]   → search_raw → market_search_intelligent (≤3)
        │                          (inalterado na intenção: paridade PNCP-only)
        │
        └─ multi-fonte          → UNIÃO JUSTA (Camada A + Camada B)
```

### 3.1 Manual (`lista_completa`)

**Inalterado em espírito.** Continua:

- PNCP: `local_item_search` até ~3000  
- TCE/Compras: `platform_item_search` até ~3000  
- Dedup leve por id de plataforma  
- Filtro de faixa opcional  
- Retorno até 5000 linhas  

Não passa por scoring IA / top-3.

### 3.2 PNCP isolado (`fontes=["pncp"]`)

**Inalterado:** `PncpAdapter.search_raw` → pipeline inteligente completo → ≤3.

### 3.3 Multi-fonte IA (foco das mudanças)

```
┌─ Camada A (coleta isonômica) ─────────────────────────────────┐
│  paralelo:                                                     │
│   PNCP.search  → local_item_search(limit≈200)  → N hits        │
│   TCE.search   → platform FTS(limit≤200)       → N hits        │
│   CG.search    → platform FTS(limit≤200)       → N hits        │
│                                                                │
│  assign_canonical_keys (anota cross-ref; NÃO apaga fontes)     │
│  dedupe_hits (só dentro da mesma plataforma)                   │
└────────────────────────────┬───────────────────────────────────┘
                             ▼
┌─ Camada B (scoring unificado) ─────────────────────────────────┐
│  prepare_federated_candidate_rows                              │
│    origem = federated_{plat}                                   │
│  orchestrate_merged_candidate_pool                             │
│    faixa → score → literal/similar → rerank → top-3            │
│    diversidade de esfera/plataforma                            │
│    ensure_top3 + display gate                                   │
│  retorno: ≤3 itens                                             │
└────────────────────────────────────────────────────────────────┘
```

---

## 4. Detalhamento técnico por patch

### 4.1 M1 — PNCP contribui pool (`pncp_adapter.py`)

**Antes:** `search()` chamava `market_search_intelligent` e só exportava o top-3.  
**Agora:** `search()` chama `local_item_search` com o mesmo teto `PNCP_FEDERATED_PLATFORM_SEARCH_LIMIT` (50–1000, default 200).

`search_raw()` permanece no intelligent (só usado no fast-path PNCP-only).

**Implicação:** no merge, PNCP chega com dezenas/centenas de candidatos **sem** ter pré-escolhido o trio. Todas as fontes passam **uma vez** pelo Camada B.

**Timeout:** multi-fonte PNCP usa ~20–60s (pool local), não mais a expectativa de 100s do intelligent completo.

---

### 4.2 P3 — Cap plataformas (`indexed_platform_adapter.py` + config)

```text
PNCP_FEDERATED_PLATFORM_SEARCH_LIMIT = env(default 200), clamp [10, 1000]
limit efetivo = min(LIMIT, max(10, tamanho_pagina))
```

**Antes:** `min(50, tamanho_pagina)`.  
**Agora:** até 200 por padrão (alinha melhor com o front `tamanho_pagina: 200`).

---

### 4.3 M5 — Dedup justo (`dedup.py`)

| Aspecto | Antes | Agora |
|---------|-------|-------|
| Chave | `canon|…` cross-platform | Sempre `plat|id|…` |
| Cross PNCP↔TCE mesmo canon | 1 hit | **2 hits** |
| Critério de vitória (mesma plat) | Maior preço | CNPJ → nome → homologado → desc → **menor preço** |

Crosslink continua anotando `canonical_key` / `cross_refs` para rastreio; **não** remove fonte rival.

---

### 4.4 P1 — Identidade no top-3 (`_ia_item_key`)

```text
se plataforma + plataforma_item_id → "{plat}|id|{id}"
senão → plat|pncp|item|desc|orgao|preço
```

`_merge_unique_items` usa a mesma chave.

**Efeito:** 5 TCE com mesma descrição e ids distintos → até 3 no top-3 (não 1).

---

### 4.5 P2 — Completar top-3 (`max_similar` dinâmico)

Com `PNCP_SEARCH_QUALITY_FIRST`:

```text
max_sim = max(MAX_SIMILAR_IN_TOP3, 3 - min(3, len(literal_scored)))
```

Ex.: 1 literal → até 2 similares para fechar 3.  
Depois `_ensure_top3_from_pool` ainda completa a partir do `scored` in-band.

---

### 4.6 M6 — Seleção federal + diversidade (`_select_top3_prioritize_federal`)

1. Se ≥3 federais com score ≥80 **e** há não-federal com score ≥ `min_ok`:  
   - pega **2** federais;  
   - completa preferindo não-federais (ex.: TCE estadual).
2. Se top-3 ficou **mono-plataforma** e existe outra plataforma ≥ `min_ok`:  
   - troca o mais fraco pelo melhor outsider (se score não estiver >15 abaixo).

**Regra de negócio preservada:** federal ainda é priorizado, mas **não monopoliza** o trio quando há fonte estadual/outra plataforma elegível.

---

### 4.7 M7 — Penalidade de fornecedor

Sem CNPJ:

| Origem | Com nome | Sem nome / não homolog |
|--------|----------|-------------------------|
| `federated_*` / tce_rs / compras_gov | **−6** | −10 / −18 |
| PNCP clássico | −18 | −35 |

Evita que TCE “válido sem CNPJ” perca sempre para PNCP no score bruto.

---

### 4.8 M4 — Literal federado

Para `origem=federated_*` ou plataforma TCE/Compras:

- `literal_match ≥ 5` → pool **literal** (antes só ≥6 e sem atalho de tier).
- Continua excluído se `similaridade_encontrada`.

PNCP multi-fonte (`federated_pncp`) também se beneficia se vier sem `search_tier` no row — mas rows do `local_item_search` costumam trazer `search_tier`, que no scoring ainda dá `tier_bonus`.

---

## 5. O que **não** mudou (importante)

| Componente | Estado |
|------------|--------|
| Saída IA = **≤3** | Mantido (regra de negócio cotação) |
| Faixa hard (BASE±VAR) | Mantida; fora da faixa não entra / não fica |
| Filtro display (CNPJ ou razão social útil) | Mantido no fim; ainda pode reduzir 3→1 se fornecedor inválido |
| FTS plataforma = **1º token** | **Ainda** (M3 não feito) — genéricos `fio`/`água`/`cadeira` |
| Family/product reject (oxigenada≠boricada) | **Não** nesta leva — escopo qualidade de produto |
| Manual `lista_completa` | Mesmo desenho de lista ampla |
| PNCP-only intelligent | Mesmo `search_raw` |

---

## 6. Comparativo antes × depois (multi-fonte IA)

| Métrica estrutural | Antes | Depois |
|--------------------|-------|--------|
| Hits PNCP no merge | ≤3 (já ranqueados) | até ~200 do índice local |
| Hits TCE/Compras no merge | ≤50 | ≤200 |
| Dedup cross-fonte | Colapsa | Preserva |
| Top-3 com 200 TCE mesma desc | ~1 | até 3 ids distintos |
| 3 federais ≥80 + TCE bom | 3 federais | 2 federais + 1 estadual (típico) |
| Top mono-PNCP com Compras elegível | 3 PNCP | 2 PNCP + 1 Compras (se score ok) |
| Saída final | ≤3 | ≤3 |

---

## 7. Fluxo de decisão do top-3 (estado atual)

```
scored (faixa + category/spec + score)
   │
   ├─ literal_pool  (tier local OU federado lit≥5 OU lit≥6)
   └─ similar_pool
   │
   ▼
selection_pool (literal_only | similar_only | mixed)
   │
   ▼
local_rerank / IA rerank (opcional)
   │
   ▼
_select_top3_prioritize_federal  ← diversidade esfera/plataforma
   │
   ▼
_ensure_top3_from_pool(scored)   ← completa até 3, chave com plataforma
   │
   ▼
_enforce_faixa_no_top3
   │
   ▼
filter_items_for_search_display  ← pode cortar se fornecedor inválido
   │
   ▼
itens ≤ 3
```

---

## 8. Riscos residuais e limites

1. **FTS 1º token (M3 pendente)**  
   União justa melhora *presença* das fontes; ainda pode trazer genéricos ruins no pool TCE. Qualidade lexical ≠ isonomia.

2. **Display gate pós-seleção**  
   Se 2 dos 3 não têm CNPJ/nome válido, a UI/backend ainda mostra 1. Mitigado em score (−6), não no gate final.

3. **Diversidade não é cota fixa**  
   Só troca/reserva se o outsider tiver score ≥ `min_ok` e não estiver muito pior (−15). Fonte fraca de verdade continua de fora (correto).

4. **Dupla identidade**  
   Mesmo item real em PNCP e TCE pode aparecer **duas vezes** no scored e, em tese, no top-3 se diversidade empurrar. Aceitável para transparência de fonte; se no futuro quiser “1 preço canônico”, fazer na UI ou pós-top3 com preferência de fonte — sem voltar a apagar no dedup.

5. **Carga**  
   Até ~600 candidatos (200×3) no Camada B vs ~103 antes. Scoring é local; monitorar latência em termos muito genéricos.

6. **Product mismatch (auditoria 138)**  
   Independente desta leva. União justa pode até **aumentar** exposição de mismatches TCE até family filters entrarem.

---

## 9. Como validar em runtime

Após deploy do researcher, numa busca IA multi-fonte inspecionar `stats`:

| Campo | Esperado se união justa ok |
|-------|----------------------------|
| `stats.fontes.pncp.hits` | ≫ 3 (dezenas) |
| `stats.fontes.tce_rs.hits` | até 200 (não preso em 50) |
| `stats.fontes.compras_gov.hits` | > 0 se índice ready |
| `stats.total_apos_dedup` | ≈ soma (sem colapso cross) |
| `itens[].plataforma` | mix quando pool permite |
| `funil_busca.literal_pool` / `top3_final` | top3_final preferencialmente 3 |

Caso de regressão a vigiar: item com só PNCP bom e TCE lixo genérico — diversidade **não** deve forçar TCE se score &lt; min_ok.

---

## 10. Veredito interno

As modificações **corrigem a assimetria de união de fontes**: coleta isonômica, dedup que não apaga rivais, seleção que não monopoliza federal/mono-PNCP, e top-3 que não colapsa ids de plataforma.

O sistema **continua** sendo um funil de qualidade que termina em ≤3 — isso é intencional. O que mudou é que o funil agora **vê** as fontes habilitadas de forma justa antes de escolher.

**Pronto para:** deploy + QA multi-fonte (itens que antes vinham com 1 cotação e TCE cheio na manual).  
**Não substitui:** filtros de família de produto nem FTS multi-token (próximas levas de precisão).
