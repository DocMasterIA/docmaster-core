# PNCP — Regressão busca inteligente (handoff)

Documento para retomar depois. Consolida investigação, **baseline confirmado**, janela da regressão e comandos de rollback na VPS.

> **Handoff operacional completo (jul/2026):** deploy VPS, performance do lote, flags enrich, faixa direcional → [PNCP-PERFIL-OPERACIONAL-JUL2026.md](./PNCP-PERFIL-OPERACIONAL-JUL2026.md)  
> **Faixa `cima`/`baixo` (validado):** [PNCP-FAIXA-DIRECIONAL-JUL2026.md](./PNCP-FAIXA-DIRECIONAL-JUL2026.md)

---

## Estado final (jul/2026 — validado em produção)

| Item | Status |
|------|--------|
| Qualidade busca (Penrose, Acebrofilina) | OK em `e0427a0b`+ |
| Performance autostart 696 itens | OK com flags `c83af16c` |
| Faixa direcional `cima` / `baixo` | OK em `c3c1aa86`+ |
| Variação global UI default 0% | OK em `ad4dced9`+ |
| **HEAD recomendado** | `c3c1aa86` ou posterior |

---

## Conclusão confirmada (jul/2026)

| Fato | Status |
|------|--------|
| Cotação feita em **26/06/2026 ~10:21** com resultados bons | **Evidência real** (ex.: DRENO PENROSE N.4, ACEBROFILINA 50 MG/5 ML) |
| Commit vigente nesse horário | **`94711975`** (2026-06-26 00:38 -0300) |
| Rollback para `94711975` na VPS | **Melhorou** — busca voltou a respeitar termo/dose |
| Rollback para `7b7caced` (27/jun) | **Sem diferença perceptível** — não é o baseline certo |
| Regressão introduzida | **Tarde de 26/06**, commits `ff74e122` → `3fe814c6` → `b5a6f164` |

**Baseline bom para operar/testar:** `94711975a10591bfdefc6ff11640bdf5b406c923`

**HEAD histórico da investigação:** `e5648bc9` (2026-07-03) — continha regressão em relação a `94711975`.

**Correção aplicada em main:** `e0427a0b` → `c83af16c` → `b41e7a94` → `26e33b3f` → `c3c1aa86` — ver [PNCP-PERFIL-OPERACIONAL-JUL2026.md](./PNCP-PERFIL-OPERACIONAL-JUL2026.md).

---

## Código vs flags (verificado no git)

Na manhã de 26/06 o que estava **ativo** era o **código** de `94711975`. As **flags** do `docker-compose.pncp.yml` dessa mesma revisão já tinham Qwen/rerank/qualidade — não é “só código antigo sem IA”.

### O que `94711975` já tinha (compose + defaults)

| Flag / env | Valor em `94711975` | Efeito |
|------------|---------------------|--------|
| `PNCP_SEARCH_QUALITY_FIRST` | `1` | Modo qualidade |
| `PNCP_IA_RERANK_ENABLED` | `1` | Rerank IA (Qwen) |
| `PNCP_IA_RERANK_PREFER_LOCAL` | `1` | Local antes de IA |
| `PNCP_LOCAL_RERANK_ENABLED` | `1` | Rerank local |
| `PNCP_SEARCH_TIER_FLEX_RATIO` | **`0.78`** | Flex mais rígido |
| `PNCP_SEARCH_ANCHOR_TIER_ENABLED` | **`0`** | Sem tier anchor extra |
| `PNCP_HYBRID_MIN_LOCAL_RESULTS` | **`8`** | Hybrid só com pool fraco |
| `PNCP_HYBRID_MAX_LIVE_PAGES` | **`6`** | Menos páginas PNCP ao vivo |
| `PNCP_IA_BASE_URL` | `qwen_llm_service:8015` | Qwen no compose |
| `PNCP_BULK_USE_INTELLIGENT_PIPELINE` | **ausente** | Código nem lê (ver abaixo) |

