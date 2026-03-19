from __future__ import annotations

from fastapi import FastAPI

from .schemas import CorrectRequest, CorrectResponse
from .service import (
    apply_custom_replacements,
    apply_post_rules,
    language_tool_correct,
    normalize_text,
)

app = FastAPI(
    title="DocMaster Text Corrector",
    description="Microserviço de correção gramatical/ortográfica para textos PT-BR.",
    version="0.1.0",
)


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "service": "text_corrector"}


@app.post("/correct", response_model=CorrectResponse)
async def correct_text(body: CorrectRequest) -> CorrectResponse:
    try:
        text = normalize_text(body.text)

        text, c1 = apply_custom_replacements(text)

        text, c2, warnings, lt_applied = await language_tool_correct(
            text=text,
            language=body.language,
        )

        text, c3 = apply_post_rules(text)

        return CorrectResponse(
            ok=True,
            corrected_text=text,
            warnings=warnings,
            changes=[*c1, *c2, *c3],
            language_tool_applied=lt_applied,
        )
    except Exception as e:
        return CorrectResponse(
            ok=False,
            corrected_text=body.text,
            warnings=[],
            changes=[],
            language_tool_applied=False,
            error=str(e),
        )
