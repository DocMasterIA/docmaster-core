# Análise detalhada do rag_service

Documento técnico com análise de arquitetura, módulos, fluxos, dependências e recomendações do **rag_service** do DocMaster Core.

---

## 1. Visão geral

O **rag_service** é um serviço **FastAPI** (porta 8004) que concentra:

- **Ingestão** de documentos (texto, PDF, DOCX) no ChromaDB com embeddings (Ollama/nomic-embed-text).
- **Retrieval** (RAG) com filtro por `document_type` (lei, guia, etp, dfd, termo_referencia).
- **Geração de documento completo** a partir de prompt livre: estrutura via llm_agent + textos por seção via LLM + montagem DOCX/PDF.
- **Geração TR/DFD a partir de modelo fixo**: slots preenchidos por IA (tr_slots_llm) + substituição em DOCX (tr_template, dfd_template).
- **Análise de documentos** contra a Lei 14.133 (document_analyzer): extração, chunking, RAG lei/guia, LLM por chunk, agregação e resumo executivo.
- **Conformidade** de texto isolado (check_compliance) e **classificação** de tipo + extração de seções (classify, sem indexar).

**Não faz**: autenticação (Django faz), OCR, persistência de usuário/prefeitura, validação jurídica automática.

---

## 2. Estrutura de arquivos e responsabilidades

| Arquivo | Responsabilidade |
|---------|------------------|
| `app/main.py` | Ponto de entrada FastAPI; delega `create_app()` em `api.py`. |
| `app/config.py` | Variáveis de ambiente: ChromaDB, URLs llm_api/llm_agent, timeouts, RAG_TOP_K, RAG_POSTPROCESS, RAG_LLM_SANITIZE. |
| `app/api.py` | Rotas FastAPI (`/api/rag/*`), schemas de request inline (GenerateDocumentRequest, RenderDocumentRequest, SmartIngest*, GenerateTR*, GenerateDFD*), `create_app()`. |
| `app/schemas.py` | Modelos Pydantic de entrada/saída: Ingest, Query, Collections, Health, CheckCompliance, AnalyzeDocumentResponse. |
| `app/chroma_client.py` | Cliente ChromaDB HTTP, get_or_create_collection, list_collections, delete_collection. |
| `app/ingestion.py` | split_text (RecursiveCharacterTextSplitter), ingest_text (LangChain Chroma + OllamaEmbeddings). |
| `app/retrieval.py` | retrieve (com `where` opcional), generate_answer (llm_api), check_compliance (lei + LLM SIM/NÃO). |
| `app/loaders.py` | load_pdf_text (pypdf), load_docx_text (docx2txt), load_document_text, get_file_metadata. |
| `app/document_generator.py` | Orquestração: structure-from-prompt (llm_agent), RAG por seção, geração de texto (cláusula, lista, tabela) via LLM, pós-processamento e sanitização. |
| `app/docx_generator.py` | json_to_docx (structure + section_texts + table_data), docx_to_pdf (LibreOffice headless), json_to_docx_and_pdf. |
| `app/document_analyzer.py` | analyze_document: load_document_text, extract_sections, chunking, RAG lei/guia, LLM por chunk, merge + dedup + resumo executivo. |
| `app/document_classifier.py` | detect_document_type (DFD/ETP/TR/outro), extract_sections (numeradas ou maiúsculas), ExtractedSection, KNOWN_SECTIONS. |
| `app/smart_ingest.py` | smart_ingest_file (tipo por path ou explícito, seções ou lei por Art. X), smart_ingest_folder, get_sections_summary. |
| `app/manual_ingest.py` | ingest_manual: document_type=guia, chunking conceitual, tipo_documento (etp, dfd, termo_referencia, geral). |
| `app/tr_template.py` | TR_modelo_base.docx: TRTemplateSlots, render_tr_from_slots (placeholders em parágrafos/tabelas, _fill_items_table). |
| `app/tr_slots_llm.py` | fill_tr_slots_with_llm: structure-from-prompt (llm_agent) + prompt TR slots + parse JSON + _choose_art75_inciso; mescla slots_override. |
| `app/dfd_template.py` | DFD_modelo_base.docx: render_dfd_from_tr_slots (objeto, justificativa, cidade a partir de TRTemplateSlots). |

