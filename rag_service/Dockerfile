# Serviço FastAPI do RAG (DocMaster IA)
# Build (na raiz do repo): docker build -t rag_service -f rag_service/Dockerfile .
# Run: docker run --rm -p 8004:8004 -e CHROMA_HOST=host.docker.internal rag_service

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependências (contexto = docmaster-core)
COPY rag_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código da aplicação
COPY rag_service/ ./rag_service/

# Templates compartilhados (ex.: TR_modelo_base.docx)
# O código do RAG espera encontrar o template em:
#   /app/templates/tr_base/TR_modelo_base.docx
# por causa de TEMPLATE_PATH_DEFAULT em rag_service/app/tr_template.py
COPY templates/ ./templates/

# Porta do serviço (override com -e PORT=...)
ENV PORT=8004
EXPOSE 8004

# Usuário não-root (segurança básica)
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

# PYTHONPATH no CMD garante que rag_service seja encontrado
WORKDIR /app
CMD ["sh", "-c", "PYTHONPATH=/app exec uvicorn rag_service.app.main:app --host 0.0.0.0 --port ${PORT}"]
