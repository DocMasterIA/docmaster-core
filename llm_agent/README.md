# llm_agent — Document Structure Agent

Overview of how **llm_agent** works: it generates the **logical structure** (skeleton) of public procurement documents, without drafting legal text. With a catalog/registry, the model only **selects and orders** registered sections; without a catalog, it uses hints by document type and a minimal fallback.

---

## Flow in use today (summary)

1. **Client** calls **POST /api/agent/structure** (with document_type + context) or **POST /api/agent/structure-from-prompt** (with user_prompt).
2. **structure-from-prompt**: the LLM interpreter extracts `document_type` and `context` from the text; the result becomes a `StructureRequest` (with `user_prompt` preserved when a catalog is present).
3. **generate_structure**:
   - If there is a **sections_catalog** (in the body or loaded from the `SECTIONS_REGISTRY_PATH` file): it filters **eligible** sections (type, scope, conditional_rules, category), sends the LLM only the list (key/title/description); the LLM returns `section_keys` (and, if there is a `user_prompt`, `matches` with a confidence level). The final structure is built only from catalog entries.
   - If there is **no** catalog: it builds a prompt with BASE_SYSTEM_PROMPT + DOCUMENT_TYPE_HINTS; the LLM returns JSON with `root_sections`; the result is validated and a minimal fallback is applied on failure.
4. **Response**: `StructureResponse` with `ok`, `structure` (DocumentStructure), `error` (optional), `retries` and, when there was a `user_prompt` in the catalog flow, `section_matches` (request ↔ section correspondence with confidence high/medium/low).
5. **POST /api/agent/registry** (optional): updates the registry file; body = full registry JSON; the next generation uses the new catalog (local use, no authentication).

No endpoint drafts legal text or operates at the level of numbered/versioned clauses; that is left for later layers (RAG, composition).

---

## 1. Goal

- Produce a document **skeleton** as JSON: a list of sections (key, title, required, content_type, table_schema when applicable, children).
- **Does not** draft clauses, legal grounds, or final content.
- Integrates with the LLM orchestration module (**llm_api**), which in turn calls the model (e.g. Ollama).
- Supports two modes of operation:
  - **With catalog/registry**: sections come from a registry; the model only chooses which ones to include and in what order.
  - **Without catalog**: the model generates the structure from hints by document type, with a fallback to a minimal structure on failure.

---

## 2. Architecture

```
                    ┌─────────────────┐
                    │   Client        │
                    │ (Django, curl)  │
                    └────────┬────────┘
                             │
         POST /api/agent/structure
         POST /api/agent/structure-from-prompt
         POST /api/agent/registry (update registry)
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         llm_agent (FastAPI, port 8003)                  │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ api.py      │  │ agent.py    │  │ registry.py  │  │ catalog_     │   │
│  │ (routes)    │──│ (orchestrates│──│ (loads/      │  │ filter.py    │   │
│  │             │  │  the flow)  │  │  saves JSON) │  │ (eligible)   │   │
│  └─────────────┘  └──────┬──────┘  └──────────────┘  └──────────────┘   │
│                          │                                              │
│  ┌─────────────┐  ┌──────┴──────┐  ┌──────────────┐                     │
│  │ prompts.py  │  │ client.py   │  │ schemas.py   │                     │
│  │ (system +   │  │ (HTTP →     │  │ (request/    │                     │
│  │  user)      │  │  llm_api)   │  │  response)   │                     │
│  └─────────────┘  └──────┬──────┘  └──────────────┘                     │
└──────────────────────────┼──────────────────────────────────────────────┘
                           │
                           ▼
                    ┌─────────────────┐
                    │ llm_api (:8002) │  →  Ollama (model)
                    └─────────────────┘
```

- **api.py**: exposes the endpoints under `/api/agent/`.
- **agent.py**: decides the flow (catalog vs. hints), builds payloads, calls the LLM, parses responses, and builds `DocumentStructure`.
- **client.py**: the only HTTP call to llm_api (`/api/llm/generate`); it does not talk to Ollama directly.
- **registry.py**: reads the registry JSON file (`SECTIONS_REGISTRY_PATH`), converts it to `SectionCatalog`, keeps a cache; updates the file when it receives `POST /registry` with a valid key.
- **catalog_filter.py**: given a `SectionCatalog`, a document type, and context, returns the list of **eligible** sections (deterministic filter: type, scope, conditional rules, category).
- **prompts.py**: system texts and user-prompt construction (interpreter, free generation, selection from the catalog).
- **schemas.py**: Pydantic models for input/output and the versioned catalog.

