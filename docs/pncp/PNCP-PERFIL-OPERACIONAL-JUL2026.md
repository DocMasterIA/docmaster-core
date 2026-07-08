# PNCP — Perfil operacional jul/2026 (handoff completo)

Documento único para retomar operação, deploy e tuning do **pncp_researcher_service** após:

1. Regressão de qualidade de busca (jun/2026)
2. Otimização do autostart em lote (696+ itens)
3. Correção da **faixa regional direcional** (`cima` / `baixo`)
4. Ajustes de UI (variação global default 0%)

**Estado jul/2026:** validado em produção — «tudo funcionando certinho».

---

## Resumo executivo

| Tema | Estado |
|------|--------|
| **Qualidade de busca** | Baseline `94711975` + melhorias seletivas em `e0427a0b` / `c83af16c` |
| **Bulk intelligent** | **Desligado** (`PNCP_BULK_USE_INTELLIGENT_PIPELINE=0`) |
| **Performance lote** | Enrich cap corrigido, `LOCAL_ENRICH=0`, 1 chamada nacional no autostart |
| **Faixa direcional** | Gate estrito + enrich pré/pós-faixa — ver [PNCP-FAIXA-DIRECIONAL-JUL2026.md](./PNCP-FAIXA-DIRECIONAL-JUL2026.md) |
| **UI variação global** | Default **0%** em CotacaoDetalhe (não 20%) |
| **Deploy VPS** | `git pull` + hotfix researcher + `npm run build` front; recreate só para mudar env |

### Commits de referência (ordem cronológica)

| Commit | Descrição |
|--------|-----------|
| `94711975` | Último bom confirmado (26/06 ~10:21) — enrich **sem** preço homologado |
| `e0427a0b` | Restaura pipeline lote legado + compose conservador + faixa `sentido` |
| `c83af16c` | Performance lote (enrich cap, front nacional único) |
| `b41e7a94` | `faixa_sentido` explícito em todos os caminhos de pool/top3 |
| `26e33b3f` | Refiltro de faixa **após** enrich PNCP |
| `ac03a4b1` | Hotfix indentação `pncp_supplier_enrichment.py` (backend) |
| `ad4dced9` | Variação global UI default 0% |
| `c3c1aa86` | Faixa direcional completa (`row_unit_price_for_faixa_gate`, pre-enrich, `faixaAtiva` front) |

**HEAD recomendado:** `c3c1aa86` ou posterior.

---

## 1. Correção de qualidade de busca

### Problema

Após 26/06 tarde: ruído na busca («lacre» em «dreno», doses erradas em xaropes).

### Causa

`ff74e122` (bulk intelligent), `b5a6f164` (spec/index agressivo), flags permissivas (FLEX 0.65, ANCHOR=1).

### Solução (sem rollback total para `94711975`)

1. `busca_lote` → fluxo legado `busca_lote_top3_parity` (sem `bulk_intelligent`)
2. `_iter_search_term_fallbacks` → ordem `raw → preprocess → anchor`
3. **Mantido:** `termo_spec`, faixa com `sentido`, `product_spec_match`
4. `PNCP_BULK_USE_INTELLIGENT_PIPELINE=0` no compose

### Testes de sanidade

| Termo | Critério |
|-------|----------|
| `DRENO DE PEN ROSE ESTÉRIL N. 4` | Top com penrose + nº 4 |
| `ACEBROFILINA 50 MG/5 ML XAROPE C/120ML` | Dose/volume corretos |

---

## 2. Faixa regional e direção global

Documento detalhado: **[PNCP-FAIXA-DIRECIONAL-JUL2026.md](./PNCP-FAIXA-DIRECIONAL-JUL2026.md)**

### Resumo técnico

