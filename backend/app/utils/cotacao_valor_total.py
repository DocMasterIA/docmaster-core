"""Cálculo do valor total estimado de uma sessão de cotação PNCP."""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional


def _safe_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f or f in (float("inf"), float("-inf")):
        return None
    return f


def somar_valor_total_estimado_itens(
    itens: Iterable[Any],
    refletidos: Optional[Mapping[int, Mapping[str, Any]]] = None,
) -> Optional[float]:
    """
    Soma os totais por item na mesma ordem de prioridade da UI de cotação:
    valor_total_refletido → valor_total → valor_unitario.
    """
    refletidos = refletidos or {}
    soma = 0.0
    tem_valor = False
    for item in itens or []:
        if isinstance(item, dict):
            item_id = int(item.get("id") or 0)
            valor_total = item.get("valor_total")
            valor_unitario = item.get("valor_unitario")
        else:
            item_id = int(getattr(item, "id", 0) or 0)
            valor_total = getattr(item, "valor_total", None)
            valor_unitario = getattr(item, "valor_unitario", None)

        ref = refletidos.get(item_id, {}) if item_id else {}
        vt = _safe_float(ref.get("valor_total_refletido"))
        if vt is None:
            vt = _safe_float(valor_total)
        if vt is None:
            vt = _safe_float(valor_unitario)
        if vt is not None and vt >= 0:
            soma += float(vt)
            tem_valor = True
    return round(soma, 2) if tem_valor else None
