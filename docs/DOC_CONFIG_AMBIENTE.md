# Configuração e Ambiente

Documentação das variáveis de ambiente, URLs entre serviços e feature flags do DocMaster Core.

---

## 1. Visão geral

O sistema é composto por quatro processos principais:

- **Django** (backend): porta 8000 (padrão).
- **llm_api**: porta 8002 (orquestração LLM / Ollama).
- **llm_agent**: porta 8003 (estrutura documental).
- **rag_service**: porta 8004 (RAG, ChromaDB, geração de documento).

O Django chama o RAG; o RAG chama o llm_agent e o llm_api; o llm_agent chama o llm_api. O frontend pode chamar o Django e (via proxy) o llm_api.

---

## 2. Variáveis de ambiente por módulo

### 2.1 Django (`backend/mdlicitatech/settings.py`)

| Variável | Default | Descrição |
|----------|---------|-----------|
| `SECRET_KEY` | - | Chave secreta Django |
| `DEBUG` | False | Modo debug |
| `ALLOWED_HOSTS` | - | Hosts permitidos |
| `CORS_ALLOWED_ORIGINS` | (em DEBUG: localhost:5173, 127.0.0.1:5173) | Origens CORS |
| `LLM_API_BASE_URL` | `http://127.0.0.1:8002` | Base URL do llm_api (proxy `/api/llm/<path>`) |
| `RAG_SERVICE_URL` | `http://127.0.0.1:8004` | Base URL do RAG (gerar-via-llm) |

### 2.2 RAG Service (`rag_service/app/config.py`)

| Variável | Default | Descrição |
|----------|---------|-----------|
| `CHROMA_HOST` | localhost | Host do ChromaDB |
| `CHROMA_PORT` | 8000 | Porta do ChromaDB |
| `CHROMA_COLLECTION` | docmaster_docs | Nome da coleção padrão |
| `LLM_ORCHESTRATION_BASE_URL` | http://localhost:8002 | Base URL do llm_api (geração de texto) |
| `LLM_ORCHESTRATION_GENERATE_PATH` | /api/llm/generate | Path do endpoint generate |
| `LLM_AGENT_BASE_URL` | http://localhost:8003 | Base URL do llm_agent (estrutura) |
| `OLLAMA_BASE_URL` | http://localhost:11434 | Base do Ollama (embeddings, quando usado localmente) |
| `RAG_TIMEOUT` | 0 | Timeout HTTP RAG (0 = sem limite) |
| `EMBEDDING_TIMEOUT` | 30.0 | Timeout para embeddings |
| `RAG_TOP_K` | 5 | Número de trechos por retrieval |
| `RAG_POSTPROCESS` | 1 | 1 = pós-processamento de cláusulas ativo |
| `RAG_LLM_SANITIZE` | 1 | 1 = sanitização via LLM ativa (remover meta-comentários) |

### 2.3 LLM Agent (`llm_agent/app/config.py`)

| Variável | Default | Descrição |
|----------|---------|-----------|
| `LLM_ORCHESTRATION_BASE_URL` | http://localhost:8002 | Base URL do llm_api |
| `LLM_ORCHESTRATION_GENERATE_PATH` | /api/llm/generate | Path do generate |
| `AGENT_TIMEOUT` | 120.0 | Timeout em segundos para chamadas ao llm_api |
| `AGENT_MAX_RETRIES` | 2 | Tentativas para corrigir saída inválida (estrutura) |
| `SECTIONS_REGISTRY_PATH` | ../data/sections_registry.json | Caminho do arquivo de registro de seções |
| `REGISTRY_UPDATE_KEY` | "" | Chave para permitir POST /api/agent/registry (header X-Update-Key); vazio pode recusar atualização |

### 2.4 LLM API (`llm_api/app/config.py`)

