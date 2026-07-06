# PNCP — Perfil operacional jul/2026 (handoff completo)

Documento único para retomar operação, deploy e tuning do **pncp_researcher_service** após a investigação de regressão de busca e otimização do **autostart em lote** (696+ itens).

Relacionado: [PNCP-BUSCA-INTELIGENTE-REGRESSAO-UI-VS-BACKEND.md](./PNCP-BUSCA-INTELIGENTE-REGRESSAO-UI-VS-BACKEND.md) (bisect, commits culpados, rollback total `94711975`).

---

## Resumo executivo

| Tema | Estado jul/2026 |
|------|-----------------|
| **Qualidade de busca** | Baseline comportamental `94711975` + melhorias seletivas (`termo_spec`, faixa `sentido`) em `e0427a0b` / `c83af16c` |
| **Bulk intelligent** | **Desligado** (`PNCP_BULK_USE_INTELLIGENT_PIPELINE=0`) — causava regressão de ruído |
| **Performance lote** | Enrich cap corrigido, `LOCAL_ENRICH=0`, front com 1 chamada nacional no autostart |
| **Deploy VPS** | `git pull` + recreate com env explícita; usar `PNCP_NO_HOST_PORT=1` se porta 8012 falhar |
| **Lote “travado”** | Não é freeze — itens sem índice local esperam até **90s** (híbrido PNCP ao vivo) |

**Commits de referência (main):**

- `94711975` — último bom confirmado (26/06 ~10:21)
- `e0427a0b` — restaura pipeline lote legado + compose conservador + doc regressão
- `c83af16c` — performance lote (enrich cap, front nacional único, defaults compose)

---

## 1. Correção de qualidade (o que foi feito)

### Problema

Após 26/06 tarde, busca inteligente passou a trazer ruído (ex.: «lacre» ao buscar «dreno», doses erradas em xaropes).

### Causa

Combinação de **código** (`ff74e122` bulk intelligent, `b5a6f164` spec/index) e **flags** mais permissivas (FLEX 0.65, ANCHOR=1, hybrid agressivo).

### Solução aplicada (sem rollback total)

Em vez de ficar em `94711975` para sempre:

1. **`service.py`** — `busca_lote` volta ao fluxo **legado** (`busca_lote_top3_parity`); removido ramo `bulk_intelligent`.
2. **`_iter_search_term_fallbacks`** — ordem `raw → preprocess → anchor` (como `94711975`).
3. **Mantido** de commits posteriores: `termo_spec`, faixa regional com `sentido`, melhorias em `product_spec_match.py`.
4. **`config.py` / compose** — `PNCP_BULK_USE_INTELLIGENT_PIPELINE` default **False**; tiers/hybrid alinhados ao perfil `94711975`.

### O que **não** foi alterado (de propósito)

- Ingestão 24/7
- `supplier_resolver` / nomes de fornecedor
- Filtros verbais extensos em `product_category_match.py` (rejeitados)
- Busca manual item a item (fora do `busca_lote`)

### Variação global — direção (`cima` / `baixo` / `ambos`)

Correção pós-`94711975` (commits `31daf6b2`, `04f87054`, `7b7caced`) que **não pode se perder** no merge:

| Camada | O que faz |
|--------|-----------|
| `pricing_faixa.py` | `compute_faixa_regional` com banda assimétrica (cima/baixo) |
| `pricing_display.py` | `item_matches_faixa_band`: recall homolog/estimado **só** com `ambos` |
| `service.py` | `ref_sentido` / `faixa_sentido` explícito em scoring, lote, IA rerank e top3 |
| `pncp_cotacao_api.py` | `variacao_sentido_global` no payload `search-context` |
| `BuscaInteligenteCotacoes.vue` | `computeFaixaRegional` + `pnCpRowWithinFaixaRegional`; sentido **só da sessão global** |

**Deploy:** researcher **e** backend Django **e** build do frontend — hotfix só no `service.py` não basta se o backend não envia `variacao_sentido_global` nos itens.

Teste rápido: variação global **só para cima** 20%, base R$ 100 → faixa R$ 100–120; preço R$ 90 não deve aparecer mesmo com estimado na banda.

### Testes de sanidade pós-deploy

| Termo | Critério |
|-------|----------|
| `DRENO DE PEN ROSE ESTÉRIL N. 4` | Top contém penrose + número 4 |
| `ACEBROFILINA 50 MG/5 ML XAROPE C/120ML` | Dose/volume corretos no top3 |

---

## 2. Performance do autostart (lote)

### Sintoma

«Busca automática em andamento: item N de 696» — maioria rápida, mas **alguns itens param minutos** no contador. O número N **muda entre cotações** (item 8 numa, 12 noutra) porque é a **descrição do produto**, não a posição fixa.

### Causas identificadas

