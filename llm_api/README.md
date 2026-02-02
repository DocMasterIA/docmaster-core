# Módulo de Orquestração LLM (FastAPI)

Camada intermediária entre o backend da aplicação e o servidor de IA local: integração padronizada, segura e auditável, com cliente HTTP, tratamento de erros (401, 429, 5xx), retries, timeout e registro de respostas brutas. Interface padronizada para chamadas **planner** e **section**. Não há garantia de resultados específicos quanto às respostas do modelo.

---

## Estrutura

```
llm_api/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI app, CORS, rota raiz
│   ├── config.py         # OLLAMA_BASE_URL, timeout, retries, audit dir
│   ├── exceptions.py     # LLMClientError, 401, 429, 5xx, Timeout
│   ├── client.py         # Cliente HTTP (httpx), retries, timeout
│   ├── adapter.py        # planner(), section(), auditoria
│   ├── audit.py          # log_request_response (arquivo + logger)
│   ├── interfaces/
│   │   ├── __init__.py
│   │   ├── planner.py    # call_planner
│   │   └── section.py    # call_section
│   └── api/
│       ├── __init__.py
│       └── routes.py     # POST /api/llm/planner, POST /api/llm/section, GET /api/llm/health
├── README.md
└── requirements.txt
```

---

## Configuração (variáveis de ambiente)

| Variável | Descrição | Default |
|----------|-----------|---------|
| `OLLAMA_BASE_URL` | Base URL do Ollama (servidor de IA local) | `http://localhost:11434` |
| `LLM_TIMEOUT` | Timeout da requisição (segundos) | `60.0` |
| `LLM_MAX_RETRIES` | Número máximo de retries | `3` |
| `LLM_AUDIT_LOG_DIR` | Diretório para logs de auditoria (JSONL) | (vazio = só logger) |
| `LLM_ENDPOINT_PLANNER` | Path do endpoint planner | `/v1/planner` |
| `LLM_ENDPOINT_SECTION` | Path do endpoint section | `/v1/section` |

---

## Endpoints

- **GET /** – Raiz do serviço.
- **GET /api/llm/health** – Health check.
- **POST /api/llm/planner** – Chamada tipo planner (body: `prompt`, opcional `context`, `options`).
- **POST /api/llm/section** – Chamada tipo section (body: `prompt`, opcional `section_id`, `context`).

Respostas de sucesso: `{"ok": true, "data": ...}`. Erros: 401, 429, 4xx/5xx com `detail` em JSON.

---

## Estrutura de logs de auditoria

Quando `LLM_AUDIT_LOG_DIR` está definido, cada chamada ao servidor de IA gera uma linha em arquivo **JSON Lines** no diretório indicado, com nome `llm_audit_YYYY-MM-DD.jsonl`.

Cada linha contém:

- `timestamp`: ISO 8601 (UTC)
- `request_id`: UUID da chamada
- `call_type`: `"planner"` ou `"section"`
- `request_payload`: payload enviado (serializável)
- `response_raw`: resposta bruta do servidor (ou `{"error": "..."}` em falha)
- `duration_ms`: duração em milissegundos
- `status_code`: (opcional) status HTTP da resposta

O mesmo conteúdo é enviado ao logger Python (`llm.audit`) em nível INFO.

---

## Como rodar

**Opção 1 – dentro de `llm_api`:**
```bash
cd llm_api
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

**Opção 2 – na raiz do repositório (usando o venv do projeto):**
```bash
pip install fastapi "uvicorn[standard]" httpx  # se ainda não tiver
uvicorn app.main:app --reload --host 0.0.0.0 --port 8002 --app-dir llm_api
```

Documentação interativa: **http://localhost:8002/docs**

---

## Docker

Build (na raiz do repositório):

```bash
docker build -t llm_api -f llm_api/Dockerfile .
```

Executar (Ollama no host; Linux use `host.docker.internal` ou IP do host):

```bash
docker run --rm -p 8002:8002 \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  llm_api
```

Variáveis úteis em Docker:

- `OLLAMA_BASE_URL` – URL do Ollama (no host: `http://host.docker.internal:11434`; em rede Docker: `http://ollama:11434` se o serviço se chamar `ollama`).
- `PORT` – Porta interna (default `8002`).
- `LLM_AUDIT_LOG_DIR` – Ex.: `/app/logs`; monte um volume se quiser persistir logs.

Em **docker-compose**, o Django deve apontar para este serviço com `LLM_API_BASE_URL=http://llm_api:8002` (nome do serviço = hostname na rede).

---

## Tratamento de erros

- **401**: `LLMUnauthorizedError` → HTTP 401
- **429**: `LLMRateLimitError` → HTTP 429 (com retry automático no client)
- **5xx**: `LLMServerError` → HTTP 502/503/504 (com retry automático no client)
- **Timeout**: `LLMTimeoutError` → HTTP 504
- Demais erros de cliente: `LLMClientError` → HTTP 400 ou status recebido

Retries são aplicados apenas para 429 e 5xx, com backoff simples entre tentativas.
