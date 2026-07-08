# Multi-fonte — como separar por partes (sem preço)

Guia de **particionamento**: o que conectar, em que ordem, com quais fronteiras. Complementa [MODULO-FONTES-PRECOS-00-PREPARACAO.md](./MODULO-FONTES-PRECOS-00-PREPARACAO.md).

---

## 1. Três camadas (sempre nesta ordem)

Separe mentalmente — e no backlog — em **três camadas independentes**:

```text
┌─────────────────────────────────────────────────────────────┐
│ CAMADA C — Produto (Vue + Django cotação)                   │
│   escolher fontes, salvar, PDF Art. 5º, autostart           │
└───────────────────────────┬─────────────────────────────────┘
                            │ JSON canônico (MarketPriceHit)
┌───────────────────────────▼─────────────────────────────────┐
│ CAMADA B — Orquestração (núcleo federado)                  │
│   merge, dedup, faixa, scoring, timeout, feature flags      │
└───────────────────────────┬─────────────────────────────────┘
                            │ FederatedSearchQuery
┌───────────────────────────▼─────────────────────────────────┐
│ CAMADA A — Conectores (1 módulo = 1 plataforma ou 1 UF TCE)  │
│   só fala com API/CSV da origem → devolve hits normalizados  │
└─────────────────────────────────────────────────────────────┘
```

**Regra:** conector **nunca** grava no Django nem conhece PDF. Orquestrador **nunca** conhece SOAP do BLL. Produto **nunca** conhece CKAN do TCE.

---

## 2. Parte 0 — Núcleo (fazer antes de qualquer plataforma nova)

Uma entrega fechada, testável sozinha:

| Peça | O quê | Onde (sugestão) |
|------|-------|-----------------|
| **0.1 Contrato** | `MarketPriceHit`, `FederatedSearchQuery`, `PriceSourceAdapter` | `pncp_researcher_service/app/adapters/` (novo pacote) |
| **0.2 PNCP como adapter** | Refatorar `market_search_intelligent` para implementar a interface — **comportamento idêntico** | `adapters/pncp_adapter.py` |
| **0.3 Orquestrador** | `federated_search(query, sources[])` — gather paralelo, timeout por fonte | `adapters/federated.py` |
| **0.4 Dedup** | Mesma compra em duas fontes → 1 hit | `adapters/dedup.py` |
| **0.5 Endpoint experimental** | `POST /market-search/federated` + flag env | `api.py` |
| **0.6 Persistência mínima** | `source.plataforma = "pncp"` em saves novos (default retroativo) | Django `pncp_cotacao_api.py` |
| **0.7 UI mínima** | Checkbox «PNCP» (único, marcado) — prepara multi-select | `BuscaInteligenteCotacoes.vue` |

**Critério de pronto:** busca federada com `sources=["pncp"]` = igual à busca atual.

Nada de TCE/BLL até **0** estar verde.

---

## 3. Parte 1 — Por plataforma: o que «conectar» significa

Cada linha abaixo é **um pacote de trabalho** (pode virar epic/issue). Nem todos têm a mesma forma de conexão.

### 3.1 Compras.gov (Dados Abertos)

**O que conectar:** API REST `dadosabertos.compras.gov.br` — módulo **Pesquisa de Preço** (material/serviço).

**Não conectar:** painel web antigo (desatualizado desde jul/2025).

| Subparte | Entrega | Dependência |
|----------|---------|-------------|
| **1-CG-HTTP** | Client HTTP + paginação + parse JSON | — |
| **1-CG-NORM** | Mapear resposta → `MarketPriceHit` (`plataforma: compras_gov`) | 1-CG-HTTP |
| **1-CG-CAT** | Resolver termo livre → `codigoItemCatalogo` (catálogo SIASG) | catálogo local ou API catálogo Compras.gov |
| **1-CG-ADAPTER** | `ComprasGovAdapter.search()` | 1-CG-NORM + 1-CG-CAT |
| **1-CG-UI** | Fonte «Compras.gov» no multi-select | Parte 0 |

**Overlap PNCP:** tratar como **dedup** na Camada B, não duplicar lógica.

---

### 3.2 Portal de Compras Públicas (PCP)

