# DOCUMENT_CLAUSE_STRUCTURE_SYSTEM_PROMPT — Explicação e fluxo esperado

## O que ele está fazendo **hoje**

**Nada no runtime.** O `DOCUMENT_CLAUSE_STRUCTURE_SYSTEM_PROMPT` é apenas um **texto de referência** guardado em `llm_agent/app/prompts.py`. Nenhum endpoint, nenhum fluxo do llm_agent o utiliza atualmente. Ele **não** é enviado ao LLM, **não** gera resposta e **não** aparece em nenhum curl que você rode hoje.

Ele existe para:
- Documentar o **contrato conceitual** de como o sistema deve tratar **cláusulas** (identificador lógico, numeração, versão, escopo, hierarquia).
- Servir de **prompt de sistema** quando no futuro existir um agente ou serviço que **estruture, analise ou modifique** documentos no nível de **cláusulas** (não só no nível de seções/esqueleto).

Ou seja: hoje é **especificação**, não **código em uso**.

---

## O que o prompt **define** (contrato conceitual)

O texto do prompt impõe as seguintes regras ao agente que um dia o usar:

1. **Documento = cláusulas hierárquicas**  
   Cada cláusula pode ter subcláusulas numeradas (5, 5.1, 5.2, 5.3). Nada é “texto solto”; tudo pertence a uma hierarquia, contexto legal e versão.

2. **Atributos de cada cláusula**  
   - Identificador lógico estável (ex.: `RESPONSABILIDADES_CONTRATADA`).  
   - Número exibido dinâmico (5, 5.1, 5.2) — pode mudar ao recompor o documento.  
   - Escopo (federal, estadual, municipal, por município).  
   - Versão e status (ativa, substituída, revogada).  
   - Dependências contextuais (tipo de contrato, partes, legislação).

3. **Subcláusulas**  
   Sempre dependentes do pai. Não mover/remover/alterar sem avaliar impacto na cláusula principal.

4. **Modificação de documento**  
   - Identificar cláusulas pelo **identificador lógico**, não só pelo número.  
   - Classificar mudança: alteração de conteúdo, substituição de versão ou exclusão.  
   - Nunca sobrescrever sem versionamento; recalcular numeração; manter coerência entre irmãs.

5. **Tipos de cláusula**  
   Globais, condicionais ou específicas (municipal/estado). Em conflito, priorizar a mais específica e registrar a decisão.

6. **Adição**  
   Definir se é bloco principal ou subcláusula, atribuir id lógico, nível hierárquico e verificar impacto em irmãs.

7. **Remoção**  
   Decidir o que fazer com subcláusulas (remover, migrar, invalidar) e não deixar referências quebradas.

8. **Objetivo**  
   Manter integridade estrutural, lógica e legal; cláusulas como **componentes estruturais**, não parágrafos soltos.

---

## Fluxo **esperado** (quando o prompt for usado no futuro)

Quando existir um serviço/agente de **estrutura ou modificação no nível de cláusulas**, o fluxo esperado seria algo como abaixo. Isso **não** está implementado hoje; é o desenho alvo.

### Entrada de dados (exemplo conceitual)

O serviço receberia, por exemplo:

- **Documento atual** (ou seu id): estrutura de cláusulas com identificador lógico, numeração exibida, versão, escopo.
- **Pedido de modificação**: “Adicionar subcláusula em RESPONSABILIDADES_CONTRATADA sobre multa por atraso” ou “Substituir cláusula 5.2 pela versão 2” ou “Remover cláusula PENALIDADES e migrar 5.3 para 6.1”.

Exemplo de body (hipotético):

```json
{
  "document_id": "doc-uuid-123",
  "action": "add_subclause",
  "parent_logical_id": "RESPONSABILIDADES_CONTRATADA",
  "new_clause": {
    "logical_id": "MULTA_ATRASO",
    "scope": "global",
    "version": "1",
    "content_summary": "Multa por atraso na entrega conforme art. X"
  },
  "context": {
    "tipo_contrato": "prestacao_servicos",
    "municipio": "São Paulo"
  }
}
```

Ou, para **analisar** um documento e devolver a estrutura de cláusulas:

```json
{
  "action": "structure",
  "document_type": "termo_referencia",
  "context": { "objeto": "...", "orgao": "...", "extras": {} },
  "existing_clauses": []
}
```

### Papel do prompt

O **DOCUMENT_CLAUSE_STRUCTURE_SYSTEM_PROMPT** seria usado como **system prompt** na chamada ao LLM que:

- Gera ou atualiza a **estrutura de cláusulas** (identificadores lógicos, hierarquia, numeração exibida, escopo, versão).  
- Ou analisa um documento e devolve uma representação dessas cláusulas.  
- Ou calcula a **diff** de uma modificação (o que adicionar, remover, renumerar) respeitando as regras do prompt.

