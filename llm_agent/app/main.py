"""
Ponto de entrada FastAPI do llm_agent.

Uso (dev local):
    uvicorn llm_agent.app.main:app --reload --host 0.0.0.0 --port 8003
"""
from __future__ import annotations

from fastapi import FastAPI

from .api import create_app

app: FastAPI = create_app()