| Camada | Arquivo | Responsabilidade |
|--------|---------|------------------|
| Cálculo banda | `pricing_faixa.py` | `compute_faixa_regional(base, pct, sentido)` |
| Gate preço | `pricing_display.py` | `row_unit_price_for_faixa_gate`, `item_matches_faixa_band` |
| Orquestração | `service.py` | pre-enrich, pool, enrich, refiltro, top3 |
| Sessão | `pncp_cotacao_api.py` | `variacao_sentido_global` no search-context |
| UI busca | `BuscaInteligenteCotacoes.vue` | payload faixa + filtro `pnCpRowWithinFaixaRegional` |
| UI cotação | `CotacaoDetalhe.vue` | variação global % + direção (default 0%) |

### Fluxo lote (autostart) — ordem final

```text
itens do índice local
  → pre-enrich homolog (se cima/baixo)
  → pool recall (_build_bulk_manual_recall_pool) com gate de faixa
  → enrich pool (cap PNCP_BULK_ENRICH_HOMOLOG_MAX)
  → refiltro faixa (eliminados_faixa_pos_enrich)
  → top3 + refiltro top3
  → resposta HTTP
```

### Regra de negócio `cima`

Preço homologado exibido deve ser **≥ valor base**. Catálogo/estimado **não** substitui homologado no gate direcional.

### UI — variação global

- Campo «Variação global da cotação» em `CotacaoDetalhe.vue`
- Default exibição: **0%** (antes 20% sem estar salvo)
- **Salvar** sessão após alterar % ou direção antes do autostart
- Direção: `cima` | `baixo` | `ambos`

---

## 3. Performance do autostart (lote)

### Sintoma

«Item N de 696» parado minutos — não é freeze; item difícil (sem índice → hybrid PNCP até 90s).

### Correções (`c83af16c`)

| Mudança | Antes | Depois |
|---------|-------|--------|
| `_bulk_recall_enrich_cap` | `max(16, bulk)` | só `PNCP_BULK_ENRICH_HOMOLOG_MAX` |
| `PNCP_BULK_LOCAL_ENRICH_HOMOLOG_MAX` | 6 | **0** |
| `PNCP_BULK_ENRICH_HOMOLOG_MAX` | 3 | **2** |
| Front autostart | UF + retry BR | **1 chamada nacional** |

### Expectativa (696 itens)

| Perfil | Por item | Total |
|--------|----------|-------|
| Com índice local | 5–15s | 1–3 h |
| Sem índice + hybrid | até 90s | várias horas |
| `HYBRID_BULK=0` | 5–35s vazio | 1–2 h + rebusca manual |

---

## 4. Flags importantes

### Qualidade (recomendado)

```text
PNCP_BULK_USE_INTELLIGENT_PIPELINE=0
PNCP_SEARCH_TIER_FLEX_RATIO=0.78
PNCP_SEARCH_ANCHOR_TIER_ENABLED=0
PNCP_HYBRID_MIN_LOCAL_RESULTS=8
PNCP_IA_RERANK_BULK_ENABLED=false
```

### Performance lote

```text
PNCP_BULK_ENRICH_HOMOLOG_MAX=2
PNCP_BULK_LOCAL_ENRICH_HOMOLOG_MAX=0
PNCP_BULK_SEARCH_MAX_SECONDS=90
PNCP_HYBRID_BULK_ENABLED=1
```

### Velocidade máxima (trade-off: mais vazios)

```text
PNCP_HYBRID_BULK_ENABLED=0
PNCP_BULK_SEARCH_MAX_SECONDS=35
```

---

## 5. Deploy na VPS

### Pré-requisitos

- Repo `~/docmaster-core`
- Volume PNCP external (`docker-compose.pncp.override.yml`)
- Rede `docmaster_net` — backend → `pncp_researcher_service:8012`

### Atualização completa (código + front) — rotina normal

```bash
cd ~/docmaster-core
git pull
git rev-parse --short HEAD   # c3c1aa86+

# Researcher (faixa + lote + qualidade)
./scripts/deploy-pncp-researcher-code.sh

# Frontend (faixaAtiva + variação 0%)
cd frontend-vue && npm run build
# reiniciar nginx / docker compose restart frontend-vue (conforme stack)

# Backend — só se necessário (supplier_enrichment já corrigido em ac03a4b1)
docker compose restart backend   # se pull trouxe mudanças no Django
```