A **entrada** (document_id, action, new_clause, context, etc.) viria no **user prompt** ou em payload estruturado; a **saída** seria um JSON que descreve a nova estrutura (lista de cláusulas com logical_id, display_number, parent_id, version, scope, status).

### Exemplo de curl (hipotético, futuro)

```bash
# Exemplo de como seria um endpoint que USA o DOCUMENT_CLAUSE_STRUCTURE_SYSTEM_PROMPT
# Este endpoint NÃO existe hoje no llm_agent.

curl -s -X POST http://localhost:8003/api/agent/document-clause-structure \
  -H "Content-Type: application/json" \
  -d '{
    "action": "structure",
    "document_type": "termo_referencia",
    "context": {
      "objeto": "Prestação de serviços de TI",
      "orgao": "Secretaria de Educação",
      "extras": { "municipio": "São Paulo" }
    },
    "clause_catalog": [
      {
        "logical_id": "OBJETO",
        "title": "Do Objeto",
        "scope": "global",
        "version": "1"
      },
      {
        "logical_id": "RESPONSABILIDADES_CONTRATADA",
        "title": "Das Responsabilidades da Contratada",
        "scope": "global",
        "version": "1"
      }
    ]
  }' | jq .
```

### Saída esperada (hipotética)

Algo nesse formato (estrutura de cláusulas com id lógico, numeração exibida, hierarquia), **não** o formato atual de `StructureResponse` (que é só seções/esqueleto):

```json
{
  "ok": true,
  "document_type": "termo_referencia",
  "clauses": [
    {
      "logical_id": "OBJETO",
      "display_number": "1",
      "title": "Do Objeto",
      "scope": "global",
      "version": "1",
      "status": "active",
      "parent_logical_id": null,
      "children": []
    },
    {
      "logical_id": "RESPONSABILIDADES_CONTRATADA",
      "display_number": "2",
      "title": "Das Responsabilidades da Contratada",
      "scope": "global",
      "version": "1",
      "status": "active",
      "parent_logical_id": null,
      "children": [
        {
          "logical_id": "RESPONSABILIDADES_ENTREGA",
          "display_number": "2.1",
          "title": "Entrega",
          "parent_logical_id": "RESPONSABILIDADES_CONTRATADA",
          "children": []
        }
      ]
    }
  ],
  "numbering_recomputed": true
}
```

Hoje o llm_agent **não** devolve `clauses` com `logical_id` / `display_number` / `version` / `scope`; devolve `structure.root_sections` com `key`, `title`, `required`, `content_type`, etc. O formato acima é o **alvo** quando o prompt for usado em um fluxo de cláusulas.

---

## Comparação: hoje (llm_agent) vs. fluxo com DOCUMENT_CLAUSE_STRUCTURE

| Aspecto | Hoje (llm_agent) | Fluxo esperado com o prompt |
|--------|--------------------------------|-----------------------------|
| Nível | **Seções** (esqueleto): key, title, required, content_type, children. | **Cláusulas**: logical_id, display_number, version, scope, status, hierarquia. |
| Numeração | Não há “5”, “5.1”; só ordem na lista. | Numeração exibida dinâmica (5, 5.1, 5.2), recalculada após mudanças. |
| Versão / status | Não existem por seção. | Cada cláusula tem versão e status (ativa, substituída, revogada). |
| Escopo | Categoria/context no filtro de **seções** elegíveis. | Escopo por **cláusula** (federal, estadual, municipal, específico). |
| Modificação | Não há “modificar documento existente”. | Adicionar/remover/substituir cláusula; versionar; renumerar; sem referências quebradas. |
| Uso do prompt | **Nenhum**; prompt não é chamado. | Seria o **system prompt** do LLM nesse fluxo. |

---

## Resumo

- **Hoje:** `DOCUMENT_CLAUSE_STRUCTURE_SYSTEM_PROMPT` só existe como constante em `prompts.py` e como referência em `docs/CLAUSULAS_HIERARQUICAS.md`. Nenhum curl, nenhum endpoint e nenhum fluxo do llm_agent o utilizam. Não há entrada nem saída associadas a ele no código atual.
- **Conteúdo:** O prompt define o **comportamento** desejado de um agente que trabalhe com cláusulas hierárquicas (id lógico, numeração, versão, escopo, modificação com versionamento e coerência).
- **Fluxo esperado (futuro):** Um serviço que receba documento + ação de modificação (ou pedido de estrutura), chame o LLM com esse prompt como system e payload estruturado como user, e devolva uma estrutura de cláusulas (com logical_id, display_number, version, scope, etc.) em vez de só a lista de seções que o llm_agent retorna hoje. O exemplo de curl e a saída esperada acima são **ilustrativos** desse fluxo futuro, não de algo que já exista no llm_agent.
