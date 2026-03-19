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

        # 1) Primeiro, deixa o LanguageTool fazer a correção gramatical principal.
        text, c1, warnings1, lt_applied_1 = await language_tool_correct(
            text=text,
            language=body.language,
        )

        # 2) Depois aplica correções pontuais de OCR/digitação do dicionário customizado.
        text, c2 = apply_custom_replacements(text)

        # 3) Segunda passada do LanguageTool para ajustar concordância/acentuação
        # após as trocas do dicionário.
        text, c3, warnings2, lt_applied_2 = await language_tool_correct(
            text=text,
            language=body.language,
        )

        # 4) Pós-regras leves e determinísticas.
        text, c4 = apply_post_rules(text)

        warnings = [*warnings1, *warnings2]
        lt_applied = lt_applied_1 or lt_applied_2

        return CorrectResponse(
            ok=True,
            corrected_text=text,
            warnings=warnings,
            changes=[*c1, *c2, *c3, *c4],
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
