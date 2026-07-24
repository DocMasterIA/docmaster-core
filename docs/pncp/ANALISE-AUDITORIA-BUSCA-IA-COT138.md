# Análise detalhada — Auditoria Busca IA (cotação 138)

Fonte: `frontend-vue/e2e-artifacts/busca-ia-audit-138-2026-07-24T15-46-10-501Z.{md,json}`  
Contexto: VAR global ±50%, busca concluída 52/52 itens, 152 cotações na UI.

---

## 1. Diagnóstico executivo

| Camada | Estado | Evidência |
|--------|--------|-----------|
| Gate BASE±VAR (preço) | **OK** | `foraFaixa = 0` |
| Identidade do produto (match) | **FALHA** | `mismatches = 42` em 19 itens; 27,6% das cotações |
| Qualidade do top-3 | **Degradada** | Itens inteiros com 3/3 mismatch (oxigenada, cadeira, fios nylon, fitas) |
| Mix de fontes | **Enviesado + tóxico** | TCE-RS: 36 hits → **75% são mismatch**; PNCP: 114 → **11% mismatch** |

Conclusão: o researcher está **aprovando preço dentro da faixa de produto errado**. A média da cotação nesses itens não é confiável mesmo com VAR “respeitada”.

Mecanismo dominante observado:

1. Pool federado (esp. TCE-RS) devolve candidatos lexicalmente fracos (“água…”, “fio…”, “cadeira…”, “fita…”).
2. `product_category_strict_reject` / `product_spec_strict_reject` **não cobrem** conflitos de família (oxigenada≠boricada, nylon≠dental, microporosa≠isolante).
3. `_PRODUCT_LINE_EXCLUSIVE` só conhece Smarch↔Kinesio.
4. Scoring ainda atribui 52–58% (às vezes 70+) e o top-3 completa com lixo quando faltam 3 bons.
5. Faixa ±50% é larga o bastante para **qualquer** preço “parecido” passar o único hard-gate que existe hoje.

---

## 2. Números (amostra 138)

### 2.1 Totais

| Métrica | Valor |
|---------|------:|
| Itens UI | 52 |
| Cotações | 152 |
| Média cot./item | 2,92 |
| Fora da faixa | **0** |
| Mismatch termo×candidato | **42** |
| Match parcial (auditor) | 73 |
| Itens com ≥1 mismatch | **19** (36,5% dos itens) |
| Itens CV preço > 30% | 10 |
| Itens com <3 cotações | 3 |

### 2.2 Plataforma × mismatch (itemReports)

| Fonte | Cotações | Mismatches | Taxa mismatch |
|-------|--------:|----------:|--------------:|
| PNCP | 114 | 13 | **11%** |
| TCE-RS | 36 | 27 | **75%** |
| Compras.gov | 2 | 2 | 100% (n pequeno) |

**Implicação de patch:** filtrar só “score mínimo” não resolve; o problema é **concentrado no TCE-RS** (e em genéricos curtos). Qualquer patch deve ser testado com hits TCE, não só PNCP.

### 2.3 Score dos mismatches (amostra)

| Faixa de score | Qtd mismatches |
|----------------|---------------:|
| < 55% | 21 |
| 55–69% | 11 |
| ≥ 70% | 8 |

Há mismatches com score **≥70%** (Penrose títulos curtos, medroxiprogesterona dose errada, atadura crepom). Logo: **subir `min_score` sozinho não basta**.

### 2.4 Famílias de falha (agrupamento)

| Família do termo | Itens afetados | Hits mismatch | Severidade produto |
|------------------|---------------:|--------------:|--------------------|
| Fio sutura (nylon/algodão) | 6 | 16 | Crítica — produto errado |
| Dreno Penrose | 4 | 9 | Mista (FP auditor + nº errado real) |
| Fita (autoclave/microporosa) | 2 | 5 | Crítica |
| Água oxigenada | 1 | 3 | Crítica — 100% do top-3 errado |
| Cadeira de banho | 1 | 3 | Crítica — 100% do top-3 errado |
| Bandagem Smarch | 2 | 2 | Alta — dimensão/linha |
| Coletor perfuro | 1 | 1 | Média — capacidade 7L vs 13L |
| Hormônio (medroxiprogesterona) | 1 | 1 | Alta — 50mg/ml vs 150mg |

---

## 3. Casos âncora (impacto em preço)

### 3.1 ÁGUA OXIGENADA 10 VOLUMES

| | |
|--|--|
| BASE | R$ 7,93 · faixa R$ 3,97–11,90 |
| Top-3 | boricada R$4,00 · destilada R$6,25 · aguarrás R$11,00 |
| Stats | mediana R$6,25 · média R$7,08 · **CV 41%** · max/min ×2,75 |
| Match | **0 ok / 3 mismatch** · todos TCE-RS · score 54% |

