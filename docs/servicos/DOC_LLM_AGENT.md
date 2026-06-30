# LLM Agent (FastAPI)

Documentação do **llm_agent**: interpretação de prompt livre, geração de estrutura de documentos (seções), estrutura de cláusulas hierárquicas e registro de seções.

---

## 1. Base URL e porta

- **Base**: `http://localhost:8003` (ou valor de `LLM_AGENT_BASE_URL` no RAG).
- **Prefixo das rotas**: `/api/agent`.
- **Inicialização**: `llm_agent/app/main.py` → `create_app()` em `llm_agent/app/api.py`.

---

## 2. Endpoints

| Método | URL | Descrição |
|--------|-----|-----------|
| POST | `/api/agent/registry` | Atualizar registro de seções (JSON persistido em arquivo) |
| POST | `/api/agent/structure-from-prompt` | Prompt livre → interpretador → estrutura + context + especificações |
| POST | `/api/agent/structure` | Gerar estrutura a partir de StructureRequest (document_type, context, catalog) |
| POST | `/api/agent/clause-structure` | Gerar árvore de cláusulas (esqueleto, sem texto jurídico) |

---

## 3. Contratos principais

### 3.1 POST `/api/agent/registry`

- **Body**: `SectionsRegistry`: `catalog_id`, `catalog_version`, `entries` (lista de `RegistrySectionEntry`).
- **Segurança**: Opcionalmente exigir header `X-Update-Key` (valor de `REGISTRY_UPDATE_KEY`); se vazio, endpoint pode recusar atualização conforme implementação.
- **Response**: `{"ok": true, "message": "Registro de seções atualizado."}` ou 500.

### 3.2 POST `/api/agent/structure-from-prompt`

- **Body**: `PromptStructureRequest`: `user_prompt` (obrigatório).
- **Fluxo**: Interpreta prompt → obtém `document_type`, `context`, `especificacoes` → chama `generate_structure` → retorna estrutura + context + especificacoes (para o RAG usar).
- **Response**: JSON com estrutura (root_sections, document_type), `context` (objeto, orgao, modalidade), `especificacoes` (listas/tabelas ou null), `section_matches` (quando há catálogo e user_prompt).

### 3.3 POST `/api/agent/structure`

- **Body**: `StructureRequest`: `document_type` (obrigatório), `context` (ContextoBasico: objeto obrigatório, orgao, modalidade, extras), `sections_catalog` (opcional), `user_prompt` (opcional), `especificacoes` (opcional).
- **Response**: `StructureResponse`: `ok`, `structure` (DocumentStructure: document_type, root_sections), `error`, `retries`, `section_matches` (opcional).

### 3.4 POST `/api/agent/clause-structure`

- **Body**: `ClauseStructureRequest`: `document_type`, `context` (dict livre), `section_key` (opcional), `base_description` (opcional).
- **Response**: `ClauseStructureResponse`: `ok`, `root_clauses` (lista de `ClauseNode`), `error`, `retries`. Cláusulas são esqueleto (logical_id, title, status, scope, version, children), sem texto jurídico.

---

## 4. Schemas principais (resumo)

- **ContextoBasico**: `objeto`, `orgao`, `modalidade`, `extras`.
- **EspecificacoesDocumento**: `listas` (dict chave → lista de itens), `tabelas` (dict chave → TabelaEspecificacao: colunas, linhas_sugeridas).
- **SectionNode**: `key`, `title`, `required`, `content_type` (text|table|list), `table_schema` (se table), `children` (lista de SectionNode).
- **DocumentStructure**: `document_type`, `root_sections` (lista de SectionNode).
- **ClauseNode**: `logical_id`, `title` (opcional), `status`, `scope`, `version`, `children`.
- **SectionCatalogEntry / RegistrySectionEntry**: key, title, document_types, categories, description, content_type, required, table_schema, conditional_rules, applicability_scope, version, is_active/enabled, parent_key.

---

## 5. Prompts (llm_agent/app/prompts.py)

