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
| `RAG_TIMEOUT` | 0 | Timeout para chamada LLM (s); 0 = sem limite |

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

## Qualidade do texto gerado

A geração de cláusulas usa o modelo configurado no **llm_api** (Ollama). Modelo padrão: `OLLAMA_MODEL=llama3.1:8b` (definido no llm_api).

Para melhorar português, acentuação e reduzir markdown residual:
- **Prompts** reforçam: sempre pt-BR, sem markdown, acentuação correta.
- **Pós-processamento** (_postprocess_clause_text): remove **negrito**, corrige § 1o→§ 1º, residuos→resíduos, etc.

Para trocar o modelo, defina `OLLAMA_MODEL` no llm_api (ex.: `llama3.2`, `mistral`, `phi3`).
