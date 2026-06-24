"""Normalização da justificativa — 3 parágrafos distintos, sem eco nem listas."""
from __future__ import annotations

import re
from typing import List, Set

_BULLET_LINE_RE = re.compile(r"^\s*(?:[-*•–—]|\d{1,2}[.)])\s+")

_RUNON_BREAK_RE = re.compile(
    r"(?<=[.!?…])\s+(?=(?:A|O|As|Os)\s+(?:"
    r"não\s+realização|ausência|execução|realização|inexecução|deterioração|degradação"
    r"))",
    re.IGNORECASE,
)

_STOPWORDS: Set[str] = {
    "a", "o", "e", "de", "da", "do", "das", "dos", "em", "para", "com", "por", "ao", "à",
    "aos", "às", "um", "uma", "uns", "umas", "que", "se", "na", "no", "nas", "nos", "ser",
    "são", "é", "além", "disso", "como", "mais", "sem", "sobre", "entre", "após", "até",
    "também", "ainda", "pelo", "pela", "pelos", "pelas", "seu", "sua", "seus", "suas",
}


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
    kept: List[str] = []
    for line in (para or "").split("\n"):
        if _is_bullet_line(line):
            break
        kept.append(line)
    return "\n".join(kept).strip()


def _para_tokens(para: str) -> Set[str]:
    words = re.findall(r"[a-zà-ú]{4,}", (para or "").lower())
    return {w for w in words if w not in _STOPWORDS}


def _paragraph_similarity(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _dedupe_paragraphs(paras: List[str], *, max_keep: int = 3, threshold: float = 0.28) -> List[str]:
    """Mantém até max_keep parágrafos sem eco semântico (mesmas ideias reformuladas)."""
    kept: List[str] = []
    kept_tokens: List[Set[str]] = []
    for para in paras:
        tokens = _para_tokens(para)
        if any(_paragraph_similarity(tokens, prev) >= threshold for prev in kept_tokens):
            continue
        kept.append(para)
        kept_tokens.append(tokens)
        if len(kept) >= max_keep:
            break
    return kept


def _split_runon_paragraph(text: str) -> List[str]:
    """Quebra bloco único em parágrafos quando a LLM não usa linha em branco."""
    text = (text or "").strip()
    if not text or "\n" in text:
        return []
    parts = [p.strip() for p in _RUNON_BREAK_RE.split(text) if p.strip()]
    if len(parts) < 2:
        return []
    # Evita quebrar no primeiro "A deterioração" do texto (início natural do 1º parágrafo).
    if parts[0].lower().startswith("a deterioração") and len(parts) > 1:
        return parts
    if len(parts[0]) < 80:
        return []
    return parts


def _split_paragraphs(text: str) -> List[str]:
    text = re.sub(r"\r\n?", "\n", (text or "").strip())
    if not text:
        return []
    parts = [p.strip() for p in re.sub(r"\n{3,}", "\n\n", text).split("\n\n") if p.strip()]
    if len(parts) <= 1:
        lines = [ln.strip() for ln in text.split("\n") if ln.strip() and not _is_bullet_line(ln)]
        if len(lines) >= 2:
            parts = lines
        elif len(parts) == 1:
            runon = _split_runon_paragraph(parts[0])
            if runon:
                parts = runon
    return [_strip_bullets_from_paragraph(p) for p in parts if _strip_bullets_from_paragraph(p)]


def normalize_justificativa_tres_paragrafos(text: str) -> str:
    """
    Justificativa final: no máximo 3 parágrafos distintos.
    Remove listas, eco/resumo da LLM e parágrafos que repetem o mesmo eixo argumentativo.
    """
    cleaned = _strip_list_tail(text)
    paras = _split_paragraphs(cleaned)
    if not paras:
        return ""
    paras = _dedupe_paragraphs(paras, max_keep=3)
    return "\n\n".join(paras)
