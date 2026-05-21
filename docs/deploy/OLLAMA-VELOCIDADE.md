# Ollama — velocidade da geração (cláusulas / TR)

## Por que 7–15s?

A dispensa normal chama `POST /api/llm/generate` → `llm_api` → Ollama. O tempo depende quase só de:

| Fator | Efeito |
|--------|--------|
| **Tamanho do modelo** | `qwen2.5:7b` em **CPU** costuma 10–20s por resposta curta. `qwen2.5:3b` ou `phi3:mini` → ~2–5s. |
| **GPU** | Com NVIDIA e modelo carregado na VRAM, 7B pode cair para ~2–4s. |
| **Cold start** | Primeira requisição após reinício do Ollama carrega o modelo (+10–30s). `OLLAMA_KEEP_ALIVE=24h` no compose ajuda. |
| **Contenção** | TR/DFD, RAG e cláusulas no mesmo `OLLAMA_MODEL` disputam CPU/GPU. |

O front envia `fast: true` → o `llm_api` usa **`OLLAMA_MODEL_FAST`** (padrão `qwen2.5:3b`), não o modelo pesado do TR.

## Diagnóstico na VPS (copiar/colar)

```bash
cd ~/docmaster-core   # ou pasta DEPLOY do compose

# 1) Modelos instalados e modelo em uso
docker compose exec -T llm_api printenv | grep -E '^OLLAMA_MODEL'
docker exec ollama ollama list

# 2) GPU (se vazio, tudo roda em CPU — esperado ser mais lento com 7B)
docker exec ollama sh -c 'nvidia-smi 2>/dev/null || echo "Sem GPU no container Ollama"'

# 3) Teste de latência (substitua o prompt se quiser)
time docker exec ollama ollama run qwen2.5:3b "Objeto: teste. Justificativa: teste." --verbose 2>&1 | tail -5
time docker exec ollama ollama run qwen2.5:7b "Objeto: teste. Justificativa: teste." --verbose 2>&1 | tail -5
```

Compare os tempos dos dois `time`. Se **3b** for muito menor que **7b**, configure o fast model abaixo.

## Configuração recomendada (CPU, alvo ~3s nas cláusulas)

No `.env` na pasta do `docker compose` (home do deploy):

```env
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_MODEL_FAST=qwen2.5:3b
```

Baixar o modelo rápido (uma vez):

```bash
docker exec ollama ollama pull qwen2.5:3b
```

Recriar só o que lê env:

```bash
docker compose up -d --force-recreate llm_api
```

Rebuild do front (já manda `fast: true`):

```bash
docker compose build frontend-vue --no-cache
docker compose up -d frontend-vue
```

## Alternativas de modelo rápido (pt-BR razoável)

| Modelo | Tamanho | Notas |
|--------|---------|--------|
| `qwen2.5:3b` | ~2 GB | Padrão do projeto para `OLLAMA_MODEL_FAST` |
| `phi3:mini` | ~2 GB | Muito rápido em CPU; texto um pouco mais “seco” |
| `gemma2:2b` | ~1.5 GB | Ainda mais leve |

```bash
docker exec ollama ollama pull phi3:mini
# .env: OLLAMA_MODEL_FAST=phi3:mini
```

## GPU (opcional)

No `docker-compose.yml` do projeto há bloco `deploy.resources.reservations` NVIDIA no serviço `ollama`. Só acelera se o host tiver driver + `nvidia-container-toolkit`. Sem isso, o Ollama usa CPU (normal em VPS barata).

## Verificar se a requisição usa o modelo rápido

Na resposta JSON do Ollama (via Django), o campo `data.model` deve ser `qwen2.5:3b` (ou o valor de `OLLAMA_MODEL_FAST`), não `qwen2.5:7b`.

Teste direto no servidor:

```bash
curl -s -X POST http://127.0.0.1:8002/api/llm/generate \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Objeto: a. Justificativa: b.","fast":true,"stream":false,"options":{"num_predict":120}}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('model'), d.get('ok'))"
```

## Script automático

```bash
./scripts/diagnose-ollama-speed.sh
```
