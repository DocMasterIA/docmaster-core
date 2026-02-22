# RAG Service (FastAPI)

Documentação do serviço **rag_service**: ingestão, retrieval (ChromaDB), geração de documento completo, análise de conformidade, renderização DOCX/PDF.

---

## 1. Base URL e porta

- **Base**: `http://localhost:8004` (ou valor de `RAG_SERVICE_URL` no Django).
- **Prefixo das rotas**: `/api/rag`.
- **Inicialização**: `rag_service/app/main.py` → `create_app()` em `rag_service/app/api.py`.

---

## 2. Endpoints

| Método | URL | Descrição |
|--------|-----|-----------|
| GET | `/api/rag/health` | Health check + status ChromaDB |
| POST | `/api/rag/ingest` | Ingestão de texto no vector store |
| POST | `/api/rag/query` | Consulta RAG (retrieval + opcional resposta LLM) |
| POST | `/api/rag/generate-document` | Geração de documento completo (estrutura + textos; opcional DOCX) |
| POST | `/api/rag/render-document` | Renderizar structure + section_texts/table_data em DOCX/PDF |
| POST | `/api/rag/check-compliance` | Verificar texto contra Lei 14.133 |
| GET | `/api/rag/collections` | Listar coleções ChromaDB |
| DELETE | `/api/rag/collections/{name}` | Remover coleção |
| POST | `/api/rag/ingest-manual` | Ingestão de manual/guia (upload ou path) |
| POST | `/api/rag/smart-ingest/file` | Ingestão de arquivo com extração de seções |
| POST | `/api/rag/smart-ingest/folder` | Ingestão de pasta (PDFs/DOCXs) |
| GET | `/api/rag/summary` | Resumo das seções indexadas por tipo |
| POST | `/api/rag/analyze-document` | Analisar documento (upload ou path) vs Lei 14.133 |
| POST | `/api/rag/classify` | Classificar tipo e extrair seções (sem indexar) |

---

## 3. Contratos principais (request/response)

### 3.1 GET `/api/rag/health`

- **Response**: `HealthResponse`: `ok`, `chroma_connected`, `message`.

### 3.2 POST `/api/rag/ingest`

- **Body**: `IngestRequest`: `text` (obrigatório), `metadata` (opcional), `collection` (opcional).
- **Response**: `IngestResponse`: `ok`, `message`, `chunks_added`, `collection`, `error`.

### 3.3 POST `/api/rag/query`

- **Body**: `QueryRequest`: `query`, `collection`, `top_k`, `include_sources` (default true), `generate_answer` (default true).
- **Response**: `QueryResponse`: `ok`, `answer`, `sources` (lista de `RetrievedChunk`), `error`.

### 3.4 POST `/api/rag/generate-document`

- **Body**: `GenerateDocumentRequest`: `user_prompt` (obrigatório), `collection`, `top_k_per_section` (default 5), `context` (opcional: usuario, template_id, document_type_hint).
- **Query**: `output_docx` (bool, default false), `format` ("docx" | "json"), `inspect` (bool, com format=json retorna docx em base64 para debug).
- **Response**: JSON com `ok`, `structure`, `section_texts`, `table_data`; se `output_docx=true` e `format=docx` pode retornar `FileResponse` (DOCX). Inclui `docx_path`, `pdf_path`, `pdf_available` quando gera arquivo.

### 3.5 POST `/api/rag/render-document`

- **Body**: `RenderDocumentRequest`: `structure`, `section_texts`, `table_data` (opcional).
- **Query**: `format`: "docx" (retorna arquivo) ou "json" (retorna paths).
- **Response**: FileResponse DOCX ou JSON com `docx_path`, `pdf_path`, `pdf_available`.

### 3.6 POST `/api/rag/check-compliance`

- **Body**: `CheckComplianceRequest`: `text`, `collection`, `top_k` (default 5).
- **Response**: `CheckComplianceResponse`: `ok`, `compliant`, `observations`, `relevant_articles`, `error`.

### 3.7 POST `/api/rag/ingest-manual`

- **Form**: `file` (upload) **ou** `path` (caminho servidor), `collection` (opcional).
- **Response**: `ok`, mensagem e dados retornados por `ingest_manual` (chunks, collection, etc.).

### 3.8 POST `/api/rag/smart-ingest/file`

- **Body**: `SmartIngestFileRequest`: `path`, `collection`, `extra_metadata`, `document_type` (opcional; inferido por path se omitido).
- **Response**: JSON `ok` + resultado de `smart_ingest_file`.

### 3.9 POST `/api/rag/smart-ingest/folder`

- **Body**: `SmartIngestFolderRequest`: `folder_path`, `collection`, `extra_metadata`, `recursive` (default true), `document_type` (opcional).
- **Response**: JSON `ok` + resultado de `smart_ingest_folder`.

### 3.10 GET `/api/rag/summary`

- **Query**: `collection` (opcional).
- **Response**: `ok` + resumo por tipo de documento e seção (`get_sections_summary`).

### 3.11 POST `/api/rag/analyze-document`

- **Form**: `file` (upload) **ou** `path`; **Query**: `top_k` (default 8), `collection`.
- **Response**: `AnalyzeDocumentResponse`: `ok`, `document_type`, `sections_detected`, `pontos_importantes`, `acertos`, `erros`, `conformidade_geral`, `observacoes`, `error`.

### 3.12 POST `/api/rag/classify`

- **Body**: `SmartIngestFileRequest` (path, document_type opcional).
- **Response**: `ok`, `document_type`, `inferred_from`, `sections_found`, `sections` (key, title, number, content_preview). Não indexa.

