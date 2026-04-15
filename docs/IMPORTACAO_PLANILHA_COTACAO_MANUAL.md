# Importacao de Planilha - Cotacao Manual (PNCP)

Este documento define os campos aceitos na importacao de planilha para preencher itens da cotacao manualmente.

## Endpoint

- `POST /api/pncp/cotacoes/research/sessions/<sessao_id>/items/import`
- Campo de arquivo: `arquivo`
- Campo opcional de mapeamento: `column_map` (JSON)

## Formatos aceitos

- `.csv`
- `.xlsx` (Excel)
- Google Sheets: exportar como CSV/XLSX e enviar no mesmo endpoint

## Planilhas modelo padronizadas

Modelos prontos para download no frontend:

- Excel (`.xlsx`): `/modelos/cotacao-manual-modelo.xlsx`
- Google Sheets (`.csv`): `/modelos/cotacao-manual-modelo.csv`

Observacao:

- O modelo CSV pode ser importado diretamente no Google Sheets (`Arquivo > Importar > Upload`).
- Os dois modelos seguem a mesma ordem de colunas canonicas desta documentacao.

## IDs de coluna obrigatorios

As colunas abaixo devem existir (diretamente ou via alias/mapeamento):

- `descricao_item`
- `quantidade`
- `unidade_medida`
- `valor_unitario`

## IDs de coluna opcionais

- `numero_item`
- `numero_pncp`
- `ano_compra`
- `sequencial_compra`
- `orgao`
- `municipio`
- `uf`
- `modalidade`

Ordem usada no modelo padrao:

1. `descricao_item`
2. `quantidade`
3. `unidade_medida`
4. `valor_unitario`
5. `numero_item`
6. `numero_pncp`
7. `ano_compra`
8. `sequencial_compra`
9. `orgao`
10. `municipio`
11. `uf`
12. `modalidade`

## Aliases aceitos (normalizacao automatica)

Exemplos de alias que sao convertidos automaticamente para IDs canonicos:

- `descricao` -> `descricao_item`
- `descricaoitem` -> `descricao_item`
- `qtd` -> `quantidade`
- `unidade` -> `unidade_medida`
- `valor` -> `valor_unitario`
- `valorunitario` -> `valor_unitario`
- `id_item` -> `numero_item`
- `item_id` -> `numero_item`
- `item` -> `numero_item`
- `numeropncp` -> `numero_pncp`
- `ano` -> `ano_compra`
- `sequencial` -> `sequencial_compra`

## Regras de normalizacao de cabecalho

Antes de mapear as colunas, o backend:

- converte para minusculo
- remove acentos
- troca separadores por `_` (espaco, hifen etc.)

Exemplos:

- `Descricao Item` -> `descricao_item`
- `VALOR UNITARIO` -> `valor_unitario`
- `unidade-medida` -> `unidade_medida`

## `column_map` (opcional)

Voce pode enviar um JSON para mapear IDs canonicos para o nome da coluna da planilha.

Exemplo:

```json
{
  "descricao_item": "descricao_produto",
  "quantidade": "qtd",
  "unidade_medida": "und",
  "valor_unitario": "valor"
}
```

## Comportamento de validacao

- Se o arquivo estiver vazio, a API retorna erro.
- Linhas sem `descricao_item` sao consideradas invalidas.
- A resposta inclui:
  - `itens_inseridos`
  - `linhas_arquivo`
  - `linhas_invalidas`
  - `errors` (ate 20 erros de linha)
  - `required_column_ids`

## Observacoes

- Itens sao inseridos na cotacao em lote (bulk create).
- Cotacoes encerradas nao permitem importacao.
- Importacao so e permitida para cotacoes do usuario autenticado.
