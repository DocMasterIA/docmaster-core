# Dockerfile do backend Django (DocMaster)
# Python 3.11 + dependências para WeasyPrint (PDF) e Gunicorn

FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=backend.mdlicitatech.settings \
    PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_multiproc

WORKDIR /app

# Dependências de sistema: WeasyPrint (cairo, pango, fontes), LibreOffice (preview DOCX→PDF) e utilitários
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-liberation \
    fonts-dejavu-core \
    poppler-utils \
    libreoffice-writer \
    && rm -rf /var/lib/apt/lists/*

# Dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Código da aplicação
COPY backend/ backend/
COPY manage.py .

# Coleta dos arquivos estáticos (admin, unfold, app) para produção
RUN python manage.py collectstatic --noinput --clear \
    && mkdir -p /tmp/prometheus_multiproc

EXPOSE 8000

# Migrações na subida; Gunicorn. --timeout 0 = sem limite de tempo por requisição (PDF/WeasyPrint pode demorar muito).
# Ajuste com env GUNICORN_TIMEOUT (segundos) se quiser um teto, ex.: 3600.
ENV GUNICORN_TIMEOUT=0
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn backend.mdlicitatech.wsgi:application --bind 0.0.0.0:8000 --workers 2 --threads 4 --timeout ${GUNICORN_TIMEOUT:-0} --graceful-timeout 600 --config backend/mdlicitatech/gunicorn_conf.py --access-logfile - --error-logfile -"]