---

## 3. Configuração (config.py)

- **ChromaDB**: `CHROMA_HOST`, `CHROMA_PORT`, `CHROMA_COLLECTION`.
- **LLM**: `LLM_ORCHESTRATION_BASE_URL`, `LLM_ORCHESTRATION_GENERATE_PATH`, `LLM_AGENT_BASE_URL`, `OLLAMA_BASE_URL`.
- **Timeouts**: `RAG_TIMEOUT` (0 = sem limite), `RAG_HTTP_TIMEOUT` derivado, `EMBEDDING_TIMEOUT`.
- **Retrieval**: `RAG_TOP_K`.
- **Comportamento**: `RAG_POSTPROCESS` (pós-processamento de cláusulas), `RAG_LLM_SANITIZE` (remoção de meta-comentários via LLM).

Não há validação de URL nem health check de Chroma/Ollama na inicialização; falhas aparecem na primeira requisição.

---

## 4. API (api.py) – Endpoints

| Método | Path | Função |
|--------|------|--------|
| GET | `/api/rag/health` | Health + conexão ChromaDB. |
| POST | `/api/rag/ingest` | Ingestão de texto (IngestRequest). |
| POST | `/api/rag/query` | RAG: retrieve + opcional generate_answer. |
| POST | `/api/rag/generate-document` | generate_full_document + opcional json_to_docx_and_pdf; query: output_docx, format, inspect. |
| POST | `/api/rag/render-document` | Só render: structure + section_texts + table_data → DOCX/PDF. |
| POST | `/api/rag/check-compliance` | check_compliance (texto vs Lei 14.133). |
| GET | `/api/rag/collections` | list_collections. |
| DELETE | `/api/rag/collections/{name}` | delete_collection. |
| POST | `/api/rag/ingest-manual` | ingest_manual (file ou path); document_type=guia. |
| POST | `/api/rag/smart-ingest/file` | smart_ingest_file. |
| POST | `/api/rag/smart-ingest/folder` | smart_ingest_folder. |
| GET | `/api/rag/summary` | get_sections_summary. |
| POST | `/api/rag/analyze-document` | analyze_document (file ou path + top_k). |
| POST | `/api/rag/classify` | classify: tipo + extract_sections, sem indexar. |
| POST | `/api/rag/generate-tr-from-model` | fill_tr_slots_with_llm + render_tr_from_slots; opcional DFD complementar. |
| POST | `/api/rag/generate-tr-and-dfd-zip` | TR + DFD em ZIP (teste). |

Helpers: `_check_chroma()`, `_merge_user_context_into_tr_slots()` (fiscal.nome, nome_usuario, secretaria_usuario, cidade, cidade_estado, codigo_uf a partir de `context.usuario`).

---

## 5. document_generator – Orquestração da geração “do zero”

### 5.1 Fluxo (generate_full_document)

1. **Estrutura**: `_call_llm_agent_structure(user_prompt)` → POST llm_agent `/api/agent/structure-from-prompt` → `structure`, `context`, `especificacoes`.
2. **Contexto**: merge de `context` do llm_agent com `context_override` (Django: usuario, template_id, document_type_hint). `document_type` e filtro RAG (`doc_type_filter`) podem ser sobrescritos por `document_type_hint`.
3. **Seções de texto**: para cada seção `content_type=text`, query RAG com `where={"document_type": doc_type_filter}`, fallback sem filtro; monta `rag_context`, sanitiza lei (8.666/8.333 → 14.133), marca citações legais puras; chama `_generate_clause_text` (LLM) e aplica `_llm_sanitize_meta_comments` + `_postprocess_clause_text`.
4. **Seções lista**: idem com `_generate_list_content` e `_postprocess_list_text`.
5. **Tabelas**: table_data inicial de `especificacoes.tabelas.linhas_sugeridas`; para seções table sem dados, `_generate_table_rows` (LLM → JSON de linhas).
6. **Retorno**: structure, section_texts, document_type, context, especificacoes, table_data.