---

## 4. Módulos e funções (serviços)

| Módulo | Funções principais | Descrição |
|--------|---------------------|-----------|
| `chroma_client` | `get_chroma_client`, `get_or_create_collection`, `list_collections`, `delete_collection` | Cliente ChromaDB e coleções |
| `ingestion` | `split_text`, `ingest_text` | Chunking e ingestão de texto |
| `loaders` | `load_pdf_text`, `load_docx_text`, `load_document_text`, `get_file_metadata` | Carregar texto de PDF/DOCX |
| `retrieval` | `retrieve`, `generate_answer`, `check_compliance` | Busca vetorial, resposta LLM, conformidade Lei 14.133 |
| `document_generator` | `generate_full_document` | Orquestra llm_agent (estrutura) + RAG + LLM (textos de cláusulas/listas/tabelas) |
| `document_analyzer` | `analyze_document` | Análise de documento vs Lei 14.133 (RAG + LLM) |
| `document_classifier` | `detect_document_type`, `extract_sections`, `classify_and_extract` | Tipo e seções (sem indexar) |
| `smart_ingest` | `smart_ingest_file`, `smart_ingest_folder`, `get_sections_summary` | Ingestão com classificação por path/tipo |
| `manual_ingest` | `ingest_manual` | Ingestão de manual/guia (document_type=guia) |
| `docx_generator` | `json_to_docx`, `docx_to_pdf`, `json_to_docx_and_pdf` | Montagem DOCX/PDF a partir de structure + section_texts + table_data |

---

## 5. Prompts e contextos (document_generator)

- **CLAUSE_COMPOSITION_SYSTEM_PROMPT**: Composição de cláusulas jurídicas (texto completo, sem meta-comentários, pt-BR, Lei 14.133, sem markdown/placeholders).
- **LIST_COMPOSITION_SYSTEM_PROMPT**: Geração de itens de lista (um por linha, sem numeração/marcadores na saída).
- **TABLE_ROWS_SYSTEM_PROMPT** (e variantes): Geração de linhas de tabela a partir de schema e contexto.
- **LLM_SANITIZE_PROMPT**: Remoção de meta-comentários do texto gerado (Nota:, section_key:, etc.).
- **Contexto**: Montado por `_format_user_context(context)` (usuario, objeto, orgao, etc.) e `_format_especificacoes(especificacoes)` (listas/tabelas do interpretador). Instruções por seção em `_get_section_specific_instructions(document_type, section_key)`.

Contexto enviado ao RAG vem do backend (build_llm_context_from_request) + body do generate-document (`context` override).

---

## 6. Prompts de teste

- **Query RAG**:  
  `POST /api/rag/query`  
  Body: `{"query": "Quais são as obrigações da contratada no termo de referência?", "collection": null, "generate_answer": true}`

- **Generate document**:  
  `POST /api/rag/generate-document`  
  Body: `{"user_prompt": "Gerar termo de referência para aquisição de material de escritório", "context": {"usuario": {"nome_completo": "Fulano", "secretaria": "Educação", "prefeitura": "Prefeitura X", "orgao": "Secretaria de Educação"}}, "top_k_per_section": 5}`  
  Query: `output_docx=true&format=docx` para receber o DOCX.

- **Check compliance**:  
  `POST /api/rag/check-compliance`  
  Body: `{"text": "A contratada deverá entregar os bens em 30 dias.", "collection": null, "top_k": 5}`

- **Analyze document**:  
  `POST /api/rag/analyze-document`  
  Form: `path=/caminho/no/servidor/documento.pdf` ou upload em `file`; Query: `top_k=8`.

- **Classify (sem indexar)**:  
  `POST /api/rag/classify`  
  Body: `{"path": "/caminho/ETP_exemplo.pdf"}`.

---

## 7. O que o RAG Service FAZ

- Ingestão de texto (e arquivos via smart-ingest / ingest-manual) no ChromaDB com metadados (document_type, section, etc.).
- Retrieval por similaridade e geração de resposta com LLM (query).
- Geração de documento completo: interpreta prompt (via llm_agent), obtém estrutura, recupera exemplos por seção, gera textos de cláusulas/listas/tabelas via LLM, monta DOCX/PDF.
- Renderização de structure + section_texts + table_data em DOCX (e PDF se LibreOffice disponível).
- Verificação de conformidade de texto com a Lei 14.133 (check-compliance).
- Análise de documento (upload ou path) vs Lei 14.133 (analyze-document).
- Classificação de tipo e extração de seções (classify) sem indexar.
- Listagem e exclusão de coleções.

---

## 8. O que o RAG Service NÃO FAZ

- Não autentica usuários (consumido por backend Django que já autenticou).
- Não persiste usuário/prefeitura (recebe contexto no body).
- Não faz OCR; análise/ingestão apenas em documentos com texto nativo (PDF/DOCX).
- Geração de documento “a partir de template TR com placeholders” ainda não implementada (ver TR_MODELO_BASE_ANALISE.md).

---

## 9. Possíveis melhorias

- Endpoint “gerar TR a partir do modelo” (template DOCX + placeholders `( ... )`): extrair slots, preencher via LLM, montar DOCX.
- Suporte a stream de geração (SSE) para feedback em tempo real no frontend.
- Cache de embeddings ou de resultados de retrieval por (query, collection, top_k).
- Limite de tamanho de arquivo e timeout explícito em ingest-manual e analyze-document.
- Documentar dependência do LibreOffice para PDF e fallback quando não disponível.
- Opção de retornar apenas structure + section_texts (sem chamar docx_generator) para edição no frontend antes de render.
