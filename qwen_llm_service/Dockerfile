# Build (raiz do repo): docker build -t docmaster-qwen_llm_service -f qwen_llm_service/Dockerfile .

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY qwen_llm_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY qwen_llm_service/ ./qwen_llm_service/

ENV PORT=8015
EXPOSE 8015

RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

ENV PYTHONPATH=/app
CMD ["sh", "-c", "exec uvicorn qwen_llm_service.app.main:app --host 0.0.0.0 --port ${PORT:-8015}"]
