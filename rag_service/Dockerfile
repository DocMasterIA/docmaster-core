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

# Templates de pacotes (TR/DFD/Ofício)
# O código do RAG usa:
#   /app/template_packages/lei_14133/<pacote>/*.docx
# com fallback em:
#   /app/template_packages/tr_base/*.docx
COPY template_packages/ ./template_packages/

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
