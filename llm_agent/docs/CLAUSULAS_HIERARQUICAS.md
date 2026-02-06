# Modelo de cláusulas hierárquicas (estrutura e modificação de documentos)

Este documento descreve o **contrato conceitual** para quando o sistema estruturar, analisar ou modificar documentos no nível de **cláusulas** (não apenas seções/esqueleto). O prompt canônico está em `prompts.DOCUMENT_CLAUSE_STRUCTURE_SYSTEM_PROMPT`.

---

## Princípios

- **Documentos = cláusulas hierárquicas**: cada cláusula pode ter subcláusulas numeradas (5, 5.1, 5.2, 5.3); cada nível tem significado jurídico próprio. Nada é “texto solto”.
- **Cláusula como componente**: sempre pertence a uma hierarquia, a um contexto legal e a uma versão. Trate-as como blocos estruturais, não como parágrafos.

---

## Atributos de uma cláusula

| Atributo | Descrição |
|----------|-----------|
| **Identificador lógico** | Estável (ex.: `RESPONSABILIDADES_CONTRATADA`). Usado para referência e versionamento, não para exibição. |
| **Número exibido** | Dinâmico (ex.: 5, 5.1, 5.2). Pode mudar conforme a composição do documento; deve ser recalculado após alterações. |
| **Escopo de validade** | Federal, estadual, municipal ou específico por município. |
| **Versão** | Para rastreabilidade e histórico. |
| **Status** | Ativa, substituída, revogada. |
| **Dependências contextuais** | Tipo de contrato, natureza das partes, legislação aplicável. |

---

## Subcláusulas

- São **semanticamente dependentes** da cláusula pai.
- Não mover, remover ou alterar subcláusulas sem avaliar o **impacto jurídico e estrutural** na cláusula principal.

---

## Modificação de documentos

1. **Identificar** cláusulas pelo **identificador lógico**, não só pelo número.
2. **Classificar a mudança**: alteração de conteúdo, substituição de versão ou exclusão.
3. **Preservar histórico**: nunca sobrescrever sem versionamento.
4. **Recalcular** a numeração exibida após adições ou remoções.
5. **Garantir coerência** textual entre cláusulas irmãs (ex.: 5.1 a 5.4).

---

## Tipos de cláusulas por escopo

- **Globais**: válidas para qualquer localidade.
- **Condicionais**: válidas apenas sob certos critérios.
- **Específicas**: exclusivas de um município, estado ou cenário.

Uma cláusula municipal/específica pode **complementar**, **substituir** ou **coexistir** com uma global (quando explicitamente indicado). Em **conflito**, priorizar a mais específica e **registrar a decisão**. Nunca gerar contradições entre global e específica.

---

## Adição de cláusula

- Definir se é **bloco principal** ou **subcláusula**.
- Atribuir **identificador lógico** claro.
- Definir **nível hierárquico**.
- Verificar se é necessário **ajustar cláusulas irmãs**.

---

## Remoção de cláusula

- Avaliar o que fazer com **subcláusulas**: remover, migrar ou invalidar.
- **Não deixar referências quebradas** no documento.

---

## Objetivo do agente

Manter a **integridade estrutural, lógica e legal** do documento como um **sistema vivo**, versionável e recombinável — não apenas gerar texto jurídico.

---

## Uso no projeto

- O **llm_agent** atual trabalha no nível de **seções** (esqueleto); não gerencia ainda cláusulas numeradas, versões nem escopo por cláusula.
- Este modelo serve de referência para a **camada de composição/edição** (RAG, banco de cláusulas, versionamento) quando for implementada. O prompt `DOCUMENT_CLAUSE_STRUCTURE_SYSTEM_PROMPT` deve ser usado por qualquer serviço ou agente que estruture, analise ou modifique documentos no nível de cláusulas.
