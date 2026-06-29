"""
Fechamento normativo do campo objeto no TR — «neste Termo de Referência».

Único fechamento permitido (aquisição e contratação):
«, conforme quantidades e demais condições estabelecidas neste Termo de Referência»

DFD e Ofício convertem para «no Termo de Referência» na renderização (tr_deixis).
"""
from __future__ import annotations

import re

TR_FECHAMENTO_PADRAO = (
    ", conforme quantidades e demais condições estabelecidas neste Termo de Referência"
)
# Alias legado nos testes/importadores
TR_FECHAMENTO_AQUISICAO = TR_FECHAMENTO_PADRAO

_RE_TR_FECHAMENTO_ANY = re.compile(
    r"(?i),?\s*conforme\s+"
    r"(?:"
    r"quantidades(?:\s+e(?:\s+quantitativos?)?)?"
    r"|requisitos\s+t[eé]cnicos"
    r"|especifica[cç][oõ]es\s+t[eé]cnicas(?:,?\s*quantitativos?\s+e)?"
    r")"
    r"\s+demais\s+condi[çc][õo]es\s+estabelecidas\s+"
    r"(?:neste|no)\s+termo\s+de\s+refer[eê]ncia\.?"
)
_RE_EM_QUANTIDADE = re.compile(
    r"(?i),?\s*em\s+quantidade\s+conforme\s+estipulado\s+(?:neste|no)\s+termo\s+de\s+refer[eê]ncia\.?"
)


def ensure_tr_objeto_fechamento(text: str) -> str:
    """Garante o fechamento normativo único com «neste Termo de Referência»."""
    t = (text or "").strip()
    if not t:
        return t

    if _RE_TR_FECHAMENTO_ANY.search(t) or _RE_EM_QUANTIDADE.search(t):
        t = _RE_EM_QUANTIDADE.sub("", t)
        t = _RE_TR_FECHAMENTO_ANY.sub("", t)
        t = re.sub(r"\s{2,}", " ", t).rstrip(".,;: ").strip()

    base = t.rstrip(".,;: ").strip()
    if not base:
        return t
    return f"{base}{TR_FECHAMENTO_PADRAO}."
