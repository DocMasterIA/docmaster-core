FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pncp_researcher_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pncp_researcher_service/ ./pncp_researcher_service/

ENV PORT=8012
EXPOSE 8012

RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

WORKDIR /app
CMD ["sh", "-c", "PYTHONPATH=/app exec uvicorn pncp_researcher_service.app.main:app --host 0.0.0.0 --port ${PORT}"]
