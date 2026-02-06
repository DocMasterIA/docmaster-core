# llm_agent — Agente de Estrutura Documental

Resumo detalhado do funcionamento do módulo **llm_agent**: geração da **estrutura lógica** (esqueleto) de documentos de licitação pública, sem redação de texto jurídico. O agente não inventa seções; quando há catálogo/registro, apenas **seleciona e ordena** seções previamente cadastradas.

---

## 1. Objetivo

- Produzir um **esqueleto** do documento em JSON: lista de seções (key, title, required, content_type, table_schema quando aplicável, children).
- **Não** redigir cláusulas, fundamentos legais nem conteúdo final.
- Integrar com o módulo de orquestração LLM (**llm_api**), que por sua vez chama o modelo (ex.: Ollama).
- Permitir dois modos de operação:
  - **Com catálogo/registro**: seções vêm de um cadastro; a IA só escolhe quais incluir e em que ordem.
  - **Sem catálogo**: a IA gera a estrutura a partir de dicas (hints) por tipo de documento, com fallback para estrutura mínima em caso de falha.

---

## 2. Arquitetura

```
                    ┌─────────────────┐
                    │   Cliente       │
                    │ (Django, curl)  │
                    └────────┬────────┘
                             │
         POST /api/agent/structure
         POST /api/agent/structure-from-prompt
         POST /api/agent/registry (atualizar registro)
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         llm_agent (FastAPI, porta 8003)                 │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ api.py      │  │ agent.py    │  │ registry.py  │  │ catalog_     │   │
│  │ (rotas)     │──│ (orquestra  │──│ (carrega/    │  │ filter.py    │   │
│  │             │  │  fluxo)     │  │  salva JSON) │  │ (elegíveis)  │   │
│  └─────────────┘  └──────┬──────┘  └──────────────┘  └──────────────┘   │
│                          │                                              │
│  ┌─────────────┐  ┌──────┴──────┐  ┌──────────────┐                     │
│  │ prompts.py  │  │ client.py   │  │ schemas.py   │                     │
│  │ (sistema +  │  │ (HTTP →     │  │ (request/    │                     │
│  │  usuário)   │  │  llm_api)   │  │  response)   │                     │
│  └─────────────┘  └──────┬──────┘  └──────────────┘                     │
└──────────────────────────┼──────────────────────────────────────────────┘
                           │
                           ▼
                    ┌─────────────────┐
                    │ llm_api (:8002) │  →  Ollama (modelo)
                    └─────────────────┘
```

- **api.py**: expõe os endpoints sob `/api/agent/`.
- **agent.py**: decide o fluxo (catálogo vs. hints), monta payloads, chama o LLM, parseia respostas e monta `DocumentStructure`.
- **client.py**: única chamada HTTP ao llm_api (`/api/llm/generate`); não fala direto com o Ollama.
- **registry.py**: lê o arquivo JSON de registro (`SECTIONS_REGISTRY_PATH`), converte para `SectionCatalog`, mantém cache; atualiza o arquivo quando recebe `POST /registry` com chave válida.
- **catalog_filter.py**: a partir de um `SectionCatalog`, tipo de documento e contexto, retorna a lista de seções **elegíveis** (filtro determinístico: tipo, escopo, regras condicionais, categoria).
- **prompts.py**: textos de sistema e construção de prompts de usuário (interpretador, geração livre, seleção a partir do catálogo).
- **schemas.py**: modelos Pydantic de entrada/saída e do catálogo versionável.

---

## 3. Endpoints

| Método e path | Descrição |
|---------------|-----------|
| **POST /api/agent/structure** | Gera a estrutura. Body: `StructureRequest` (document_type, context, opcionalmente sections_catalog). Retorno: `StructureResponse` (ok, structure, error, retries). |
| **POST /api/agent/structure-from-prompt** | Interpreta prompt livre. Body: `{ "user_prompt": "..." }`. Internamente chama o interpretador LLM → `StructureRequest` → `generate_structure`. Retorno: mesmo `StructureResponse`. |
| **POST /api/agent/registry** | Atualiza o registro de seções (arquivo JSON). Body: `SectionsRegistry` completo. Header obrigatório: `X-Update-Key` (valor deve ser o mesmo de `REGISTRY_UPDATE_KEY`). |

A API é pensada para uso interno (ex.: backend Django), não para consumo público direto.

---

## 4. Fluxo principal: `generate_structure`

1. **Catálogo**
   - Se a requisição trouxer `sections_catalog` com entradas, usa esse catálogo.
   - Senão, tenta carregar o registro em arquivo (`get_catalog_from_registry()`). Se existir e tiver `entries`, usa esse catálogo.

