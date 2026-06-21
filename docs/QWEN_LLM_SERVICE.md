# Qwen LLM Service — microserviço gateway

Documentação **completa da integração** (todos os fluxos, envs, rede, deploy, pendências da API):  
→ **[QWEN-INTEGRACAO-DOCMASTER.md](./QWEN-INTEGRACAO-DOCMASTER.md)**

Este ficheiro descreve apenas o **serviço** `qwen_llm_service`.

---

## Objetivo

Gateway FastAPI para a API Qwen (DashScope, modo OpenAI-compatible), expondo o mesmo contrato que o `llm_api`:

- `GET /health`
- `POST /api/llm/generate`
- `GET /api/llm/usage-today`

---

## Onde fica

| Item | Caminho |
|------|---------|
| Código | `qwen_llm_service/app/` |
| Dockerfile | `qwen_llm_service/Dockerfile` |
| Compose | `docker-compose.yml` — serviço `qwen_llm_service`, **profile `qwen`** |
| Rede | `default` + **`docmaster_net`** (acesso pelo PNCP researcher) |

---

## Contrato `POST /api/llm/generate`

**Request:**

```json
{
  "prompt": "texto de entrada",
  "model": "qwen-plus",
  "stream": false
}
```

**Response:**

```json
{
  "ok": true,
  "data": {
    "response": "...",
    "model": "qwen-plus",
    "done": true,
    "usage": { "input_tokens": 123, "output_tokens": 45 }
  },
  "token_usage": {
    "prompt_tokens": 123,
    "completion_tokens": 45,
    "total_tokens": 168
  }
}
```

`stream=true` → **501** (não implementado; todos os consumidores usam `stream: false`).

---

## Variáveis de ambiente

Definidas em `qwen_llm_service/app/config.py`:

| Variável | Default | Notas |
|----------|---------|-------|
| `PORT` | `8015` | |
| `QWEN_API_KEY` | — | **Obrigatória** em produção |
| `QWEN_API_BASE_URL` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | |
| `QWEN_MODEL` | `qwen3.6-plus` | Deve existir na conta |
| `QWEN_TIMEOUT` | `120` | Segundos |
| `QWEN_MAX_OUTPUT_TOKENS` | `4096` | |
| `QWEN_MAX_PROMPT_CHARS` | `120000` | |
| `QWEN_DAILY_TOKEN_BUDGET` | `0` | `0` = ilimitado |
| `QWEN_AUDIT_LOG_DIR` | `/app/logs` | JSONL diário |

Exemplo: `qwen_llm_service/.env.example`

---

## Subir com Docker

```bash
# .env na raiz do compose com QWEN_API_KEY=...
docker compose --profile qwen up -d --build qwen_llm_service
docker compose logs --tail 100 qwen_llm_service
```

---

## Testes rápidos

```bash
curl -sS http://127.0.0.1:8015/health

curl -sS -X POST http://127.0.0.1:8015/api/llm/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Responda só: OK","stream":false}'

curl -sS http://127.0.0.1:8015/api/llm/usage-today
```

**Provider direto** (validar chave antes de culpar o gateway):

```bash
curl -sS -X POST "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions" \
  -H "Authorization: Bearer SUA_CHAVE" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-plus","messages":[{"role":"user","content":"ping"}],"max_tokens":8}'
```

---

## Erros frequentes

| HTTP / mensagem | Causa |
|-----------------|-------|
| 503 `QWEN_API_KEY não configurada` | Env vazia no container |
| 401 `Não autorizado` | Chave inválida ou modelo/região |
| 429 | Rate limit / budget (`QWEN_DAILY_TOKEN_BUDGET`) |
| 502 timeout | `QWEN_TIMEOUT` ou rede |

Verificar env no container:

```bash
docker compose exec -T qwen_llm_service sh -c 'test -n "$QWEN_API_KEY" && echo OK || echo VAZIA'
docker compose config | grep -A2 QWEN_
```

---

## Quem consome este serviço

Ver matriz completa em [QWEN-INTEGRACAO-DOCMASTER.md](./QWEN-INTEGRACAO-DOCMASTER.md):

- `rag_service` — ETP (`LLM_ETP_GENERATION_BASE_URL`), cláusulas (`LLM_CLAUSULAS_GENERATION_BASE_URL`)
- `backend` — proxy inexigibilidade (`LLM_CLAUSULAS_API_BASE_URL`)
- `pncp_researcher_service` — busca inteligente (`PNCP_IA_BASE_URL`)
