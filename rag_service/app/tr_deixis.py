"""
Deixis «neste» vs «no» + «termo de referência» conforme o documento.

- TR: o texto fala do próprio documento → «neste Termo de Referência».
- DFD / Solicitação-Ofício: citam o TR à parte → «no Termo de Referência».

A IA ou o override podem gerar qualquer forma; cada render ajusta só o necessário.
"""
from __future__ import annotations

import re

_RE_NESTE_TR = re.compile(
    r"\bneste\s+termo\s+de\s+refer[eê]?ncia\b",
    re.IGNORECASE,
)
_RE_NO_TR = re.compile(
    r"\bno\s+termo\s+de\s+refer[eê]?ncia\b",
    re.IGNORECASE,
)


def _replace_leading_word(m: re.Match, new_word: str) -> str:
    phrase = m.group(0)
    parts = phrase.split()
    if len(parts) < 4:
        return phrase
    lead = parts[0]
    if lead.isupper():
        w = new_word.upper()
    elif lead[:1].isupper():
        w = new_word.capitalize()
    else:
        w = new_word.lower()
    return f"{w} {' '.join(parts[1:])}"


def adapt_text_for_tr(text: str) -> str:
    """TR: «no termo de referência» → «neste termo de referência» (mantém «neste» se já vier assim)."""
    if not text:
        return text
    return _RE_NO_TR.sub(lambda m: _replace_leading_word(m, "neste"), text)


def adapt_text_for_dfd_or_oficio(text: str) -> str:
    """DFD / ofício: «neste termo de referência» → «no termo de referência» (mantém «no» se já vier assim)."""
    if not text:
        return text
    return _RE_NESTE_TR.sub(lambda m: _replace_leading_word(m, "no"), text)