```text
Por item (sequencial, BULK_CONCURRENCY=1):
  1. local_item_search (SQLite/FTS)     → rápido na maioria
  2. enrich PNCP ao vivo (CNPJ)         → até N chamadas HTTP /resultados
  3. se local_priced == 0:
       hybrid market_search (PNCP live) → até 2 páginas × timeout PNCP (60s)
  4. teto backend: PNCP_BULK_SEARCH_MAX_SECONDS (90s)
  5. teto frontend: BULK_SEARCH_TIMEOUT_MS (185s) + até 2 retries em erro rede
```

### Correções de código (`c83af16c`)

| Mudança | Antes | Depois |
|---------|-------|--------|
| `_bulk_recall_enrich_cap` | `max(SEARCH_ENRICH=16, BULK=3)` | só `PNCP_BULK_ENRICH_HOMOLOG_MAX` |
| `PNCP_BULK_LOCAL_ENRICH_HOMOLOG_MAX` | 6 | **0** (sem enrich no loop de termos) |
| `PNCP_BULK_ENRICH_HOMOLOG_MAX` (compose) | 3 | **2** |
| Front `BuscaInteligenteCotacoes.vue` | UF → se vazio, retry nacional | autostart: **1 chamada nacional** |

### `PNCP_BULK_LOCAL_ENRICH_HOMOLOG_MAX=0` — o que **não** faz

- **Não apaga** homologados no índice SQLite.
- **Não desliga** enrich na busca manual (`PNCP_SEARCH_ENRICH_HOMOLOG_MAX=16`).
- **Não desliga** enrich no finalize do lote (`PNCP_BULK_ENRICH_HOMOLOG_MAX=2`).
- Só pula enrich **entre tentativas de termo** no meio do `busca_lote`.

### Expectativa de tempo (696 itens)

| Perfil | Tempo típico por item | 696 itens (ordem de grandeza) |
|--------|----------------------|-------------------------------|
| Com índice local | 5–15s | 1–3 h |
| Sem índice + hybrid ligado | até **90s** | várias horas |
| Sem índice + `HYBRID_BULK=0` | 5–35s (vazio rápido) | 1–2 h + rebusca manual dos vazios |

---

## 3. Flags importantes

### Qualidade de busca (perfil conservador — recomendado)

| Variável | Valor | Notas |
|----------|-------|-------|
| `PNCP_BULK_USE_INTELLIGENT_PIPELINE` | `0` | Bulk intelligent off |
| `PNCP_SEARCH_TIER_FLEX_RATIO` | `0.78` | Flex mais rígido |
| `PNCP_SEARCH_ANCHOR_TIER_ENABLED` | `0` | Sem tier anchor extra |
| `PNCP_HYBRID_MIN_LOCAL_RESULTS` | `8` | Hybrid manual só com pool fraco |
| `PNCP_HYBRID_MAX_LIVE_PAGES` | `6` | Busca manual |
| `PNCP_IA_RERANK_BULK_ENABLED` | `false` | Sem rerank IA no lote |

### Performance do lote

| Variável | Default compose atual | Função |
|----------|----------------------|--------|
| `PNCP_BULK_ENRICH_HOMOLOG_MAX` | `2` | Enrich CNPJ no finalize do lote |
| `PNCP_BULK_LOCAL_ENRICH_HOMOLOG_MAX` | `0` | Enrich no loop de termos (off) |
| `PNCP_BULK_SEARCH_MAX_SECONDS` | `90` | Timeout por item no researcher |
| `PNCP_HYBRID_BULK_ENABLED` | `1` | PNCP ao vivo no lote se índice vazio |
| `PNCP_BULK_MAX_TERM_FALLBACKS` | `6` | Termos alternativos (early exit se tem preço) |

### Perfil velocidade máxima no lote (trade-off: mais itens vazios)

```bash
PNCP_HYBRID_BULK_ENABLED=0
PNCP_BULK_SEARCH_MAX_SECONDS=35
```

Itens sem índice local retornam vazio em segundos; rebuscar manualmente depois.

---

## 4. Deploy na VPS (DESKTOP)

### Pré-requisitos

- Repo em `~/docmaster-core`
- Volume PNCP preservado (`docker-compose.pncp.override.yml` com volume external)
- Backend fala com researcher pela rede `docmaster_net` (`pncp_researcher_service:8012`)

### Atualizar código

```bash
cd ~/docmaster-core
git pull
git rev-parse --short HEAD   # esperado: c83af16c ou posterior
```

### Recriar container com flags corretas

**Importante:** variáveis **exportadas no shell** (`env | grep PNCP_BULK`) sobrescrevem os defaults `:-2` / `:-0` do compose. Sempre `unset` antes do recreate.