**Detalhe técnico:** [MODULO-FONTES-PRECOS-03-PORTAL-COMPRAS-PUBLICAS.md](./MODULO-FONTES-PRECOS-03-PORTAL-COMPRAS-PUBLICAS.md).

**O que conectar:** API/WebService **de parceiro** (Ecustomize) — após credenciamento.

**Não conectar:** scraping do site; robô sem termo assinado.

| Subparte | Entrega | Dependência |
|----------|---------|-------------|
| **1-PCP-DIS** | Obter doc sandbox, credencial teste, escopo endpoints | comercial |
| **1-PCP-HTTP** | Client auth (API key / OAuth conforme doc) | 1-PCP-DIS |
| **1-PCP-NORM** | Hits → `MarketPriceHit`, inciso II, `url_origem` | 1-PCP-HTTP |
| **1-PCP-ADAPTER** | `PortalComprasPublicasAdapter` | 1-PCP-NORM |
| **1-PCP-VAULT** | Credencial por prefeitura (tenant) | Parte 0 + O3 vault |

**Inciso:** II (municipal/estadual marketplace).

---

### 3.3 TCE/RS

**O que conectar:** portal CKAN + **arquivos CSV** LicitaCon (não «API de busca por produto»).

| Subparte | Entrega | Dependência |
|----------|---------|-------------|
| **1-TCE-DIS** | Confirmar URLs datasets, periodicidade, layout 14 CSVs | — |
| **1-TCE-ING** | Job: download ZIP → parse LICITACAO + ITEM + PROPOSTA → staging | 1-TCE-DIS |
| **1-TCE-IDX** | Índice FTS (SQLite separado ou schema `fonte=tce_rs`) | 1-TCE-ING |
| **1-TCE-CRON** | Refresh diário + log | 1-TCE-IDX |
| **1-TCE-ADAPTER** | `TceRsAdapter.search(termo, uf=RS)` sobre índice | 1-TCE-IDX |
| **1-TCE-UI** | Fonte «TCE-RS» | Parte 0 |

**Outro TCE (PR, SC):** copiar pipeline **1-TCE-*** com sufixo UF — validar layout antes.

---

### 3.4 BLL Compras

**Separar dois produtos diferentes** (não misturar no mesmo adapter):

| Produto BLL | O que conectar | Adapter |
|-------------|----------------|---------|
| **Banco de Preços** (pesquisa mercado) | ⚠️ API **não documentada** publicamente | `BllPrecosAdapter` — só após discovery |
| **Web Service promotor** (processos do órgão) | Manual SOAP/REST + chave promotor | `BllProcessoAdapter` |

| Subparte | Entrega | Dependência |
|----------|---------|-------------|
| **1-BLL-DIS** | Confirmar se existe API do Banco de Preços para terceiros | — |
| **1-BLL-WS** | Client WS: resultados homologados por processo | chave cliente |
| **1-BLL-NORM** | Proposta/classificação → `MarketPriceHit` | 1-BLL-WS |
| **1-BLL-ADAPTER** | Um ou dois adapters conforme discovery | acima |

**Overlap PNCP:** BLL envia ao PNCP — dedup agressivo.

---

### 3.5 BNC

**O que conectar:** indefinido até contrato — tratar como discovery isolado.

| Subparte | Entrega | Dependência |
|----------|---------|-------------|
| **1-BNC-DIS** | API oficial? sandbox? escopo preços vs processos | comercial |
| **1-BNC-*** | Só planejar após doc | 1-BNC-DIS |

Não colocar BNC no mesmo sprint que TCE ou PCP.

---

## 4. Parte 2 — Produto (depois de ≥1 conector além PNCP)

| Peça | O quê |
|------|-------|
| **2.1 Sessão** | `filtros.fontes_habilitadas: ["pncp", "tce_rs"]` |
| **2.2 Busca manual** | Enviar fontes no payload; exibir badge plataforma na grade |
| **2.3 Save** | `source.plataforma`, `url_origem`, inciso correto |
| **2.4 PDF** | Linha do relatório cita plataforma + link |
| **2.5 Contagem Art. 5º** | Buckets `governamentais` / `entesPublicos` por `plataforma` + inciso |

---

## 5. Parte 3 — Autostart multi-fonte (por último)

