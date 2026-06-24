"""Normalização da justificativa — exatamente 3 parágrafos, sem listas nem continuação."""
from __future__ import annotations

import re
from typing import List

_BULLET_LINE_RE = re.compile(r"^\s*(?:[-*•–—]|\d{1,2}[.)])\s+")


def _is_bullet_line(line: str) -> bool:
    return bool(_BULLET_LINE_RE.match((line or "").strip()))


def _strip_list_tail(text: str) -> str:
    """Corta na primeira linha de lista (bullets ou numeração) e descarta o restante."""
    text = re.sub(r"\r\n?", "\n", (text or "").strip())
    if not text:
        return ""
    kept: List[str] = []
    for line in text.split("\n"):
        if _is_bullet_line(line):
            break
        kept.append(line)
    return "\n".join(kept).strip()


def _strip_bullets_from_paragraph(para: str) -> str:
    """Remove bullets embutidos no meio de um parágrafo."""
    kept: List[str] = []
    for line in (para or "").split("\n"):
        if _is_bullet_line(line):
            break
        kept.append(line)
    return "\n".join(kept).strip()


def _split_paragraphs(text: str) -> List[str]:
    text = re.sub(r"\r\n?", "\n", (text or "").strip())
    if not text:
        return []
    parts = [p.strip() for p in re.sub(r"\n{3,}", "\n\n", text).split("\n\n") if p.strip()]
    if len(parts) <= 1:
        lines = [ln.strip() for ln in text.split("\n") if ln.strip() and not _is_bullet_line(ln)]
        if len(lines) >= 2:
            parts = lines
    return [_strip_bullets_from_paragraph(p) for p in parts if _strip_bullets_from_paragraph(p)]


def normalize_justificativa_tres_paragrafos(text: str) -> str:
    """
    Garante no máximo 3 parágrafos prose na justificativa.
    Remove listas com marcadores e conteúdo após o 3º parágrafo (eco/resumo da LLM).
    """
    cleaned = _strip_list_tail(text)
    paras = _split_paragraphs(cleaned)
    if not paras:
        return ""
    if len(paras) > 3:
        paras = paras[:3]
    return "\n\n".join(paras)