### Recriar container (mudar env / rebuild imagem)

```bash
cd ~/docmaster-core
unset PNCP_BULK_LOCAL_ENRICH_HOMOLOG_MAX PNCP_BULK_ENRICH_HOMOLOG_MAX

PNCP_NO_HOST_PORT=1 \
PNCP_BUILD_CONTEXT=docmaster-core \
PNCP_BUILD=1 \
PNCP_BULK_ENRICH_HOMOLOG_MAX=2 \
PNCP_BULK_LOCAL_ENRICH_HOMOLOG_MAX=0 \
./scripts/ensure-pncp-researcher.sh --recreate
```

`PNCP_NO_HOST_PORT=1` — usar se porta 8012 falhar no WSL/Docker Desktop.

### Hotfix só researcher (sem env)

```bash
./scripts/deploy-pncp-researcher-code.sh
```

---

## 6. Verificação pós-deploy

### Versão e código

```bash
cd ~/docmaster-core && git rev-parse --short HEAD

docker exec pncp_researcher_service grep -c bulk_intelligent \
  /app/pncp_researcher_service/app/service.py
# esperado: 0

docker exec pncp_researcher_service grep -c row_unit_price_for_faixa_gate \
  /app/pncp_researcher_service/app/pricing_display.py
# esperado: >= 2

docker exec pncp_researcher_service grep -c eliminados_faixa_pos_enrich \
  /app/pncp_researcher_service/app/service.py
# esperado: >= 2
```

### Flags no container

```bash
docker exec pncp_researcher_service env | grep -E \
  'BULK_ENRICH|BULK_LOCAL|HYBRID_BULK|BULK_USE_INTELLIGENT' | sort
```

Esperado:

```text
PNCP_BULK_ENRICH_HOMOLOG_MAX=2
PNCP_BULK_LOCAL_ENRICH_HOMOLOG_MAX=0
PNCP_BULK_USE_INTELLIGENT_PIPELINE=0
```

### Health

```bash
docker exec pncp_researcher_service python -c \
  "import urllib.request; print(urllib.request.urlopen(
    'http://127.0.0.1:8012/api/pncp-research/health', timeout=5).read().decode())"
```

### Checklist funcional

- [ ] Penrose N.4 e Acebrofilina 50mg/5ml no top3
- [ ] Base R$ 19, cima 50% — sem preço < R$ 19
- [ ] Variação global UI mostra 0% quando não salva
- [ ] Autostart lote: 1 request nacional por item (não UF+BR)

---

## 7. Diagnóstico — lote lento

Item N lento = descrição da N-ésima linha em «Itens da cotação».

Teste isolado no container:

```bash
docker exec pncp_researcher_service python -c "
import asyncio, json, time
from pncp_researcher_service.app.schemas import MarketSearchRequest
from pncp_researcher_service.app.service import market_search_intelligent

async def main():
    p = MarketSearchRequest(
        termo_busca='DESCRICAO DO ITEM',
        busca_lote=True,
        max_paginas=6,
        valor_base_referencia=19.0,
        variacao_percentual_referencia=50.0,
        variacao_sentido_referencia='cima',
    )
    t0 = time.time()
    out = await market_search_intelligent(p)
    funil = (out.get('stats') or {}).get('funil_busca') or {}
    print('elapsed_s:', round(time.time()-t0, 1))
    print('sentido:', out.get('filtros', {}).get('variacao_sentido_referencia'))
    print('faixa:', out.get('filtros', {}).get('faixa_regional_min'),
          out.get('filtros', {}).get('faixa_regional_max'))
    print('pre_enrich:', funil.get('pre_enrich_direcional'))
    print('pos_enrich_cut:', funil.get('eliminados_faixa_pos_enrich'))
    print('top3:', funil.get('top3_final'))
    for it in out.get('itens') or []:
        print(' -', it.get('valor_unitario_homologado') or it.get('valor_unitario'))
asyncio.run(main())
"
```

