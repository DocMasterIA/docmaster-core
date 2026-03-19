from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class CorrectRequest(BaseModel):
    text: str = Field(..., description="Texto a corrigir.")
    mode: str = Field("generic", description="Modo de correção: generic|tr|etp|dfd.")
    language: str = Field("pt-BR", description="Idioma para correção no LanguageTool.")

    @field_validator("text")
    @classmethod
    def _text_required(cls, v: str) -> str:
        val = (v or "").strip()
        if not val:
            raise ValueError("text é obrigatório.")
        return val


class ChangeItem(BaseModel):
    from_text: str
    to_text: str
    rule: str


class CorrectResponse(BaseModel):
    ok: bool
    corrected_text: str
    warnings: List[str] = Field(default_factory=list)
    changes: List[ChangeItem] = Field(default_factory=list)
    language_tool_applied: bool = False
    error: Optional[str] = None
