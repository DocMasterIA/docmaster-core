FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY text_corrector_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY text_corrector_service/app/ ./app/

ENV PORT=8011
EXPOSE 8011

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8011"]
