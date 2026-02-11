# DocMaster IA – Serviço RAG

Módulo de **Retrieval-Augmented Generation** para ingestão, busca vetorial e geração contextualizada. Integra **LangChain** e **ChromaDB**.

## Requisitos

- **ChromaDB** instalado e rodando no servidor (ou via Docker)
- **Ollama** com modelo de embeddings (ex.: `nomic-embed-text`) e modelo de geração
- **llm_api** para geração de respostas (opcional; pode usar Ollama diretamente)

## Endpoints

| Método | Path | Descrição |
|--------|------|-----------|
| GET | `/api/rag/health` | Health check + status ChromaDB |
| POST | `/api/rag/ingest` | Ingere texto no vector store |
| POST | `/api/rag/query` | Consulta RAG (retrieval + geração) |
| GET | `/api/rag/collections` | Lista coleções |
| DELETE | `/api/rag/collections/{name}` | Remove coleção |

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `CHROMA_HOST` | localhost | Host do ChromaDB |
| `CHROMA_PORT` | 8000 | Porta do ChromaDB |
| `CHROMA_COLLECTION` | docmaster_docs | Coleção padrão |
| `OLLAMA_BASE_URL` | http://localhost:11434 | URL do Ollama (embeddings) |
| `LLM_ORCHESTRATION_BASE_URL` | http://localhost:8002 | URL do llm_api |
| `RAG_TOP_K` | 5 | Trechos a recuperar por query |
| `RAG_TIMEOUT` | 60 | Timeout para chamada LLM (s) |

## Uso local

```bash
# Na raiz do projeto
uvicorn rag_service.app.main:app --reload --host 0.0.0.0 --port 8004
```

## Docker

```bash
docker compose up -d rag_service
```

Documentação interativa: http://localhost:8004/docs
