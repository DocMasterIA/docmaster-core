"""Sanitização do campo objeto — sem fechamento normativo do TR nem justificativa."""
from __future__ import annotations

import re
from typing import List

_OBJETO_JUSTIFICATIVA_BLEED_MARKERS = (
    "a presente contratação justifica-se",
    "a presente contratacao justifica-se",
    "justifica-se pela necessidade",
    "caso não seja realizada",
    "caso a contratação não seja",
    "em caso de não contratação",
    "por conseguinte, a justificativa",
)


def _is_pure_boilerplate_sentence(sentence: str) -> bool:
    low = sentence.lower().strip()
    if re.match(r"^a execu[cç][aã]o obedecer", low):
        return True
    if re.match(r"^obedecer[aá] rigorosamente", low):
        return True
    if re.match(r"^conforme (especifica|quantidades|requisitos)", low):
        return True
    return any(m in low for m in _OBJETO_JUSTIFICATIVA_BLEED_MARKERS)


def sanitize_objeto_clause_pura(text: str) -> str:
    """
    Objeto = só o que se contrata e finalidade administrativa.
    Remove fechamento normativo do TR e frases típicas de justificativa.
    """
    t = (text or "").strip()
    if not t:
        return ""

    parts = re.split(r"(?<=[.!?])\s+", t)
    kept: List[str] = []
    for sent in parts:
        s = sent.strip()
        if not s or _is_pure_boilerplate_sentence(s):
            continue
        kept.append(s)
    t = " ".join(kept).strip()

    trailing_patterns = [
        r"[,;]?\s*a execu[cç][aã]o obedecer[aá][^.]*\.?",
        r"[,;]?\s*obedecer[aá] rigorosamente[^.]*\.?",
        r"[,;]?\s*conforme especifica[cç][oõ]es t[eé]cnicas[^.]*termo de refer[eê]ncia[^.]*\.?",
        r"[,;]?\s*conforme quantidades e demais condi[cç][oõ]es estabelecidas neste termo de refer[eê]ncia\.?",
        r"[,;]?\s*conforme requisitos t[eé]cnicos e demais condi[cç][oõ]es estabelecidas neste termo de refer[eê]ncia\.?",
        r"[,;]?\s*em quantidade conforme estipulado neste termo de refer[eê]ncia\.?",
    ]
    for pat in trailing_patterns:
        t = re.sub(pat, "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s{2,}", " ", t).strip()
    t = re.sub(r"[;:,]+\s*$", "", t).strip()
    if t and not t.endswith((".", "!", "?")):
        t = f"{t}."
    return t