**Efeito na cotação:** a “média” (~R$7) parece alinhada à BASE, mas **nenhum hit é oxigenada**. Enviesamento silencioso.

**Por que passou no código hoje**

- `product_category_strict_reject`: head do termo = `agua`; head do candidato = `agua` → **não rejeita**.
- `product_line_strict_reject`: `_PRODUCT_LINE_EXCLUSIVE` **não tem** oxigenada/boricada/destilada/aguarras.
- Spec `volumes=10`: candidato sem “10 volumes” — `product_spec_strict_reject` só rejeita se `rerank_adjustment <= -38` **ou** calibre/dose conflitantes; água sem dose tipada escapa.
- Literal fraco + token “agua” compartilhido sustenta score ~54 e entra no top-3.

**Patch A — família química da água (P0)**

Arquivo: `pncp_researcher_service/app/product_spec_match.py`  
Estender `_PRODUCT_LINE_EXCLUSIVE` (ou novo `product_family_strict_reject`):

```
oxigenada  ⊥  {boricada, destilada, aguarras, sanitaria, mineral}
boricada   ⊥  {oxigenada, destilada, aguarras, ...}
...
```

Regra: se termo contém âncora da família, candidato com outra âncora da mesma família **sem** a do termo → `strict_reject=True`.

Testes unitários obrigatórios com os 3 pares da auditoria.

---

### 3.2 FIO NYLON N° 4.0 / 5.0 / 6.0 (+ agulha)

Padrão repetido em **5 itens** com o **mesmo trio TCE**:

| Candidato | Preço típico | Score |
|-----------|-------------:|------:|
| FIO fio de corte 3,0mm | 1,46 | 53% |
| FIO DENTAL 100M | 2,87 | 53% |
| FIO FIO 1,0 | 2,92 | 53% |

BASE ~R$2,02–2,16 · mediana do grupo R$2,87 (= fio dental) · **CV ~28%** · 3/3 mismatch.

**Por que passou**

- Category: head=`fio`, candidato começa com `fio` → OK.
- Spec calibre: termo tem N°4.0; candidato dental/corte sem calibre USP → muitas vezes `got.calibre is None` → **não rejeita** (só rejeita se ambos têm calibre e divergem).
- Família nylon vs dental **não existe** no exclusive map.
- Agulha 2,5/3,5/4 cm ignorada no reject (só entra em rerank adjustment fraco).

**Patch B — sutura (P0)**

1. Exclusive: `nylon ⊥ {dental, corte}` (e `algodao` sutura ⊥ `crepom` quando head é fio).
2. Se termo tem `calibre` (N° / USP) **e** tokens `{nylon|seda|vicryl|algodao|poliester}`:
   - exigir no blob do item: material **ou** padrão “fio … n°/usp”;
   - se candidato tem calibre e diverge → reject (já existe);
   - **novo:** se termo tem calibre e candidato **não tem** calibre parseável **e** não tem material de sutura → reject (anti “FIO FIO 1,0” / dental).
3. Se termo contém `agulha` + comprimento, penalizar/reject forte ausência de agulha + comprimento absurdo.

Testes: nylon 4.0 vs dental; vs corte 3mm; vs “FIO 1,0”.

**Nota de preço:** nos fios, o hit “bom” PNCP quase não aparece; o top-3 está **todo** contaminado. Após patch, aceitar top-3 incompleto (&lt;3) é preferível a 3 errados.

---

### 3.3 CADEIRA DE BANHO ADULTO EM ALUMINIO

| Hit | Preço | Δ BASE | Fonte |
|-----|------:|--------|-------|
| Pistão a gás para cadeiras | 180 | −50% | TCE |
| Cadeira (genérico) | 456 | +27% | Compras.gov |
| Cadeira (genérico) | 476 | +33% | TCE |

CV **36%** · 3/3 mismatch · BASE 358,75.

**Por que passou**

- Category `_MISMATCH_PRIMARY_NOUNS` inclui `cadeira`, mas só rejeita se `primary != head`. Aqui head=`cadeira` e primary=`cadeira`/`pistao` — **pistao** não está na lista; “Cadeira” sozinha passa.
- Não há exigência de modificadores obrigatórios (`banho`, `adulto`, `aluminio`).

**Patch C — modificadores obrigatórios (P0/P1)**

Novo helper `required_modifiers_reject(termo, item)`:

| Se termo contém | Exigir no candidato (pelo menos N de) |
|-----------------|--------------------------------------|
| `cadeira` + `banho` | `banho` (obrigatório) |
| `cadeira` + `aluminio`/`aco` | material correspondente |
| `fita` + `microporosa` | `microporosa` (não só `fita`) |
| `fita` + `autoclave`/`indicadora` | `autoclave` **ou** `indicadora` |
| `fio` + `nylon` | `nylon` |

