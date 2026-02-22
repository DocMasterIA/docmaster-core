# Backend Django (mdlicitatech)

Documentação do módulo **backend**: aplicação Django principal, URLs, APIs, serviços, contexto para LLM e limitações.

---

## 1. Estrutura e URLs

### 1.1 Roteamento principal

Arquivo: `backend/mdlicitatech/urls.py`

| Padrão | Inclusão | Descrição |
|--------|----------|-----------|
| `admin/painel/` | `dashboard_view` | Dashboard customizado do admin |
| `admin/` | Django admin | Painel admin padrão |
| `""` | `backend.app.urls` | Rotas globais do app (login, APIs, proxy LLM) |
| `^(?P<prefeitura_slug>[-\w]+)/` | `backend.app.prefeitura_urls` | Rotas multi-tenant por slug da prefeitura |

### 1.2 Rotas globais do app

Arquivo: `backend/app/urls.py`

| Método | URL | View/Handler | Descrição |
|--------|-----|-------------|-----------|
| GET | `favicon.ico` | favicon_view | Favicon |
| GET | `login/` | login_global_redirect | Redirecionamento global de login |
| GET | `<prefeitura_url>/` | LoginView | Tela de login (tenant) |
| GET | `<prefeitura_url>/logout` | LogoutView | Logout |
| GET | `<prefeitura_url>/dashboard/` | DashboardView | Dashboard do tenant |
| GET | `<prefeitura_url>/area_do_usuario/` | AreaDoUsuarioView | Área do usuário |
| GET | `<prefeitura_url>/gerador_de_documentos/` | DocumentGeneratorView | UI do gerador de documentos |
| GET | `<prefeitura_url>/biblioteca_documentos/` | GetTemplatesView | Biblioteca de templates |
| POST | `api/documentos_modelos/enviar` | upload_template_and_request_mapping_api | Upload de template + mapeamento |
| GET | `api/documentos_modelos/` | get_template_list_api | Listar templates (ou um por id) |
| POST | `api/documentos_modelos/gerar` | generate_document_with_values_api | Gerar doc a partir de template + values |
| POST | `api/documentos/gerar-via-llm` | gerar_via_llm_api | Gerar documento via LLM (RAG) |
| GET/POST | `api/documentos_modelos/lista_10` | template_list_api | Listar até 10 templates (autocomplete) |
| GET | `api/documentos_modelos/<uuid:template_id>/pdf/` | template_preview_pdf_api | Preview PDF do template |
| GET | `api/me/` | api_me | Dados do usuário logado |
| GET | `api/me/documents/` | api_me_documents | Documentos do usuário |
| POST | `api/auth/login/` | api_auth_login | Login (API) |
| POST | `api/auth/logout/` | api_auth_logout | Logout (API) |
| GET/POST | `api/llm/<path:path>` | llm_proxy | Proxy para LLM_API_BASE_URL (requer sessão) |
| GET/POST | `area_do_usuario/docs/ajax/` | area_do_usuario_ajax | AJAX área do usuário |
| GET | `secretaria-autocomplete/ajax/` | SecretariaAutocomplete | Autocomplete de secretaria |

Todas as APIs de documentos e templates exigem autenticação (`@api_login_required`); em caso de não autenticado retornam 401 JSON.

---

## 2. APIs – Contratos e exemplos

### 2.1 POST `api/documentos_modelos/enviar`

- **Entrada**: `multipart/form-data`: `template_file` (obrigatório), `name` (opcional), `mapping_instructions` (opcional).
- **Comportamento**: Cria template, gera preview (imagem), extrai estrutura do DOCX (sem IA de mapeamento). Retorna `template_id` e `schema` (fields vazios; notas indicam uso de tokens `{{ }}`).
- **Saída**: `{"ok": true, "template_id": "<uuid>", "schema": {...}}` ou erro 4xx/5xx.

### 2.2 GET `api/documentos_modelos/`

- **Query**: `id` (opcional) – se informado, retorna um template; senão lista até 10.
- **Saída**: `{"template": {...}}` ou `{"templates": [...]}` com `id`, `name`, `has_schema`, `preview_image`.

### 2.3 POST `api/documentos_modelos/gerar`

- **Entrada (JSON)**: `template_id` (obrigatório), `values` (objeto chave-valor), `output`: `"pdf"` ou `"docx"`.
- **Comportamento**: Renderiza DOCX a partir do schema (estratégia index) ou fallback por tokens; se `output=pdf` gera PDF e retorna arquivo.
- **Saída**: FileResponse (PDF ou DOCX) ou `{"ok": false, "error": "..."}`.

### 2.4 POST `api/documentos/gerar-via-llm`

- **Entrada (JSON)**:
  - `user_prompt` (obrigatório): texto livre (ex.: "gerar ETP para coleta seletiva").
  - `template_id` (opcional).
  - `document_type_hint` (opcional).
  - `output` (opcional): `"docx"` (padrão) ou outro; quando `docx` pode retornar arquivo.
- **Comportamento**: Monta contexto do usuário (`build_llm_context_from_request`), envia POST para `RAG_SERVICE_URL/api/rag/generate-document`. Se `output=docx` e a resposta contiver arquivo, retorna FileResponse (DOCX).
- **Saída**: JSON `{ok, structure, section_texts, ...}` ou arquivo DOCX; em erro 502/503/504 retorna mensagem adequada.

