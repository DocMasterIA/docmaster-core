# LLM Orchestration Module (FastAPI)

Intermediate layer between the application backend and the local AI server: a standardized, safe, and auditable integration, with an HTTP client, error handling (401, 429, 5xx), retries, timeout, and raw-response logging. Standardized interface for **planner**, **section**, and **analysis** calls (bid-document analysis). There is no guarantee of specific results from the model responses.

---

## Structure

```
llm_api/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI app, CORS, root route
│   ├── config.py         # OLLAMA_BASE_URL, timeout, retries, audit dir
│   ├── exceptions.py     # LLMClientError, 401, 429, 5xx, Timeout
│   ├── client.py         # HTTP client (httpx), retries, timeout
│   ├── adapter.py        # planner(), section(), analysis(), audit
│   ├── audit.py          # log_request_response (file + logger)
│   ├── interfaces/
│   │   ├── __init__.py
│   │   ├── planner.py    # call_planner
│   │   └── section.py    # call_section
│   └── api/
│       ├── __init__.py
│       └── routes.py     # POST /api/llm/planner, section, analysis; GET /api/llm/health
├── README.md
└── requirements.txt
```

---

## Configuration (environment variables)

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_BASE_URL` | Base URL of Ollama (local AI server) | `http://localhost:11434` |
| `LLM_TIMEOUT` | Request timeout (seconds) | `60.0` |
| `LLM_MAX_RETRIES` | Maximum number of retries | `3` |
| `LLM_AUDIT_LOG_DIR` | Directory for audit logs (JSONL) | (empty = logger only) |
| `LLM_ENDPOINT_PLANNER` | Planner endpoint path | `/v1/planner` |
| `LLM_ENDPOINT_SECTION` | Section endpoint path | `/v1/section` |
| `LLM_ENDPOINT_ANALYSIS` | Analysis endpoint path (e.g. bid documents) | `/v1/analysis` |

---

## Endpoints

- **GET /** – Service root.
- **GET /api/llm/health** – Health check.
- **POST /api/llm/planner** – Planner-style call (body: `prompt`, optional `context`, `options`).
- **POST /api/llm/section** – Section-style call (body: `prompt`, optional `section_id`, `context`).
- **POST /api/llm/analysis** – Document analysis/evaluation (e.g. bid documents); body: `document`, optional `context`, `options`. It does not generate or modify a document.

Success responses: `{"ok": true, "data": ...}`. Errors: 401, 429, 4xx/5xx with `detail` as JSON.

---

## Audit log structure

When `LLM_AUDIT_LOG_DIR` is set, each call to the AI server writes one line to a **JSON Lines** file in that directory, named `llm_audit_YYYY-MM-DD.jsonl`.

Each line contains:

- `timestamp`: ISO 8601 (UTC)
- `request_id`: call UUID
- `call_type`: `"planner"`, `"section"`, or `"analysis"`
- `request_payload`: payload sent (serializable)
- `response_raw`: raw server response (or `{"error": "..."}` on failure)
- `duration_ms`: duration in milliseconds
- `status_code`: (optional) HTTP status of the response

The same content is sent to the Python logger (`llm.audit`) at INFO level.

---

## How to run

**Option 1 – inside `llm_api`:**
```bash
cd llm_api
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

**Option 2 – from the repository root (using the project venv):**
```bash
pip install fastapi "uvicorn[standard]" httpx  # if not already installed
uvicorn app.main:app --reload --host 0.0.0.0 --port 8002 --app-dir llm_api
```

Interactive docs: **http://localhost:8002/docs**

---

## Docker

Build (from the repository root):

```bash
docker build -t llm_api -f llm_api/Dockerfile .
```

Run (Ollama on the host; on Linux use `host.docker.internal` or the host IP):

```bash
docker run --rm -p 8002:8002 \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  llm_api
```

Useful variables in Docker:

- `OLLAMA_BASE_URL` – Ollama URL (on the host: `http://host.docker.internal:11434`; on a Docker network: `http://ollama:11434` if the service is named `ollama`).
- `PORT` – Internal port (default `8002`).
- `LLM_AUDIT_LOG_DIR` – e.g. `/app/logs`; mount a volume if you want to persist logs.

In **docker-compose**, Django should point at this service with `LLM_API_BASE_URL=http://llm_api:8002` (service name = hostname on the network).

---

## Error handling

- **401**: `LLMUnauthorizedError` → HTTP 401
- **429**: `LLMRateLimitError` → HTTP 429 (with automatic retry in the client)
- **5xx**: `LLMServerError` → HTTP 502/503/504 (with automatic retry in the client)
- **Timeout**: `LLMTimeoutError` → HTTP 504
- Other client errors: `LLMClientError` → HTTP 400 or the status received

Retries apply only to 429 and 5xx, with simple backoff between attempts.
