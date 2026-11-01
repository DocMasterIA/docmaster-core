# TCE-RS / LicitaCon — CSV mapping (2025 / 2026)

Source: LicitaCon export (TCE-RS). Separator `,`, encoding UTF-8.  
Local folder: `pncp_researcher_service/data/tce_rs/raw/{2025,2026}/`.

> The official layout is subject to confirmation on CKAN; this doc describes what arrived in the delivered folders.

---

## 1. Is there a separate service for TCE-RS?

**Operationally, yes** — container `price_index_feed_tce_rs` (:8014), isolated from the PNCP feed.
The code still lives in the same image (`FEED_PLATFORM=tce_rs`).

| Piece | Where it lives |
|-------|----------------|
| Ingest / materialization | Container `price_index_feed_tce_rs` (`SERVICE_MODE=feed`, `FEED_PLATFORM=tce_rs`, :8014) |
| Search | `pncp_researcher_service` (:8012) via `TceRsAdapter` (read-only) |
| SQLite | `/data/platforms/tce_rs_local.db` (written only by the TCE-RS feed) |
| Ingest code | `app/platform_index/ingest/tce_rs/` |
| Architecture | [ARQUITETURA-FEEDS-INDEPENDENTES.md](../../../docs/pncp/ARQUITETURA-FEEDS-INDEPENDENTES.md) |

---

## 2. Files by year

| File | ~2025 | ~2026 | Role in price research |
|------|-------|-------|------------------------|
| `licitacao.csv` | 90 MB | 46 MB | **Key** — process, agency, object, link |
| `item.csv` / `itemw.csv` | 294 MB (`item`) | 144 MB (`itemw`) | **Key** — description + prices |
| `item_prop.csv` | 368 MB | 100 MB | Bids per item (CNPJ + VL_UNITARIO) |
| `proposta.csv` | 18 MB | 6 MB | Bid at process level |
| `pessoas.csv` | 185 MB | 185 MB | Supplier name (join by document) |
| `lote.csv` / `lote_prop.csv` | medium | medium | Aggregation by lot (secondary) |
| `evento_lic.csv` | 34 MB | 16 MB | Publication dates / phases |
| `licitante.csv` | 13 MB | 4.6 MB | Participants |
| `documento_lic.csv` | 223 MB | 108 MB | PDFs (outside the price index, for now) |
| `dotacao_lic.csv` | 7.8 MB | 3.4 MB | Budget appropriation (outside the price core) |
| `comissao.csv` / `memcomissao.csv` / `membrocons.csv` | small | small | Committee / consortium (irrelevant for price) |

**2026 note:** the item file is named `itemw.csv`, but its **33 columns are identical** to the 2025 `item.csv` — treat it as an alias in the parser.

---

## 3. Natural key (join)

Every “process” table shares the composite key:

```text
CD_ORGAO + NR_LICITACAO + ANO_LICITACAO + CD_TIPO_MODALIDADE
```

Item and item bids add:

```text
+ NR_LOTE + NR_ITEM
```

Supplier:

```text
TP_DOCUMENTO + NR_DOCUMENTO  →  pessoas (NM_PESSOA)
```

Canonical IDs suggested for our index:

```text
processo_id        = tce_rs:{CD_ORGAO}:{ANO}:{NR}:{MOD}
plataforma_item_id = {processo_id}:{NR_LOTE}:{NR_ITEM}
```

---

## 4. Column meanings (core)

### 4.1 `licitacao.csv` (65 cols) — process

| Column | Meaning | Use in the index |
|--------|---------|------------------|
| `CD_ORGAO` | Agency code at TCE | key / filter |
| `NM_ORGAO` | Agency name | `orgao` |
| `NR_LICITACAO` / `ANO_LICITACAO` | Procurement number and year | key |
| `CD_TIPO_MODALIDADE` | Modality (PCE, PDE, PRD, PCP, CPC…) | key / metadata |
| `NR_PROCESSO` / `ANO_PROCESSO` | Administrative process number | `numero_processo` |
| `DS_OBJETO` | Procurement object | context / search fallback |
| `DT_ABERTURA` / `DT_HOMOLOGACAO` / `DT_ADJUDICACAO` | Dates | `data_referencia` (prefer homologation) |
| `VL_LICITACAO` / `VL_HOMOLOGADO` | Process totals | do not use as the unit price |
| `LINK_LICITACON_CIDADAO` | Citizen portal URL | `url_origem` |
| `CD_TIPO_FASE_ATUAL` | Current phase (PUB, HAP, …) | optional filter |
| `TP_OBJETO` | Object type (COM, OSE, …) | optional filter |
| `NR_DOCUMENTO_VENCEDOR` | Global winner CNPJ/CPF | fallback when the item has no bid |