---

## 3. Endpoints

| Method and path | Description |
|-----------------|-------------|
| **POST /api/agent/structure** | Generates the structure. Body: `StructureRequest` (document_type, context; optional: sections_catalog, user_prompt). Returns: `StructureResponse` (ok, structure, error, retries; section_matches when there was a user_prompt in the catalog flow). |
| **POST /api/agent/structure-from-prompt** | Interprets a free-form prompt. Body: `{ "user_prompt": "..." }`. LLM interpreter → `StructureRequest` → `generate_structure`. Returns: the same `StructureResponse`; with a catalog, it includes section_matches (request ↔ section with confidence). |
| **POST /api/agent/registry** | Updates the section registry (JSON file). Body: full `SectionsRegistry`. Local use, no key. |
| **POST /api/agent/clause-structure** | Generates **only** the clause/subclause skeleton (ClauseNode). Body: `ClauseStructureRequest` (document_type, context; optional: section_key, base_description). Returns: `ClauseStructureResponse` (ok, root_clauses, error, retries). Subclauses have no title. |

The API is intended for internal use (e.g. the Django backend), not for direct public consumption.

---

## 4. Main flow: `generate_structure`

1. **Catalog**
   - If the request includes `sections_catalog` with entries, that catalog is used.
   - Otherwise, it tries to load the file registry (`get_catalog_from_registry()`). If it exists and has `entries`, that catalog is used.

2. **With a catalog**
   - Calls `filter_eligible_sections(catalog, document_type, context)` → list of eligible sections.
   - If the list is empty, returns a `StructureResponse` with a minimal fallback structure and an explanatory `error`.
   - Builds the **selection** prompt: system (may only return keys from the list; matching by intent) + user (key/title/description list + context).
   - Calls the LLM via `call_generate`. Expects JSON `{ "section_keys": ["key1", "key2", ...] }`.
   - Validates: only accepts keys that are in the eligible set; order is preserved.
   - If parsing fails or the result is empty, uses a fallback: the order of the catalog roots, or all eligible sections.
   - Builds `DocumentStructure` with `_build_structure_from_catalog_selection`: each key becomes a `SectionNode` (key, title, required, content_type, table_schema) from the catalog entry; hierarchy via `parent_key`.
   - Returns `StructureResponse(ok=True, structure=...)` or, on an order fallback, `ok=False` with a structure that is still usable.

3. **Without a catalog**
   - Builds a prompt with **BASE_SYSTEM_PROMPT** + **DOCUMENT_TYPE_HINTS** for the document type and sends the context in the user prompt.
   - Calls the LLM; expects JSON with `document_type` and `root_sections` (a list of nodes with key, title, required, content_type, table_schema, children).
   - Strips any markdown (```json ... ```) and validates with `DocumentStructure.model_validate`; applies `_validate_semantics` (minimum required sections by type).
   - On failure (network, invalid JSON, validation): retries up to `AGENT_MAX_RETRIES + 1` times.
   - If every attempt fails: returns the **minimal** structure for that type (`_minimal_structure_for`), with `ok=False` and `error` set.

In every case the output is **structure only** (a skeleton); no legal text is generated in this module.

---

## 5. Interpreter (free-form prompt → StructureRequest)

Used by the **structure-from-prompt** endpoint:

- System prompt: extract **only** a JSON object with `document_type` (snake_case) and `context` (an object with objeto, orgao, modalidade, extras).
- User prompt: the user's free text.
- Expected response: valid JSON. On parse or network failure, fallback: `document_type="termo_referencia"`, `context.objeto` = a slice of the prompt (up to 500 characters).

The result is a `StructureRequest` that proceeds to `generate_structure` like any other call to `/structure`.

---

## 6. Section registry (JSON file)

