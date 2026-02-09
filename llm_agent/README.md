# llm_agent — Agente de Estrutura Documental

Resumo do funcionamento do **llm_agent**: geração da **estrutura lógica** (esqueleto) de documentos de licitação pública, sem redação de texto jurídico. Com catálogo/registro, a IA apenas **seleciona e ordena** seções cadastradas; sem catálogo, usa dicas por tipo de documento e fallback mínimo.

---

## Fluxo em uso hoje (resumo)

1. **Cliente** chama **POST /api/agent/structure** (com document_type + context) ou **POST /api/agent/structure-from-prompt** (com user_prompt).
2. **structure-from-prompt**: o interpretador LLM extrai `document_type` e `context` do texto; o resultado vira um `StructureRequest` (com `user_prompt` preservado quando há catálogo).
3. **generate_structure**:
   - Se houver **sections_catalog** (no body ou carregado do arquivo `SECTIONS_REGISTRY_PATH`): filtra **elegíveis** (tipo, escopo, conditional_rules, categoria), envia ao LLM só a lista (key/title/description); o LLM devolve `section_keys` (e, se houver `user_prompt`, `matches` com nível de certeza). A estrutura final é montada só com entradas do catálogo.
   - Se **não** houver catálogo: monta prompt com BASE_SYSTEM_PROMPT + DOCUMENT_TYPE_HINTS; o LLM devolve JSON com `root_sections`; valida e aplica fallback mínimo em falha.
4. **Resposta**: `StructureResponse` com `ok`, `structure` (DocumentStructure), `error` (opcional), `retries` e, quando houve `user_prompt` no fluxo com catálogo, `section_matches` (correspondência pedido ↔ seção com confidence high/medium/low).
5. **POST /api/agent/registry** (opcional): atualiza o arquivo de registro; body = JSON completo do registro; próxima geração usa o novo catálogo (uso local, sem autenticação).

Nenhum endpoint gera texto jurídico nem opera no nível de cláusulas numeradas/versionadas; isso fica para camadas futuras (RAG, composição).

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
| **POST /api/agent/structure** | Gera a estrutura. Body: `StructureRequest` (document_type, context; opcional: sections_catalog, user_prompt). Retorno: `StructureResponse` (ok, structure, error, retries; section_matches quando houve user_prompt no fluxo com catálogo). |
| **POST /api/agent/structure-from-prompt** | Interpreta prompt livre. Body: `{ "user_prompt": "..." }`. Interpretador LLM → `StructureRequest` → `generate_structure`. Retorno: mesmo `StructureResponse`; com catálogo, inclui section_matches (pedido ↔ seção com confidence). |
| **POST /api/agent/registry** | Atualiza o registro de seções (arquivo JSON). Body: `SectionsRegistry` completo. Uso local, sem chave. |
| **POST /api/agent/clause-structure** | Gera **apenas** o esqueleto de cláusulas/subcláusulas (ClauseNode). Body: `ClauseStructureRequest` (document_type, context; opcionais: section_key, base_description). Retorno: `ClauseStructureResponse` (ok, root_clauses, error, retries). Subcláusulas não têm título. |

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
- **Atualização**: `POST /api/agent/registry` com body = JSON completo do registro. O arquivo é reescrito e o cache invalidado; a próxima geração usa o novo conteúdo (pensado para uso local).

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

## 8. Prompts em uso hoje

| Prompt / função | Onde é usado | Papel |
|------------------|--------------|--------|
| **INTERPRETER_SYSTEM_PROMPT** | structure-from-prompt → interpret_user_prompt | Extrair JSON (document_type + context) do texto livre. |
| **BASE_SYSTEM_PROMPT** + **DOCUMENT_TYPE_HINTS** | generate_structure (fluxo **sem** catálogo) | Gerar JSON de estrutura (root_sections) quando não há registro. |
| **CATALOG_SELECTION_SYSTEM_PROMPT** | generate_structure (fluxo **com** catálogo, sem user_prompt) | Devolver só `section_keys` da lista permitida. |
| **CATALOG_SELECTION_WITH_MATCHES_SYSTEM_PROMPT** | generate_structure (fluxo com catálogo **e** user_prompt) | Devolver `section_keys` e `matches` (key, user_phrase, confidence). |
| **DOCUMENT_CLAUSE_STRUCTURE_SYSTEM_PROMPT** | generate_clause_structure (clause-structure) | Definir apenas a estrutura de cláusulas/subcláusulas (ClauseNode), sem texto jurídico. |
| **build_catalog_selection_user_prompt** | agent.py ao montar prompt de seleção | Lista permitida (key, title, description) + contexto (e opcionalmente user_prompt). |
| **build_system_prompt** / **build_user_prompt** | Fluxo sem catálogo | Tipo + contexto para geração livre de estrutura. |

---

## 9. Configuração (variáveis de ambiente)

| Variável | Descrição | Default |
|----------|-----------|---------|
| **LLM_ORCHESTRATION_BASE_URL** | Base URL do llm_api | `http://localhost:8002` |
| **LLM_ORCHESTRATION_GENERATE_PATH** | Path do endpoint generate | `/api/llm/generate` |
| **AGENT_TIMEOUT** | Timeout (s) da chamada HTTP ao llm_api | 60.0 |
| **AGENT_MAX_RETRIES** | Tentativas extras em caso de resposta inválida | 2 |
| **SECTIONS_REGISTRY_PATH** | Caminho do arquivo JSON do registro | `…/llm_agent/data/sections_registry.json` |
| **REGISTRY_UPDATE_KEY** | (Não usado.) Reservado para futura proteção do POST /registry. | (vazio) |

