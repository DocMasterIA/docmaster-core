"""
Ponto de entrada FastAPI do serviço RAG.

Uso (dev local):
    uvicorn rag_service.app.main:app --reload --host 0.0.0.0 --port 8004
"""
from __future__ import annotations

from fastapi import FastAPI

from .api import create_app

app: FastAPI = create_app()
