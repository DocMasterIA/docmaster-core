"""
Adapter LLM: interface padronizada entre a aplicação e o servidor de IA.

Métodos de alto nível (planner, section) que utilizam o client, registram
auditoria e devolvem respostas normalizadas. Ponto único de chamada.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from app.audit import log_request_response
from app.client import request
from app.config import (
    LLM_ENDPOINT_PLANNER,
    LLM_ENDPOINT_SECTION,
    OLLAMA_GENERATE_PATH,
    OLLAMA_MODEL,
)

logger = logging.getLogger("llm.adapter")


async def _call(
    call_type: str,
    path: str,
    payload: dict[str, Any],
) -> dict[str, Any] | str:
    """
    Envia requisição ao servidor de IA, registra auditoria e retorna resposta.

    - call_type: "planner" ou "section" (para logs).
    - path: endpoint relativo (ex.: /v1/planner).
    - payload: corpo JSON da requisição.
    """
    request_id = str(uuid.uuid4())
    start = time.perf_counter()

    try:
        body, status_code = await request("POST", path, json_payload=payload)
        duration_ms = (time.perf_counter() - start) * 1000
        log_request_response(
            call_type=call_type,
            request_payload=payload,
            response_raw=body,
            duration_ms=duration_ms,
            request_id=request_id,
            status_code=status_code,
        )
        return body
    except Exception as e:
        duration_ms = (time.perf_counter() - start) * 1000
        log_request_response(
            call_type=call_type,
            request_payload=payload,
            response_raw={"error": str(e)},
            duration_ms=duration_ms,
            request_id=request_id,
        )
        raise


async def planner(payload: dict[str, Any]) -> dict[str, Any] | str:
    """
    Chamada padronizada do tipo planner.

    Payload e formato de resposta dependem do contrato do servidor de IA.
    Não há garantia de resultado específico.
    """
    return await _call("planner", LLM_ENDPOINT_PLANNER, payload)


async def section(payload: dict[str, Any]) -> dict[str, Any] | str:
    """
    Chamada padronizada do tipo section.

    Payload e formato de resposta dependem do contrato do servidor de IA.
    Não há garantia de resultado específico.
    """
    return await _call("section", LLM_ENDPOINT_SECTION, payload)


async def generate(
    prompt: str,
    model: str | None = None,
    stream: bool = False,
) -> dict[str, Any] | str:
    """
    Chama o Ollama em /api/generate (API real do Ollama).

    - prompt: texto enviado ao modelo.
    - model: nome do modelo (default: OLLAMA_MODEL).
    - stream: se True, resposta em streaming (ainda retornamos o body como está).
    Retorna o JSON bruto do Ollama (ex.: response, model, done, etc.).
    """
    payload: dict[str, Any] = {
        "model": model or OLLAMA_MODEL,
        "prompt": prompt,
        "stream": stream,
    }
    return await _call("generate", OLLAMA_GENERATE_PATH, payload)