---

## 10. Schemas principais (entrada/saída)

- **StructureRequest**: document_type, context (ContextoBasico), sections_catalog (opcional), user_prompt (opcional; quando preenchido, no fluxo com catálogo a resposta pode trazer section_matches).
- **StructureResponse**: ok, structure (DocumentStructure ou null), error (opcional), retries, section_matches (opcional; lista de SectionMatchAnnotation quando user_prompt foi usado no fluxo com catálogo).
- **DocumentStructure**: document_type, root_sections (lista de SectionNode).
- **SectionNode**: key, title, required, content_type ("text" | "table" | "list"), table_schema (opcional), children (lista recursiva).
- **PromptStructureRequest**: user_prompt (para structure-from-prompt).
- **SectionsRegistry**: catalog_id, catalog_version, entries (lista de RegistrySectionEntry); usado no body de POST /registry e no arquivo JSON.
- **ClauseNode**: logical_id, title (apenas para cláusulas de topo), status, scope, version, children (lista recursiva; subcláusulas sem título).
- **ClauseStructureRequest**: document_type, context (dict livre), section_key (opcional), base_description (opcional).
- **ClauseStructureResponse**: ok, root_clauses (lista de ClauseNode ou null), error (opcional), retries.

O catálogo interno (**SectionCatalog** / **SectionCatalogEntry**) inclui, entre outros: key, title, document_types, categories, description, content_type, required, conditional_rules, applicability_scope, version, is_active, parent_key, table_schema (opcional). Não inclui campos de “funcionamento jurídico” (fundamento legal, obrigatoriedade por autoridade etc.), reservados para RAG.

---

## 11. Partes declaradas mas ainda não usadas / indefinidas

Itens que existem no código ou na documentação como **contrato** ou **referência futura**, mas **não** são usados por nenhum endpoint nem fluxo atual.

| Item | Onde está | Situação |
|------|-----------|----------|
| **DOCUMENT_CLAUSE_STRUCTURE_SYSTEM_PROMPT** | prompts.py | Texto de referência para quando existir agente de **cláusulas hierárquicas** (id lógico, numeração, versão, escopo). Nenhum endpoint o envia ao LLM. Ver docs/DOCUMENT_CLAUSE_STRUCTURE_PROMPT.md. |
| **CLAUSE_COMPOSITION_SYSTEM_PROMPT** | prompts.py | Reservado para agente que **gera texto de cláusulas** a partir de base registrada + RAG. Nenhum endpoint de geração de texto de cláusulas existe no llm_agent. |
| **ClauseCompositionRequest** / **ClauseCompositionResponse** | schemas.py | Schemas de entrada/saída para esse futuro agente de composição. Não são usados por nenhuma rota. |
| **Endpoint de estrutura/modificação no nível de cláusulas** | — | Não implementado. O fluxo esperado (documento com cláusulas numeradas, versionamento, escopo por cláusula) está apenas descrito na doc. |
| **Endpoint de geração de texto de cláusulas** | — | Não implementado. Seria o consumidor de CLAUSE_COMPOSITION_SYSTEM_PROMPT e dos schemas ClauseComposition*. |

O que **é** usado hoje: **SectionMatchAnnotation** e **section_matches** em StructureResponse (preenchidos quando há `user_prompt` no fluxo com catálogo); **user_prompt** em StructureRequest (opcional, repassado para o prompt de seleção e para montar section_matches).

---

## 12. O que este módulo não faz (deixado para depois)

- **Redação de cláusulas**: nenhum texto jurídico é produzido aqui.
- **Fundamento legal, obrigatoriedade por órgão (ex.: TCU), layout final (tabela vs texto, colunas)**: não são declarados no registro; ficam para a camada de RAG e para o agente de composição jurídica.
- **Inferência de seções fora do catálogo**: com catálogo/registro, a IA só seleciona e ordena keys existentes; sem catálogo, as dicas (hints) guiam a geração livre, mas o módulo não mantém um banco de cláusulas nem RAG.
- **Estrutura no nível de cláusulas** (identificador lógico, numeração exibida, versão por cláusula): definida conceitualmente no DOCUMENT_CLAUSE_STRUCTURE_SYSTEM_PROMPT, mas sem implementação.

---

## 13. Execução

- Desenvolvimento local (com llm_api rodando, ex.: na porta 8002):
  ```bash
  uvicorn llm_agent.app.main:app --reload --host 0.0.0.0 --port 8003
  ```
- Em produção/Docker: o serviço llm_agent sobe na porta configurada (ex.: 8003) e usa `LLM_ORCHESTRATION_BASE_URL` para falar com o llm_api. O arquivo de registro deve estar acessível no caminho `SECTIONS_REGISTRY_PATH` (volume ou path interno ao container).

Documentação complementar: `docs/PROMPTS_TESTE.md` (prompts e curls para testar), `docs/MALEABILIDADE_SECOES.md` (categorias e matching por intenção), `docs/DOCUMENT_CLAUSE_STRUCTURE_PROMPT.md` (prompt de cláusulas hierárquicas — não usado hoje), `docs/TECNOLOGIAS_COMPOSICAO.md` (sugestões de tecnologias para evolução).
