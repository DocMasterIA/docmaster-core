"""
Rotas FastAPI para o módulo LLM.

Endpoints funcionais que recebem JSON, chamam adapter (planner/section),
tratam erros e retornam resposta padronizada.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.adapter import generate, planner, section
from app.exceptions import (
    LLMClientError,
    LLMRateLimitError,
    LLMServerError,
    LLMTimeoutError,
    LLMUnauthorizedError,
)
from app.interfaces.planner import call_planner
from app.interfaces.section import call_section

router = APIRouter(prefix="/llm", tags=["llm"])


# Schemas de entrada (podem ser refinados conforme contrato do servidor de IA)
class PlannerRequest(BaseModel):
    """Payload para chamada planner. Ajustar campos conforme contrato."""
    prompt: str = ""
    context: dict[str, Any] | None = None
    options: dict[str, Any] | None = None


class SectionRequest(BaseModel):
    """Payload para chamada section. Ajustar campos conforme contrato."""
    prompt: str = ""
    section_id: str | None = None
    context: dict[str, Any] | None = None


class GenerateRequest(BaseModel):
    """Payload para chamada direta ao Ollama /api/generate."""
    prompt: str
    model: str | None = None
    stream: bool = False


def _payload_from_planner_request(req: PlannerRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {"prompt": req.prompt}
    if req.context is not None:
        payload["context"] = req.context
    if req.options is not None:
        payload["options"] = req.options
    return payload


def _payload_from_section_request(req: SectionRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {"prompt": req.prompt}
    if req.section_id is not None:
        payload["section_id"] = req.section_id
    if req.context is not None:
        payload["context"] = req.context
    return payload


@router.post("/planner")
async def endpoint_planner(body: PlannerRequest) -> dict[str, Any]:
    """
    Endpoint para chamada do tipo planner.

    Recebe JSON com prompt (e opcionalmente context, options), chama o
    servidor de IA e retorna a resposta. Sem garantia de formato específico.
    """
    try:
        payload = _payload_from_planner_request(body)
        result = await call_planner(payload)
        if isinstance(result, dict):
            return {"ok": True, "data": result}
        return {"ok": True, "data": {"raw": result}}
    except LLMUnauthorizedError as e:
        raise HTTPException(status_code=401, detail=e.message)
    except LLMRateLimitError as e:
        raise HTTPException(status_code=429, detail=e.message)
    except LLMServerError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=e.message)
    except LLMTimeoutError as e:
        raise HTTPException(status_code=504, detail=e.message)
    except LLMClientError as e:
        raise HTTPException(status_code=e.status_code or 400, detail=e.message)


@router.post("/section")
async def endpoint_section(body: SectionRequest) -> dict[str, Any]:
    """
    Endpoint para chamada do tipo section.

    Recebe JSON com prompt (e opcionalmente section_id, context), chama o
    servidor de IA e retorna a resposta. Sem garantia de formato específico.
    """
    try:
        payload = _payload_from_section_request(body)
        result = await call_section(payload)
        if isinstance(result, dict):
            return {"ok": True, "data": result}
        return {"ok": True, "data": {"raw": result}}
    except LLMUnauthorizedError as e:
        raise HTTPException(status_code=401, detail=e.message)
    except LLMRateLimitError as e:
        raise HTTPException(status_code=429, detail=e.message)
    except LLMServerError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=e.message)
    except LLMTimeoutError as e:
        raise HTTPException(status_code=504, detail=e.message)
    except LLMClientError as e:
        raise HTTPException(status_code=e.status_code or 400, detail=e.message)


@router.post("/generate")
async def endpoint_generate(body: GenerateRequest) -> dict[str, Any]:
    """
    Chama o Ollama em /api/generate (modelo real).

    Recebe prompt (obrigatório), model (opcional) e stream (opcional).
    Retorna o JSON do Ollama (response, model, done, etc.).
    """
    try:
        result = await generate(
            prompt=body.prompt,
            model=body.model,
            stream=body.stream,
        )
        if isinstance(result, dict):
            return {"ok": True, "data": result}
        return {"ok": True, "data": {"raw": result}}
    except LLMUnauthorizedError as e:
        raise HTTPException(status_code=401, detail=e.message)
    except LLMRateLimitError as e:
        raise HTTPException(status_code=429, detail=e.message)
    except LLMServerError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=e.message)
    except LLMTimeoutError as e:
        raise HTTPException(status_code=504, detail=e.message)
    except LLMClientError as e:
        raise HTTPException(status_code=e.status_code or 400, detail=e.message)


@router.get("/health")
async def health() -> dict[str, str]:
    """Health check do serviço de orquestração LLM."""
    return {"status": "ok", "service": "llm-orchestration"}