- **File**: path set by `SECTIONS_REGISTRY_PATH` (default: `llm_agent/data/sections_registry.json`).
- **Format**: JSON with `catalog_id`, `catalog_version`, and `entries` (a list of entries in the **RegistrySectionEntry** schema).
- **Fields per entry (summary)**:
  - **key**, **title**: stable identifier and title.
  - **document_types**: list of types (e.g. `["estudo_tecnico_preliminar", "termo_referencia"]`).
  - **categories** (optional): document patterns (e.g. `["compra_medicamentos", "obras"]`); used when the context provides `extras.categoria` or `extras.document_pattern`.
  - **description** (optional): short text so the model can match by intent (a request worded differently).
  - **content_type**: `"text"` | `"table"` | `"list"` (structural level; fine layout decisions are left to RAG).
  - **required**, **status** ("optional" | "required"): structural requirement.
  - **conditional_rules** (optional): deterministic inclusion rules. Shortcut: `{ "if": ["obra", "servico_continuado"], "if_path": "extras.tipo_objeto" }` → eligible only if the value at `if_path` is in `if`.
  - **applicability_scope** (optional): municipality, state, agency, administration type; the section is eligible only if the context matches.
  - **enabled**, **version**, **effective_from**, **parent_key** (optional).
  - **table_schema** (optional): only when content_type is a table; in practice the module treats most entries as text; layout details come later.

**What does not belong in the registry (left to the RAG/composition layer)**  
Legal basis, requirement by authority (e.g. TCU), and other “operating declarations” of sections/clauses are not declared here.

- **Loading**: on first need (or after an update), the registry is read from disk, validated as `SectionsRegistry`, and converted to `SectionCatalog` (`registry_entry_to_catalog_entry` for each entry); the result is cached in memory.
- **Update**: `POST /api/agent/registry` with body = the full registry JSON. The file is rewritten and the cache is invalidated; the next generation uses the new content (intended for local use).

---

## 7. Eligible-section filter (`catalog_filter`)

Input: `SectionCatalog`, `document_type`, `ContextoBasico`.

- **Filters applied (all deterministic)**:
  - **is_active**: only entries with `enabled` true.
  - **document_type**: the requested type must be in `entry.document_types`.
  - **applicability_scope**: if the section has a scope (municipality, state, agency, administration type), the context must match (e.g. same agency, same state in `extras`).
  - **conditional_rules**: every rule must be true for the context (e.g. `has_field`, `field_equals`, `field_in` on paths such as `extras.tipo_objeto`).
  - **Category**: if the context has `extras.categoria` or `extras.document_pattern` (string or list), only sections **without** `categories` or with an intersection between `entry.categories` and the context categories are included. If the context does not provide a category, there is no category filter (everything that passes the other filters is included).

Output: a list of eligible `SectionCatalogEntry` items, in catalog order. The model may then only **choose and order** within that list; it cannot invent keys.

---

## 8. Prompts in use today

| Prompt / function | Where it is used | Role |
|-------------------|------------------|------|
| **INTERPRETER_SYSTEM_PROMPT** | structure-from-prompt → interpret_user_prompt | Extract JSON (document_type + context) from free text. |
| **BASE_SYSTEM_PROMPT** + **DOCUMENT_TYPE_HINTS** | generate_structure (**without** a catalog) | Generate structure JSON (root_sections) when there is no registry. |
| **CATALOG_SELECTION_SYSTEM_PROMPT** | generate_structure (**with** a catalog, no user_prompt) | Return only `section_keys` from the allowed list. |
| **CATALOG_SELECTION_WITH_MATCHES_SYSTEM_PROMPT** | generate_structure (catalog flow **and** user_prompt) | Return `section_keys` and `matches` (key, user_phrase, confidence). |
| **DOCUMENT_CLAUSE_STRUCTURE_SYSTEM_PROMPT** | generate_clause_structure (clause-structure) | Define only the clause/subclause structure (ClauseNode), with no legal text. |
| **build_catalog_selection_user_prompt** | agent.py when building the selection prompt | Allowed list (key, title, description) + context (and optionally user_prompt). |
| **build_system_prompt** / **build_user_prompt** | Flow without a catalog | Type + context for free structure generation. |

---

## 9. Configuration (environment variables)

| Variable | Description | Default |
|----------|-------------|---------|
| **LLM_ORCHESTRATION_BASE_URL** | Base URL of llm_api | `http://localhost:8002` |
| **LLM_ORCHESTRATION_GENERATE_PATH** | Path of the generate endpoint | `/api/llm/generate` |
| **AGENT_TIMEOUT** | Timeout (s) of the HTTP call to llm_api | 60.0 |
| **AGENT_MAX_RETRIES** | Extra attempts when the response is invalid | 2 |
| **SECTIONS_REGISTRY_PATH** | Path of the registry JSON file | `…/llm_agent/data/sections_registry.json` |
| **REGISTRY_UPDATE_KEY** | (Unused.) Reserved for future protection of POST /registry. | (empty) |

---

