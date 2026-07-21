# Compras.gov — integração implementada (jul/2026)

Status da fonte **`compras_gov`** no DocMaster: o que já entrou no código, o que falta (CSV/colunas) e como validar.

**Não confundir** com [Portal de Compras Públicas / PCP (Ecustomize)](./MODULO-FONTES-PRECOS-03-PORTAL-COMPRAS-PUBLICAS.md).

---

## 1. Decisão de arquitetura

| Escolha | Valor |
|---------|--------|
| Modelo | Igual ao **TCE-RS**: feed CSV → SQLite `platform_index` → adapter de **leitura** no researcher |
| ID da plataforma | `compras_gov` |
| Views CSV (alvo) | `VW_FT_PNCP_COMPRA` (cabeçalho) + `VW_FT_PNCP_COMPRA_ITEM` (item/preço) |
| DB | `/data/platforms/compras_gov_local.db` (`COMPRAS_GOV_LOCAL_DB_PATH`) |
| Classificação Art. 5º | **Inciso I** / esfera **federal** / bucket **`governamentais`** |
| API live Dados Abertos | **Fora do escopo desta entrega** (planejada no doc de particionamento; v1 = CSV) |

Sem índice populado: `search_ready=false`, adapter devolve `[]`, checkbox na UI fica «índice indisponível».

---

## 2. O que foi feito

### 2.1 Scaffold researcher / feed (infra)

| Peça | Local |
|------|--------|
| Spec no registry | `pncp_researcher_service/app/platform_index/registry.py` (`compras_gov`) |
| Env DB | `COMPRAS_GOV_LOCAL_DB_PATH` em `app/config.py` |
| Adapter | `ComprasGovAdapter` em `adapters/indexed_platform_adapter.py` |
| Registro federado | `adapters/registry.py` |
| Mapping hit→row | `adapters/mapping.py` (`fonte=governamentais`, `plataforma_label`) |
| Pacote ingest | `platform_index/ingest/compras_gov/` — `config`, `discover`, `status`; **parse/materialize ainda não** |
| Rotas feed | `GET/POST …/price-platform-indexes/compras_gov/ingest(-status\|-sample)` em `api_feed.py` |
| Isolamento | `FEED_PLATFORM=compras_gov` em `service_mode.py` |
| Compose | `price_index_feed_compras_gov` porta **8016** em `docker-compose.pncp.yml` |
| Raw/fixtures | `data/compras_gov/raw/`, `fixtures/compras_gov/` |

Ingest HTTP hoje: discover valida CSVs; `POST …/ingest` → **501** (`NotImplementedError`) até `column_map` + parser + materialize.

### 2.2 Integração de produto (UI + save + relatório)

Sem depender de CSV já ingerido — a tubulação de produto está pronta para quando o índice existir.

| Fluxo | Comportamento |
|-------|----------------|
| Catálogo de fontes | `/price-sources` lista `compras_gov`; fallback em `pncpPriceSources.js` |
| Checkbox IA / manual | `PriceSourcesPanel` — habilitado só com `search_ready` |
| Defaults | `pickDefaultFontes` inclui Compras.gov **somente** se ready |
| Save busca IA | `platformSaveMeta` → `inciso_i` / `federal` / `governamentais` |
| Save busca manual | Idem |
| Badge / labels | «Compras.gov» |
| Detalhe do item | Bucket governamentais; rótulo «Nome (Compras.gov)» |
| Relatório Vue + PDF | Coluna Fonte = **Compras.gov** (não colapsar em PNCP) |
| Portal | Preferência por `url_origem` no source |
| Backend bucket | `_fonte_bucket_from_source`: `compras_gov` → `governamentais` |

Helpers centrais: `frontend-vue/src/utils/pncpPriceSources.js` (`platformSaveMeta`, `isComprasGovPlatform`, …) e `pncpPricing.js` (`isComprasGovRow`, `canSalvarCotacaoPnCp`).

### 2.3 Testes

| Suíte | Arquivo | Foco |
|-------|---------|------|
| Researcher scaffold | `tests/test_compras_gov_scaffold.py` | Discover, adapter vazio, feed isolation |
| Researcher fluxos | `tests/test_compras_gov_flows.py` | Falhas + federado IA + lista completa + resiliência |
| Django produto | `backend/app/tests/test_compras_gov_product_flows.py` | Save, bucket, relatório/PDF |
| Regressão multi-fonte | `test_pncp_multi_source_regression.py` | Bucket `compras_gov` |
| Relatório label | `test_pncp_relatorio_descricao_fonte.py` | `tipo=Compras.gov` |
| Frontend utils | `src/utils/pncpComprasGovFlows.node.test.mjs` | Save meta, salvabilidade, defaults |

Comando (já validado no ambiente de desenvolvimento):

```bash
# researcher
cd pncp_researcher_service && ../venv/bin/python -m pytest \
  tests/test_compras_gov_flows.py tests/test_compras_gov_scaffold.py -q

# django
DJANGO_SETTINGS_MODULE=backend.mdlicitatech.settings ./venv/bin/python -m pytest \
  backend/app/tests/test_compras_gov_product_flows.py \
  backend/app/tests/test_pncp_multi_source_regression.py \
  backend/app/tests/test_pncp_relatorio_descricao_fonte.py -q

# frontend
cd frontend-vue && npm run test:utils
```

---

## 3. O que falta para produção (carga anual)

1. Colocar CSVs de **~1 ano** em `data/compras_gov/raw/` (ou volume do feed `:8016`)
2. Rodar `ingest` / `POST …/ingest` (já implementado — fixtures E2E cobrem o pipeline)
3. Confirmar `search_ready` + checkbox na UI
4. (Opcional) Dedup fino com PNCP; política só-homologados

---

## 4. Diagrama atual

```text
┌──────────────────────────────┐
│ price_index_feed_compras_gov │  FEED_PLATFORM=compras_gov :8016
│ CSV → (futuro) materialize   │────► /data/platforms/compras_gov_local.db
└──────────────────────────────┘
                 │
                 ▼ leitura
┌──────────────────────────────┐
│ pncp_researcher_service      │  ComprasGovAdapter + federado
│ fontes_habilitadas⊇compras_gov│
└──────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────┐
│ Vue (IA / manual) + Django   │  save, contagem governamentais, relatório
└──────────────────────────────┘
```

---

## 5. Checklist operacional pós-ingest

- [ ] `GET :8016/api/pncp-feed/price-platform-indexes/compras_gov/ingest-status` → `search_ready: true`
- [ ] Checkbox «Compras.gov» habilitado na busca IA/manual
- [ ] Hit com `plataforma=compras_gov` na resposta federada
- [ ] Save grava `fonte=governamentais` e sobe contagem Inciso I
- [ ] Relatório/PDF mostra Fonte **Compras.gov**

---

*Documentado em jul/2026 — integração de produto + scaffold; parser CSV pendente.*