### 5.2 Prompts e pós-processamento

- **CLAUSE_COMPOSITION_SYSTEM_PROMPT**: composição jurídica, pt-BR, sem markdown/placeholders/intros, Lei 14.133, sem repetição.
- **LIST_COMPOSITION_SYSTEM_PROMPT**: itens de lista, um por linha, sem numeração/marcadores na saída.
- **TABLE_ROWS_SYSTEM_PROMPT**: array JSON de objetos por coluna.
- **LLM_SANITIZE_PROMPT**: remoção de Nota:, section_key:, intros (usado quando RAG_LLM_SANITIZE ativo).
- **Instruções por seção**: `_get_section_specific_instructions(section_key, for_list, document_type)` – ETP (objeto, conclusão, solução proposta, conformidade, alternativas, riscos), contratada/contratante, critérios, justificativa, prazo, garantia, etc.
- **ETP**: `_get_etp_preamble()` injetado no prompt quando document_type é ETP.
- **Pós-processamento** (`_postprocess_clause_text`): markdown, §/art., “presente artigo” → “nesta seção”, leis 8.666/8.333 → 14.133, placeholders genéricos, typos (acatuladoras→acautelatórias, etc.), remoção de meta-comentários e de parágrafos de citação legal pura, remoção de duplicatas, cabeçalhos repetidos.
- **Contexto RAG**: `_sanitize_rag_context_for_legislation`, `_mark_pure_legal_citations_in_rag` para reduzir cópia literal de lei.

### 5.3 Dependências

- **llm_agent**: estrutura e contexto (obrigatório para generate-document).
- **llm_api**: todas as gerações de texto (cláusula, lista, tabela, sanitização).
- **ChromaDB**: retrieve por seção com filtro document_type; coleção padrão ou passada no request.

---

## 6. docx_generator

- **json_to_docx**: structure.root_sections percorridas recursivamente; por nó: título (Heading 1/2/3), conteúdo text (parágrafos), table (cabeçalho + table_data), list (bullets). Estilos: Times New Roman, cor preta; bordas em tabelas.
- **docx_to_pdf**: subprocess LibreOffice headless; falha silenciosa (retorna None) se LibreOffice não instalado ou erro.
- **json_to_docx_and_pdf**: gera DOCX em temp dir (ou output_dir/base_name), depois PDF; retorna docx_path, pdf_path, pdf_available.

Não há tratamento de caracteres especiais nem de tamanho máximo de documento; tabelas sem table_data recebem uma linha vazia como placeholder.

---

## 7. document_analyzer

- **Entrada**: path (DOCX/PDF) ou text.
- **Classificação**: `_infer_document_type` (detect_document_type; heurística ETP no início do texto).
- **Chunking**: `_build_analysis_chunks`: por seção (extract_sections) com limite MAX_SECTION_CHARS (2.800), ou por parágrafo.
- **Por chunk**: RAG com `where={"document_type": "lei"}`, fallback "outro" + filtro por source_file; opcional RAG `document_type=guia` (até 2 trechos). Prompt ANALYSIS_SYSTEM_PROMPT + ANALYSIS_USER_PROMPT_TEMPLATE; resposta em JSON (pontos_importantes, acertos, ressalvas, erros, riscos_juridicos, sugestoes_reescrita, conformidade_geral, observacoes).
- **Agregação**: `_merge_analysis_results`: dedup, remoção de subsumidos, merge por overlap de palavras, remoção de hedges (especulativos), acertos ambíguos → ressalvas, remoção de contradições acerto/erro.
- **Resumo executivo**: `_generate_resumo_executivo` (uma chamada LLM com resultado agregado).

