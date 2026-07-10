"""Configuração pytest para testes Django do backend."""
from __future__ import annotations

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.mdlicitatech.settings")
django.setup()