```bash
cd ~/docmaster-core

unset PNCP_BULK_LOCAL_ENRICH_HOMOLOG_MAX PNCP_BULK_ENRICH_HOMOLOG_MAX

PNCP_NO_HOST_PORT=1 \
PNCP_BUILD_CONTEXT=docmaster-core \
PNCP_BULK_ENRICH_HOMOLOG_MAX=2 \
PNCP_BULK_LOCAL_ENRICH_HOMOLOG_MAX=0 \
./scripts/ensure-pncp-researcher.sh --recreate
```

`PNCP_NO_HOST_PORT=1` — obrigatório se Docker Desktop/WSL retornar:

```text
ports are not available: exposing port TCP 127.0.0.1:8012
```

Cria/usa `docker-compose.pncp.noports.yml`. O site continua funcionando via rede Docker interna.

### Hotfix só de código (sem mudar env)

```bash
cd ~/docmaster-core
./scripts/deploy-pncp-researcher-code.sh
```

Não atualiza variáveis de ambiente — só `service.py`, `config.py`, etc.

### Frontend (mudança autostart nacional único)

```bash
cd ~/docmaster-core/frontend-vue
npm run build
# reiniciar serviço que serve o front (nginx / compose frontend-vue)
```

### Perfil velocidade (opcional, no recreate)

```bash
unset PNCP_BULK_LOCAL_ENRICH_HOMOLOG_MAX PNCP_BULK_ENRICH_HOMOLOG_MAX

PNCP_NO_HOST_PORT=1 \
PNCP_BUILD_CONTEXT=docmaster-core \
PNCP_BULK_ENRICH_HOMOLOG_MAX=2 \
PNCP_BULK_LOCAL_ENRICH_HOMOLOG_MAX=0 \
PNCP_HYBRID_BULK_ENABLED=0 \
PNCP_BULK_SEARCH_MAX_SECONDS=35 \
./scripts/ensure-pncp-researcher.sh --recreate
```

---

## 5. Verificar versão no container

### Repo

```bash
cd ~/docmaster-core && git rev-parse --short HEAD
```

### Código dentro do container

```bash
# Versão nova: zero referências a bulk_intelligent no service.py
docker exec pncp_researcher_service grep -c bulk_intelligent \
  /app/pncp_researcher_service/app/service.py
# esperado: 0

# Fix enrich cap (jul/2026)
docker exec pncp_researcher_service grep -A2 '_bulk_recall_enrich_cap' \
  /app/pncp_researcher_service/app/service.py | head -5
# deve mencionar "só PNCP_BULK_ENRICH"
```

### Flags ativas

```bash
docker exec pncp_researcher_service env | grep -E \
  'BULK_ENRICH|BULK_LOCAL|HYBRID_BULK|BULK_USE_INTELLIGENT|SEARCH_TIER_FLEX|SEARCH_ANCHOR' | sort
```

Esperado (perfil atual):

```text
PNCP_BULK_ENRICH_HOMOLOG_MAX=2
PNCP_BULK_LOCAL_ENRICH_HOMOLOG_MAX=0
PNCP_BULK_USE_INTELLIGENT_PIPELINE=0
```

Se ainda mostrar `6` / `3`: container não foi recriado ou shell exporta valores antigos.

### Health

```bash
docker exec pncp_researcher_service python -c \
  "import urllib.request; print(urllib.request.urlopen(
    'http://127.0.0.1:8012/api/pncp-research/health', timeout=5).read().decode())"
```

Campos úteis: `db_bytes`, `ingest.worker_started`, `ia.rerank_bulk_enabled` (deve ser `false`).

---

## 6. Lote “travado” — diagnóstico

### Não é travamento real

O front processa **1 item por vez** (`BULK_CONCURRENCY=1`). Enquanto um item difícil roda, o contador fica parado em «item N de 696».

### Identificar o item lento

Quando aparecer «item 12 de 696», ver a **12ª linha** em «Itens da cotação» — anotar a descrição.

### Itens que costumam demorar

- Descrição longa colada do edital
- Termo genérico sem match no índice local (6 GB+ SQLite)
- Produto raro → dispara **híbrido PNCP ao vivo**

### Testar um termo isolado (no container)

```bash
docker exec pncp_researcher_service python -c "
import asyncio, json, time
from pncp_researcher_service.app.schemas import MarketSearchRequest
from pncp_researcher_service.app.service import market_search_intelligent

async def main():
    termo = 'COLE AQUI A DESCRICAO DO ITEM LENTO'
    t0 = time.time()
    p = MarketSearchRequest(termo_busca=termo, busca_lote=True, max_paginas=6, tamanho_pagina=200)
    out = await market_search_intelligent(p)
    funil = (out.get('stats') or {}).get('funil_busca') or {}
    print('elapsed_s:', round(time.time()-t0, 1))
    print('modo:', funil.get('modo_resposta'))
    print('local_com_preco:', funil.get('local_com_preco'))
    print('hybrid:', (out.get('stats') or {}).get('hybrid_fallback_used'))
    print('timeout:', (out.get('stats') or {}).get('busca_lote_timeout'))
    print('top3:', funil.get('top3_final'))
asyncio.run(main())
"
```

