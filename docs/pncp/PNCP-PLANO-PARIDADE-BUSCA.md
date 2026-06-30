# PNCP — Avaliação e plano: paridade busca individual vs. lote

Documento de trabalho (jun/2026). Objetivo: paridade **IA item isolado** (`?itemId=`) ↔ **IA cotação inteira** (`busca_lote` / autostart).

**Análise de código (fonte):** [`PNCP-ANALISE-CODIGO-IA-ITEM-VS-LOTE.md`](PNCP-ANALISE-CODIGO-IA-ITEM-VS-LOTE.md)  
**Notas operacionais:** [`PNCP-NOTAS-PENDENCIAS.md`](PNCP-NOTAS-PENDENCIAS.md).

---

## 1. Síntese do problema (campo)

| Sintoma | Item isolado (`?itemId=`) | Lote / autostart |
|---------|---------------------------|------------------|
| Quantidade | Até **3** cotações (campo confirmado) | **0** no mesmo item (casos reportados) |
| Motor backend | Scoring completo + fallbacks | `_finalize_busca_lote_top3_response` apenas |
| Tempo | Aceitável por item | ~2×+ no total (fila + enrich) |
| Recall “novo” no lote | — | Acha preços em itens que antes não achava (outros itens) |

**Conclusão (código):** **dois pipelines** em `market_search_intelligent`; o lote faz **early return** na linha ~2591 e **não executa** o bloco de scoring do item isolado.

---

## 2. Mapa técnico: por que individual ≠ lote

Mesmo frontend (`BuscaInteligenteCotacoes.vue`), mesma API (`POST /market-search/intelligent`), flags diferentes:

| Dimensão | Individual | Lote (`bulkMode` + autostart) |
|----------|------------|-------------------------------|
| `busca_lote` | `false` | `true` |
| Ramo backend | Scoring completo → literal/similar → local rerank → (opcional Qwen) → top3 | **Saída antecipada** → `_finalize_busca_lote_top3_response` |
| `max_paginas` × `tamanho_pagina` | 500 × 200 | 3 × 80 (teto SQL ~200) |
| Hybrid PNCP ao vivo | Se pool local &lt; 8 com preço | **Só se local = 0 preço** |
| Enrich PNCP | Até 16 no top3 final | **Até 6 no loop de termos + até 16 no pool** |
| Qwen rerank / resumo IA | Rerank manual ligado; resumo ligado | Rerank bulk **off**; resumo **off** |
| Concorrência frontend | 1 busca | `BULK_CONCURRENCY = 1` (fila serial) |
| Timeout HTTP | 120 s | 95 s, até 2 retries |
| Seleção final | `_select_top3_*` + mixed literal/similar + faixa | Pool “manual parity” na faixa → top3 → filtro fornecedor |

**Hipótese central da regressão de precisão no lote:** o autostart **não usa** o motor inteligente que funciona bem no individual; usa um atalho mais rápido/de recall, com ranking simplificado (`tier` + `literal_match` + `product_spec`), sem fallback relaxado/agressivo nem rerank local.

**Hipótese central da lentidão:** enrich PNCP duplicado (loop + final, até **22** lookups/item no pior caso) + fila serial + scoring/spec em **todo** o pool na faixa.

---

## 3. “Melhorias” prováveis e efeito colateral

| Mudança (época recente) | Ganho | Custo / risco |
|-------------------------|-------|----------------|
| `busca_lote_top3_parity` (pool manual + top3) | Corrigiu “1 preço quando havia 3 no DB” (ex. álcool gel) | Perdeu scoring/rerank do individual → **menos precisão** |
| Enrich ampliado (nome sem CNPJ) | Mais linhas salváveis; recall fornecedor | **+ segundos/item** |
| `somente_homologados: true` no lote | Alinha com manual | Menos linhas se antes entrava não-homologado |
| Faixa obrigatória no scoring lote | Menos preço fora da variação | Menos resultados se faixa apertada |
| `product_spec_strong_core_match` | Melhor equivalência (gel 70% 500 ml) | CPU no pool grande |
| Filtro CNPJ honesto no save | Save confiável | UI mostra mais do que salva (se enrich falhar) |
| Homologado no índice (backfill) | Preço correto quando preenchido | Muitas linhas ainda **só estimado** → usuário vê estimado |

Nada disso precisa ser revertido em bloco; o plano é **recombinar**: individual-quality no lote, enrich enxuto, homologado no índice.

---

## 4. O que investigar **sem** debug pesado

### 4.1 Amostra fixa (5–10 itens) — ~30 min

Escolher itens “ouro”, incluindo **13871** e 2–3 que falharam no lote:

1. Busca **individual** (`?itemId=`).
2. Mesmo payload com `"busca_lote": true` via curl/script.
3. Comparar só estes campos da resposta:

```json
stats.regra_selecao
stats.funil_busca.modo_resposta
stats.funil_busca.candidates_na_faixa
stats.funil_busca.candidates_exibiveis
stats.funil_busca.top3_final
stats.enriquecidos_pncp_na_busca
itens[].valor_unitario_homologado
itens[].valor_unitario_estimado
itens[].valor_unitario
itens[].score_aprovacao
```

**Ferramentas já no repo:**

- `scripts/regression-pncp-check.py` (individual vs bulk por termo)
- `pncp_researcher_service/app/search_diagnose.py` (diagnóstico local)

Não precisa rodar os 696 — basta provar **divergência de pipeline** na amostra.

### 4.2 SQL no DESKTOP (5 min)

Cobertura de homologado (explica preço estimado na UI):

