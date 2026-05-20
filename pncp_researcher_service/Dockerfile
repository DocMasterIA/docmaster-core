FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pncp_researcher_service/requirements.txt .
RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements.txt

COPY pncp_researcher_service/ ./pncp_researcher_service/

ENV PORT=8012
EXPOSE 8012

RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app

COPY pncp_researcher_service/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

WORKDIR /app
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["sh", "-c", "PYTHONPATH=/app exec uvicorn pncp_researcher_service.app.main:app --host 0.0.0.0 --port ${PORT}"]