**Exemplo de corpo (gerar via LLM):**

```json
{
  "user_prompt": "Gerar termo de referência para aquisição de material de escritório",
  "template_id": null,
  "document_type_hint": "termo_referencia",
  "output": "docx"
}
```

### 2.5 GET `api/documentos_modelos/lista_10`

- **Query**: `q` (opcional) – filtro por nome.
- **Saída**: `{"templates": [{"id", "name"}, ...]}` (até 10).

### 2.6 GET `api/documentos_modelos/<uuid:template_id>/pdf/`

- **Saída**: `{"ok": true, "pdf_url": "..."}` ou gera preview PDF se não existir; erro 500 se falha.

### 2.7 Proxy LLM – `api/llm/<path:path>`

- Repassa GET/POST para `LLM_API_BASE_URL` (ex.: `http://127.0.0.1:8002`). Requer usuário autenticado (sessão). Útil para o frontend chamar planner/section/generate sem expor a porta do llm_api diretamente.

---

## 3. Serviços internos

### 3.1 `backend/app/services/llm_context.py`

- **Função**: `build_llm_context_from_request(request)`.
- **Entrada**: `HttpRequest` (com `request.user` autenticado).
- **Saída**: `dict` com chaves como `usuario` (nome_completo, secretaria, prefeitura, orgao), usado no body para o RAG (generate-document). Opcionalmente o chamador adiciona `template_id`, `document_type_hint`.

### 3.2 `backend/app/services/services.py`

- **Principais**: `extract_docx_structure`, `validate_mapping_response`, `save_template_schema`, `assemble_document_context`, `generate_pdf_from_docx`, `convert_html_to_pdf`, `_ensure_media_subdir`.
- **Uso**: Extração de estrutura do DOCX, validação de mapeamento, persistência de schema, montagem de contexto para render, geração de PDF a partir de DOCX.

### 3.3 `backend/app/services/render.py`

- **Principais**: `render_docx_from_template`, `render_docx_fallback`, `render_preview_html`, `render_docx_by_index`, `render_docx_with_tokens`.
- **Uso**: Renderização de DOCX a partir de template (estratégia index ou tokens Jinja).

### 3.4 `backend/app/services/preview.py`

- **Principais**: `generate_docx_preview`, `generate_docx_preview_pdf`.
- **Uso**: Geração de preview em imagem e PDF do template.

### 3.5 `backend/app/llm_proxy.py`

- **Função**: `llm_proxy(request, path)` – monta URL como `LLM_API_BASE_URL + "/" + path`, repassa método, headers, body; retorna resposta do llm_api. Requer `api_login_required`.

---

## 4. Contexto para LLM/RAG

O contexto enviado ao RAG em `gerar-via-llm` é construído por `build_llm_context_from_request(request)` e pode ser enriquecido com:

- `template_id`: se o frontend envia.
- `document_type_hint`: se o frontend envia.

O RAG usa esse contexto no `generate-document` (e o llm_agent na estrutura e o document_generator nos prompts de cláusulas).

---

## 5. O que o backend FAZ

- Autenticação por sessão e APIs (login/logout, api/me, api/auth/*).
- Multi-tenant por prefeitura (slug na URL).
- Upload de templates DOCX, extração de estrutura, preview (imagem e PDF).
- Geração de documento a partir de template + values (schema index ou tokens).
- Geração de documento via LLM: orquestra chamada ao RAG (generate-document) com contexto do usuário e retorna JSON ou DOCX.
- Proxy para o LLM API (frontend não precisa conhecer porta do llm_api).
- Listagem de templates, preview PDF, área do usuário e autocomplete de secretaria.

---

## 6. O que o backend NÃO FAZ

- Não gera estrutura nem texto jurídico (isso é RAG + llm_agent + llm_api).
- Não hospeda ChromaDB nem embeddings.
- Não persiste histórico de documentos gerados via LLM (apenas retorna ou arquivo na resposta).
- Não valida conteúdo jurídico (conformidade é feita no RAG).
- Mapeamento de campos do template é manual (tokens `{{ }}`); não há IA de mapeamento no upload.

---

## 7. Prompts de teste (indiretos)

O backend não define prompts; apenas envia `user_prompt` ao RAG. Exemplos úteis para testar `api/documentos/gerar-via-llm`:

- `"Gerar termo de referência para aquisição de material de escritório para a Secretaria de Educação."`
- `"Gerar estudo técnico preliminar para coleta seletiva, com estimativa de custos."`
- `"Gerar documento de formalização de demanda para contratação de serviços de TI."`

---

## 8. Possíveis melhorias

- Histórico de gerações (salvar document_type, user_prompt, structure, section_texts, link para DOCX) por usuário/prefeitura.
- Cache de preview PDF para evitar regerar a cada GET.
- Suporte a API token (além de sessão) para integração externa.
- Validação de tamanho/ tipo de arquivo no upload de template.
- Endpoint para “gerar TR a partir do modelo” (template DOCX com placeholders `( ... )`) conforme arquitetura em TR_MODELO_BASE_ANALISE.md.
- Opção de retorno apenas JSON (structure + section_texts) sem chamar render DOCX no RAG quando o frontend quiser só editar antes de baixar.
