"""Nomes de fornecedor placeholder retornados pela PNCP (não são razão social)."""

from __future__ import annotations

import re
from typing import Any

GENERIC_SUPPLIER_NAMES = frozenset(
    {
        "demais",
        "nao informado",
        "não informado",
        "nao informada",
        "não informada",
        "epp",
        "me",
        "mei",
        "outros",
        "n/a",
        "na",
        "n.a",
        "n.a.",
        "nao se aplica",
        "não se aplica",
        "nao aplicavel",
        "não aplicavel",
        "não aplicável",
        "sem fornecedor",
        "nao consta",
        "não consta",
        "inexistente",
        "-",
        "—",
        # Booleanos / literais serializados no JSON PNCP (ex.: fornecedor=true).
        "true",
        "false",
        "none",
        "null",
    }
)


def coerce_supplier_name_text(raw: Any) -> str:
    """Converte valor bruto em texto de nome; descarta bool, números e literais inválidos."""
    if raw is None:
        return ""
    if isinstance(raw, bool):
        return ""
    if isinstance(raw, (int, float)):
        return ""
    s = str(raw).strip()
    if not s:
        return ""
    low = re.sub(r"\s+", " ", s).strip().lower()
    if low in GENERIC_SUPPLIER_NAMES:
        return ""
    return s
