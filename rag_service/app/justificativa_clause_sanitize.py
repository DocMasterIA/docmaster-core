"""Normalização da justificativa — exatamente 3 parágrafos, sem repetição."""
from __future__ import annotations

import re
from typing import List


def _split_paragraphs(text: str) -> List[str]:
    text = re.sub(r"\r\n?", "\n", (text or "").strip())
    if not text:
        return []
    parts = [p.strip() for p in re.sub(r"\n{3,}", "\n\n", text).split("\n\n") if p.strip()]
    if len(parts) <= 1:
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        if len(lines) >= 2:
            parts = lines
    return parts


def normalize_justificativa_tres_paragrafos(text: str) -> str:
    """
    Garante no máximo 3 parágrafos na justificativa.
    Quando a LLM excede (repetição/resumo), mantém os 3 primeiros — estrutura necessidade / riscos / interesse público.
    """
    paras = _split_paragraphs(text)
    if not paras:
        return ""
    if len(paras) > 3:
        paras = paras[:3]
    return "\n\n".join(paras)
