# Busca inteligente PNCP — reestruturação qualidade + Qwen

**Objetivo:** pesquisas de preço mais **precisas**, com **menos itens fracos** no top 3, usando rerank e resumo via **Qwen** (`PNCP_IA_BASE_URL`).

**Código:** `pncp_researcher_service` — revisão `2026-06-19-quality-qwen` (`PNCP_SEARCH_CODE_REV`).

Documentação Qwen/API: [QWEN-INTEGRACAO-DOCMASTER.md](./QWEN-INTEGRACAO-DOCMASTER.md)

---

## 1. Pipeline (antes vs depois)

### Antes (recall alto, qualidade irregular)

```
Termo → FTS tiers flex (65%) + anchor 2 palavras
     → scoring + fallback relaxado + fallback agressivo
     → reescala 35–100 (inflava itens fracos)
     → pool literal/similar
     → rerank IA só se pool 100% literal OU 100% similar
     → top 3 (até 3 similares se faltava literal)
```

Problemas observados:

- Muitos itens «parecidos» mas errados após relaxar termos.
- Rerank **não rodava** no caso mais comum (`mixed_fallback`: 1–2 literais + similares).
- Ollama 7B local no rerank (4,5s) → timeouts frequentes → fallback heurístico.

### Depois (qualidade primeiro + Qwen)

```
Termo → tiers strict/core + flex 78% (sem anchor por default)
     → scoring estrito; relaxado só se pool < 2; agressivo desligado
     → scores absolutos (sem reescala inflacionada)
     → pool literal/similar filtrado para IA
     → rerank Qwen também no pool misto
     → top 3 com no máximo 1 slot «similaridade»
     → resumo IA por item (Qwen)
```

---

## 2. Variáveis de ambiente (modo qualidade)

Defaults no `docker-compose.pncp.yml`:

| Variável | Default | Efeito |
|----------|---------|--------|
| `PNCP_SEARCH_QUALITY_FIRST` | `1` | Liga pacote qualidade |
| `PNCP_SEARCH_TIER_FLEX_RATIO` | `0.78` | Exige 78% dos tokens núcleo (era 65%) |
| `PNCP_SEARCH_ANCHOR_TIER_ENABLED` | `0` | Desliga tier «2 palavras» (anchor) |
| `PNCP_SEARCH_MAX_SIMILAR_IN_TOP3` | `1` | Máx. 1 similar no top 3 sem rerank |
| `PNCP_IA_RERANK_MIXED_POOL` | `1` | Rerank IA quando literal+similar misturados |
| `PNCP_SEARCH_MIN_SCORE_APROVACAO` | `55` | Piso de score (modo qualidade ≥ 55) |
| `PNCP_IA_BASE_URL` | `http://qwen_llm_service:8015` | Gateway Qwen |
| `PNCP_IA_TIMEOUT_SECONDS` | `22` | Timeout rerank |
| `PNCP_IA_ITEM_RESUMO_TIMEOUT_SECONDS` | `18` | Timeout resumo item |

### Voltar ao modo «recall» (mais itens, menos precisão)

```env
PNCP_SEARCH_QUALITY_FIRST=0
PNCP_SEARCH_TIER_FLEX_RATIO=0.65
PNCP_SEARCH_ANCHOR_TIER_ENABLED=1
PNCP_SEARCH_MAX_SIMILAR_IN_TOP3=3
PNCP_IA_RERANK_MIXED_POOL=0
PNCP_SEARCH_MIN_SCORE_APROVACAO=50
PNCP_IA_BASE_URL=http://llm_api:8002
PNCP_IA_TIMEOUT_SECONDS=4.5
```

Recriar: `docker compose -f docker-compose.pncp.yml up -d --force-recreate pncp_researcher_service`

---

## 3. Papéis da IA (Qwen)

| Etapa | Função | Quando |
|-------|--------|--------|
| **Rerank** | Escolhe 3 IDs mais aderentes entre até 36 candidatos | Busca inteligente manual (não lote) |
| **Resumo** | 1 frase `ia_interpretacao_item` para título ambíguo | Top 3 retornado |

Prompt rerank reforçado: rejeita categoria errada, kits vagos, scores inflados.

**Pré-requisito:** `QWEN_API_KEY` + `qwen_llm_service` Up — ver [QWEN-INTEGRACAO-DOCMASTER.md](./QWEN-INTEGRACAO-DOCMASTER.md).

Sem Qwen válido: busca ainda funciona com heurística SQL+scoring, mas **sem** rerank/resumo IA.

---

## 4. Funil de métricas (`stats.funil_busca`)

Campos úteis no JSON de resposta / diagnose:

| Campo | Significado |
|-------|-------------|
| `search_quality_first` | Modo qualidade ativo |
| `ia_rerank_allowed` | Rerank IA autorizado para o pool atual |
| `ia_rerank_pool_mode` | `literal_only`, `similar_only`, `mixed_fallback` |
| `literal_pool` / `similar_pool` | Tamanho dos pools |
| `scored_estrito` / `scored_relaxado` | Itens após cada fase |
| `fallback_agressivo_desligado` | Modo qualidade bloqueou fallback agressivo |
| `ia_rerank_usado` (em `stats`) | Rerank Qwen aplicou top 3 |

Health: `GET /api/pncp-research/health` → `ia.base_url`, `search_code_rev`.

---

## 5. Deploy

```bash
# 1. Qwen (stack principal)
docker compose --profile qwen up -d --build qwen_llm_service

# 2. PNCP com envs novas
cp docmaster-core/docker-compose.pncp.yml ~/docker-compose.pncp.yml
docker compose -f ~/docker-compose.pncp.yml up -d --build --force-recreate pncp_researcher_service

# 3. Conferir
curl -s http://127.0.0.1:8012/api/pncp-research/health | python3 -m json.tool
```

Esperado em `health`:

```json
"ia": {
  "base_url": "http://qwen_llm_service:8015",
  "rerank_enabled": true,
  "item_resumo_enabled": true
}
```

`search_code_rev`: `2026-06-19-quality-qwen`

---

## 6. Testes locais

```bash
cd pncp_researcher_service
python3 -m unittest tests.test_search_quality_mode tests.test_pncp_ia_config -v
```

---

## 7. Arquivos alterados

| Arquivo | Mudança |
|---------|---------|
| `app/config.py` | Flags qualidade + flex 0.78 default |
| `app/local_index.py` | Anchor tier opcional |
| `app/service.py` | Rerank mixed, cap similar, prompt, fallbacks |
| `docker-compose.pncp.yml` | Envs qualidade + Qwen |
| `tests/test_search_quality_mode.py` | Testes unitários |

---

## 8. Trade-offs

| Ganho | Custo |
|-------|-------|
| Top 3 mais aderente ao termo | Menos resultados em termos muito raros |
| Rerank Qwen no pool misto | Latência ~5–20s por busca + custo API |
| Menos «lixo» similar | Pode retornar < 3 cotações se índice/faixa apertar |

Se faltar cotação legítima, revisar: faixa de preço ±%, homologados no índice, ou relaxar **só** `PNCP_SEARCH_TIER_FLEX_RATIO` para `0.72` mantendo Qwen.
