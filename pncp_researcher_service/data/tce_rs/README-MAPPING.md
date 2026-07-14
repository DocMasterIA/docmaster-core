# TCE-RS / LicitaCon — mapeamento dos CSVs (2025 / 2026)

Fonte: export LicitaCon (TCE-RS). Separador `,`, encoding UTF-8.  
Pasta local: `pncp_researcher_service/data/tce_rs/raw/{2025,2026}/`.

> Layout oficial sujeito a confirmação no CKAN; este doc descreve o que veio nas pastas entregues.

---

## 1. Existe serviço separado para TCE-RS?

**Operacionalmente sim** — container `price_index_feed_tce_rs` (:8014), isolado do feed PNCP.
Código ainda na mesma imagem (`FEED_PLATFORM=tce_rs`).

| Peça | Onde vive |
|------|-----------|
| Ingest / materialização | Container `price_index_feed_tce_rs` (`SERVICE_MODE=feed`, `FEED_PLATFORM=tce_rs`, :8014) |
| Busca | `pncp_researcher_service` (:8012) via `TceRsAdapter` (só leitura) |
| SQLite | `/data/platforms/tce_rs_local.db` (escrito só pelo feed TCE-RS) |
| Código ingest | `app/platform_index/ingest/tce_rs/` |
| Arquitetura | [ARQUITETURA-FEEDS-INDEPENDENTES.md](../../../docs/pncp/ARQUITETURA-FEEDS-INDEPENDENTES.md) |

---

## 2. Arquivos por ano

| Arquivo | ~2025 | ~2026 | Papel na pesquisa de preços |
|---------|-------|-------|------------------------------|
| `licitacao.csv` | 90 MB | 46 MB | **Chave** — processo, órgão, objeto, link |
| `item.csv` / `itemw.csv` | 294 MB (`item`) | 144 MB (`itemw`) | **Chave** — descrição + preços |
| `item_prop.csv` | 368 MB | 100 MB | Propostas por item (CNPJ + VL_UNITARIO) |
| `proposta.csv` | 18 MB | 6 MB | Proposta no nível do processo |
| `pessoas.csv` | 185 MB | 185 MB | Nome do fornecedor (join por documento) |
| `lote.csv` / `lote_prop.csv` | médio | médio | Agregação por lote (secundário) |
| `evento_lic.csv` | 34 MB | 16 MB | Datas de publicação / fases |
| `licitante.csv` | 13 MB | 4,6 MB | Participantes |
| `documento_lic.csv` | 223 MB | 108 MB | PDFs (fora do índice de preço, por agora) |
| `dotacao_lic.csv` | 7,8 MB | 3,4 MB | Dotação (fora do core de preço) |
| `comissao.csv` / `memcomissao.csv` / `membrocons.csv` | pequeno | pequeno | Comissão / consórcio (irrelevante p/ preço) |

**Atenção 2026:** o arquivo de itens chama-se `itemw.csv`, mas as **33 colunas são idênticas** a `item.csv` de 2025 — tratar como alias no parser.

---

## 3. Chave natural (join)

Todas as tabelas “de processo” compartilham a chave composta:

```text
CD_ORGAO + NR_LICITACAO + ANO_LICITACAO + CD_TIPO_MODALIDADE
```

Item e propostas de item acrescentam:

```text
+ NR_LOTE + NR_ITEM
```

Fornecedor:

```text
TP_DOCUMENTO + NR_DOCUMENTO  →  pessoas (NM_PESSOA)
```

IDs canônicos sugeridos para nosso índice:

```text
processo_id        = tce_rs:{CD_ORGAO}:{ANO}:{NR}:{MOD}
plataforma_item_id = {processo_id}:{NR_LOTE}:{NR_ITEM}
```

---

## 4. Significado das colunas (núcleo)

### 4.1 `licitacao.csv` (65 cols) — processo

