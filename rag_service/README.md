# DocMaster IA – RAG Service

**Retrieval-Augmented Generation** module for ingestion, vector search, and contextual generation. Integrates **LangChain** and **ChromaDB**.

## Requirements

- **ChromaDB** installed and running on the server (or via Docker)
- **Ollama** with an embeddings model (e.g. `nomic-embed-text`) and a generation model
- **llm_api** for response generation (optional; Ollama can be used directly)

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/rag/health` | Health check + ChromaDB status |
| POST | `/api/rag/ingest` | Ingests text into the vector store |
| POST | `/api/rag/query` | RAG query (retrieval + generation) |
| GET | `/api/rag/collections` | Lists collections |
| DELETE | `/api/rag/collections/{name}` | Removes a collection |

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CHROMA_HOST` | localhost | ChromaDB host |
| `CHROMA_PORT` | 8000 | ChromaDB port |
| `CHROMA_COLLECTION` | docmaster_docs | Default collection |
| `OLLAMA_BASE_URL` | http://localhost:11434 | Ollama URL (embeddings) |
| `LLM_ORCHESTRATION_BASE_URL` | http://localhost:8002 | llm_api URL |
| `RAG_TOP_K` | 5 | Passages to retrieve per query |
| `RAG_TIMEOUT` | 0 | Timeout for the LLM call (s); 0 = no limit |

## Local usage

```bash
# From the project root
uvicorn rag_service.app.main:app --reload --host 0.0.0.0 --port 8004
```

## Docker

```bash
docker compose up -d rag_service
```

Interactive docs: http://localhost:8004/docs

## Generated text quality

Clause generation uses the model configured in **llm_api** (Ollama). Default model: `OLLAMA_MODEL=llama3.1:8b` (set in llm_api).

To improve Portuguese, accents, and reduce leftover markdown:
- **Prompts** reinforce: always pt-BR, no markdown, correct accents.
- **Post-processing** (_postprocess_clause_text): fixes clear typos and strips leftover markdown.
- **LLM sanitization** (RAG_LLM_SANITIZE=1): the model removes meta-comments (intros, notes, section_key) — it does not depend on a hand-maintained regex list.
- Disable post-processing: `RAG_POSTPROCESS=0`. Disable LLM sanitization: `RAG_LLM_SANITIZE=0`.

To switch models, set `OLLAMA_MODEL` in llm_api (e.g. `llama3.2`, `mistral`, `phi3`).