## 10. Main schemas (input/output)

- **StructureRequest**: document_type, context (ContextoBasico), sections_catalog (optional), user_prompt (optional; when set, the catalog-flow response may include section_matches).
- **StructureResponse**: ok, structure (DocumentStructure or null), error (optional), retries, section_matches (optional; list of SectionMatchAnnotation when user_prompt was used in the catalog flow).
- **DocumentStructure**: document_type, root_sections (list of SectionNode).
- **SectionNode**: key, title, required, content_type ("text" | "table" | "list"), table_schema (optional), children (recursive list).
- **PromptStructureRequest**: user_prompt (for structure-from-prompt).
- **SectionsRegistry**: catalog_id, catalog_version, entries (list of RegistrySectionEntry); used in the POST /registry body and in the JSON file.
- **ClauseNode**: logical_id, title (top-level clauses only), status, scope, version, children (recursive list; subclauses have no title).
- **ClauseStructureRequest**: document_type, context (free-form dict), section_key (optional), base_description (optional).
- **ClauseStructureResponse**: ok, root_clauses (list of ClauseNode or null), error (optional), retries.

The internal catalog (**SectionCatalog** / **SectionCatalogEntry**) includes, among other fields: key, title, document_types, categories, description, content_type, required, conditional_rules, applicability_scope, version, is_active, parent_key, table_schema (optional). It does not include “legal operation” fields (legal basis, requirement by authority, and so on), which are reserved for RAG.

---

## 11. Declared but still unused / undefined parts

Items that exist in the code or the documentation as a **contract** or **future reference**, but are **not** used by any current endpoint or flow.

| Item | Where it lives | Status |
|------|----------------|--------|
| **DOCUMENT_CLAUSE_STRUCTURE_SYSTEM_PROMPT** | prompts.py | Reference text for when a **hierarchical clause** agent exists (logical id, numbering, version, scope). No endpoint sends it to the LLM. See docs/DOCUMENT_CLAUSE_STRUCTURE_PROMPT.md. |
| **CLAUSE_COMPOSITION_SYSTEM_PROMPT** | prompts.py | Reserved for an agent that **generates clause text** from a registered base + RAG. No clause-text generation endpoint exists in llm_agent. |
| **ClauseCompositionRequest** / **ClauseCompositionResponse** | schemas.py | Input/output schemas for that future composition agent. They are not used by any route. |
| **Clause-level structure/modification endpoint** | — | Not implemented. The expected flow (a document with numbered clauses, versioning, per-clause scope) is only described in the docs. |
| **Clause text generation endpoint** | — | Not implemented. It would be the consumer of CLAUSE_COMPOSITION_SYSTEM_PROMPT and the ClauseComposition* schemas. |

What **is** used today: **SectionMatchAnnotation** and **section_matches** on StructureResponse (filled when there is a `user_prompt` in the catalog flow); **user_prompt** on StructureRequest (optional, forwarded to the selection prompt and used to build section_matches).

---

## 12. What this module does not do (left for later)

- **Clause drafting**: no legal text is produced here.
- **Legal basis, requirement by agency (e.g. TCU), final layout (table vs text, columns)**: not declared in the registry; left to the RAG layer and the legal composition agent.
- **Inferring sections outside the catalog**: with a catalog/registry, the model only selects and orders existing keys; without a catalog, hints guide free generation, but the module does not keep a clause database or RAG.
- **Clause-level structure** (logical identifier, displayed numbering, per-clause version): defined conceptually in DOCUMENT_CLAUSE_STRUCTURE_SYSTEM_PROMPT, but not implemented.

---

## 13. Running

- Local development (with llm_api running, e.g. on port 8002):
  ```bash
  uvicorn llm_agent.app.main:app --reload --host 0.0.0.0 --port 8003
  ```
- In production/Docker: the llm_agent service starts on the configured port (e.g. 8003) and uses `LLM_ORCHESTRATION_BASE_URL` to talk to llm_api. The registry file must be reachable at `SECTIONS_REGISTRY_PATH` (a volume or a path inside the container).

Further documentation: `docs/PROMPTS_TESTE.md` (prompts and curls for testing), `docs/MALEABILIDADE_SECOES.md` (categories and intent matching), `docs/DOCUMENT_CLAUSE_STRUCTURE_PROMPT.md` (hierarchical clause prompt — unused today), `docs/TECNOLOGIAS_COMPOSICAO.md` (technology suggestions for later evolution).