### 4.2 `item.csv` / `itemw.csv` (33 cols) — item

| Column | Meaning | Use in the index |
|--------|---------|------------------|
| `NR_LOTE` / `NR_ITEM` | Lot and item | item key |
| `DS_ITEM` | Item description | **`descricao` / FTS** |
| `QT_ITENS` | Quantity | `quantidade` |
| `SG_UNIDADE_MEDIDA` | Unit (UN, KG, …) | `unidade_medida` |
| `VL_UNITARIO_ESTIMADO` | Estimated unit price | price fallback |
| `VL_UNITARIO_HOMOLOGADO` | Homologated unit price | **`valor_unitario_homologado` (preferred)** |
| `VL_TOTAL_*` | Totals | optional |
| `TP_RESULTADO_ITEM` | Item result | filter (see §5) |
| `TP_DOCUMENTO` / `NR_DOCUMENTO` | Document associated with the item | supplier join (when filled) |
| `BL_COVID19` / `TP_BENEFICIO_MICRO_EPP` | flags | ignore in the core |

Sample (~150k rows): ~40–50% have `VL_UNITARIO_HOMOLOGADO > 0`; almost all have an estimate. Many `TP_RESULTADO_ITEM` values are empty even when the homologated price is filled — **do not filter only by `A`**.

### 4.3 `item_prop.csv` (18 cols) — bid per item

| Column | Meaning | Use |
|--------|---------|-----|
| `TP_DOCUMENTO` / `NR_DOCUMENTO` | Type + bidder CNPJ/CPF | supplier |
| `VL_UNITARIO` / `VL_TOTAL_ITEM` | Bid amount | price when the item has no homologated value |
| `TP_RESULTADO_PROPOSTA` | Bid result (`C` seen on winners) | pick the winner |
| `DT_HOMOLOGACAO` | Bid homologation date | data_referencia |
| `TP_RESULTADO_HABILITACAO` | Qualification | optional filter |

Join `pessoas` on (`TP_DOCUMENTO`,`NR_DOCUMENTO`) → `NM_PESSOA` (confirmed on a sample: `C` bids → correct legal name).

### 4.4 `pessoas.csv` (21 cols)

| Column | Use |
|--------|-----|
| `NM_PESSOA` | `fornecedor_nome` |
| `SG_UF` / `CD_MUNICIPIO_IBGE` | supplier geo (lower priority than the agency) |
| The rest | address/contact — outside the core |

### 4.5 Tables outside the price core (phase 1)

- `documento_lic` — attachments (TR, notice); not in the price FTS for now  
- `evento_lic` — can enrich `data_referencia` via the `PUB` event  
- `lote` / `lote_prop` / `proposta` — aggregates; only if the item comes back empty  
- `dotacao_lic`, `comissao`, `memcomissao`, `membrocons`, `licitante` — outside the price MVP  

---

## 5. Suggested join (MVP pipeline)

```text
1. licitacao  ──┐
2. item(/itemw) ┼── INNER JOIN on the composite key
3. LEFT JOIN item_prop “best bid” for the item
      priority: TP_RESULTADO_PROPOSTA = C (or homologated)
                otherwise the lowest VL_UNITARIO > 0
4. LEFT JOIN pessoas ON the bid document (or the item / procurement winner)
5. Filter rows with unit price > 0
      prefer VL_UNITARIO_HOMOLOGADO
      otherwise VL_UNITARIO of the winning bid
      otherwise VL_UNITARIO_ESTIMADO (mark the origin in raw)
6. UF fixed to "RS"; municipality: prefer the agency CD_MUNICIPIO_IBGE when available
   (it is not in licitacao today — it can stay NULL in the MVP or be enriched later)
7. Materialize → platform_processos + platform_itens_leitura (+ raw)
```

