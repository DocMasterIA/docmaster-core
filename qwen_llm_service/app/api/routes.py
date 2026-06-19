from __future__ import annotations

import math
import time
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..audit import log_event
from ..budget import check_pre_request, get_usage_today, record_usage
from ..config import settings
from ..qwen_client import QwenGatewayError, chat_completion

router = APIRouter(prefix="/llm", tags=["llm"])


class GenerateRequest(BaseModel):
    """Mesmo contrato que llm_api (rag_service / Django)."""

    prompt: str = Field(..., min_length=1)
    model: str | None = None
    stream: bool = False


@router.post("/generate")
async def generate(body: GenerateRequest) -> dict[str, Any]:
    if body.stream:
        raise HTTPException(
            status_code=501,
            detail="Streaming não suportado neste gateway; use stream=false (como o RAG já faz).",
        )

    prompt = body.prompt.strip()
    if len(prompt) > settings.qwen_max_prompt_chars:
        raise HTTPException(
            status_code=400,
            detail=f"Prompt excede QWEN_MAX_PROMPT_CHARS ({settings.qwen_max_prompt_chars}).",
        )

    ratio = max(1, settings.qwen_estimated_chars_per_token)
    est_in = max(1, math.ceil(len(prompt) / ratio))
    max_out = min(settings.qwen_max_output_tokens, 32000)

    ok, err = check_pre_request(est_in, max_out)
    if not ok:
        raise HTTPException(status_code=429, detail=err)

    t0 = time.perf_counter()
    try:
        text, usage = await chat_completion(prompt, body.model, max_out)
    except QwenGatewayError as e:
        log_event(
            {
                "event": "qwen_error",
                "status": e.status_code,
                "message": e.message,
                "model_requested": body.model or settings.qwen_model_default,
            }
        )
        raise HTTPException(status_code=e.status_code, detail=e.message) from e

    inp = int(usage.get("prompt_tokens") or 0)
    out = int(usage.get("completion_tokens") or 0)
    if inp == 0 and out == 0 and text:
        out = max(1, math.ceil(len(text) / ratio))
        inp = est_in

    record_usage(inp, out)

    ms = (time.perf_counter() - t0) * 1000
    log_event(
        {
            "event": "qwen_ok",
            "duration_ms": round(ms, 2),
            "model": body.model or settings.qwen_model_default,
            "usage": {"input": inp, "output": out, "estimated_input_before": est_in},
        }
    )

    # Formato próximo ao Ollama + envelope igual ao llm_api (rag lê data.response)
    data: dict[str, Any] = {
        "response": text,
        "model": body.model or settings.qwen_model_default,
        "done": True,
        "usage": {"input_tokens": inp, "output_tokens": out},
    }
    return {
        "ok": True,
        "data": data,
        "token_usage": {
            "prompt_tokens": inp,
            "completion_tokens": out,
            "total_tokens": inp + out,
        },
    }


@router.get("/usage-today")
async def usage_today() -> dict[str, Any]:
    inp, out, total = get_usage_today()
    return {
        "input_tokens": inp,
        "output_tokens": out,
        "total_tokens": total,
        "daily_budget": settings.qwen_daily_token_budget,
    }
