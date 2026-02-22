# LLM API (Orquestração FastAPI)

Documentação do **llm_api**: camada de orquestração que fala com o Ollama (ou outro backend LLM), expondo endpoints planner, section, analysis e generate.

---

## 1. Base URL e porta

- **Base**: `http://localhost:8002` (ou valor de `LLM_API_BASE_URL` no Django / `LLM_ORCHESTRATION_BASE_URL` no RAG e no agent).
- **Prefixo das rotas**: `/api/llm`.
- **Inicialização**: `llm_api/app/main.py`; router em `llm_api/app/api/routes.py`.

---

## 2. Endpoints

| Método | URL | Descrição |
|--------|-----|-----------|
| POST | `/api/llm/planner` | Chamada tipo planner (prompt, context, options) |
| POST | `/api/llm/section` | Chamada tipo section (prompt, section_id, context) |
| POST | `/api/llm/analysis` | Análise/avaliação de documento (document, context, options); não gera nem modifica |
| POST | `/api/llm/generate` | Chamada direta ao Ollama /api/generate (prompt, model, stream) |
| GET | `/api/llm/test-audit` | Testar gravação do diretório de auditoria |
| GET | `/api/llm/health` | Health check do serviço |

---

## 3. Contratos principais

### 3.1 POST `/api/llm/planner`

- **Body**: `PlannerRequest`: `prompt`, `context` (opcional), `options` (opcional).
- **Response**: `{"ok": true, "data": <result>}` onde result é o retorno do backend (ou `{"raw": result}`). Erros: 401, 429, 502, 504, 400 conforme exceções do adapter.

### 3.2 POST `/api/llm/section`

- **Body**: `SectionRequest`: `prompt`, `section_id` (opcional), `context` (opcional).
- **Response**: Mesmo formato do planner.

### 3.3 POST `/api/llm/analysis`

- **Body**: `AnalysisRequest`: `document`, `context` (opcional), `options` (opcional).
- **Response**: Mesmo formato; usado para análise de editais/documentos (avaliação sem gerar).

### 3.4 POST `/api/llm/generate`

- **Body**: `GenerateRequest`: `prompt` (obrigatório), `model` (opcional), `stream` (opcional, default false).
- **Comportamento**: Chama o Ollama em `OLLAMA_BASE_URL + OLLAMA_GENERATE_PATH` (default `/api/generate`) com o modelo `OLLAMA_MODEL` (default `llama3.1:8b`) se model não for informado.
- **Response**: `{"ok": true, "data": <ollama_response>}` (response, model, done, etc.). Erros mapeados para 401, 429, 502, 504, 400.

### 3.5 GET `/api/llm/test-audit`

- **Response**: `{"ok": true, "message": "Log de auditoria gravado", "dir": "<path>"}` ou `{"ok": false, "error": "...", "dir": "..."}`. Grava uma linha de teste no diretório de auditoria.

### 3.6 GET `/api/llm/health`

- **Response**: `{"status": "ok", "service": "llm-orchestration"}`.

---

## 4. Módulos e funções

| Módulo | Funções principais | Descrição |
|--------|---------------------|-----------|
| `adapter` | `generate`, `planner`, `section` | Chamadas ao Ollama/backend (generate usa endpoint e modelo configuráveis) |
| `interfaces/planner` | `call_planner(payload)` | Adapta payload e chama adapter planner |
| `interfaces/section` | `call_section(payload)` | Adapta payload e chama adapter section |
| `interfaces/analysis` | `call_analysis(payload)` | Adapta payload para análise de documento |
| `client` | HTTP client | Cliente para Ollama/LLM backend |
| `audit` | `_get_audit_dir`, `log_request_response` | Diretório de auditoria e gravação de log request/response |
| `exceptions` | LLMUnauthorizedError, LLMRateLimitError, LLMServerError, LLMTimeoutError, LLMClientError | Exceções mapeadas para códigos HTTP |

---

## 5. Configuração (resumo)

- **OLLAMA_BASE_URL**: Base do Ollama (default `http://localhost:11434`).
- **OLLAMA_GENERATE_PATH**: Path do generate (default `/api/generate`).
- **OLLAMA_MODEL**: Modelo padrão (default `llama3.1:8b`).
- **LLM_TIMEOUT**, **LLM_MAX_RETRIES**: Timeout e retentativas.
- **LLM_AUDIT_LOG_DIR**: Diretório de logs de auditoria (opcional); se vazio, usa pasta padrão (ex.: "logs").
- **LLM_ENDPOINT_PLANNER**, **LLM_ENDPOINT_SECTION**, **LLM_ENDPOINT_ANALYSIS**: Endpoints relativos ao backend (defaults `/v1/planner`, `/v1/section`, `/v1/analysis`); podem ser sobrescritos por env.

---

## 6. Prompts de teste

- **Generate (exemplo comentado no código)**:  
  `curl -X POST http://localhost:8002/api/llm/generate -H "Content-Type: application/json" -d '{"prompt": "Quais são os tipos de editais de licitação?"}'`

- **Generate com modelo**:  
  Body: `{"prompt": "Resuma em uma frase a Lei 14.133.", "model": "llama3.1:8b"}`

- **Planner**:  
  Body: `{"prompt": "Liste as seções típicas de um termo de referência.", "context": {"objeto": "aquisição de material"}}`

- **Analysis**:  
  Body: `{"document": "Trecho de um edital...", "context": {"tipo": "termo_referencia"}}`

---

## 7. O que o LLM API FAZ

- Expõe endpoints HTTP para planner, section, analysis e generate.
- Traduz requests para o backend Ollama (ou outro) e devolve resposta padronizada (ok + data).
- Trata erros (timeout, rate limit, server error, client error) e retorna códigos HTTP adequados.
- Opcionalmente grava logs de auditoria (request/response) em diretório configurável.

---

## 8. O que o LLM API NÃO FAZ

- Não interpreta prompt livre nem gera estrutura de documento (isso é llm_agent).
- Não faz RAG nem retrieval (isso é rag_service).
- Não autentica usuários (Django faz; proxy pode exigir sessão).
- Os endpoints planner/section/analysis usam paths configuráveis que podem apontar para outro serviço; por padrão o adapter usa Ollama para generate; planner/section/analysis podem ter implementação específica no adapter.

---

## 9. Possíveis melhorias

- Documentar contrato exato esperado pelo backend para planner/section/analysis (payload e resposta).
- Suporte a stream (SSE) no endpoint generate quando `stream=true`.
- Variáveis de ambiente para desabilitar auditoria (e não gravar em disco em testes).
- Health check que verifique conectividade com Ollama (GET em OLLAMA_BASE_URL ou /api/tags).
- Limite de tamanho de prompt no generate para evitar overload.