Se `hybrid: True` ou `elapsed_s` ~90 → item sem índice; considerar `PNCP_HYBRID_BULK_ENABLED=0`.

### Cancelar e relançar

Itens já processados ficam salvos na sessão. Após deploy de performance, pode **recarregar a página** e deixar o autostart continuar nos incompletos.

---

## 7. Armadilhas de deploy

| Armadilha | Sintoma | Solução |
|-----------|---------|---------|
| `git pull` sem `--recreate` | Compose novo, env antiga (`6`/`3`) | Recriar container |
| `env \| grep PNCP_BULK` com valores | Compose ignora `:-default` | `unset` antes do recreate |
| `deploy-pncp-researcher-code.sh` só | Código novo, flags velhas | Recreate para env |
| Porta 8012 WSL | `expose returned status 500` | `PNCP_NO_HOST_PORT=1` |
| `docker compose up` sem rebuild | Imagem antiga após recreate | `PNCP_BUILD=1` ou hotfix script |
| Front sem build | Dupla chamada UF+BR no lote | `npm run build` no frontend-vue |

---

## 8. Rollback

### Rollback total (qualidade conhecida 26/06 manhã)

```bash
cd ~/docmaster-core
git switch --detach 94711975
PNCP_NO_HOST_PORT=1 PNCP_BUILD_CONTEXT=docmaster-core \
  ./scripts/ensure-pncp-researcher.sh --recreate
```

Ver detalhes: [PNCP-BUSCA-INTELIGENTE-REGRESSAO-UI-VS-BACKEND.md](./PNCP-BUSCA-INTELIGENTE-REGRESSAO-UI-VS-BACKEND.md).

### Rollback só de performance (manter qualidade `e0427a0b+`)

No recreate, restaurar:

```bash
PNCP_BULK_ENRICH_HOMOLOG_MAX=3
PNCP_BULK_LOCAL_ENRICH_HOMOLOG_MAX=6
PNCP_HYBRID_BULK_ENABLED=1
PNCP_BULK_SEARCH_MAX_SECONDS=90
```

E reverter `BuscaInteligenteCotacoes.vue` (autostart UF + fallback nacional).

---

## 9. Arquivos centrais

| Arquivo | Papel |
|---------|--------|
| `pncp_researcher_service/app/service.py` | `market_search_intelligent`, lote, hybrid, enrich cap |
| `pncp_researcher_service/app/local_index.py` | FTS, tiers, `local_item_search` |
| `pncp_researcher_service/app/product_spec_match.py` | Dose, mg/ml, volume |
| `pncp_researcher_service/app/config.py` | Defaults env |
| `docker-compose.pncp.yml` | Flags produção |
| `frontend-vue/src/views/BuscaInteligenteCotacoes.vue` | Autostart, timeout 185s, payload lote |
| `scripts/ensure-pncp-researcher.sh` | Deploy / recreate |
| `scripts/deploy-pncp-researcher-code.sh` | Hotfix código |
| `scripts/lib/pncp-compose-args.sh` | `PNCP_NO_HOST_PORT`, noports |

---

## 10. Próximos passos (backlog)

1. `tests/test_search_regression.py` — Penrose + Acebrofilina no CI
2. Reduzir `BULK_SEARCH_TIMEOUT_MS` no front para ~40s alinhado ao backend
3. `maxAttempts: 1` no lote (evitar retry duplo)
4. Gate de deploy: `grep -c bulk_intelligent` = 0 + testes regressão
5. Documentar item lento no UI (mostrar descrição truncada durante autostart)

---

## Referências

- [PNCP-BUSCA-INTELIGENTE-REGRESSAO-UI-VS-BACKEND.md](./PNCP-BUSCA-INTELIGENTE-REGRESSAO-UI-VS-BACKEND.md)
- [PNCP-PARIDADE-LOTE-STATUS-IMPLEMENTADO.md](./PNCP-PARIDADE-LOTE-STATUS-IMPLEMENTADO.md)
- [PNCP-BUSCA-INTELIGENTE-QUALIDADE.md](./PNCP-BUSCA-INTELIGENTE-QUALIDADE.md)
- [../deploy/PNCP-RESEARCHER-24-7.md](../deploy/PNCP-RESEARCHER-24-7.md)
- [../deploy/PNCP-COMANDOS-OPERACAO.txt](../deploy/PNCP-COMANDOS-OPERACAO.txt)

---

*Última atualização: 2026-07-06 — perfil operacional pós `c83af16c`; baseline qualidade `94711975`; performance lote documentada.*
