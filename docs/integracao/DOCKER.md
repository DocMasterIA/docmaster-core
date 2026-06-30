# Docker – DocMaster IA

Referência para rodar a aplicação em Docker.

---

## docker-compose.yml (raiz do repo)

O arquivo **`docker-compose.yml`** na raiz já inclui o serviço **llm_api**:

```bash
docker compose up -d llm_api
```

- **Porta:** 8002 (acesso: http://localhost:8002)
- **Ollama no host:** `OLLAMA_BASE_URL=http://host.docker.internal:11434`  
  No **Linux**, se não funcionar, descomente no compose a seção `extra_hosts` com `host.docker.internal:host-gateway`.
- Quando o **Django** rodar em outro serviço no mesmo compose, defina `LLM_API_BASE_URL=http://llm_api:8002` e `depends_on: [llm_api]`.

---

## Serviço FastAPI (LLM)

- **Dockerfile:** `llm_api/Dockerfile`
- **Build (raiz do repo):** `docker build -t llm_api -f llm_api/Dockerfile .`
- **Porta:** 8002 (configurável com `-e PORT=...`)

O serviço escuta em `0.0.0.0`, adequado para receber requisições de outros containers.

---

## Django + proxy LLM

O Django faz proxy para o FastAPI em `/api/llm/...` (sessão obrigatória). Em Docker:

- Defina **`LLM_API_BASE_URL`** apontando para o container do FastAPI.
- Se o serviço FastAPI se chamar `llm_api` na rede Docker:  
  `LLM_API_BASE_URL=http://llm_api:8002`

Exemplo em **docker-compose** (fragmento):

```yaml
services:
  llm_api:
    build:
      context: .
      dockerfile: llm_api/Dockerfile
    ports:
      - "8002:8002"
    environment:
      - OLLAMA_BASE_URL=http://host.docker.internal:11434  # Ollama no host
    # Ou, se Ollama for outro serviço: OLLAMA_BASE_URL=http://ollama:11434

  backend:  # Django
    ...
    environment:
      - LLM_API_BASE_URL=http://llm_api:8002
    depends_on:
      - llm_api
```

---

## Ollama em Docker

Se o Ollama rodar em outro container, use o nome do serviço na rede (ex.: `http://ollama:11434`) em `OLLAMA_BASE_URL` no container do `llm_api`. Se o Ollama estiver no host, use `http://host.docker.internal:11434` (Docker Desktop / Linux com `extra_hosts`).

---

## Build e rede

- Build do `llm_api` usa **contexto na raiz** do repositório (`docker build -f llm_api/Dockerfile .`), assim o mesmo contexto pode ser usado para outros serviços (Django, etc.) no futuro.
- O `.dockerignore` em `llm_api/` é usado quando o contexto de build é `llm_api/`; com contexto na raiz, um `.dockerignore` na raiz (se existir) reduz o que é enviado ao daemon.
