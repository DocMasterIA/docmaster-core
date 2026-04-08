# Erros Atuais - Debug (2026-04-08)

Este documento registra o estado atual dos erros observados no ambiente DocMaster IA, com foco em geracao de TR/DFD e chamadas via frontend/API.

## 1) Sintoma no Frontend (aparente CORS)

- Mensagem no browser:
  - `Access to fetch ... has been blocked by CORS policy`
  - `net::ERR_FAILED 524`
- Diagnostico:
  - O preflight CORS (`OPTIONS`) esta respondendo corretamente.
  - O erro real e timeout/upstream (524/502/504), e o browser mascara isso como CORS.

## 2) Evidencia de CORS OK

Comandos executados:

- `OPTIONS https://api.docmasteria.com.br/api/documentos/gerar-via-llm` -> `200`
- Headers retornados incluem:
  - `Access-Control-Allow-Origin: https://docmasteria.com.br`
  - `Access-Control-Allow-Credentials: true`

Conclusao: configuracao CORS base da API esta funcional.

## 3) Evidencia de autenticacao (nao CORS)

- `POST https://api.docmasteria.com.br/api/documentos/gerar-via-llm` sem sessao -> `401`
- Body:
  - `{"error":"Nao autenticado. Faca login."}`

Conclusao: para chamadas desse endpoint publico, e necessario cookie de sessao valido.

## 4) Erro principal atual (interno, sem Cloudflare)

Teste local direto no servidor:

- `POST http://127.0.0.1:8004/api/rag/generate-tr-and-dfd-zip` -> `500`
- Detail retornado:
  - `Server error '504 Gateway Timeout' for url 'http://llm_api:8002/api/llm/generate'`

Conclusao: o gargalo esta na cadeia interna `rag_service -> llm_api -> ollama`.

## 5) Estado atual de runtime (flags relevantes)

Valores observados em containers:

- `llm_api`
  - `OLLAMA_MODEL=qwen2.5:7b`
  - `LLM_TIMEOUT=300`
  - `LLM_MAX_RETRIES=1`
  - `OLLAMA_BASE_URL=http://ollama:11434`

- `rag_service`
  - `LLM_ORCHESTRATION_BASE_URL=http://llm_api:8002`
  - `LLM_AGENT_BASE_URL=http://llm_agent:8003`
  - `RAG_TIMEOUT=0` (observado em runtime; invalida timeout finito)

## 6) Hipotese tecnica mais provavel

1. Fluxo de TR/DFD executa chamadas LLM pesadas e encadeadas.
2. Uma ou mais chamadas ao `llm_api` estouram tempo e retornam `504`.
3. `rag_service` propaga falha como `500`.
4. Via dominio publico, Cloudflare pode virar `524`, que no browser aparece como "CORS".

## 7) Impacto

- Geracao TR/DFD instavel e muito lenta.
- Endpoint local de teste tambem falha (`500`), logo o problema nao depende do frontend.

## 8) Acoes recomendadas imediatas

1. Garantir timeout finito no `rag_service`:
   - `RAG_TIMEOUT=300` (ou `600`)
2. Aumentar timeout do `llm_api` para carga atual:
   - `LLM_TIMEOUT=600` (ou `900` se necessario)
3. Recriar servicos:
   - `docker compose up -d --build --force-recreate llm_api llm_agent rag_service`
4. Validar env efetiva:
   - `docker compose exec -T llm_api printenv | awk '/LLM_TIMEOUT|LLM_MAX_RETRIES|OLLAMA_MODEL/'`
   - `docker compose exec -T rag_service printenv | awk '/RAG_TIMEOUT|LLM_ORCHESTRATION_BASE_URL/'`
5. Repetir teste local (sem Cloudflare):
   - `POST http://127.0.0.1:8004/api/rag/generate-tr-and-dfd-zip`

## 9) Observacao sobre colecao Chroma

- O default do projeto e `CHROMA_COLLECTION=docmaster_docs`.
- Nome `docmaster_pncp` e valido, mas e uma escolha de configuracao (nao obrigatoria do codigo).

## 10) Resumo executivo

- Nao e CORS raiz.
- Nao e Cloudflare raiz (erro reproduz localmente).
- Erro atual e timeout interno em `llm_api` durante geracao TR/DFD.
