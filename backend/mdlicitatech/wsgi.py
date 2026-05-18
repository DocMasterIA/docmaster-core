"""
WSGI config for mdlicitatech project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.mdlicitatech.settings")

# Antes do Django: garante ValueClass multiprocess e registro das métricas docmaster_*.
import backend.app.metrics  # noqa: E402, F401

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()

from backend.app.metrics import connect_auth_signals  # noqa: E402

connect_auth_signals()
