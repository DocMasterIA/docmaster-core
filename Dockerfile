# Dockerfile do backend Django (DocMaster)
# Python 3.11 + dependências para WeasyPrint (PDF) e Gunicorn

FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=backend.mdlicitatech.settings

WORKDIR /app

# Dependências de sistema: WeasyPrint (cairo, pango, fontes) e utilitários
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
    && rm -rf /var/lib/apt/lists/*

# Dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Código da aplicação
COPY backend/ backend/
COPY manage.py .

# Coleta dos arquivos estáticos (admin, unfold, app) para produção
RUN python manage.py collectstatic --noinput --clear

EXPOSE 8000

# Migrações executadas na inicialização; em seguida, Gunicorn
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn backend.mdlicitatech.wsgi:application --bind 0.0.0.0:8000 --workers 2 --threads 4 --access-logfile - --error-logfile -"]
