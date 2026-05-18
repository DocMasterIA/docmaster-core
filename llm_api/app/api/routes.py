"""
Rotas FastAPI para o módulo LLM.

Endpoints funcionais que recebem JSON, chamam adapter (planner/section/analysis),
tratam erros e retornam resposta padronizada.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.adapter import generate, planner, section
from app.exceptions import (
    LLMClientError,
    LLMRateLimitError,
    LLMServerError,
    LLMTimeoutError,
    LLMUnauthorizedError,
)
from app.interfaces.analysis import call_analysis
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


class AnalysisRequest(BaseModel):
    """Payload para análise de documento (ex.: análise de editais). Avaliação sem gerar/editar."""
    document: str = ""
    context: dict[str, Any] | None = None
    options: dict[str, Any] | None = None


class GenerateRequest(BaseModel):
    """Payload para chamada direta ao Ollama /api/generate."""
    prompt: str
    model: str | None = None
    stream: bool = False
    prefeitura: str | None = None


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


def _payload_from_analysis_request(req: AnalysisRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {"document": req.document}
    if req.context is not None:
        payload["context"] = req.context
    if req.options is not None:
        payload["options"] = req.options
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


@router.post("/analysis")
async def endpoint_analysis(body: AnalysisRequest) -> dict[str, Any]:
    """
    Endpoint para análise/avaliação de documento (ex.: análise de editais).

    Recebe JSON com document (texto a avaliar) e opcionalmente context, options.
    Não gera nem modifica documento; retorna avaliação do servidor de IA.
    """
    try:
        payload = _payload_from_analysis_request(body)
        result = await call_analysis(payload)
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
async def endpoint_generate(body: GenerateRequest, request: Request) -> dict[str, Any]:
    """
    Chama o Ollama em /api/generate (modelo real).

    Recebe prompt (obrigatório), model (opcional) e stream (opcional).
    Retorna o JSON do Ollama (response, model, done, etc.).
    """

    """
    teste: curl -X POST http://localhost:8002/api/llm/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Quais são os tipos de editais de licitação?"}'
    """
    from app.request_context import set_prefeitura

    header_pref = (request.headers.get("X-DocMaster-Prefeitura") or "").strip()
    prefeitura = body.prefeitura or header_pref or None
    set_prefeitura(prefeitura)
    try:
        result = await generate(
            prompt=body.prompt,
            model=body.model,
            stream=body.stream,
            prefeitura=prefeitura,
        )
        if isinstance(result, dict):
            from app.token_usage import extract_token_usage

            prompt_t, completion_t, _model = extract_token_usage(result)
            return {
                "ok": True,
                "data": result,
                "token_usage": {
                    "prompt_tokens": prompt_t,
                    "completion_tokens": completion_t,
                    "total_tokens": prompt_t + completion_t,
                },
            }
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


@router.get("/test-audit")
async def test_audit() -> dict[str, Any]:
    """
    Testa se o diretório de auditoria existe e é gravável (pasta automática ou LLM_AUDIT_LOG_DIR).
    Grava uma linha de teste e retorna ok ou erro.
    """
    from app.audit import _get_audit_dir, log_request_response

    audit_dir = str(_get_audit_dir())
    try:
        log_request_response(
            call_type="test",
            request_payload={"test": True},
            response_raw={"message": "teste de escrita"},
            duration_ms=0.0,
        )
        return {"ok": True, "message": "Log de auditoria gravado", "dir": audit_dir}
    except Exception as e:
        return {"ok": False, "error": str(e), "dir": audit_dir}


@router.get("/health")
async def health() -> dict[str, str]:
    """Health check do serviço de orquestração LLM."""
    return {"status": "ok", "service": "llm-orchestration"}

#....