# Serviço FastAPI de orquestração LLM (DocMaster IA)
# Build (na raiz do repo): docker build -t llm_api -f llm_api/Dockerfile .
# Run:   docker run --rm -p 8002:8002 -e OLLAMA_BASE_URL=http://host.docker.internal:11434 llm_api

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependências (contexto = raiz do repo)
COPY llm_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código da aplicação
COPY llm_api/app/ ./app/

# Porta do serviço (override com -e PORT=...)
ENV PORT=8002
EXPOSE 8002

# Usuário não-root (segurança)
RUN useradd --create-home --shell /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
