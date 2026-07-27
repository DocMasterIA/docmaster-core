# Estudo — Notas Fiscais (Portal da Transparência) no Pesquisa de Preços

**Fonte oficial:** [Download de dados — Notas Fiscais](https://portaldatransparencia.gov.br/download-de-dados/notas-fiscais)  
**Dicionário:** [Dicionário de Dados — Notas Fiscais](https://portaldatransparencia.gov.br/pagina-interna/605482-notas-fiscais)  
**Data do estudo:** 24–25/jul/2026  
**Status:** discovery + **spike jan/2026 concluído** (CSVs locais)

Canvas: abrir `canvases/notas-fiscais-integracao-estudo.canvas.tsx` no Cursor.

**Amostra analisada:** `/home/adryan/Downloads/202601_NFe/`  
(`202601_NFe_NotaFiscal.csv` · `…Evento.csv` · `…Item.csv`)

---

## 1. Veredito (atualizado com spike)

A base é **fortemente viável** para Inciso V:

| Sinal | jan/2026 |
|-------|----------|
| Notas | **109.084** |
| Itens | **391.169** (~3,6 itens/nota) |
| Disco CSV | **~290 MB** / mês (57 + 232; Evento vazio) |
| VU > 0 | **99,9%** |
| Descrição preenchida | **100%** |
| NCM preenchido | **99,4%** |
| CNPJ emitente 14 dig. | **96,5–97%** |
| CNPJ destinatário 14 dig. | **100%** |
| Autorização de uso | **99,8%** das notas |

Arquitetura: CSV → SQLite `platform_index` → adapter (padrão Compras.gov/TCE).  
**Tabela-mãe da busca = `NotaFiscalItem`.** Cabeçalho serve para filtro de evento/órgão; Evento mensal pode vir vazio.

---

## 2. Achados do spike (jan/2026)

### 2.1 Encoding e join

- Encoding real: **`cp1252`** (não UTF-8).
- Separador: **`;`**.
- Chaves: NF ∩ Item = **108.559**; **525** notas sem item; 0 itens órfãos.
- **`NotaFiscalEvento.csv` sem linhas de dados** neste mês (só header). Cancelamento/autorização vêm de `NotaFiscal.EVENTO MAIS RECENTE`.

### 2.2 Colunas reais

**NotaFiscal (25 cols):** chave, modelo, série, número, natureza, data emissão, **evento mais recente**, emitente (CNPJ/razão/UF/município), órgão superior/destinatário (códigos + nomes), CNPJ/nome/UF destinatário, destino operação, consumidor final, presença comprador, valor nota.

**NotaFiscalItem (31 cols):** denormaliza quase todo o cabeçalho **exceto** evento/valor da nota; acrescenta:
`NÚMERO PRODUTO`, `DESCRIÇÃO DO PRODUTO/SERVIÇO`, `CÓDIGO NCM/SH`, `NCM/SH (TIPO DE PRODUTO)`, `CFOP`, `QUANTIDADE`, `UNIDADE`, `VALOR UNITÁRIO`, `VALOR TOTAL`.

**NotaFiscalEvento (10 cols):** schema existe; dump deste mês **vazio**.

### 2.3 Qualidade para pesquisa de preços

| Métrica | Valor |
|---------|------:|
| VU > 0 | 390.923 (99,9%) |
| Qtd > 0 | 389.347 (99,5%) |
| Desc vazia | 0 |
| Desc len p50 / p90 / max | 31 / 65 / **120** |
| Desc exatamente 120 chars | 2.523 (0,64%) — **possível truncamento** no export |
| VU p50 / p90 | R$ 31,00 / R$ 1.684 |
| Itens/chave p50 / max | 1 / 511 |

Unidades mais comuns: `UNIDAD`, `KG`, `PEÇA`, `L`, `CX` (normalizar no ingest).

### 2.4 Perfil institucional

- Órgão superior: Defesa (44k), Educação (30k), Saúde (12k), Justiça (7k)…  
- UF destinatário: RJ, DF, RS, MG, SP… (cobertura nacional federal).  
- Natureza textual bagunçada (`VENDA`, `Venda`, `VENDA DE MERCADORIA`…) — **não** usar como chave; preferir **CFOP**.

### 2.5 CFOP (atenção)

| Prefixo | Qtd itens | Leitura |
|---------|----------:|---------|
| 5 | 201.152 | Saída dentro do estado |
| 6 | 149.909 | Saída interestadual |
| 1 | 29.494 | Entrada |
| 2 | 10.607 | Entrada (outros) |

Top CFOPs: `5102`, `6949`, `5405`, `6108`, `6102`…  
Decisão pendente: whitelist de CFOP de **venda a órgão** vs remessa/bonificação (`5949`, `6949`, `5917`…).

### 2.6 NCM

Top 4 dígitos: `9018`/`9021` (médico), `4901` (impressos), `2710` (combustíveis), `3004` (medicamentos) — base rica para filtro de família.

---

## 3. Implicações de integração

### 3.1 Pipeline mínimo

```text
NotaFiscalItem (obrigatório)
    └─ JOIN NotaFiscal ON chave
         └─ filtrar EVENTO MAIS RECENTE ∈ {Autorização de Uso, …}
NotaFiscalEvento — opcional (quando houver linhas); não bloquear ingest se vazio
```

### 3.2 Mapeamento confirmado

| DocMaster | Coluna CSV |
|-----------|------------|
| `plataforma_item_id` | `{CHAVE}:{NÚMERO PRODUTO}` |
| `descricao_item` | DESCRIÇÃO DO PRODUTO/SERVIÇO (atenção truncamento 120) |
| `valor_unitario` / homologado | VALOR UNITÁRIO |
| `quantidade` / `unidade_medida` | QUANTIDADE / UNIDADE |
| `fornecedor_*` | CPF/CNPJ + RAZÃO SOCIAL EMITENTE |
| `orgao` / `uf` | ÓRGÃO DESTINATÁRIO ou NOME DESTINATÁRIO / UF DESTINATÁRIO |
| `data_referencia` | DATA EMISSÃO |
| extra `ncm` / `cfop` | CÓDIGO NCM/SH / CFOP |
| `url_origem` | portal pela CHAVE DE ACESSO |

### 3.3 Regras de qualidade (obrigatórias)

1. `VU > 0` e descrição não vazia.  
2. Preferir **CNPJ emitente 14**; CPF (0% neste mês) — política de mascarar se aparecer.  
3. Excluir ou isolar `EVENTO MAIS RECENTE = Sem informação`.  
4. **Não** depender de `NotaFiscalEvento` para cancelamento neste formato.  
5. Pós-FTS: **mesmos** `product_spec` / `product_category` do PNCP (texto livre + desc curta).  
6. Normalizar unidade (`UNIDAD`→`UN`, etc.).  
7. Avaliar filtro CFOP (config).

### 3.4 Dimensionamento

| Janela | CSV bruto (ordem) | Itens (ordem) |
|--------|-------------------|---------------|
| 1 mês | ~0,3 GB | ~0,4 M |
| 12 meses | ~3–4 GB | ~4–5 M |

SQLite+FTS: planejar volume Docker **≥ 10–20 GB** com folga (índices + upsert).

### 3.5 ID / produto

- `platform_id`: `notas_fiscais`  
- Inciso: **V** / bucket `notasFiscais` (já na UI)  
- Feed isolado (ex. `:8017`) espelhando Compras.gov  

---

## 4. Decisões ainda abertas

1. Whitelist CFOP (só vendas 5xxx/6xxx “mercadoria”?).  
2. Manter itens com desc truncada em 120 chars? (marcar `desc_truncada`).  
3. Janela default: 6 vs 12 meses.  
4. Deep-link oficial estável da chave (URL portal).  
5. Dedup visual vs PNCP (aceitar overlap Inciso V).  

---

## 5. Fases

| Fase | Status |
|------|--------|
| **0 — Spike** | **Feito** (jan/2026) |
| 1 — Scaffold | Próximo |
| 2 — Ingest Item+join NF | — |
| 3 — Federado + UI Inciso V | — |
| 4 — Qualidade lexical isonômica | — |

---

## 6. Referências

- Amostra local: `/home/adryan/Downloads/202601_NFe/`  
- [MODULO-FONTES-PRECOS-04-COMPRAS-GOV.md](./MODULO-FONTES-PRECOS-04-COMPRAS-GOV.md)  
- [ARQUITETURA-FEEDS-INDEPENDENTES.md](./ARQUITETURA-FEEDS-INDEPENDENTES.md)  