| Variável | Default | Descrição |
|----------|---------|-----------|
| `OLLAMA_BASE_URL` | http://localhost:11434 | Base do Ollama |
| `LLM_TIMEOUT` | 120.0 | Timeout em segundos |
| `LLM_MAX_RETRIES` | 3 | Retentativas em falha transitória |
| `LLM_AUDIT_LOG_DIR` | None | Diretório de logs de auditoria; se vazio, usa pasta padrão |
| `LLM_ENDPOINT_PLANNER` | /v1/planner | Endpoint planner (relativo ao backend) |
| `LLM_ENDPOINT_SECTION` | /v1/section | Endpoint section |
| `LLM_ENDPOINT_ANALYSIS` | /v1/analysis | Endpoint analysis |
| `OLLAMA_GENERATE_PATH` | /api/generate | Path do generate no Ollama |
| `OLLAMA_MODEL` | llama3.1:8b | Modelo padrão Ollama |

---

## 3. URLs entre serviços (resumo)

| De | Para | URL usada (config) |
|----|------|---------------------|
| Frontend / Django | llm_api | `LLM_API_BASE_URL` (proxy: /api/llm/*) |
| Django | RAG | `RAG_SERVICE_URL` → /api/rag/generate-document |
| RAG | llm_agent | `LLM_AGENT_BASE_URL` → /api/agent/structure-from-prompt, /api/agent/structure |
| RAG | llm_api | `LLM_ORCHESTRATION_BASE_URL` + `LLM_ORCHESTRATION_GENERATE_PATH` |
| llm_agent | llm_api | `LLM_ORCHESTRATION_BASE_URL` + `LLM_ORCHESTRATION_GENERATE_PATH` |
| RAG | ChromaDB | `CHROMA_HOST`:`CHROMA_PORT` |

---

## 4. Feature flags / comportamento

- **RAG_POSTPROCESS** (RAG): Ativa pós-processamento das cláusulas geradas (ex.: normalização, remoção de duplicatas). 0 ou "false" desativa.
- **RAG_LLM_SANITIZE** (RAG): Ativa sanitização via LLM (remover Nota:, section_key:, intros). 0 ou "false" desativa.
- **REGISTRY_UPDATE_KEY** (llm_agent): Se definido, pode ser exigido no header para POST /api/agent/registry; se vazio, implementação pode recusar atualização.
- **LLM_AUDIT_LOG_DIR** (llm_api): Se definido, logs de auditoria vão para esse diretório; caso contrário, usa pasta padrão (ex.: "logs").

---

## 5. Exemplo de .env (desenvolvimento)

Não há `.env` no repositório; as variáveis são lidas com `os.environ.get` e defaults no código. Exemplo de arquivo local (não versionado):

```bash
# Django
DEBUG=1
LLM_API_BASE_URL=http://127.0.0.1:8002
RAG_SERVICE_URL=http://127.0.0.1:8004

# RAG
CHROMA_HOST=localhost
CHROMA_PORT=8000
CHROMA_COLLECTION=docmaster_docs
LLM_ORCHESTRATION_BASE_URL=http://localhost:8002
LLM_AGENT_BASE_URL=http://localhost:8003
RAG_TOP_K=5
RAG_POSTPROCESS=1
RAG_LLM_SANITIZE=1

# LLM Agent
LLM_ORCHESTRATION_BASE_URL=http://localhost:8002
AGENT_TIMEOUT=120
AGENT_MAX_RETRIES=2
SECTIONS_REGISTRY_PATH=/caminho/absoluto/data/sections_registry.json

# LLM API
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
LLM_TIMEOUT=120
LLM_MAX_RETRIES=3
# LLM_AUDIT_LOG_DIR=/var/log/docmaster/llm
```

---

## 6. Ordem de inicialização sugerida (dev)

1. ChromaDB (se em servidor separado).
2. Ollama (modelo carregado).
3. llm_api (porta 8002).
4. llm_agent (porta 8003).
5. rag_service (porta 8004).
6. Django (porta 8000).

Assim, todas as dependências estão de pé quando o usuário chama "gerar via LLM" no frontend.
