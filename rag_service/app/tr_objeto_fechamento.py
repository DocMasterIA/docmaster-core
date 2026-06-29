"""
Fechamento normativo do campo objeto no TR — «neste Termo de Referência».

DFD e Ofício convertem para «no Termo de Referência» na renderização (tr_deixis).
"""
from __future__ import annotations

import re

TR_FECHAMENTO_AQUISICAO = (
    ", conforme quantidades e demais condições estabelecidas neste Termo de Referência"
)
TR_FECHAMENTO_CONTRATACAO = (
    ", conforme requisitos técnicos e demais condições estabelecidas neste Termo de Referência"
)

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


def _objeto_is_aquisicao(text: str) -> bool:
    low = text.lower()
    service_hints = (
        "serviço",
        "servicos",
        "prestação",
        "prestacao",
        "manutenção",
        "manutencao",
        "execução",
        "execucao",
        "obra",
        "engenharia",
        "locação",
        "locacao",
    )
    has_service = any(h in low for h in service_hints)
    has_goods = bool(
        re.search(r"(?i)\b(aquisi(?:c|ç)[aã]o|fornecimento|material|produto|insumo|equipamento)\b", low)
    )
    if has_service and not has_goods:
        return False
    if has_goods and not has_service:
        return True
    return bool(re.search(r"(?i)\b(aquisi(?:c|ç)[aã]o|fornecimento)\b", low))


def ensure_tr_objeto_fechamento(text: str) -> str:
    """Garante fechamento normativo com «neste Termo de Referência» (padrão TR)."""
    t = (text or "").strip()
    if not t:
        return t

    fechamento = TR_FECHAMENTO_AQUISICAO if _objeto_is_aquisicao(t) else TR_FECHAMENTO_CONTRATACAO

    if _RE_TR_FECHAMENTO_ANY.search(t) or _RE_EM_QUANTIDADE.search(t):
        t = _RE_EM_QUANTIDADE.sub("", t)
        t = _RE_TR_FECHAMENTO_ANY.sub("", t)
        t = re.sub(r"\s{2,}", " ", t).rstrip(".,;: ").strip()

    base = t.rstrip(".,;: ").strip()
    if not base:
        return t
    return f"{base}{fechamento}."
