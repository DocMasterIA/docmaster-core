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

# Entrypoint: ajusta permissões de /app/logs (volume) e sobe o app como appuser
COPY llm_api/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Porta do serviço (override com -e PORT=...)
ENV PORT=8002
EXPOSE 8002

# Usuário appuser para rodar uvicorn; entrypoint faz chown em /app/logs antes de trocar de usuário
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app

# Roda como root para entrypoint poder chown; entrypoint depois faz su appuser
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]

