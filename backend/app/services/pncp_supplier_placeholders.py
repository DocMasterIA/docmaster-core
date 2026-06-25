"""Nomes de fornecedor placeholder retornados pela PNCP (não são razão social)."""

from __future__ import annotations

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
    }
)