2. **Com catálogo**
   - Chama `filter_eligible_sections(catalog, document_type, context)` → lista de seções elegíveis.
   - Se a lista for vazia, retorna `StructureResponse` com estrutura mínima de fallback e `error` explicativo.
   - Monta o prompt de **seleção**: sistema (só pode devolver keys da lista; matching por intenção) + usuário (lista key/title/description + contexto).
   - Chama o LLM via `call_generate`. Espera um JSON `{ "section_keys": ["key1", "key2", ...] }`.
   - Valida: só aceita keys que estejam no conjunto elegível; ordem preservada.
   - Se o parse falhar ou vier vazio, usa fallback: ordem das raízes do catálogo ou todas as elegíveis.
   - Monta `DocumentStructure` com `_build_structure_from_catalog_selection`: cada key vira um `SectionNode` (key, title, required, content_type, table_schema) a partir da entrada do catálogo; hierarquia por `parent_key`.
   - Retorna `StructureResponse(ok=True, structure=...)` ou, em caso de fallback de ordem, `ok=False` com estrutura ainda assim utilizável.

3. **Sem catálogo**
   - Monta prompt com **BASE_SYSTEM_PROMPT** + **DOCUMENT_TYPE_HINTS** para o tipo de documento e envia o contexto no prompt de usuário.
   - Chama o LLM; espera um JSON com `document_type` e `root_sections` (lista de nós com key, title, required, content_type, table_schema, children).
   - Remove eventual markdown (```json ... ```) e valida com `DocumentStructure.model_validate`; aplica `_validate_semantics` (seções obrigatórias mínimas por tipo).
   - Em falha (rede, JSON inválido, validação): repete até `AGENT_MAX_RETRIES + 1` vezes.
   - Se todas falharem: retorna estrutura **mínima** para aquele tipo (`_minimal_structure_for`), com `ok=False` e `error` preenchido.

Em todos os casos a saída é **só estrutura** (esqueleto); nenhum texto jurídico é gerado neste módulo.

---

## 5. Interpretador (prompt livre → StructureRequest)

Usado pelo endpoint **structure-from-prompt**:

- Prompt de sistema: extrair **apenas** um JSON com `document_type` (snake_case) e `context` (objeto com objeto, orgao, modalidade, extras).
- Prompt de usuário: o texto livre do usuário.
- Resposta esperada: JSON válido. Em falha de parse ou rede, fallback: `document_type="termo_referencia"`, `context.objeto` = trecho do prompt (até 500 caracteres).

O resultado é um `StructureRequest` que segue para `generate_structure` como qualquer outra chamada a `/structure`.

---

## 6. Registro de seções (arquivo JSON)

- **Arquivo**: caminho definido por `SECTIONS_REGISTRY_PATH` (default: `llm_agent/data/sections_registry.json`).
- **Formato**: JSON com `catalog_id`, `catalog_version` e `entries` (lista de entradas no formato do schema **RegistrySectionEntry**).
- **Campos por entrada (resumo)**:
  - **key**, **title**: identificador estável e título.
  - **document_types**: lista de tipos (ex.: `["estudo_tecnico_preliminar", "termo_referencia"]`).
  - **categories** (opcional): padrões do documento (ex.: `["compra_medicamentos", "obras"]`); usado quando o contexto informa `extras.categoria` ou `extras.document_pattern`.
  - **description** (opcional): texto curto para a IA fazer matching por intenção (pedido em outra redação).
  - **content_type**: `"text"` | `"table"` | `"list"` (nível estrutural; decisões finas de layout ficam para RAG).
  - **required**, **status** ("optional" | "required"): obrigatoriedade estrutural.
  - **conditional_rules** (opcional): regras determinísticas de inclusão. Atalho: `{ "if": ["obra", "servico_continuado"], "if_path": "extras.tipo_objeto" }` → só elegível se o valor em `if_path` estiver em `if`.
  - **applicability_scope** (opcional): município, estado, órgão, tipo_administracao; a seção só é elegível se o contexto bater.
  - **enabled**, **version**, **effective_from**, **parent_key** (opcional).
  - **table_schema** (opcional): só quando content_type for tabela; na prática o módulo trata a maioria como texto; detalhes de layout ficam para depois.

**O que não fica no registro (ficam para a camada RAG/composição)**  
Fundamento legal, obrigatoriedade por autoridade (ex.: TCU), e demais “declarações de funcionamento” de seções/cláusulas não são declarados aqui.

- **Carregamento**: na primeira necessidade (ou após atualização), o registro é lido do disco, validado como `SectionsRegistry` e convertido para `SectionCatalog` (função `registry_entry_to_catalog_entry` para cada entrada); resultado é cacheado em memória.
- **Atualização**: `POST /api/agent/registry` com body = JSON completo do registro e header `X-Update-Key` igual a `REGISTRY_UPDATE_KEY`. O arquivo é reescrito e o cache invalidado; a próxima geração usa o novo conteúdo.

---

## 7. Filtro de seções elegíveis (`catalog_filter`)

Entrada: `SectionCatalog`, `document_type`, `ContextoBasico`.

- **Filtros aplicados (todos determinísticos)**:
  - **is_active**: só entradas com `enabled` verdadeiro.
  - **document_type**: o tipo solicitado deve estar em `entry.document_types`.
  - **applicability_scope**: se a seção tiver escopo (município, estado, órgão, tipo_administracao), o contexto deve bater (ex.: mesmo órgão, mesmo estado em `extras`).
  - **conditional_rules**: todas as regras devem ser verdadeiras para o contexto (ex.: `has_field`, `field_equals`, `field_in` em paths como `extras.tipo_objeto`).
  - **Categoria**: se o contexto tiver `extras.categoria` ou `extras.document_pattern` (string ou lista), só entram seções **sem** `categories` ou com interseção entre `entry.categories` e as categorias do contexto. Se o contexto não informar categoria, não se filtra por categoria (todas que passam nos outros filtros entram).

