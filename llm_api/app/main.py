"""
Aplicação FastAPI do módulo de orquestração LLM.

Ponto de entrada: uvicorn app.main:app
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("llm")

app = FastAPI(
    title="LLM Orchestration API",
    description="Camada de orquestração e comunicação com o servidor de IA local (planner, section).",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/")
async def root() -> dict[str, str]:
    """Raiz do serviço."""
    return {"service": "llm-orchestration", "docs": "/docs"}