Limites de itens por lista (ex.: 15 acertos, 12 ressalvas) e tratamento de HTML/encoding em `_decode_html`, `_ensure_str`.

---

## 8. document_classifier

- **DocumentType**: TERMO_REFERENCIA, ETP, DFD, OUTRO.
- **detect_document_type**: busca no início do texto (search_limit 1500); ordem DFD → ETP → TR (DFD primeiro para não confundir com TR citado no corpo).
- **extract_sections**: regex para seções numeradas (1. TÍTULO, 2.1 SUBTÍTULO) e não numeradas (linha em maiúsculas); preenche conteúdo entre seções; normalização por KNOWN_SECTIONS → key (objeto, justificativa, obrigacoes_contratada, etc.).

Usado por smart_ingest, manual_ingest e document_analyzer.

---

## 9. smart_ingest e manual_ingest

- **smart_ingest_file**: load_document_text; tipo por `_infer_document_type_from_path` (pasta pai: etp, dfd, termo_referencia, lei, outro) ou explícito. Lei: split por "Art. X"; demais: extract_sections ou texto inteiro em chunks (RecursiveCharacterTextSplitter 500 chars). Metadados: document_type, section_key, section_title, chunk_index. Chroma add_documents.
- **smart_ingest_folder**: glob PDF/DOCX, chama smart_ingest_file por arquivo; summary com total_files, success_count, error_count, by_type.
- **get_sections_summary**: collection.get(include=["metadatas"]), agrega por document_type e section_key (sem paginação; pode ser pesado em coleções grandes).
- **manual_ingest**: document_type=guia fixo; extract_sections + _chunk_for_conceptual_use (parágrafos, max 600 chars); metadados tipo_documento (etp, dfd, termo_referencia, geral). Batch add (CHROMA_ADD_BATCH_SIZE 2000).

---

## 10. tr_template, tr_slots_llm, dfd_template

- **tr_template**: TR_modelo_base.docx; TRTemplateSlots (objeto, dispensa, itens, justificativa, fiscal, dotacao, nome_usuario, secretaria_usuario, cidade_estado, cidade, codigo_uf, etc.). Substituição exata de strings em parágrafos e células; tabela de itens reconstruída (cabeçalho + linhas ItemSlot). _clear_headers remove cabeçalho do modelo.
- **tr_slots_llm**: structure-from-prompt (llm_agent) + prompt TR_SLOTS_SYSTEM_PROMPT (JSON objeto, dispensa art.75/inciso I–XV, itens, justificativa, fiscal, dotacao vazia) + _parse_llm_json_response. Opcional _choose_art75_inciso em chamada separada. Mescla slots_override e context.usuario (fiscal.nome, etc.) com prioridade para override.
- **dfd_template**: DFD_modelo_base.docx; placeholders objeto, justificativa, cidade preenchidos a partir de TRTemplateSlots; sem IA.

---

## 11. retrieval

- **retrieve**: LangChain Chroma, search_kwargs k e filter (where); retorno lista de dicts (content, score quando disponível, metadata). Embeddings: Ollama nomic-embed-text.
- **generate_answer**: concatena context_docs, monta prompt e POST llm_api `/api/llm/generate`; extrai texto de data.response ou data.text.
- **check_compliance**: retrieve com where document_type=lei (fallback outro + filtro por source_file); prompt parecerista Lei 14.133; parse SIM/NÃO da primeira linha; retorna compliant, observations, relevant_articles.

---

## 12. ingestion e chroma_client

- **ingestion**: RecursiveCharacterTextSplitter (1000/200), Document LangChain com metadata; OllamaEmbeddings; Chroma.add_documents. Usado pelo endpoint /ingest (texto bruto).
- **chroma_client**: chromadb.HttpClient(host, port), get_or_create_collection com metadata descritiva; list_collections retorna nomes; delete_collection sem tratamento fino de erro.

