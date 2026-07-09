# Mapeamento de slots — export Excel da cotação PNCP

Planilha-modelo (`.xlsx` ou `.xlsm`) com placeholders `{SLOT}`.
O backend substitui os valores ao exportar a cotação.

## Nomenclatura do arquivo exportado

Mesmo padrão do PDF de relatório:

`docmaster-pesquisador-pncp_{usuario}_{YYYYMMDD-HHMM}_cotacao-{id}_{titulo}.xlsx`

Exemplo: `docmaster-pesquisador-pncp_marcelo-faria_20260706-1251_cotacao-73_medicamentos.xlsx`

O modelo base pode ser `.xlsm`, mas o arquivo gerado é **sempre `.xlsx`** (sem macros, compatível com Google Sheets).

## Onde colocar o arquivo

Caminho padrão (primeiro que existir):

```
template_packages/excell_base/relatorio_base_excell.xlsm   ← modelo oficial (Mapa de Apuração)
template_packages/excell_base/relatorio_saida_excell.xlsx  ← legado
template_packages/pncp/cotacao_pesquisa_precos.xlsx        ← fallback dev
```

No container Docker: `/app/template_packages/excell_base/relatorio_base_excell.xlsm`

Override por variável de ambiente / settings:

```
PNCP_COTACAO_EXCEL_TEMPLATE=/caminho/absoluto/modelo.xlsx
```

## Mapa de células no modelo oficial

| Célula | Slot |
|--------|------|
| `A2` | `{PREFEITURA_ESTADO}` |
| `A3` | `{CNPJ}` |
| `A4` | `{TELEFONE}` |
| `A5` | `Departamento: {DEPARTAMENTO}` |
| `A9` | `Relatório gerado em {DATA_HORARIO_GERACAO}` |
| `A14` | `{ID_ITEM}` |
| `B14` | `{NOME_ITEM}` |
| `C14` | `{UNIDADE}` |
| `D14` | `{QUANTIDADE}` |
| `E14` | `{COTACOES_VALIDAS}` |
| `F14` | `{VALOR_MEDIO}` |
| `G14` | `{VALOR_TOTAL_HOMOLOGADO}` |
| `B16` | `{OBSERVACOES}` |
| `B18` | `{VALOR_EXTENSO}` |
| `A20` | `{PREFEITURA_E_DATA}` |
| `A23` | `{RESPONSAVEL_PESQUISA_PREÇOS}` |

Linha 14 é replicada para cada item da cotação. As linhas de rodapé (observações, valor extenso, data, assinatura) **permanecem abaixo dos itens**, com merges e alturas preservados.

## Slots globais (uma vez na planilha)

| Slot | Origem no sistema | Exemplo |
|------|-------------------|---------|
| `{DATA_HORARIO_GERACAO}` | Data/hora do **download** (`timezone.now()`) | `08/07/2026 às 20:15` |
| `{PREFEITURA_E_DATA}` | Prefeitura vinculada à cotação/usuário + data da pesquisa | `Prefeitura Municipal de Campinas (SP), 05/07/2026` |
| `{PREFEITURA_ESTADO}` | Só prefeitura + UF (sem data) | `Prefeitura Municipal de Campinas (SP)` |
| `{RESPONSAVEL_PESQUISA_PREÇOS}` | Nome de quem criou a cotação (`criado_por_nome` ou usuário) | `Maria Silva` |
| `{VALOR_EXTENSO}` | Soma estimada dos itens, por extenso | `mil duzentos reais e cinquenta centavos` |
| `{CNPJ}` | Preenchido no modal de exportação; fixo por usuário | `01.067.271/0001-27` |
| `{TELEFONE}` | Preenchido no modal de exportação; fixo por usuário | `(64) 99298-5174` |
| `{DEPARTAMENTO}` | Preenchido no modal; fixo só nesta cotação | `Compras` |
| `{OBSERVACOES}` | Preenchido no modal; fixo só nesta cotação | `Prazo de entrega 15 dias` |

### Regras de origem

- **Prefeitura:** `texto_orgao_capa_prefeitura_cotacao` — prefeitura da cotação ou do usuário; fallback `—`.
- **Responsável:** snapshot `criado_por_nome` → nome completo do usuário → e-mail.
- **Valor extenso:** soma por item de `valor_total_refletido` → `valor_total` → `valor_unitario` (mesma regra da tela de cotação), via `valor_monetario_por_extenso`.

### Aliases aceitos

| Alias | Slot canônico |
|-------|----------------|
| `{RESPONSAVEL_PESQUISA_PRECOS}` | `{RESPONSAVEL_PESQUISA_PREÇOS}` |
| `{VALOR_POR_EXTENSO}` | `{VALOR_EXTENSO}` |

## Slots por item (linha-modelo)

Coloque **uma linha** na planilha com estes placeholders; o sistema **replica a linha** para cada item da cotação.

| Slot | Origem | Exemplo |
|------|--------|---------|
| `{ID_ITEM}` | `numero_item` da sessão; se vazio, `id` interno | `22` |
| `{NOME_ITEM}` | `descricao_item` | `Álcool gel 500 ml` |
| `{UNIDADE}` | `unidade_medida_refletida` → `unidade_medida` | `UN` |
| `{QUANTIDADE}` | `quantidade` do item | `100` |
| `{COTACOES_VALIDAS}` | Soma das cotações nas 5 fontes (Art. 5º) | `3` |
| `{VALOR_MEDIO}` | Mesma regra da coluna **Média de preço** na tela (`valor_unitario_refletido` → fallbacks) | `R$ 6,34` |
| `{VALOR_TOTAL_HOMOLOGADO}` | `valor_total_refletido` → `valor_total` → `valor_unitario` | `R$ 634,00` |

A linha-modelo pode misturar slots de item com texto fixo e slots globais (globais são re-substituídos em cada linha).

## Fluxo técnico

1. `GET /api/pncp/cotacoes/research/sessions/<id>/export/xlsx`
2. Se existir planilha-modelo → `render_cotacao_excel_from_template`
3. Senão → exportação tabular legado (abas Resumo / Itens / Cotações)

Código: `backend/app/services/pncp_cotacao_excel_template.py`

## Auditoria do XLSM recebido

Após colocar o arquivo no caminho padrão:

```python
from pathlib import Path
from backend.app.services.pncp_cotacao_excel_template import list_slots_in_workbook

print(list_slots_in_workbook(Path("backend/template_packages/pncp/cotacao_pesquisa_precos.xlsm")))
```

Confirme que todas as abas listadas contêm os slots esperados.

## Macros (.xlsm)

O export usa `openpyxl` com `keep_vba=True` para `.xlsm`. Macros existentes no modelo são preservadas; o preenchimento é só substituição de texto nas células.

## Checklist ao receber o modelo

1. Copiar para `backend/template_packages/pncp/cotacao_pesquisa_precos.xlsm`
2. Rodar auditoria de slots (`list_slots_in_workbook`)
3. Exportar uma cotação de teste e validar capa + linhas de itens
4. Rebuild do container `backend` em produção