**Importante:** em `94711975` o `service.py` tem **zero** referências a `bulk_intelligent`. O pipeline bulk inteligente só existe a partir de **`ff74e122`**. Flags `PNCP_BULK_USE_INTELLIGENT_PIPELINE` no container **não fazem nada** com código `94711975`.

### Flags adicionadas **depois** de `94711975` (só compose)

| Commit | Hora | Flags novas / alteradas | Precisa código novo? |
|--------|------|-------------------------|----------------------|
| **`ff74e122`** | 15:06 | `PNCP_BULK_USE_INTELLIGENT_PIPELINE=1`, `PNCP_BULK_INTELLIGENT_SQL_LIMIT=2000`, `BULK_SEARCH_MAX_SECONDS` 90→120 | **Sim** (`ff74e122+`) |
| **`3fe814c6`** | 15:19 | `PNCP_BULK_INTELLIGENT_MAX_TERM_FALLBACKS=6` | **Sim** |
| **`b5a6f164`** | 16:44 | `SQL_LIMIT` 2000→**4000**, `MAX_TERM_FALLBACKS=8`, `FLEX_RATIO` **0.78→0.65**, `ANCHOR_TIER` **0→1**, `HYBRID_MIN` **8→4**, `MAX_LIVE_PAGES` **6→10**, `BULK_SEARCH_MAX_SECONDS` 180 | Lidas pelo `local_index`/`service` antigos — **aumentam recall** |

### Onde piorou (limite)

```text
CÓDIGO (principal)
  94711975 ──bom──► ff74e122 ──piora──► 3fe814c6 ──piora──► b5a6f164 ──► … ──► HEAD
  (10:21 OK)        15:06 bulk         15:19           16:44 spec+index

FLAGS (reforço da piora a partir de b5a6f164)
  94711975: FLEX=0.78, ANCHOR=0, HYBRID 8/6
  b5a6f164/HEAD: FLEX=0.65, ANCHOR=1, HYBRID 4/10  ← mais ruído (lacre, flex, anchor)
```

| Zona | Commit | Expectativa |
|------|--------|-------------|
| **Melhor confirmado** | `94711975` | Penrose, Acebrofilina OK |
| **1ª regressão de código** | `ff74e122` | Bulk intelligent + mudanças em `service.py` |
| **2ª regressão de código** | `b5a6f164` | `product_spec_match.py` (+68 linhas), `local_index.py`, mais `service.py` |
| **Flags que provavelmente pioram** | compose `b5a6f164`+ | FLEX 0.65, ANCHOR=1, hybrid mais agressivo |

### “Sweet spot” recomendado para testar depois

1. **Código:** `94711975` (confirmado bom).
2. **Flags:** usar o **`docker-compose.pncp.yml` de `94711975`** no recreate do container (não herdar compose de `HEAD` com FLEX=0.65 / ANCHOR=1).
3. **Se precisar bulk intelligent no lote:** subir **só** até `ff74e122` ou `3fe814c6` (código + flags de `ff74e122`), **sem** as flags permissivas de `b5a6f164`.
4. **Bisect:** `git bisect start` / `bad HEAD` / `good 94711975` — testar Penrose + Acebrofilina a cada passo.

### Ver flags reais no container (VPS)

```bash
docker exec pncp_researcher_service printenv | grep -E \
  'PNCP_SEARCH_|PNCP_BULK_|PNCP_IA_|PNCP_HYBRID_|PNCP_LOCAL_RERANK' | sort
```

Comparar com `git show 94711975:docker-compose.pncp.yml | grep PNCP_SEARCH`.

---

## Evidência de cotação (26/06/2026)

Itens que **funcionavam** na cotação da manhã de 26/06:

| Termo buscado | Resultado esperado (salvo na cotação) |
|---------------|----------------------------------------|
| `DRENO DE PEN ROSE ESTÉRIL N. 4` | DRENO DE PENROSE, látex, tubular, **Número 4** |
| `ACEBROFILINA 50 MG/5 ML XAROPE C/120ML` | Dose/volume respeitados |

