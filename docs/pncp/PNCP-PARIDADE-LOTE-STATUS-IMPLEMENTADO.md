# PNCP — paridade IA lote ↔ item isolado: o que foi implementado

Registro do trabalho **aplicado no código** (jun/2026) para corrigir o sintoma descrito nas notas operacionais: **mesmo item → item isolado até 3 cotações; cotação inteira (autostart/lote) 0 ou 1, lento**.

Documentos relacionados:

| Documento | Papel |
|-----------|--------|
| [`PNCP-NOTAS-PENDENCIAS.md`](PNCP-NOTAS-PENDENCIAS.md) | Sintomas reportados em campo (§ homologado; § **IA item 3 vs lote 0**; § regressão autostart) |
| [`PNCP-ANALISE-CODIGO-IA-ITEM-VS-LOTE.md`](PNCP-ANALISE-CODIGO-IA-ITEM-VS-LOTE.md) | Análise linha a linha — **causa raiz** (early return, cap SQL, break termos, híbrido) |
| [`PNCP-PLANO-PARIDADE-BUSCA.md`](PNCP-PLANO-PARIDADE-BUSCA.md) | Plano estratégico (Fase B = mesmo motor) |
| [`PNCP-IMPLEMENTACAO-PARIDADE-LOTE.md`](PNCP-IMPLEMENTACAO-PARIDADE-LOTE.md) | Runbook original com checkpoints (referência; defaults foram adiantados para `1`) |

---

## Sintoma alvo (das notas)

- **Item isolado** (`/busca-inteligente?itemId=`): até **3** cotações boas (ex.: álcool gel 70% 500 ml com termos curtos).
- **Cotação inteira** (`?autostart=1`, `busca_lote: true`): **0** ou **1** cotação, **muito lento**.
- **Não confundir** com estimado vs homologado — tema separado (§ preço homologado em `PNCP-NOTAS-PENDENCIAS.md`).

**Caso de campo (pós-deploy inicial):** descrição longa de edital para álcool gel; lote retornava só *«Lote 1 - ALCOOL EM GEL 500 ML…»*; pesquisa individual com termos focados (`ÁLCOOL GEL 70% EMBALAGEM DE 500ML`, etc.) trazia vários preços.

---

## Causas confirmadas no código (mapa da análise)

| # | Causa (análise §9) | Efeito |
|---|-------------------|--------|
| 1 | Early return `_finalize_busca_lote_top3_response` | Pipeline de scoring/rerank do `?itemId=` **não rodava** no lote |
| 2 | Cap SQL ~200–240 no lote vs ~100k no isolado | Candidatos homologados **fora** do top FTS |
| 3 | Break `priced_n >= 1` no legado | Parava variantes de termo cedo demais |
| 4 | Híbrido só se `local_priced == 0` (legado) | Sem PNCP ao vivo quando índice tinha 1 preço irrelevante |
| 5 | Edital longo como **1º termo** de busca | Match fraco + N× SQL por item |
| 6 | Frontend `max_paginas: 3`, timeout 95s | Híbrido limitado; timeouts em item pesado |

---

## Implementação — onda 1 (pipeline inteligente no lote)

**Objetivo:** lote usar o **mesmo motor** pós-índice que `busca_lote: false`, com rollback por env.

### Backend (`pncp_researcher_service`)

| Mudança | Arquivo |
|---------|---------|
| Flag `PNCP_BULK_USE_INTELLIGENT_PIPELINE` (default **`True`**) | `app/config.py` |
| Gate: `if bulk_legacy:` → `_finalize_busca_lote_top3_response`; senão → scoring completo | `app/service.py` |
| Ramo intelligent: filtro fornecedor no índice, híbrido se `local_priced < 8`, sem break `priced_n >= 1` | `app/service.py` |
| `funil["modo_resposta"] = "bulk_intelligent_top3"` | `app/service.py` |
| `PNCP_BULK_INTELLIGENT_SQL_LIMIT` (2000) | `app/config.py` |
| Timeout API lote ≥ 120s quando pipeline ON | `app/api.py` |
| Testes flag off/on + legado | `tests/test_bulk_search_lote.py`, `tests/test_bulk_search_performance.py` |

### Infra / frontend

| Mudança | Arquivo |
|---------|---------|
| Envs no compose: flag `1`, timeout 120s, SQL limit 2000 | `docker-compose.pncp.yml` |
| Timeout bulk 125s | `frontend-vue/.../BuscaInteligenteCotacoes.vue` |

### Deploy DESKTOP (jun/2026)

- Erro `ports are not available` na **8012** → usar `docker-compose.pncp.noports.yml` (padrão WSL/Docker Desktop).
- Health via `docker exec` (não `curl localhost:8012` no host).
- Confirmado: `bulk_intelligent= True`, contentor `healthy`.

---