Para cadeira: rejeitar `pistao` / `gas` sem `banho`.

---

### 3.4 FITA CIRÚRGICA MICROPOROSA / FITA ADESIVA INDICADORA AUTOCLAVE

Microporosa: hits “Fita”, “ISOLANTE”, “EMPACOTAMENTO” — scores 52%.  
Autoclave: um hit `FITA AUTOCLAVE 19X30` (provável **true positive** mal classificado pelo auditor) + isolante + empacotamento.

**Patch D — fitas (P0)**

Exclusive:

```
microporosa ⊥ {isolante, empacotamento, crepe, esparadrapo}
indicadora|autoclave ⊥ {isolante, empacotamento}
```

+ modificador: termo `microporosa` ⇒ candidato deve conter `microporosa` (ou sinônimo catalogado).

**Ajuste auditor (P2):** `FITA … AUTOCLAVE 19X30` vs termo autoclave 19mm×30m → tratar como `match`/`partial` (dimensão compacta `19x30`), não mismatch por falta de “indicadora”.

---

### 3.5 BANDAGEM / FAIXA DE SMARCH

PNCP traz Smarch 15cm×2m (partial OK). TCE traz elástica 10×4,5 (mismatch dimensão).

`_PRODUCT_LINE_EXCLUSIVE` já cobre Smarch↔Kinesio, **não** dimensão.

**Patch E — dimensão (P1)**

Já existe `width_cm` / `length_m` em `ProductSpecHints`. Reforçar `product_spec_strict_reject`:

- Se termo e item têm `width_cm` e divergem > ~20% → reject.
- Se termo tem Smarch + width e item é “bandagem elastica” sem smarch e width diverge → reject.

---

### 3.6 DRENO PEN ROSE N.1–4

Muitos “mismatches” são **falsos positivos do auditor** (título `(2704358) - DRENO PENROSE` sem número explícito, score 86%).

Há **verdadeiro negativo**: termo N.3 vs texto “Número 4”.

**Patch F — calibre Penrose (P1) + calibração auditor (P2)**

- Researcher: se ambos têm número Penrose e divergem → reject (pode reusar calibre).
- Auditor: se termo tem `penrose`/`pen rose` e candidato tem `penrose` sem número → `partial`, não `mismatch`; se números divergem → `mismatch`.

Não priorizar Penrose no P0 do researcher além do calibre quando parseável.

---

### 3.7 MEDROXIPROGESTERONA 50MG/ML vs 150MG

Dose/concentração errada com overlap lexical alto e score 70%.

**Patch G — dose (P0)**  
Garantir que `dose_mg` / `conc_mg_per_ml` do termo, quando presentes, rejeitam `got` divergente (revisar `_float_close` e extração em “150MG AMPOLA” vs “50MG/ML”). Caso clássico de spec já prevista mas **extração falhou** ou strong_core_match liberou cedo (`product_spec_strict_reject` retorna False se `strong_core_match`).

Verificar ramo:

```python
if product_spec_strong_core_match(...):
    return False  # bypass perigoso
```

**Patch G2:** strong_core_match **não** pode anular conflito de dose/concentração.

---

### 3.8 COLETOR 7L vs 13L

Capacidade divergente.

**Patch H — volume de capacidade (P1)**  
Parse `(\d+)\s*(l|lts|litros)` como constraint de capacidade (não confundir com ml de ampola). Reject se ambos parseados e |a−b|/max(a,b) > 20%.

---

## 4. Onde o pipeline deixa passar (mapa de código)

```
federated_search / local index
        │
        ▼
prepare_federated_candidate_rows   (sem family reject)
        │
        ▼
market_search_intelligent scoring (service.py ~2704)
        │  product_category_strict_reject  ← fraco p/ mesma head noun
        │  product_spec_strict_reject      ← exclusive só Smarch; dose bypass
        │  score 52–70 ainda entra
        ▼
top-3 ensure / faixa hard (preço)  ← produto errado com preço “bom” SOBREVIVE
        │
        ▼
UI / cotação / média
```

Arquivos-alvo:

| Arquivo | Papel no patch |
|---------|----------------|
| `app/product_spec_match.py` | Famílias exclusive, dose bypass, dimensão, capacidade |
| `app/product_category_match.py` | Modifiers; rejeitar genéricos; pistão≠cadeira banho |
| `app/service.py` | Garantir rejects também no caminho bulk/manual_parity e pós-federado |
| `app/adapters/orchestrator.py` ou pós-`prepare_federated_candidate_rows` | Opcional: pré-filtro antes do score (economiza top-3 lixo TCE) |
| `frontend-vue/e2e/helpers/compareItems.mjs` | Reduzir FP Penrose / 19X30 / 2-0 |

---