Depois dos commits da tarde de 26/06 (e posteriores), os mesmos termos passaram a trazer ruído (ex.: lacre com «dreno de 5 mm», doses erradas).

---

## Janela da regressão (git)

```text
94711975  2026-06-26 00:38  ← ÚLTIMO BOM (antes das 10:21)
    │
    ├── ff74e122  2026-06-26 15:06  service.py, config.py, BuscaInteligenteCotacoes.vue, bulk intelligent
    ├── 3fe814c6  2026-06-26 15:19  service.py, config.py, BuscaInteligenteCotacoes.vue
    └── b5a6f164  2026-06-26 16:44  service.py, local_index.py, product_spec_match.py, supplier_resolver.py
    │
    … commits 27/jun–03/jul …
    │
e5648bc9  2026-07-03  HEAD main (fix indentação local_index + sanitize fornecedor)
```

Arquivos que mudaram de `94711975` até `HEAD` (busca):

| Arquivo | Impacto provável |
|---------|------------------|
| `pncp_researcher_service/app/service.py` | Scoring, bulk intelligent, top3 |
| `pncp_researcher_service/app/local_index.py` | FTS, tiers, filtros no índice |
| `pncp_researcher_service/app/product_spec_match.py` | Dose, mg/ml, volume (Acebrofilina, etc.) |
| `frontend-vue/src/views/BuscaInteligenteCotacoes.vue` | Payload, UF, lote |

**Próximo passo técnico:** `git bisect` entre `94711975` e `b5a6f164` (ou `HEAD`) com teste fixo Penrose + Acebrofilina.

---

## Comandos VPS — voltar para `94711975` (versão boa)

```bash
cd ~/docmaster-core

git stash push -u -m "backup antes rollback 94711975"   # opcional
git fetch origin
git switch --detach 94711975

git rev-parse HEAD
# 94711975a10591bfdefc6ff11640bdf5b406c923
```

### PNCP researcher

```bash
cd ~
PNCP_BUILD=1 PNCP_BUILD_CONTEXT=docmaster-core \
  ~/docmaster-core/scripts/ensure-pncp-researcher.sh
```

Se falhar build/porta 8012, hotfix:

```bash
cd ~/docmaster-core
for f in pncp_researcher_service/app/*.py; do
  docker cp "$f" pncp_researcher_service:/app/pncp_researcher_service/app/$(basename "$f")
done
docker restart pncp_researcher_service
```

### Backend + frontend (UI usa estes serviços)

```bash
cd ~/docmaster-core
docker compose build backend frontend-vue
docker compose up -d --force-recreate backend frontend-vue
```

### Confirmar versão no container

```bash
cd ~/docmaster-core
git rev-parse --short HEAD   # 94711975

docker exec pncp_researcher_service python -c \
  "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8012/api/pncp-research/health', timeout=5); print('health OK')"
```

### Teste rápido Penrose (terminal)

```bash
docker exec pncp_researcher_service python -c "
import asyncio
from pncp_researcher_service.app.schemas import MarketSearchRequest
from pncp_researcher_service.app.service import market_search_intelligent

async def main():
    body = MarketSearchRequest(
        termo_busca='DRENO DE PEN ROSE ESTÉRIL N. 4',
        somente_homologados=True,
        busca_lote=False,
        max_paginas=15,
        tamanho_pagina=50,
    )
    r = await market_search_intelligent(body)
    for i, it in enumerate((r.get('itens') or [])[:3], 1):
        print(i, it.get('score_aprovacao'), (it.get('descricao_item') or '')[:120])
asyncio.run(main())
"
```

---

## Comandos VPS — voltar para versão mais recente (`main`)

```bash
cd ~/docmaster-core
git switch main
git pull origin main
git rev-parse --short HEAD   # e5648bc9 ou mais novo
```

Redeploy (mesma sequência):

```bash
cd ~
PNCP_BUILD=1 PNCP_BUILD_CONTEXT=docmaster-core \
  ~/docmaster-core/scripts/ensure-pncp-researcher.sh

cd ~/docmaster-core
docker compose build backend frontend-vue
docker compose up -d --force-recreate backend frontend-vue
```