- **INTERPRETER_SYSTEM_PROMPT**: Interpreta texto livre e extrai JSON com `document_type`, `context` (objeto obrigatório, orgao, modalidade), `especificacoes` (listas/tabelas só quando o usuário indicar). Saída apenas JSON.
- **build_interpreter_user_prompt(user_prompt)**: Envolve o texto do usuário na instrução do interpretador.
- **BASE_SYSTEM_PROMPT**: Geração apenas de estrutura (seções, content_type, table_schema); não redige texto jurídico.
- **DOCUMENT_TYPE_HINTS**: Dicas por tipo (termo_referencia, estudo_tecnico_preliminar, documento_formalizacao_demanda): seções base, frequentes e condicionais.
- **build_system_prompt(document_type)**: Base + hint do tipo.
- **build_user_prompt(document_type, context)**: Monta user prompt para estrutura com contexto.
- **CATALOG_SELECTION_SYSTEM_PROMPT** / **CATALOG_SELECTION_WITH_MATCHES_SYSTEM_PROMPT**: Seleção/ordenação de seções a partir do catálogo; opcionalmente section_matches (key, user_phrase, confidence).
- **build_catalog_selection_user_prompt(...)**: User prompt para seleção de catálogo.
- **CLAUSE_COMPOSITION_SYSTEM_PROMPT** (prompts.py): Composição jurídica controlada (variações de cláusulas registradas); usado quando o sistema gera texto de cláusulas a partir de base + RAG.
- **DOCUMENT_CLAUSE_STRUCTURE_SYSTEM_PROMPT**: Estrutura hierárquica de cláusulas/subcláusulas (sem corpo de texto).

---

## 6. Contextos

- **Interpretador**: Recebe apenas `user_prompt`; o contexto (objeto, orgao, modalidade) é extraído pelo LLM e devolvido no JSON.
- **Estrutura**: Recebe `context` (ContextoBasico) no StructureRequest ou derivado do interpretador; pode receber `sections_catalog` e `user_prompt` para fluxo com catálogo e section_matches.
- **Clause-structure**: Recebe `context` como dict livre (objeto, modalidade, órgão, extras, etc.) e opcionalmente `section_key`, `base_description`.

O agente chama a orquestração LLM (llm_api) em `LLM_ORCHESTRATION_BASE_URL` + `LLM_ORCHESTRATION_GENERATE_PATH` (POST /api/llm/generate). Timeout e retries: `AGENT_TIMEOUT`, `AGENT_MAX_RETRIES`. Registro de seções: arquivo em `SECTIONS_REGISTRY_PATH`.

---

## 7. Prompts de teste

- **Structure-from-prompt**:  
  `POST /api/agent/structure-from-prompt`  
  Body: `{"user_prompt": "Gerar termo de referência para aquisição de material de escritório para a Secretaria de Educação, pregão eletrônico"}`

- **Structure (com contexto explícito)**:  
  `POST /api/agent/structure`  
  Body: `{"document_type": "termo_referencia", "context": {"objeto": "serviços de limpeza", "orgao": "Secretaria de Obras", "modalidade": "pregão eletrônico"}, "especificacoes": null}`

- **Structure com especificações**:  
  Body: `{"document_type": "estudo_tecnico_preliminar", "context": {"objeto": "coleta seletiva"}, "especificacoes": {"listas": {"equipamentos": ["caminhão", "contêineres"]}, "tabelas": {"estimativa_custos": {"colunas": ["Item", "Quantidade", "Valor"]}}}}`

- **Clause-structure**:  
  `POST /api/agent/clause-structure`  
  Body: `{"document_type": "termo_referencia", "context": {"objeto": "aquisição de equipamentos"}, "base_description": "cláusula de garantias"}`

- **Registry**:  
  `POST /api/agent/registry`  
  Body: JSON completo do registro (catalog_id, catalog_version, entries com key, title, document_types, content_type, etc.).

---

## 8. O que o LLM Agent FAZ

- Interpreta prompt livre e extrai document_type, context e especificacoes (listas/tabelas) em JSON.
- Gera estrutura de documento (root_sections com key, title, content_type, table_schema, children) sem texto jurídico.
- Com catálogo: seleciona e ordena seções do catálogo; pode devolver section_matches (pedido ↔ seção com confidence).
- Gera estrutura hierárquica de cláusulas (ClauseNode) sem texto, para uso posterior por RAG/composição.
- Atualiza registro de seções persistido em arquivo (registry).

---

## 9. O que o LLM Agent NÃO FAZ

- Não gera texto de cláusulas (apenas estrutura); a geração de texto é feita no RAG (document_generator) usando prompts de composição.
- Não faz retrieval (RAG); apenas chama o llm_api (generate).
- Não persiste documentos nem usuários; apenas estrutura e registro de seções.
- Não valida conformidade com lei (isso é RAG check-compliance / analyze-document).

---

## 10. Possíveis melhorias

- Endpoint de “composição de cláusula” (ClauseCompositionRequest/Response) que chame LLM com CLAUSE_COMPOSITION_SYSTEM_PROMPT e RAG snippets (hoje a composição está no document_generator do RAG).
- Retry com re-parsing quando o interpretador devolver JSON inválido (já existe AGENT_MAX_RETRIES para estrutura).
- Documentar formato exato do sections_registry.json e exemplos de conditional_rules / applicability_scope.
- Suporte a document_type customizado (além de termo_referencia, etp, dfd) nos hints.
- Cache da estrutura por (document_type, hash(context)) para evitar reprocessamento idêntico.
