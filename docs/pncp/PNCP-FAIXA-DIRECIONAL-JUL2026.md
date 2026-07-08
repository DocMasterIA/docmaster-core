# PNCP — Faixa regional direcional (`cima` / `baixo` / `ambos`)

Documentação da correção de **jul/2026** para variação global com direção (especialmente **só para cima**), validada em produção.

Relacionado: [PNCP-PERFIL-OPERACIONAL-JUL2026.md](./PNCP-PERFIL-OPERACIONAL-JUL2026.md) (handoff completo).

---

## Problema reportado

| Cenário | Comportamento errado |
|---------|---------------------|
| Base R$ 19,16, **cima** 20% | Item com homologado R$ 17,59 no top3 |
| Base R$ 19, **cima** 50% | Item com preço R$ 17 (abaixo do base) |
| Direção **baixo** | Geralmente ok (catálogo alto já falhava na faixa antes do enrich) |

O preço exibido era o **homologado real** (correto na UI), mas o item **não deveria ter sido selecionado** com sentido `cima`.

---

## Causa raiz (três fatores)

### 1. Ordem enrich → faixa

Fluxo antigo em `service.py`:

```text
filtra faixa (preço catálogo) → enrich PNCP (preço homologado real) → exibe
```

Item passava com `valor_unitario` de catálogo (ex.: R$ 22 ≥ base R$ 19). O enrich PNCP (`merge_homologated_pricing_from_snap`) substituía por homologado R$ 17 **sem refiltrar**.

Introduzido quando o enrich passou a trazer preço vencedor (`b5a6f164`, mantido em `e0427a0b+`). No baseline `94711975` o enrich era só fornecedor/CNPJ — o bug não aparecia.

### 2. Gate de faixa usava catálogo em homologados

`item_matches_faixa_band` chamava `row_display_unit_price`, que prioriza homologado mas, na ausência dele, usa **catálogo/estimado** — inflando o preço no gate `cima`/`baixo`.

### 3. Frontend às vezes não enviava faixa ao backend

`faixaAtiva` dependia de `valor_min_referencia` / `valor_max_referencia` pré-calculados no contexto. Se min/max vinham `null`, o payload ia **sem** `valor_base`, `variacao` e `sentido` → backend tratava como sem faixa ou caía em `ambos` (banda ±50% inclui R$ 17 em base R$ 19).

---

## Solução implementada (commits)

| Commit | O quê |
|--------|-------|
| `b41e7a94` | Propagação explícita de `faixa_sentido` em pool lote, top3 manual, IA rerank |
| `26e33b3f` | `_filter_rows_in_faixa` **após** enrich (lote + busca manual) |
| `c3c1aa86` | Gate estrito + enrich pré-faixa + refiltro top3 lote + fix `faixaAtiva` no front |
| `ad4dced9` | Default UI variação global **0%** (antes 20%) em `CotacaoDetalhe.vue` |

**HEAD estável validado:** `c3c1aa86` ou posterior.

---

## Camadas da correção

### `pricing_display.py`

**`row_unit_price_for_faixa_gate(it, sentido)`**

- Com `cima` / `baixo` e `item_homologado=True` **sem** `valor_unitario_homologado` → retorna `0` (não usa catálogo/estimado).
- Com homologado presente → usa homologado.
- Com `ambos` → comportamento anterior (`row_display_unit_price` + recall estimado/homolog).

**`item_matches_faixa_band`** passou a usar o gate acima.

### `service.py`

| Função / trecho | Comportamento |
|-----------------|---------------|
| `_enrich_homolog_for_directional_faixa` | Enrich PNCP antes do gate quando sentido ≠ `ambos` |
| `_finalize_busca_lote_top3_response` | pre-enrich direcional → pool na faixa → enrich pool → **refiltro** → top3 → **refiltro top3** |
| `market_search_intelligent` (manual) | pre-enrich direcional nos itens → scoring → enrich top3 → **refiltro top3** |
| `_filter_rows_in_faixa` | Helper reutilizável pós-enrich |

Funil JSON útil para debug:

- `pre_enrich_direcional`
- `eliminados_faixa_pos_enrich`
- `variacao_sentido` / `faixa_min` / `faixa_max`

### Frontend

| Arquivo | Mudança |
|---------|---------|
| `BuscaInteligenteCotacoes.vue` | `faixaAtiva` = base > 0 **e** variação ≥ 0 (não só min/max no context); envia `variacao_sentido_referencia` quando ativa; sentido só da sessão global |
| `CotacaoDetalhe.vue` | Default exibição variação global **0%** (fallback ao carregar sessão sem valor salvo) |
| `pncpPricing.js` | `computeFaixaRegional` / `pnCpRowWithinFaixaRegional` (filtro client-side na grade) |

### Backend Django

`pncp_cotacao_api.py` — `_item_search_context_dict` envia `variacao_sentido_global` por item a partir dos filtros da sessão.

---

## Bandas de preço (referência)

Base **R$ 19**, variação **50%**:

| Sentido | Mín | Máx | R$ 17 passa? |
|---------|-----|-----|--------------|
| `cima` | 19,00 | 28,50 | **Não** |
| `baixo` | 9,50 | 19,00 | Sim |
| `ambos` | 9,50 | 28,50 | Sim |

---

## Testes automatizados

Arquivos:

- `pncp_researcher_service/tests/test_pricing_display.py`
  - `test_cima_rejeita_apos_enrich_homolog_abaixo_base`
  - `test_cima_rejeita_homologado_sem_preco_com_catalogo_na_faixa`
- `pncp_researcher_service/tests/test_pricing_faixa.py`
  - `test_filter_rows_in_faixa_pos_enrich_cima`
  - `test_bulk_recall_pool_respeita_sentido_cima`

```bash
cd pncp_researcher_service
PYTHONPATH=. python3 -m unittest tests.test_pricing_display -q
```

---

## Teste manual pós-deploy

1. Em **CotacaoDetalhe**: valor base do item (ex. R$ 19), variação global **50%**, direção **Para cima** → **Salvar** sessão.
2. Autostart ou busca inteligente no item.
3. Confirmar: nenhum resultado com preço homologado **< R$ 19**.
4. No funil da resposta: `variacao_sentido_referencia: "cima"`, `faixa_regional_min: 19`, `faixa_regional_max: 28.5`.

---

## Verificação no container

```bash
docker exec pncp_researcher_service grep -c 'row_unit_price_for_faixa_gate' \
  /app/pncp_researcher_service/app/pricing_display.py
# esperado: >= 2

docker exec pncp_researcher_service grep -c 'eliminados_faixa_pos_enrich' \
  /app/pncp_researcher_service/app/service.py
# esperado: >= 2

docker exec pncp_researcher_service grep -c 'pre_enrich_direcional' \
  /app/pncp_researcher_service/app/service.py
# esperado: >= 2
```

---

## Deploy mínimo (hotfix faixa)

```bash
cd ~/docmaster-core && git pull
./scripts/deploy-pncp-researcher-code.sh
cd frontend-vue && npm run build
# reiniciar serviço do front
```

Researcher + frontend são necessários. Backend Django só se `variacao_sentido_global` não estiver chegando nos itens (raro após `e0427a0b`).

---

*Última atualização: 2026-07-06 — validado em produção pelo operador.*