Só quando manual federado estiver estável.

| Peça | O quê |
|------|-------|
| **3.1 Política** | PNCP first; se `< 3` hits → fallback fontes da sessão |
| **3.2 Budget tempo** | Timeout total por item × N fontes |
| **3.3 Funil** | Métricas por plataforma (`hits`, `timeout`, `dedup_removed`) |
| **3.4 Paridade faixa** | Mesma faixa direcional em todos adapters |

---

## 6. Mapa de dependências (o que bloqueia o quê)

```text
Parte 0 (núcleo)
    ├── 1-CG-*     (Compras.gov)
    ├── 1-PCP-*    (Portal — bloqueado por 1-PCP-DIS)
    ├── 1-TCE-*    (TCE/RS — ingest antes de search)
    ├── 1-BLL-*    (bloqueado por 1-BLL-DIS)
    └── 1-BNC-*    (bloqueado por 1-BNC-DIS)

Qualquer 1-* concluído + Parte 0
    └── Parte 2 (produto)

Parte 2 estável + ≥2 fontes
    └── Parte 3 (autostart)
```

---

## 7. Como fatiar no backlog (épicos sugeridos)

| Epic | Contém | Pronto quando |
|------|--------|---------------|
| **E0** Núcleo federado | 0.1–0.7 | Paridade PNCP via federated |
| **E1** Compras.gov | 1-CG-* | Termo → hits Compras.gov na UI |
| **E2** TCE/RS | 1-TCE-* | Índice RS + busca na UI |
| **E3** Portal PCP | 1-PCP-* | Parceiro + hits PCP na UI |
| **E4** BLL | 1-BLL-* | Conforme discovery |
| **E5** BNC | 1-BNC-* | Conforme discovery |
| **E6** Produto cross | Parte 2 | Save/PDF/contagem multi-fonte |
| **E7** Autostart | Parte 3 | Lote 696 itens com fallback |

**Um epic = uma plataforma (ou núcleo).** Não misturar E1+E2 no mesmo sprint.

---

## 8. O que **não** misturar no mesmo pacote

| Mistura errada | Por quê |
|----------------|---------|
| TCE ingest + PCP API | Modelos de dados opostos (batch vs live) |
| BLL banco preços + BLL WS promotor | APIs e credenciais diferentes |
| Autostart + primeiro conector | Debug combinatório |
| Renomear `PncpCotacaoItem` + conector | Migração Django desnecessária no v1 |
| Scraping + API oficial | Risco legal; manter só oficial |

---

## 9. Ordem prática (ROI técnico)

```text
1. E0 — núcleo (PNCP vira adapter)
2. Escolher UM segundo epic conforme cliente:
      • RS / municípios RS     → E2 TCE/RS
      • municípios multi-UF    → E3 PCP (se parceiro ok)
      • complemento federal   → E1 Compras.gov (overlap PNCP)
3. E6 — produto (save/PDF)
4. E4/E5 — BLL/BNC só com doc
5. E7 — autostart
```

---

## 10. Checklist «o que conectar» por entrega

Antes de marcar um conector como feito:

- [ ] `PriceSourceAdapter` implementado
- [ ] `capabilities()` documenta limites (ex.: «só RS», «exige catálogo»)
- [ ] `health()` verifica API/índice
- [ ] Hits passam faixa + spec match na orquestração
- [ ] Dedup com PNCP testado (10 termos golden)
- [ ] `source.plataforma` persiste no save
- [ ] Inciso correto no bucket Art. 5º
- [ ] Teste manual: termo conhecido, comparar com site da origem

---

## 11. Referências

- [PLANO-FONTES-PRECOS-MULTIPLAS-PLATAFORMAS.md](./PLANO-FONTES-PRECOS-MULTIPLAS-PLATAFORMAS.md) — visão original
- [MODULO-FONTES-PRECOS-00-PREPARACAO.md](./MODULO-FONTES-PRECOS-00-PREPARACAO.md) — estado atual PNCP
- Compras.gov Swagger: https://dadosabertos.compras.gov.br/swagger-ui/
- TCE/RS CKAN: https://dados.tce.rs.gov.br/

---

*Particionamento técnico — jul/2026.*
