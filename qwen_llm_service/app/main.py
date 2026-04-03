from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="Qwen LLM Gateway",
    description=(
        "Gateway leve para Qwen (API OpenAI-compatible). "
        "Expõe POST /api/llm/generate no mesmo contrato do llm_api para uso pelo rag_service."
    ),
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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "qwen_llm_service"}
