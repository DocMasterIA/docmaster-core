# Seções maleáveis: categorias e matching por intenção

## Objetivo

- **Categorias/padrão**: dependendo do “tipo” do documento (ex.: termo de referência para **compra de medicamentos**), o sistema pode incluir seções adicionais cadastradas para essa categoria.
- **Matching por intenção**: o pedido do usuário raramente bate com o título exato da seção; a IA escolhe, na lista permitida, as seções que **melhor correspondem** à intenção (usando também a descrição).

## Campos no registro (`sections_registry.json`)

### `categories` (opcional)

Lista de padrões/categorias do documento. Ex.: `["compra_medicamentos", "obras", "tic"]`.

- Quando o **contexto** da requisição trouxer `extras.categoria` ou `extras.document_pattern` (string ou lista), só entram na lista elegível as seções:
  - **sem** `categories`, ou
  - com pelo menos uma categoria **igual** à informada no contexto.
- Quando o contexto **não** informar categoria, **todas** as seções que passam em tipo de documento, escopo e regras condicionais entram (não se filtra por categoria).

Exemplo de contexto para “TR compra de medicamentos”:

```json
"context": {
  "objeto": "Aquisição de medicamentos para rede municipal",
  "extras": { "categoria": "compra_medicamentos" }
}
```

Seções com `"categories": ["compra_medicamentos"]` (e que batem com tipo de documento, escopo e condições) passam a ser elegíveis.

### `description` (opcional)

Texto curto usado pela IA para **mapear intenção** (ex.: “Especificações para aquisição de medicamentos e controle”).

- No prompt de seleção, a IA vê **key**, **title** e **description**.
- Assim, mesmo que o usuário peça “cláusula de aquisição de medicamentos” ou outro título, a IA pode escolher a seção cuja descrição (e título) melhor correspondem.

## Exemplo de entrada no registry

```json
{
  "key": "especificacoes_medicamentos",
  "title": "Das Especificações para Aquisição de Medicamentos",
  "document_types": ["termo_referencia"],
  "categories": ["compra_medicamentos", "saude"],
  "description": "Especificações para aquisição de medicamentos, controle e armazenamento.",
  "content_type": "text",
  "required": false,
  "enabled": true,
  "version": "1",
  "parent_key": null
}
```

## Fluxo resumido

1. **Elegíveis**: filtro por tipo de documento, escopo, regras condicionais e, **se** houver `extras.categoria` ou `extras.document_pattern`, por categoria (só entram seções sem categoria ou com categoria no contexto).
2. **Seleção**: a IA recebe a lista (key, title, description) e o contexto; devolve apenas **keys** dessa lista, na ordem desejada, escolhendo por **intenção** (não precisa bater título exato).
3. **Esqueleto**: a estrutura final usa só seções do catálogo; decisões de layout/funcionamento de cada seção ficam para etapa futura.

## Definição posterior

- **Padrão de arquivo**: como inferir ou definir `document_pattern`/`categoria` (ex.: por objeto, por órgão, por template) será definido depois; o sistema já aceita esses campos em `context.extras`.
- **Comportamento de cada seção/cláusula**: (tabela vs texto, colunas, etc.) também fica para etapa futura.
