# Mapeamento de slots — export Excel da cotação PNCP

Planilha-modelo (`.xlsx` ou `.xlsm`) com placeholders `{SLOT}`.
O backend substitui os valores ao exportar a cotação.

## Nomenclatura do arquivo exportado

Mesmo padrão do PDF de relatório:

`docmaster-pesquisador-pncp_{usuario}_{YYYYMMDD-HHMM}_cotacao-{id}_{titulo}.xlsx`

Exemplo: `docmaster-pesquisador-pncp_marcelo-faria_20260706-1251_cotacao-73_medicamentos.xlsx`

O modelo pode ser `.xlsm`, mas o arquivo gerado é **sempre `.xlsx`** (sem macros).

## Onde colocar o arquivo

Caminho padrão (primeiro que existir):

```
backend/template_packages/pncp/cotacao_pesquisa_precos.xlsm
backend/template_packages/pncp/cotacao_pesquisa_precos.xlsx
```

Override por variável de ambiente / settings:

```
PNCP_COTACAO_EXCEL_TEMPLATE=/caminho/absoluto/modelo.xlsm
```

## Slots globais (uma vez na planilha)

| Slot | Origem no sistema | Exemplo |
|------|-------------------|---------|
| `{DATA_HORARIO_GERACAO}` | Data/hora do **download** (`timezone.now()`) | `08/07/2026 às 20:15` |
| `{PREFEITURA_E_DATA}` | Prefeitura vinculada à cotação/usuário + data da pesquisa | `Prefeitura Municipal de Campinas (SP), 05/07/2026` |
| `{PREFEITURA_ESTADO}` | Só prefeitura + UF (sem data) | `Prefeitura Municipal de Campinas (SP)` |
| `{RESPONSAVEL_PESQUISA_PREÇOS}` | Nome de quem criou a cotação (`criado_por_nome` ou usuário) | `Maria Silva` |
| `{VALOR_EXTENSO}` | Soma estimada dos itens, por extenso | `mil duzentos reais e cinquenta centavos` |

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