## 5. Plano de patches (ordem sugerida)

### P0 — bloqueio de produto errado (máximo ROI)

1. **Family exclusive expandido** (`product_line` / novo `product_family_strict_reject`)  
   - águas; sutura nylon⊥dental/corte; fitas microporosa/indicadora⊥isolante/empacotamento  
2. **Required modifiers** (banho+cadeira; nylon+fio; microporosa; autoclave)  
3. **Corrigir bypass** `product_spec_strong_core_match` sobre conflito de dose  
4. Testes unitários com fixtures literais da auditoria 138  

**Critério de aceite:** re-rodar E2E 138 → mismatches das famílias P0 = 0 nos casos oxigenada / nylon×dental / cadeira pistão / fita isolante. Aceitar top-3 incompleto.

### P1 — spec geométrica / capacidade / calibre

5. Width/length Smarch e bandagens  
6. Capacidade litros coletor  
7. Penrose número quando parseável nos dois lados  
8. Pré-filtro leve em hits federados TCE com `literal_match` mínimo mais alto **ou** family reject antes do score  

### P2 — auditor E2E + observabilidade

9. Calibrar compareItems (Penrose sem nº; `19x30`; USP `2-0`≡`2.0`)  
10. No funil `stats`, contadores: `eliminados_family`, `eliminados_modifier`, `eliminados_dose`  
11. Tag na UI `similaridade` não basta — mostrar “rejeitado por família” em diagnose  

### Fora de escopo nesta leva

- Rebalancear cota Compras.gov no ranking  
- Mudar VAR global  
- Exigir sempre 3 cotações  

---

## 6. Matriz caso → patch → teste

| Caso auditoria | Patch | Teste mínimo |
|----------------|-------|----------------|
| oxigenada → boricada/destilada/aguarrás | P0 family | `test_family_agua_oxigenada_rejects_*` |
| nylon → dental / corte / FIO 1,0 | P0 family + calibre ausente | `test_sutura_nylon_rejects_dental` |
| cadeira banho → pistão / “Cadeira” | P0 modifiers | `test_cadeira_banho_requires_banho` |
| microporosa → isolante | P0 family+modifier | `test_fita_microporosa_rejects_isolante` |
| autoclave → empacotamento/isolante | P0 | idem |
| autoclave → FITA AUTOCLAVE 19X30 | P2 auditor only | não deve ser critical |
| Smarch 15×2 → 10×4,5 | P1 dimensão | `test_smarch_width_reject` |
| medroxiprogesterona 50 vs 150 | P0 dose bypass | `test_dose_conflict_not_bypassed_by_strong_core` |
| coletor 7L vs 13L | P1 capacidade | `test_capacity_liters_reject` |
| Penrose N.3 vs Número 4 | P1 | `test_penrose_number_mismatch` |
| Penrose título sem número | P2 auditor | partial |

---

## 7. Impacto esperado na cotação (negócio)

Antes (exemplos):

- Oxigenada: média ~7,08 “bonita” com **0** produtos corretos.  
- Fios nylon: mediana = preço do **fio dental**.  
- Cadeira: R$180–476 misturando acessório e genérico; CV 36%.  

Depois dos P0:

- Esses grupos tendem a **0–1 hit** até haver match real, ou hits PNCP Smarch/sutura corretos.  
- Médias deixam de ser “estáveis e erradas”.  
- E2E deve **passar** nos críticos de família (ou falhar só em residual P1/P2).

---

## 8. Riscos de regressão

| Risco | Mitigação |
|-------|-----------|
| Rejeitar oxigenada válida descrita só como “H2O2 10 volumes” | Incluir sinônimos (`h2o2`, `peroxido`) na âncora oxigenada |
| Rejeitar sutura “NYLON PRETO 4-0” sem palavra nylon romanizada | Normalizar 4-0↔4.0; aceitar “poliamida” como nylon |
| Cadeira de banho descrita como “cadeira higienica” | Sinônimo `higienica`≡banho |
| Queda forte de recall TCE | Monitorar `itens <3`; preferível a mismatch; afinar modifiers só quando âncora presente no termo |

---

## 9. Ordem de implementação recomendada (PRs)

1. **PR1 — Family exclusive + testes** (águas, sutura, fitas)  
2. **PR2 — Required modifiers + cadeira**  
3. **PR3 — Dose: remover bypass strong_core em conflito numérico**  
4. **PR4 — Dimensão Smarch + capacidade L**  
5. **PR5 — Auditor E2E calibração FP + re-run cotação 138**  

Cada PR: unitários locais + `npm run test:e2e` na 138 (ou subset se criar flag `PLAYWRIGHT_AUDIT_ITEMS=oxigenada,fio nylon`).

---

*Documento gerado para embasar patches a partir da auditoria E2E técnica de 24/07/2026.*
