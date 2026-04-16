# Qwen LLM Service - Guia de Operação

Este documento descreve o modulo `qwen_llm_service`: objetivo, contrato, configuracao, execucao e troubleshooting.

## 1) Objetivo

O `qwen_llm_service` e um gateway FastAPI para Qwen (API OpenAI-compatible), expondo o mesmo contrato usado no `llm_api`:

- `POST /api/llm/generate`

No projeto atual, ele pode ser usado pelo `rag_service` para geracao de ETP quando `LLM_ETP_GENERATION_BASE_URL` estiver configurado.

## 2) Onde fica no projeto

- Codigo: `qwen_llm_service/app/`
- Dockerfile: `qwen_llm_service/Dockerfile`
- Integracao compose: `docker-compose.yml` (service `qwen_llm_service`, profile `qwen`)

## 3) Contrato da API

### 3.1 Health

- `GET /health`
- Resposta esperada:

```json
{
  "status": "ok",
  "service": "qwen_llm_service"
}
```

### 3.2 Generate

- `POST /api/llm/generate`
- Body:

```json
{
  "prompt": "texto de entrada",
  "model": "qwen3.6-plus",
  "stream": false
}
```

- Resposta de sucesso:

```json
{
  "ok": true,
  "data": {
    "response": "...",
    "model": "qwen3.6-plus",
    "done": true,
    "usage": {
      "input_tokens": 123,
      "output_tokens": 45
    }
  }
}
```

## 4) Variaveis de ambiente

Principais variaveis em `qwen_llm_service/app/config.py`:

- `PORT` (default: `8015`)
- `QWEN_API_BASE_URL` (default: `https://dashscope.aliyuncs.com/compatible-mode/v1`)
- `QWEN_API_KEY` (**obrigatoria**)
- `QWEN_MODEL` (default: `qwen3.6-plus`)
- `QWEN_TIMEOUT` (default: `120`)
- `QWEN_MAX_OUTPUT_TOKENS` (default: `4096`)
- `QWEN_MAX_PROMPT_CHARS` (default: `120000`)
- `QWEN_DAILY_TOKEN_BUDGET` (default: `0`, sem limite)
- `QWEN_AUDIT_LOG_DIR` (opcional)

## 5) Execucao com Docker Compose

No `docker-compose.yml`, o servico usa profile `qwen`.

Subir:

```bash
docker compose --profile qwen up -d qwen_llm_service
```

Recriar:

```bash
docker compose --profile qwen up -d --build --force-recreate qwen_llm_service
```

Ver logs:

```bash
docker compose logs --tail 200 qwen_llm_service
```

## 6) Configuracao recomendada no .env

No arquivo `.env` usado pelo compose:

```env
QWEN_API_KEY=sua_chave_aqui
QWEN_API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen3.6-plus
```

Importante:

- use `--env-file /caminho/do/.env` se houver duvida sobre qual `.env` esta sendo lido;
- `export` no shell nao e persistente entre sessoes.

## 7) Testes rapidos

### 7.1 Validar health local

```bash
curl -sS http://127.0.0.1:8015/health
```

### 7.2 Validar endpoint local

```bash
curl -sS -X POST "http://127.0.0.1:8015/api/llm/generate" \
  -H "Content-Type: application/json" \
  --data '{"prompt":"teste","stream":false}'
```

### 7.3 Validar chave direto no provider

```bash
curl -sS -X POST "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions" \
  -H "Authorization: Bearer SUA_CHAVE" \
  -H "Content-Type: application/json" \
  --data '{"model":"qwen3.6-plus","messages":[{"role":"user","content":"ping"}],"max_tokens":8}'
```

## 8) Erros comuns e diagnostico

### 8.1 `{"detail":"QWEN_API_KEY não configurada."}` (503)

Causa:

- variavel vazia no container.

Verificar:

```bash
docker compose exec -T qwen_llm_service sh -lc 'echo "len=${#QWEN_API_KEY}"'
```

### 8.2 `{"detail":"Não autorizado: verifique QWEN_API_KEY."}` (401 no provider)

Causa:

- chave invalida, revogada, incorreta para o endpoint, ou nao carregada corretamente.

Verificar:

- teste direto no provider (secao 7.3);
- confirme `.env` correto com `docker compose config`.

### 8.3 `You didn't provide an API key` no curl direto ao provider

Causa:

- comando usou `Bearer $QWEN_API_KEY`, mas a variavel estava vazia no shell.

Verificar:

```bash
echo "len=${#QWEN_API_KEY}"
```

## 9) Integracao com rag_service (ETP)

No `rag_service`, a escolha da base LLM por tipo de documento usa:

- `LLM_ETP_GENERATION_BASE_URL` para ETP (quando definido);
- fallback em `LLM_ORCHESTRATION_BASE_URL` para demais fluxos.

No compose atual:

- `LLM_ETP_GENERATION_BASE_URL=http://qwen_llm_service:8015`

## 10) Checklist operacional rapido

1. `docker compose --profile qwen up -d qwen_llm_service`
2. `curl http://127.0.0.1:8015/health`
3. confirmar env no container (`QWEN_API_KEY`, `QWEN_MODEL`)
4. testar provider direto (chave)
5. testar `/api/llm/generate` local
6. validar fluxo ETP no `rag_service`
