"""
WSGI config for mdlicitatech project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.mdlicitatech.settings')

application = get_wsgi_application()

# Garante registro das métricas docmaster_* em cada worker Gunicorn.
import backend.app.metrics  # noqa: E402, F401
