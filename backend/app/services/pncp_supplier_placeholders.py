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

# Literais de metadado gravados em fornecedor_contato_fonte / fornecedor_fonte_nome (não são razão social).
SUPPLIER_FONTE_IDENTIFIERS = frozenset(
    {
        "receitaws_cnpj",
        "receitaws",
        "brasilapi_cnpj",
        "brasilapi",
        "cnpj.ws",
        "cnpj_ws",
        "sem_email",
    }
)

_SUPPLIER_NAME_METADATA_KEY_EXACT = frozenset(
    {
        "fornecedor_fonte",
        "fornecedor_fonte_nome",
        "fornecedor_contato_fonte",
        "fornecedor_elegivel",
        "fornecedor_origem_indice",
        "fornecedor_enriquecido_ao_adicionar",
        "fornecedor_cadastro",
        "fornecedor_hibrido_live",
        "fornecedor_busca_pncp",
    }
)


def is_supplier_fonte_identifier(text: str) -> bool:
    low = re.sub(r"\s+", " ", str(text or "").strip()).lower()
    if not low:
        return False
    if low in SUPPLIER_FONTE_IDENTIFIERS:
        return True
    if low.startswith("pncp_"):
        return True
    # Tags curtas tipo receitaws_cnpj / brasilapi_cnpj sem espaços.
    if " " not in low and low.endswith("_cnpj") and low.replace("_", "").replace(".", "").isalnum():
        return True
    return False


def supplier_name_metadata_key(key: str) -> bool:
    """Chaves JSON de metadado de fornecedor — não usar como razão social."""
    k = str(key or "").strip().lower()
    if k in _SUPPLIER_NAME_METADATA_KEY_EXACT:
        return True
    return k.startswith(("fornecedor_fonte", "fornecedor_contato"))


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
    if is_supplier_fonte_identifier(s):
        return ""
    return s