| Coluna | Significado | Uso no índice |
|--------|-------------|----------------|
| `CD_ORGAO` | Código do órgão no TCE | chave / filtro |
| `NM_ORGAO` | Nome do órgão | `orgao` |
| `NR_LICITACAO` / `ANO_LICITACAO` | Número e ano da licitação | chave |
| `CD_TIPO_MODALIDADE` | Modalidade (PCE, PDE, PRD, PCP, CPC…) | chave / metadado |
| `NR_PROCESSO` / `ANO_PROCESSO` | Nº processo administrativo | `numero_processo` |
| `DS_OBJETO` | Objeto da licitação | contexto / fallback de busca |
| `DT_ABERTURA` / `DT_HOMOLOGACAO` / `DT_ADJUDICACAO` | Datas | `data_referencia` (preferir homologação) |
| `VL_LICITACAO` / `VL_HOMOLOGADO` | Totais do processo | não usar como preço unitário |
| `LINK_LICITACON_CIDADAO` | URL portal cidadão | `url_origem` |
| `CD_TIPO_FASE_ATUAL` | Fase atual (PUB, HAP, …) | filtro opcional |
| `TP_OBJETO` | Tipo objeto (COM, OSE, …) | filtro opcional |
| `NR_DOCUMENTO_VENCEDOR` | CNPJ/CPF vencedor global | fallback se item sem proposta |

### 4.2 `item.csv` / `itemw.csv` (33 cols) — item

| Coluna | Significado | Uso no índice |
|--------|-------------|----------------|
| `NR_LOTE` / `NR_ITEM` | Lote e item | chave do item |
| `DS_ITEM` | Descrição do item | **`descricao` / FTS** |
| `QT_ITENS` | Quantidade | `quantidade` |
| `SG_UNIDADE_MEDIDA` | Unidade (UN, KG, …) | `unidade_medida` |
| `VL_UNITARIO_ESTIMADO` | Preço unitário estimado | fallback de preço |
| `VL_UNITARIO_HOMOLOGADO` | Preço unitário homologado | **`valor_unitario_homologado` (preferido)** |
| `VL_TOTAL_*` | Totais | opcional |
| `TP_RESULTADO_ITEM` | Resultado do item | filtro (ver §5) |
| `TP_DOCUMENTO` / `NR_DOCUMENTO` | Documento associado ao item | join fornecedor (quando preenchido) |
| `BL_COVID19` / `TP_BENEFICIO_MICRO_EPP` | flags | ignorar no core |

Amostra (~150k linhas): ~40–50% com `VL_UNITARIO_HOMOLOGADO > 0`; quase todos têm estimado. Muitos `TP_RESULTADO_ITEM` vazios ainda com homologado preenchido — **não filtrar só por `A`**.

### 4.3 `item_prop.csv` (18 cols) — proposta por item

| Coluna | Significado | Uso |
|--------|-------------|-----|
| `TP_DOCUMENTO` / `NR_DOCUMENTO` | Tipo + CNPJ/CPF do licitante | fornecedor |
| `VL_UNITARIO` / `VL_TOTAL_ITEM` | Valor da proposta | preço quando item sem homologado |
| `TP_RESULTADO_PROPOSTA` | Resultado da proposta (`C` visto em vencedores) | escolher vencedor |
| `DT_HOMOLOGACAO` | Data homologação proposta | data_referencia |
| `TP_RESULTADO_HABILITACAO` | Habilitação | filtro opcional |

Join `pessoas` por (`TP_DOCUMENTO`,`NR_DOCUMENTO`) → `NM_PESSOA` (confirmado em amostra: propostas `C` → razão social correta).

### 4.4 `pessoas.csv` (21 cols)

| Coluna | Uso |
|--------|-----|
| `NM_PESSOA` | `fornecedor_nome` |
| `SG_UF` / `CD_MUNICIPIO_IBGE` | geo do fornecedor (menor prioridade que órgão) |
| Demais | endereço/contato — fora do core |

### 4.5 Tabelas fora do core de preço (fase 1)

- `documento_lic` — anexos (TR, edital); não entra no FTS de preço agora  
- `evento_lic` — pode enriquecer `data_referencia` via evento `PUB`  
- `lote` / `lote_prop` / `proposta` — agregados; só se item vier vazio  
- `dotacao_lic`, `comissao`, `memcomissao`, `membrocons`, `licitante` — fora do MVP de preço  

---

## 5. Junção sugerida (pipeline MVP)

```text
1. licitacao  ──┐
2. item(/itemw) ┼── INNER JOIN pela chave composta
3. LEFT JOIN item_prop “melhor proposta” do item
      prioridade: TP_RESULTADO_PROPOSTA = C (ou homologada)
                  senão menor VL_UNITARIO > 0
4. LEFT JOIN pessoas ON documento da proposta (ou do item / vencedor da licitação)
5. Filtrar linhas com preço unitário > 0
      preferir VL_UNITARIO_HOMOLOGADO
      senão VL_UNITARIO da proposta vencedora
      senão VL_UNITARIO_ESTIMADO (marcar origem no raw)
6. UF fixa "RS"; município: preferir CD_MUNICIPIO_IBGE do órgão quando disponível
   (hoje não vem em licitacao — pode ficar NULL no MVP ou enriquecer depois)
7. Materializar → platform_processos + platform_itens_leitura (+ bruto)
```

