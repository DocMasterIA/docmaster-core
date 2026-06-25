"""Preço unitário canônico para faixa, scoring e resposta HTTP."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .supplier_resolver import item_fornecedor_valido_para_busca


def _safe_float(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def row_display_unit_price(it: Dict[str, Any]) -> float:
    """
    Preço unitário positivo para exibição e faixa regional.
    Prioridade: homologado > coluna unitária > estimado > total/qtd.
    """
    for key in ("valor_unitario_homologado", "valor_unitario", "valor_unitario_estimado"):
        v = _safe_float(it.get(key))
        if v > 0.0:
            return v
    for total_key, qty_key in (
        ("valor_total_homologado", "quantidade_homologada"),
        ("valor_total", "quantidade"),
        ("valor_total_estimado", "quantidade_estimada"),
    ):
        total = _safe_float(it.get(total_key))
        qty = _safe_float(it.get(qty_key))
        if total > 0.0 and qty > 0.0:
            return total / qty
    return 0.0


def row_display_total_price(it: Dict[str, Any], *, unit: Optional[float] = None) -> float:
    """Total positivo derivado ou explícito."""
    for key in ("valor_total_homologado", "valor_total", "valor_total_estimado", "valor_global"):
        v = _safe_float(it.get(key))
        if v > 0.0:
            return v
    u = unit if unit is not None else row_display_unit_price(it)
    qty = _safe_float(it.get("quantidade_homologada")) or _safe_float(it.get("quantidade"))
    if u > 0.0 and qty > 0.0:
        return u * qty
    return 0.0


def normalize_item_pricing_for_response(it: Dict[str, Any]) -> bool:
    """
    Preenche ``valor_unitario`` / ``valor_total`` na resposta com preços positivos.
    Retorna False se não houver preço exibível.
    """
    unit = row_display_unit_price(it)
    if unit <= 0.0:
        return False
    it["valor_unitario"] = unit
    total = row_display_total_price(it, unit=unit)
    if total > 0.0:
        it["valor_total"] = total
    return True


def filter_items_with_display_price(items: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    out: list[Dict[str, Any]] = []
    for row in items:
        item = dict(row)
        if normalize_item_pricing_for_response(item):
            out.append(item)
    return out


def filter_items_for_search_display(items: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    """Preço positivo + fornecedor válido (CNPJ ou razão social; sem placeholders PNCP)."""
    out: list[Dict[str, Any]] = []
    for row in items:
        item = dict(row)
        if not item_fornecedor_valido_para_busca(item):
            continue
        if normalize_item_pricing_for_response(item):
            out.append(item)
    return out