---

## 8. Armadilhas de deploy

| Armadilha | Sintoma | Solução |
|-----------|---------|---------|
| `git pull` sem rebuild front | Faixa errada na UI | `npm run build` |
| Hotfix researcher sem front | `faixaAtiva` antiga | Build front |
| `env` com PNCP_BULK antigo | Cap enrich 6/3 | `unset` + recreate |
| Porta 8012 WSL | expose 500 | `PNCP_NO_HOST_PORT=1` |
| Variação/direção não salvas | Sentido `ambos` no backend | Salvar em CotacaoDetalhe |
| Só `service.py` no researcher | Falta `pricing_display.py` | `deploy-pncp-researcher-code.sh` copia ambos |

---

## 9. Rollback

### Total (26/06 manhã)

```bash
git switch --detach 94711975
PNCP_NO_HOST_PORT=1 PNCP_BUILD_CONTEXT=docmaster-core \
  ./scripts/ensure-pncp-researcher.sh --recreate
```

Perde: faixa direcional, enrich de preço homologado, performance lote.

### Só performance (manter `c3c1aa86`)

```bash
PNCP_BULK_ENRICH_HOMOLOG_MAX=3
PNCP_BULK_LOCAL_ENRICH_HOMOLOG_MAX=6
```

---

## 10. Arquivos centrais

| Arquivo | Papel |
|---------|--------|
| `pncp_researcher_service/app/service.py` | Busca inteligente, lote, faixa, enrich |
| `pncp_researcher_service/app/pricing_display.py` | Gate faixa, preço canônico |
| `pncp_researcher_service/app/pricing_faixa.py` | Banda regional + sentido |
| `pncp_researcher_service/app/local_index.py` | FTS, enrich homolog |
| `pncp_researcher_service/app/config.py` | Defaults env |
| `docker-compose.pncp.yml` | Flags produção |
| `frontend-vue/src/views/BuscaInteligenteCotacoes.vue` | Autostart, payload faixa |
| `frontend-vue/src/views/CotacaoDetalhe.vue` | Variação global UI |
| `frontend-vue/src/utils/pncpPricing.js` | `computeFaixaRegional` |
| `backend/app/pncp_cotacao_api.py` | Search-context sessão |
| `backend/app/services/pncp_supplier_enrichment.py` | Enriquecimento fornecedor |
| `scripts/ensure-pncp-researcher.sh` | Deploy / recreate |
| `scripts/deploy-pncp-researcher-code.sh` | Hotfix código |

---

## 11. Backlog

1. `tests/test_search_regression.py` — Penrose + Acebrofilina no CI
2. Alinhar `BULK_SEARCH_TIMEOUT_MS` front (~40s) com backend
3. `maxAttempts: 1` no lote
4. Gate CI: `grep bulk_intelligent` = 0 + testes faixa direcional
5. UI: mostrar descrição do item durante autostart lento

---

## Referências

- [PNCP-FAIXA-DIRECIONAL-JUL2026.md](./PNCP-FAIXA-DIRECIONAL-JUL2026.md) — faixa cima/baixo (detalhe)
- [PNCP-BUSCA-INTELIGENTE-REGRESSAO-UI-VS-BACKEND.md](./PNCP-BUSCA-INTELIGENTE-REGRESSAO-UI-VS-BACKEND.md) — bisect jun/2026
- [PNCP-PARIDADE-LOTE-STATUS-IMPLEMENTADO.md](./PNCP-PARIDADE-LOTE-STATUS-IMPLEMENTADO.md)
- [../deploy/PNCP-RESEARCHER-24-7.md](../deploy/PNCP-RESEARCHER-24-7.md)
- [../deploy/PNCP-COMANDOS-OPERACAO.txt](../deploy/PNCP-COMANDOS-OPERACAO.txt)

---

*Última atualização: 2026-07-06 — estado validado em produção (`c3c1aa86+`).*