---

## 13. Dependências externas

| Dependência | Uso |
|-------------|-----|
| ChromaDB (servidor) | Vector store; deve estar rodando e acessível. |
| Ollama | Embeddings (nomic-embed-text); usado em ingestion, retrieval, smart_ingest, manual_ingest. |
| llm_api | Geração de texto (generate), check_compliance, document_analyzer, tr_slots_llm, sanitização. |
| llm_agent | structure-from-prompt (generate-document e tr_slots_llm). |
| LibreOffice | docx_to_pdf (opcional). |
| pypdf, docx2txt | loaders. |
| python-docx | docx_generator, tr_template, dfd_template. |
| LangChain (langchain_chroma, langchain_community.embeddings, langchain_text_splitters, langchain_core.documents) | Ingestão e retrieval. |
| httpx | Chamadas async a llm_api e llm_agent. |

---

## 14. Pontos fortes

- Separação clara: ingestão, retrieval, geração, análise, TR/DFD por modelo.
- Um único ponto de configuração (config.py) e contratos bem definidos (schemas + request/response na API).
- Geração “do zero” e “por modelo” coexistem; contexto Django (usuario) integrado em ambos.
- Pós-processamento rico (cláusulas, listas) e sanitização por LLM reduzem meta-comentários e leis revogadas.
- Análise de documento com agregação, dedup, resumo executivo e filtro lei/guia.
- TR/DFD com art. 75 incisos I–XV e slots bem documentados.

---

## 15. Riscos e limitações

- **Disponibilidade**: se ChromaDB ou Ollama estiverem fora, a maioria dos endpoints falha; não há circuit breaker nem fallback.
- **Timeout**: RAG_TIMEOUT=0 pode travar requisições longas; timeouts são por chamada httpx, não por operação agregada.
- **Tamanho**: documentos muito grandes (analyze-document, ingest) podem estourar memória ou contexto LLM; limites (MAX_SECTION_CHARS, MAX_LAW_CHUNK_CHARS) são fixos.
- **PDF**: sem OCR; PDFs escaneados não são suportados.
- **Concorrência**: Chroma add_documents e retrieve são síncronos no uso do LangChain; muitas requisições simultâneas podem sobrecarregar Chroma/Ollama.
- **LibreOffice**: docx_to_pdf falha sem mensagem estruturada ao usuário; pdf_available=False é o único indicador.
- **get_sections_summary**: carrega todos os metadados da coleção; em coleções grandes pode ser lento ou estourar memória.

---

## 16. Recomendações de melhoria

1. **Health check**: incluir no /health verificação de conectividade com Ollama (e opcionalmente llm_agent/llm_api) e indicar degradação (ex.: chroma_ok mas ollama_ok=false).
2. **Timeouts**: definir timeout máximo por request agregado (ex.: generate-document) e retornar 504 com mensagem clara.
3. **Limites de tamanho**: validar tamanho de arquivo em ingest-manual e analyze-document; rejeitar com 413 ou mensagem explícita.
4. **PDF**: documentar claramente “sem OCR” e, se possível, retornar erro amigável quando o PDF não tiver texto extraível.
5. **Docx_generator**: em falha do LibreOffice, registrar log e opcionalmente retornar em resposta JSON que o PDF não está disponível (além de pdf_available=false).
6. **get_sections_summary**: para coleções grandes, usar paginação ou amostragem no Chroma e documentar limite.
7. **Testes**: testes de integração para generate-document (mock llm_agent/llm_api) e para analyze-document (mock RAG/LLM); testes unitários para _postprocess_clause_text, _merge_analysis_results, _parse_llm_json_response.
8. **Observabilidade**: métricas (contagem de requests por endpoint, latência, erros) e tracing (request_id) para debug em produção.

---

*Documento gerado com base na leitura do código do rag_service (fev/2025).*