## Implementação — onda 2 (recall álcool gel / edital longo)

Após deploy onda 1: lote ainda com **1 preço** e **lento** no álcool gel — segunda rodada:

| Problema | Correção |
|----------|----------|
| Limite SQL efetivo **240** (`3×80` do payload bulk) mesmo com cap 2000 | Lote intelligent: `limit = max(200, PNCP_BULK_INTELLIGENT_SQL_LIMIT)` — **ignora** `max_paginas×tamanho` |
| 1ª query = edital inteiro | `_iter_search_term_fallbacks(..., prefer_anchor_first=True)` no lote; âncora antes do texto bruto se truncado ou >8 tokens |
| Muitas queries por item | `PNCP_BULK_INTELLIGENT_MAX_TERM_FALLBACKS` (default **6**) |
| `product_spec_*` rejeitando com edital longo | Usar `termo_efetivo` (âncora) quando `termo_truncado` |
| Híbrido fraco no frontend | Bulk: `max_paginas: 6`, `tamanho_pagina: 200` (antes 3×80) |
| Funil | Expõe `bulk_intelligent_sql_limit`, `termo_truncado`, `bulk_intelligent_max_term_fallbacks` |

**Testes novos:** `test_bulk_intelligent_uses_full_sql_limit_not_frontend_cap`, `test_search_term_fallbacks_long_description_prioriza_ancora`.

---

## Comportamento esperado após onda 2

| | Item isolado | Lote (intelligent ON) |
|---|--------------|------------------------|
| Motor pós-índice | Scoring + fallbacks + rerank local + top3 | **Igual** |
| SQL cap | até ~100k (payload) | **2000** fixo (não 240) |
| 1º termo (edital longo) | raw (usuário pode editar termo) | **âncora** (`alcool gel 70% 500ml…`) |
| Qwen rerank lote | — | **off** (default env) |
| Enrich top3 | até 16 | cap **3** |
| Rollback | — | `PNCP_BULK_USE_INTELLIGENT_PIPELINE=0` |

### Validar na UI (Network → `market-search/intelligent`)

```json
"funil_busca": {
  "bulk_intelligent_pipeline": true,
  "modo_resposta": "bulk_intelligent_top3",
  "bulk_intelligent_sql_limit": 2000,
  "termo_truncado": true,
  "top3_final": 3
}
```

Se `top3_final < 3` com faixa de preço ativa → checar `valor_base_referencia` + variação (filtro de faixa no scoring).

---

## Comandos de deploy (DESKTOP)

```bash
cd ~/docmaster-core
git pull
cp -n docker-compose.pncp.noports.yml.example docker-compose.pncp.noports.yml
docker compose -f docker-compose.pncp.yml -f docker-compose.pncp.noports.yml up -d --build --force-recreate pncp_researcher_service

# Health (dentro do contentor)
docker exec pncp_researcher_service python -c \
  "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8012/api/pncp-research/health', timeout=10).read().decode())"
```

Frontend: rebuild se produção servir bundle estático (timeout 125s + paginação bulk).

---

## O que ainda está aberto (notas / backlog)

| Item | Doc / status |
|------|----------------|
| Preço **homologado** vs estimado no índice/enrich researcher | `PNCP-NOTAS-PENDENCIAS.md` § estimado — **não implementado** (A–D) |
| Autostart **696 itens** — tempo total (serial + 2000 rows × até 6 termos) | Monitorar; caps existem; tuning futuro possível |
| Paridade **100%** se usuário digita termo curto no isolado vs edital longo no lote | Mitigado por âncora; edição manual de termo no bulk **não** existe |
| Multi-plataforma TCE/BNC/BLL | `PLANO-FONTES-PRECOS-MULTIPLAS-PLATAFORMAS.md` |
| Flag legado `PNCP_BULK_USE_INTELLIGENT_PIPELINE=0` | Mantida para rollback |

---

## Arquivos tocados (resumo git)

```
pncp_researcher_service/app/config.py
pncp_researcher_service/app/service.py
pncp_researcher_service/app/api.py
pncp_researcher_service/tests/test_bulk_search_lote.py
pncp_researcher_service/tests/test_bulk_search_performance.py
pncp_researcher_service/tests/test_search_recall_helpers.py
docker-compose.pncp.yml
frontend-vue/src/views/BuscaInteligenteCotacoes.vue
```

---

## Histórico

| Data | Evento |
|------|--------|
| 2026-06-22 | Análise código + notas pendências |
| 2026-06-22 | Onda 1: flag pipeline intelligent, testes, deploy DESKTOP (noports) |
| 2026-06-22 | Campo: álcool gel 1 vs 3 — diagnóstico cap SQL 240 + termo edital |
| 2026-06-22 | Onda 2: SQL 2000 fixo, âncora first, cap termos, frontend paginação |