Ou hotfix PNCP só com `docker cp` + `docker restart` (ver acima).

---

## Tabela de commits (referência rápida)

| Commit | Data | Uso |
|--------|------|-----|
| **`94711975`** | 2026-06-26 00:38 | **Baseline bom** — cotação 26/06 10:21 |
| `ff74e122` | 2026-06-26 15:06 | 1º suspeito pós-baseline (bulk + service + Vue) |
| `3fe814c6` | 2026-06-26 15:19 | 2º suspeito |
| `b5a6f164` | 2026-06-26 16:44 | 3º suspeito (`product_spec_match`, `local_index`) |
| `7b7caced` | 2026-06-27 | **Não resolve** regressão reportada |
| `959e188e` | 2026-06-30 | **Evitar** — `IndentationError` em `local_index.py` |
| **`e5648bc9`** | 2026-07-03 | **HEAD main** atual |

---

## O que foi descartado na investigação

1. **Paridade bulk vs individual** — pipeline bulk OK; não explica Penrose ruim vs bom por versão.
2. **Só problema de frontend/UF** — rollback de **código backend** para `94711975` melhorou na prática.
3. **`7b7caced` como baseline** — testado na VPS; sem melhora vs HEAD para os casos citados.
4. **Filtros verbais grandes** (`_HEAD_SYNONYMS`, dreno/lacre em `product_category_match`) — rejeitados; não deployados.

### Causa do lacre com «dreno de 5 mm» (falso positivo FTS)

A palavra literal `dreno` na descrição do lacre casa no FTS. Isso existe desde junho; `product_category_match` (só fio→luva) **nunca** barrou esse caso. A melhora em `94711975` vem de **outras mudanças** (scoring/spec/index), não de lista verbal de categoria.

---

## Plano de correção definitiva (quando retomar)

1. **`git bisect`** `94711975`..`b5a6f164` com teste automatizado:
   - `DRENO DE PEN ROSE ESTÉRIL N. 4` → top1 contém «penrose» e «4»
   - `ACEBROFILINA 50 MG/5 ML XAROPE C/120ML` → dose/volume corretos no top3
2. Reverter ou ajustar o commit culpado em `service.py` / `local_index.py` / `product_spec_match.py` (e Vue se necessário).
3. Adicionar `tests/test_search_regression.py` + gate no deploy.
4. Opcional front: busca nacional por padrão, UF só manual (`BuscaInteligenteCotacoes.vue`).

**Não fazer sem decisão:** listas verbais extensas em `product_category_match.py`.

---

## Arquivos centrais

| Arquivo | Papel |
|---------|--------|
| `pncp_researcher_service/app/service.py` | `market_search_intelligent`, scoring, top3, bulk |
| `pncp_researcher_service/app/local_index.py` | FTS, tiers, `local_item_search` |
| `pncp_researcher_service/app/product_spec_match.py` | Dose, mg/ml, volume |
| `pncp_researcher_service/app/product_category_match.py` | Só fio→luva (77 linhas) |
| `frontend-vue/src/views/BuscaInteligenteCotacoes.vue` | Payload, UF, faixa, lote |
| `scripts/ensure-pncp-researcher.sh` | Deploy PNCP (`PNCP_BUILD_CONTEXT=docmaster-core`) |

---

## Referências

- [PNCP-PARIDADE-LOTE-STATUS-IMPLEMENTADO.md](./PNCP-PARIDADE-LOTE-STATUS-IMPLEMENTADO.md)
- [PNCP-BUSCA-INTELIGENTE-QUALIDADE.md](./PNCP-BUSCA-INTELIGENTE-QUALIDADE.md)
- [PNCP-NOTAS-PENDENCIAS.md](./PNCP-NOTAS-PENDENCIAS.md)

---

*Última atualização: 2026-07-06 — baseline `94711975`; mapa código vs flags; limite de regressão `ff74e122`/`b5a6f164`.*
