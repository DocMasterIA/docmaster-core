# TCE-RS — análise de colunas × item “premium” (sem fonte externa)

Escopo: **só** os CSVs em `data/tce_rs/raw/{2025,2026}/`.  
Objetivo do produto: item de pesquisa no **mesmo nível de metadados ricos do PNCP** (preço homologado, fornecedor, URL, órgão, datas) — **antes** de buscar APIs externas.

Medição integral 2025: 1 393 747 itens × join completo (~47 s de scan).

---

## 1. Veredito

| Pergunta | Resposta |
|----------|----------|
| As planilhas já têm o necessário para item “premium”? | **Sim, em grande parte** |
| Falta integração externa para preço/fornecedor/URL? | **Não** — o gap é o **join interno** |
| Quantos itens 2025 nascem “premium” com waterfall completo? | **~646 k (46,3%)** |
| O que ainda fica fraco só com CSVs? | Município do **órgão**; `numero_pncp` (parcial via evento) |

---

## 2. Inventário dos arquivos

### Núcleo da pesquisa de preços (obrigatório)

| Arquivo | 2025 rows | Papel |
|---------|-----------|--------|
| `licitacao.csv` | 167 150 | Processo, órgão, datas, URL cidadão |
| `item.csv` / `itemw.csv` | 1 393 747 / 660 079 | Descrição, qtd, unidade, **homologado** |
| `item_prop.csv` | 5 694 370 / 1 566 427 | Proposta vencedora (`C`) + CNPJ |
| `pessoas.csv` | 1 649 460 (igual nos dois anos) | Razão social / IBGE do fornecedor |

### Enriquecimento útil (ainda interno)

| Arquivo | Uso premium |
|---------|-------------|
| `evento_lic.csv` | `DS_PUBLICACAO` com links `pncp.gov.br/editais/...` (~52 k licitações 2025) |
| `lote.csv` / `lote_prop.csv` | Fallback raro (nível lote, não unitário) |
| `proposta.csv` | Agregado de processo — **não** substitui `item_prop` |

### Fora do índice de preços (fase premium atual)

`documento_lic`, `dotacao_lic`, `licitante`, `comissao`, `memcomissao`, `membrocons`.

---

## 3. Colunas críticas e preenchimento (2025)

### `item.csv`

| Coluna | Fill | Nota |
|--------|------|------|
| `DS_ITEM`, `QT_ITENS`, `SG_UNIDADE_MEDIDA` | 100% | núcleo FTS |
| `VL_UNITARIO_ESTIMADO` | 98,4% | **não** basta para premium |
| `VL_UNITARIO_HOMOLOGADO` | 62,1% não-vazio; **~50,1% > 0** | preço premium preferido |
| `TP_RESULTADO_ITEM` | 45% (`A` dominante) | muitos homologados com resultado vazio |
| `TP_DOCUMENTO` / `NR_DOCUMENTO` (1º par) | 38,2% | **mutuamente exclusivo** com o 2º |
| `TP_DOCUMENTO` / `NR_DOCUMENTO` (2º par) | 24,4% | nunca coexiste com o 1º (0 linhas both) |

**Bug estrutural de leitura:** `csv.DictReader` com header duplicado fica com a **última** coluna. Quando só o 1º par está preenchido e o 2º vem vazio, o documento **some**. Por isso a amostra antiga perdia fornecedor mesmo com CNPJ no CSV.

### `item_prop.csv`

| Coluna | Fill | Nota |
|--------|------|------|
| `VL_UNITARIO` | 100% | pode ser 0 |
| `TP_RESULTADO_PROPOSTA` | 69% (`C` = 2,2 M) | vencedora |
| `DT_HOMOLOGACAO` | 33% | boa data_ref |
| `TP_DOCUMENTO`/`NR_DOCUMENTO` | 100% | chave para `pessoas` |

### `licitacao.csv`

| Coluna | Fill | Nota |
|--------|------|------|
| `NM_ORGAO`, `DS_OBJETO`, `LINK_LICITACON_CIDADAO` | 100% | |
| `DT_HOMOLOGACAO` | 41,5% | |
| `NR_DOCUMENTO_FORNECEDOR` | 33,8% | fallback de fornecedor |
| `NR_DOCUMENTO_VENCEDOR` | 2,9% | fallback raro |
| município do órgão | **inexistente** | não há coluna IBGE/cidade do órgão |

### `pessoas.csv`

| Coluna | Fill | Nota |
|--------|------|------|
| `NM_PESSOA` | 65,8% das linhas | ~201 k documentos únicos com nome |
| `SG_UF` / `CD_MUNICIPIO_IBGE` | 65,8% | geo do **fornecedor**, não do órgão |
| `CD_ORGAO` | 100% | cadastro é por órgão (duplicatas de CNPJ possíveis) |

### `evento_lic.csv`

- `DS_PUBLICACAO` contém URLs `https://pncp.gov.br/editais/{cnpj}/{ano}/{seq}` em **52 314** licitações (2025).
- Dá para derivar um **soft `numero_pncp`/URL PNCP** sem API externa.
- Não é o mesmo campo federal completo em todos os casos; é enriquecimento interno.

---

## 4. Cobertura do join completo (2025)

Definição **premium** usada na medição:

> preço homologado (`item`) **ou** proposta `C` com VL>0  
> **+** fornecedor nomeado via `pessoas`  
> **+** órgão + URL LicitaCon + descrição

```text
itens totais .................... 1.393.747  100%
  └─ licitacao bater ............ 1.393.747  100%

preço:
  item.VL_UNITARIO_HOMOLOGADO>0 .   698.926   50,1%
  + proposta C (extra) ..........    27.885    2,0%
  só estimado ...................   611.506   43,9%   ← fora do premium
  sem preço .....................    55.430    4,0%

fornecedor nomeado (waterfall):
  via item_prop C ...............   576.626
  via item NR_DOCUMENTO (2º) ....   334.961
  via licitacao FORNECEDOR ......   107.416
  via item NR_DOCUMENTO (1º) ....    41.377
  via licitacao VENCEDOR ........    28.350
  total nomeado ................. 1.088.730   78,1%
  sem nome ......................   305.017   21,9%

PREMIUM completo ................   645.983   46,3%
  └─ com IBGE do fornecedor .....   645.966
  └─ + link PNCP em evento ......   179.374   12,9%
```

### Waterfall obrigatório de fornecedor (interno)

```text
1. item_prop (TP_RESULTADO_PROPOSTA=C, VL_UNITARIO>0).NR_DOCUMENTO
2. item.NR_DOCUMENTO  (1º par)
3. item.NR_DOCUMENTO  (2º par)   ← hoje subaproveitado
4. licitacao.NR_DOCUMENTO_VENCEDOR
5. licitacao.NR_DOCUMENTO_FORNECEDOR
       │
       ▼
pessoas por dígitos do documento → NM_PESSOA (+ SG_UF / CD_MUNICIPIO_IBGE)
```

### Waterfall de preço

```text
1. item.VL_UNITARIO_HOMOLOGADO > 0     → valor + homologado
2. item_prop C.VL_UNITARIO > 0         → valor (homologado null ou igual)
3. (opcional produto) estimado         → NÃO entra no índice “premium”
```

Regra de produto alinhada ao pedido: **índice de busca premium exclui estimado puro**.  
Estimado pode ficar só em `itens_bruto` / flag de qualidade, não em `itens_leitura` federada.

---

## 5. Mapa → `MarketPriceHit` / PNCP-equivalente

| Campo hit | Origem LicitaCon | Status CSV |
|-----------|------------------|------------|
| `descricao_item` | `item.DS_ITEM` | OK 100% |
| `valor_unitario` / `valor_unitario_homologado` | item homologado → prop C | OK ~52% com preço “duro” |
| `quantidade` / `unidade_medida` | `QT_ITENS` / `SG_UNIDADE_MEDIDA` | OK |
| `orgao` | `licitacao.NM_ORGAO` | OK |
| `uf` | fixo `RS` (órgão); fornecedor tem `SG_UF` próprio | OK órgão |
| `municipio` | **não há do órgão**; IBGE do fornecedor existe | parcial |
| `fornecedor_nome` / `cnpj` | waterfall + `pessoas` | OK se join correto (~78%) |
| `data_referencia` | prop/`licitacao` `DT_HOMOLOGACAO` → abertura | OK majoritário no premium |
| `url_origem` | `LINK_LICITACON_CIDADAO` | OK 100% |
| `numero_processo` | `NR_PROCESSO`/`ANO_PROCESSO` | OK |
| `numero_pncp` | parse `evento_lic.DS_PUBLICACAO` | parcial (~37% itens em lic. com link) |
| `inciso` / `esfera` | `inciso_ii` / `estadual` | fixo (aceitável Art. 5º II) |

---

## 6. Gaps reais (ainda sem exterior)

1. **Município do órgão comprador** — não existe coluna; só dá para inferir depois (cadastro de órgãos TCE) ou usar IBGE do fornecedor com label claro (`municipio_fornecedor`).
2. **~44% dos itens só têm estimado** — para premium, **ficar de fora** do índice de busca.
3. **~22% sem nome em `pessoas`** mesmo com CNPJ — documento sem `NM_PESSOA` na base (fill 66%).
4. **`numero_pncp` completo** — só URLs em evento; parsing interno ajuda crosslink, não cobre todos.

Nada disso exige Compras.gov / API TCE agora.

---

## 7. O que o código atual ainda erra (relativo a esta análise)

1. Waterfall de CNPJ incompleto (não usa 2º par do item + vencedor/fornecedor da licitação na prioridade medida).
2. Risco histórico de header duplicado engolir o 1º `NR_DOCUMENTO`.
3. Inclui **estimado** em `itens_leitura` — polui o “premium”.
4. Não lê `evento_lic` para soft-PNCP.
5. Full-year ainda não materializado no DB de produção.

---

## 8. Próximo passo (sem exterior)

1. Corrigir parser/materialize para waterfall §4 (docs duplicados + licitacao).
2. Gate premium: `itens_leitura` só com preço homologado/prop C **e** fornecedor nomeado (ou pelo menos CNPJ).
3. Opcional: parse link PNCP de `evento_lic`.
4. Só então: ingest full 2025+2026 e validar federado.
5. Exterior (CKAN/cron, cadastro de órgãos) fica **depois**.

---

*Análise gerada a partir de scan completo dos CSVs locais — jul/2026.*
