# PNCP — Busca inteligente com IA (implementação atual)

**Atualizado:** jun/2026 · revisão de código `2026-06-19-quality-qwen`

Este documento descreve o endpoint de busca inteligente e a camada de IA. Para o **modo qualidade** (tiers rígidos, rerank no pool misto, Qwen), ver o guia dedicado:

→ **[PNCP-BUSCA-INTELIGENTE-QUALIDADE.md](./PNCP-BUSCA-INTELIGENTE-QUALIDADE.md)**

Integração Qwen (chave, deploy, health): **[QWEN-INTEGRACAO-DOCMASTER.md](./QWEN-INTEGRACAO-DOCMASTER.md)**

---

## 1) Objetivo

Entregar, para cada busca inteligente:

- **até 3 cotações** selecionadas automaticamente (prioridade qualidade sobre recall);
- classificação com:
  - `score_aprovacao` (0 a 100),
  - `confiabilidade` (Alta / Média / Baixa),
  - `risco` (Baixo / Médio / Alto),
  - `status` (Aprovado / Revisar);
- opcionalmente `ia_interpretacao_item` (resumo Qwen) e rerank IA no top 3.

---

## 2) Arquitetura

| Camada | Ficheiro / rota |
|--------|-----------------|
| Lógica de busca + scoring + IA | `pncp_researcher_service/app/service.py` |
| Rotas HTTP | `pncp_researcher_service/app/api.py` |
| Índice FTS + tiers | `pncp_researcher_service/app/local_index.py` |
| Config / envs | `pncp_researcher_service/app/config.py` |
| Frontend | `frontend-vue/src/views/BuscaInteligenteCotacoes.vue` |
| Cliente HTTP | `frontend-vue/src/services/pncpResearch.js` |

**Endpoint:** `POST /api/pncp-research/market-search/intelligent`

O Django faz proxy em `/api/pncp-research/*` para o contentor PNCP (porta 8012).

---

## 3) Fluxo técnico (resumo)

```
Termo + filtros (UF, faixa de preço, homologados)
  → local_item_search (FTS5 + tiers strict/core/flex)
  → pré-filtro + scoring composto (semântica, recência, preço, literal)
  → pools literal / similar
  → rerank IA (Qwen) — também no pool misto quando PNCP_IA_RERANK_MIXED_POOL=1
  → seleção top 3 (máx. 1 similar no top 3 em modo qualidade)
  → resumo IA por item (opcional)
```

Com `PNCP_SEARCH_QUALITY_FIRST=1` (default no `docker-compose.pncp.yml`):

- tiers mais rígidos (`PNCP_SEARCH_TIER_FLEX_RATIO=0.78`);
- fallback agressivo desligado;
- relaxamento só se pool &lt; 2 candidatos;
- scores absolutos (sem reescala 35–100).

Detalhe completo: [PNCP-BUSCA-INTELIGENTE-QUALIDADE.md](./PNCP-BUSCA-INTELIGENTE-QUALIDADE.md).

---

## 4) Camada de IA (Qwen)

| Etapa | Env principal | Default |
|-------|---------------|---------|
| Gateway | `PNCP_IA_BASE_URL` | `http://qwen_llm_service:8015` |
| Rerank | `PNCP_IA_RERANK_ENABLED`, `PNCP_IA_TIMEOUT_SECONDS` | `1`, `22` |
| Resumo item | `PNCP_IA_ITEM_RESUMO_ENABLED`, `PNCP_IA_ITEM_RESUMO_TIMEOUT_SECONDS` | `1`, `18` |
| Pool misto | `PNCP_IA_RERANK_MIXED_POOL` | `1` |

**Pré-requisito:** `QWEN_API_KEY` válida + `docker compose --profile qwen up -d qwen_llm_service`.

Sem Qwen: a busca continua com heurística SQL + scoring, mas **sem** rerank/resumo IA.

Health expõe bloco `ia`:

```bash
curl -s http://127.0.0.1:8012/api/pncp-research/health | python3 -m json.tool
```

Campos úteis: `ia.base_url`, `ia.search_quality_first`, `ia.search_code_rev`.

---

## 5) Scoring e classificação

Sinais do `score_aprovacao`:

1. Aderência semântica/tokens (`_compute_match_score`)
2. Match literal (`_literal_match_score`)
3. Recência (`_score_recency`)
4. Coerência de valor vs mediana (`_score_value_coherence`)
5. Clareza/unidade e penalidade de contexto incompatível

Classificação derivada (piso configurável):

| Campo | Regra |
|-------|-------|
| `confiabilidade` Alta | score ≥ 80 |
| `confiabilidade` Média | score ≥ `PNCP_SEARCH_MIN_SCORE_APROVACAO` (55 em qualidade, 50 recall) |
| `risco` Baixo / Médio / Alto | espelha faixas acima |

Blindagem: se IA devolver score muito baixo para item já forte (`ia<=15`, `base>=70`, `literal>=45`), preserva score base.

---

## 6) Contrato da resposta

Formato compatível com `MarketSearchResponse`:

- `ok`, `filtros`, `stats`, `itens` (top 3)
- `stats.funil_busca` — métricas do funil (pools, rerank, modo qualidade)
- `stats.ia_rerank_usado` — rerank Qwen aplicou ordenação final

Campos por item: `score_aprovacao`, `confiabilidade`, `risco`, `status`, `ia_interpretacao_item` (quando resumo OK).

---

## 7) Variáveis de ambiente (busca + IA)

Ver tabela completa em [PNCP-BUSCA-INTELIGENTE-QUALIDADE.md §2](./PNCP-BUSCA-INTELIGENTE-QUALIDADE.md#2-variáveis-de-ambiente-modo-qualidade).

Principais no `docker-compose.pncp.yml`:

```env
PNCP_SEARCH_QUALITY_FIRST=1
PNCP_SEARCH_TIER_FLEX_RATIO=0.78
PNCP_SEARCH_ANCHOR_TIER_ENABLED=0
PNCP_SEARCH_MAX_SIMILAR_IN_TOP3=1
PNCP_IA_RERANK_MIXED_POOL=1
PNCP_SEARCH_MIN_SCORE_APROVACAO=55
PNCP_IA_BASE_URL=http://qwen_llm_service:8015
```

---

## 8) Testes

```bash
cd pncp_researcher_service
python3 -m unittest tests.test_search_quality_mode tests.test_pncp_ia_config -v
```

---

## 9) Limitações e trade-offs

| Aspecto | Nota |
|---------|------|
| Latência | Rerank + resumo Qwen: ~5–20s por busca inteligente |
| Recall | Modo qualidade pode retornar &lt; 3 itens em termos raros |
| Custo | 1–4 chamadas Qwen por busca (rerank + até 3 resumos) |
| Lote | Rerank IA desligado em busca em lote (performance) |

Para mais resultados (menos precisão), ver secção «Voltar ao modo recall» no doc de qualidade.