Saída: lista de `SectionCatalogEntry` elegíveis, na ordem do catálogo. O modelo depois só pode **escolher e ordenar** dentro dessa lista; não pode inventar keys.

---

## 8. Prompts (resumo)

- **INTERPRETER_SYSTEM_PROMPT**: extrair JSON com document_type e context a partir de texto livre; sem texto explicativo.
- **BASE_SYSTEM_PROMPT**: agente de estruturação; saída **apenas** JSON de estrutura (document_type + root_sections); não redigir texto jurídico; formato dos nós (key, title, required, content_type, table_schema, children).
- **DOCUMENT_TYPE_HINTS**: por tipo (termo_referencia, estudo_tecnico_preliminar, documento_formalizacao_demanda), lista de seções sugeridas e orientações (condicionais, frequentemente presentes). Usado quando **não** há catálogo.
- **CATALOG_SELECTION_SYSTEM_PROMPT**: quando há catálogo; a IA deve devolver só `{ "section_keys": [...] }` com keys da lista permitida; pode omitir seções; matching por intenção (redação diferente do usuário).
- **build_catalog_selection_user_prompt**: monta a lista permitida (key, title, description quando existir) e o contexto para o modelo escolher por intenção.

Há também **CLAUSE_COMPOSITION_SYSTEM_PROMPT** e schemas de composição jurídica (ClauseCompositionRequest/Response), reservados para uso futuro pela camada de RAG/composição de cláusulas; o llm_agent atual **não** expõe endpoint de geração de texto de cláusulas.

---

## 9. Configuração (variáveis de ambiente)

| Variável | Descrição | Default |
|----------|-----------|---------|
| **LLM_ORCHESTRATION_BASE_URL** | Base URL do llm_api | `http://localhost:8002` |
| **LLM_ORCHESTRATION_GENERATE_PATH** | Path do endpoint generate | `/api/llm/generate` |
| **AGENT_TIMEOUT** | Timeout (s) da chamada HTTP ao llm_api | 60.0 |
| **AGENT_MAX_RETRIES** | Tentativas extras em caso de resposta inválida | 2 |
| **SECTIONS_REGISTRY_PATH** | Caminho do arquivo JSON do registro | `…/llm_agent/data/sections_registry.json` |
| **REGISTRY_UPDATE_KEY** | Chave para aceitar POST /registry; vazio = atualização recusada | (vazio) |

---

## 10. Schemas principais (entrada/saída)

- **StructureRequest**: document_type, context (ContextoBasico), sections_catalog (opcional).
- **StructureResponse**: ok, structure (DocumentStructure ou null), error (opcional), retries.
- **DocumentStructure**: document_type, root_sections (lista de SectionNode).
- **SectionNode**: key, title, required, content_type ("text" | "table" | "list"), table_schema (opcional), children (lista recursiva).
- **PromptStructureRequest**: user_prompt (para structure-from-prompt).
- **SectionsRegistry**: catalog_id, catalog_version, entries (lista de RegistrySectionEntry); usado no body de POST /registry e no arquivo JSON.

O catálogo interno (**SectionCatalog** / **SectionCatalogEntry**) inclui, entre outros: key, title, document_types, categories, description, content_type, required, conditional_rules, applicability_scope, version, is_active, parent_key, table_schema (opcional). Não inclui campos de “funcionamento jurídico” (fundamento legal, obrigatoriedade por autoridade etc.), reservados para RAG.

---

## 11. O que este módulo não faz (deixado para depois)

- **Redação de cláusulas**: nenhum texto jurídico é produzido aqui.
- **Fundamento legal, obrigatoriedade por órgão (ex.: TCU), layout final (tabela vs texto, colunas)**: não são declarados no registro; ficam para a camada de RAG e para o agente de composição jurídica.
- **Inferência de seções fora do catálogo**: com catálogo/registro, a IA só seleciona e ordena keys existentes; sem catálogo, as dicas (hints) guiam a geração livre, mas o módulo não mantém um banco de cláusulas nem RAG.

---

## 12. Execução

- Desenvolvimento local (com llm_api rodando, ex.: na porta 8002):
  ```bash
  uvicorn llm_agent.app.main:app --reload --host 0.0.0.0 --port 8003
  ```
- Em produção/Docker: o serviço llm_agent sobe na porta configurada (ex.: 8003) e usa `LLM_ORCHESTRATION_BASE_URL` para falar com o llm_api. O arquivo de registro deve estar acessível no caminho `SECTIONS_REGISTRY_PATH` (volume ou path interno ao container).

Documentação complementar: `docs/TEST_REGISTRY_CURL.md` (testes com curl), `docs/MALEABILIDADE_SECOES.md` (categorias e matching por intenção).
