# Serviço FastAPI do llm_agent (estrutura documental)
# Build (na raiz do repo): docker build -t llm_agent -f llm_agent/Dockerfile .
# Run:   docker run --rm -p 8003:8003 -e LLM_ORCHESTRATION_BASE_URL=http://host.docker.internal:8002 llm_agent

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependências (contexto = raiz do repo)
COPY llm_agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código da aplicação
COPY llm_agent/ ./llm_agent/

# Porta do serviço (override com -e PORT=...)
ENV PORT=8003
EXPOSE 8003

# Usuário não-root (segurança básica)
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

CMD ["sh", " -c", "uvicorn llm_agent.app.main:app --host 0.0.0.0 --port ${PORT}"]