```bash
docker exec pncp_researcher_service sqlite3 /data/pncp/pncp_researcher_local.db "
SELECT
  COUNT(*) AS total,
  SUM(valor_unitario_homologado IS NOT NULL) AS com_vu_hom,
  SUM(valor_total_estimado IS NOT NULL AND valor_unitario_homologado IS NULL) AS so_estimado
FROM pncp_itens;"
```

Se `so_estimado` for alto, parte do “estimado em vez de homologado” é **dado**, não lógica de busca.

### 4.3 Funil agregado no autostart (sem log por item)

No fim de uma corrida parcial, amostrar 20 respostas no Network ou log nginx:

- % com `modo_resposta = busca_lote_top3_parity`
- % com `top3_final = 0` mas `candidates_na_faixa > 0` → filtro fornecedor/enrich
- % com `busca_lote_timeout: true`

### 4.4 Benchmark de tempo (1 termo, 20×)

```bash
# no host com PNCP up
time for i in $(seq 1 20); do
  curl -sS -o /dev/null -w "%{time_total}\n" \
    -X POST http://localhost:8012/api/pncp-research/market-search/intelligent \
    -H 'Content-Type: application/json' \
    -d '{"termo_busca":"...","busca_lote":true,...}'
done
```

Repetir com `"busca_lote": false`. Diferença média = custo do ramo lote isolado.

---

## 5. Plano de ação (fases)

### Fase A — Quick wins só config (1 deploy, baixo risco)

Objetivo: recuperar **tempo** sem mudar código.

| Ação | Env | Efeito esperado |
|------|-----|-----------------|
| Reduzir enrich final | `PNCP_SEARCH_ENRICH_HOMOLOG_MAX=3` | −5–10 s/item típico |
| Reduzir enrich no loop | `PNCP_BULK_LOCAL_ENRICH_HOMOLOG_MAX=0` ou `2` | Menos PNCP duplicado |
| Manter Qwen off | `PNCP_IA_RERANK_BULK_ENABLED=0` | Já ok |
| Subir concorrência *só se DESKTOP aguentar* | requer mudança Vue `BULK_CONCURRENCY` | −40–60% tempo total |

**Não fazer ainda:** zerar enrich completamente (regressão CNPJ/save).

### Fase B — Paridade lote → individual (1 PR, risco médio, **maior impacto em precisão**)

Objetivo: autostart usar **o mesmo top3** que `?itemId=`, com modo rápido.

Proposta técnica (implementação futura):

1. Extrair `_finalize_intelligent_top3(...)` usado hoje quando `busca_lote=false`.
2. No lote: chamar o **mesmo** finalize, com flags:
   - `skip_ia_resumo=true`, `skip_qwen=true` (já hoje)
   - `enrich_max=3` (cap fixo)
   - `max_pool_candidates=30` (não pontuar 200 linhas)
3. Remover ou depreciar `_finalize_busca_lote_top3_response` duplicado.

**Critério de aceite:** amostra ouro — `itemId` e `busca_lote` retornam **mesmos 3 PNCP** (ou superset) para ≥8/10 itens.

### Fase C — Preço homologado (paralelo, dados)

Objetivo: menos estimado na cotação.

1. Confirmar `PNCP_INGEST_RESULTADOS_TOPUP_ENABLED=1` e planner rodando.
2. Monitorar crescimento de `valor_unitario_homologado IS NOT NULL` (SQL semanal).
3. Opcional: na resposta API, expor `preco_fonte: homologado|estimado` para UI (transparência).

Não depende de refatorar busca.

### Fase D — Performance estrutural (1 PR, após B)

1. Enrich **uma vez**, nos K melhores candidatos **antes** do top3 (K=5–8).
2. `BULK_CONCURRENCY=2` com rate limit no backend se necessário.
3. Cache HTTP curto por `(termo, uf, faixa)` no lote (opcional).

Meta: 696 itens em **≤ 90 min** com paridade individual.

### Fase E — Regressão automatizada leve

Estender `scripts/regression-pncp-check.py` ou `test_bulk_search_lote.py`:

- Lista fixa `GOLDEN_TERMS` (incl. álcool gel, item 13871 termo).
- Assert: `bulk top3_final >= individual top3_final - 0` e mesmos `numero_pncp` quando faixa igual.

Roda no CI ou pré-deploy DESKTOP — **substitui debug manual em massa**.

---

## 6. Priorização recomendada

```
1. Amostra ouro (4.1) + SQL homologado (4.2)     → confirma diagnóstico
2. Fase B (paridade pipeline)                     → precisão lote ≈ individual
3. Fase A (env enrich)                            → tempo rápido se B ainda lento
4. Fase C (ingest homologado)                     → preço correto
5. Fase E (golden tests)                          → não regredir de novo
```

**Evitar por enquanto:** voltar ao top3 scoring antigo puro (regressão álcool gel); debug item a item nos 696; ligar Qwen no bulk.

---

## 7. Decisões para alinhar com cliente

1. **Prioridade:** tempo total da cotação vs. precisão igual ao individual vs. CNPJ na hora?
2. **Aceite:** lote pode ser 5–10% mais lento que hoje se entregar **mesma qualidade** que `?itemId=`?
3. **Preço:** exibir badge “estimado” quando homologado NULL até o backfill encher?

---

## 8. Checklist pós-implementação (futuro)

- [ ] Amostra 13871: bulk ≡ individual (3 preços, mesmos PNCP)
- [ ] 696 itens: tempo ≤ 1h30 com `BULK_CONCURRENCY=2` + enrich cap 3
- [ ] `so_estimado` no SQLite cai mês a mês
- [ ] Zero aumento de “0 preços” vs. corrida atual do lote (não perder recall novo)

---

*Última atualização: 2026-06-22 — avaliação inicial, sem implementação.*