### Map → `platform_index` schema

| Index field | LicitaCon source |
|-------------|------------------|
| `processo_id` | `tce_rs:{CD_ORGAO}:{ANO}:{NR}:{MOD}` |
| `plataforma_item_id` | `{processo_id}:{NR_LOTE}:{NR_ITEM}` |
| `descricao` | `item.DS_ITEM` |
| `quantidade` | `item.QT_ITENS` |
| `unidade_medida` | `item.SG_UNIDADE_MEDIDA` |
| `valor_unitario_homologado` | `item.VL_UNITARIO_HOMOLOGADO` |
| `valor_unitario` | homologated \|\| bid.VL_UNITARIO \|\| estimated |
| `orgao` | `licitacao.NM_ORGAO` |
| `uf` | `"RS"` |
| `municipio` | IBGE of the **supplier** (`pessoas.CD_MUNICIPIO_IBGE`); the agency has no column |
| `fornecedor_nome` / `cnpj_fornecedor` | waterfall: `item_prop C` → `item` doc1/doc2 → `licitacao` winner/supplier → `pessoas` |
| `data_referencia` | item_prop `DT_HOMOLOGACAO` \|\| procurement |
| `numero_processo` | `NR_PROCESSO`/`ANO_PROCESSO` |
| `url_origem` | `LINK_LICITACON_CIDADAO` |
| `inciso_classificacao` | `"inciso_ii"` |
| `esfera` | `"estadual"` |
| `numero_pncp` | partial: parse `evento_lic.DS_PUBLICACAO` (`pncp.gov.br/editais/...`) |

Full analysis (fill rates + premium coverage 2025): [`ANALISE-COLUNAS-PREMIUM.md`](./ANALISE-COLUNAS-PREMIUM.md).

---

## 6. What still needs to be done (technical backlog)

1. **Dedicated folder (done)** — `data/tce_rs/raw/{year}/`; raw **outside git**.  
2. **LicitaCon parser (done)** — `CD_ORGAO`/`DS_ITEM`/`VL_UNITARIO_*`, composite key, `itemw.csv`, `item_prop` + `pessoas`.  
3. **Join + price (partial)** — homologated → bid `C`; **still** includes the estimate and an incomplete CNPJ waterfall.  
4. **Sample / multi-year ingest (done)**.  
5. **Internal premium (next)** — see `ANALISE-COLUNAS-PREMIUM.md`:  
   - duplicate document headers on `item`  
   - full supplier waterfall  
   - `itens_leitura` only homologated/bid C + supplier  
   - soft-PNCP via `evento_lic`  
6. **Full-year ingest** — no `max_rows` on feed `:8014`.  
7. **Agency municipality** — only with an external agency registry (it is not in the CSVs).  
8. **CKAN/cron** — later.  
9. **UI** — TCE-RS checkbox when `search_ready`.  

---

## 7. Important notes

- **Duplicate headers** on `item`/`lote`/`licitante`: the two `TP_DOCUMENTO`/`NR_DOCUMENTO` pairs are **mutually exclusive** (0 rows with both filled in 2025). `DictReader` without a rename **drops** the 1st pair when the 2nd comes back empty (~532k docs).  
- `pessoas.csv` is large and repeats across years — dedup by document digits.  
- `documento_lic` **does not** need to be in the price FTS in the premium phase.  
- `TP_RESULTADO_ITEM`: `A` is dominant; many homologated rows have an empty result — **do not** filter only by `A`.  
- PNCP links in `evento_lic.DS_PUBLICACAO` exist (~52k procurements/2025); use them before an external API.

---

## 8. Layout in the repository

```text
pncp_researcher_service/
  data/tce_rs/
    raw/
      2025/   # LicitaCon CSVs (gitignored)
      2026/
    README-MAPPING.md   # this document
  fixtures/tce_rs/      # minimal samples for unit tests
  app/platform_index/ingest/tce_rs/
```