### Mapa → schema `platform_index`

| Campo índice | Origem LicitaCon |
|--------------|------------------|
| `processo_id` | `tce_rs:{CD_ORGAO}:{ANO}:{NR}:{MOD}` |
| `plataforma_item_id` | `{processo_id}:{NR_LOTE}:{NR_ITEM}` |
| `descricao` | `item.DS_ITEM` |
| `quantidade` | `item.QT_ITENS` |
| `unidade_medida` | `item.SG_UNIDADE_MEDIDA` |
| `valor_unitario_homologado` | `item.VL_UNITARIO_HOMOLOGADO` |
| `valor_unitario` | homologado \|\| proposta.VL_UNITARIO \|\| estimado |
| `orgao` | `licitacao.NM_ORGAO` |
| `uf` | `"RS"` |
| `municipio` | IBGE do **fornecedor** (`pessoas.CD_MUNICIPIO_IBGE`); órgão não tem coluna |
| `fornecedor_nome` / `cnpj_fornecedor` | waterfall: `item_prop C` → `item` doc1/doc2 → `licitacao` vencedor/fornecedor → `pessoas` |
| `data_referencia` | `DT_HOMOLOGACAO` item_prop \|\| licitação |
| `numero_processo` | `NR_PROCESSO`/`ANO_PROCESSO` |
| `url_origem` | `LINK_LICITACON_CIDADAO` |
| `inciso_classificacao` | `"inciso_ii"` |
| `esfera` | `"estadual"` |
| `numero_pncp` | parcial: parse `evento_lic.DS_PUBLICACAO` (`pncp.gov.br/editais/...`) |

Análise completa (fill rates + cobertura premium 2025): [`ANALISE-COLUNAS-PREMIUM.md`](./ANALISE-COLUNAS-PREMIUM.md).

---

## 6. O que precisa ser feito (backlog técnico)

1. **Pasta dedicada (feito)** — `data/tce_rs/raw/{ano}/`; raw **fora do git**.  
2. **Parser LicitaCon (feito)** — `CD_ORGAO`/`DS_ITEM`/`VL_UNITARIO_*`, chave composta, `itemw.csv`, `item_prop` + `pessoas`.  
3. **Join + preço (parcial)** — homologado → proposta `C`; **ainda** inclui estimado e waterfall de CNPJ incompleto.  
4. **Ingest amostral / multi-ano (feito)**.  
5. **Premium interno (próximo)** — ver `ANALISE-COLUNAS-PREMIUM.md`:  
   - headers duplicados de documento no `item`  
   - waterfall fornecedor completo  
   - `itens_leitura` só homologado/prop C + fornecedor  
   - soft-PNCP via `evento_lic`  
6. **Ingest full-year** — sem `max_rows` no feed `:8014`.  
7. **Município do órgão** — só com cadastro externo de órgãos (não está nos CSVs).  
8. **CKAN/cron** — depois.  
9. **UI** — checkbox TCE-RS quando `search_ready`.  

---

## 7. Observações importantes

- **Duplicação de headers** em `item`/`lote`/`licitante`: os dois pares `TP_DOCUMENTO`/`NR_DOCUMENTO` são **mutuamente exclusivos** (0 linhas com ambos preenchidos em 2025). `DictReader` sem rename **apaga** o 1º par quando o 2º vem vazio (~532 k docs).  
- `pessoas.csv` é grande e se repete entre anos — dedup por dígitos do documento.  
- `documento_lic` **não** precisa no FTS de preço na fase premium.  
- `TP_RESULTADO_ITEM`: `A` dominante; muitos homologados com resultado vazio — **não** filtrar só por `A`.  
- Links PNCP em `evento_lic.DS_PUBLICACAO` existem (~52 k licitações/2025); usar antes de API externa.

---

## 8. Layout no repositório

```text
pncp_researcher_service/
  data/tce_rs/
    raw/
      2025/   # CSVs LicitaCon (gitignored)
      2026/
    README-MAPPING.md   # este documento
  fixtures/tce_rs/      # amostras mínimas para testes unitários
  app/platform_index/ingest/tce_rs/
```
