"""Preço unitário canônico para faixa, scoring e resposta HTTP."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .pricing_faixa import normalize_variacao_sentido
from .supplier_resolver import item_fornecedor_tem_cnpj_para_salvar, item_fornecedor_valido_para_busca


def _safe_float(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _optional_positive(value: Any) -> Optional[float]:
    v = _safe_float(value)
    return v if v > 0.0 else None


def homolog_pricing_present(it: Dict[str, Any]) -> bool:
    vu = _optional_positive(it.get("valor_unitario_homologado"))
    vt = _optional_positive(it.get("valor_total_homologado"))
    return vu is not None or vt is not None


def item_needs_homolog_pricing_lookup(it: Dict[str, Any]) -> bool:
    """Item homologado indexado sem preço vencedor de /resultados."""
    if homolog_pricing_present(it):
        return False
    if not it.get("item_homologado"):
        return False
    import re

    cnpj = re.sub(r"\D", "", str(it.get("numero_pncp") or "").split("-")[0])
    ano = it.get("ano_compra")
    seq = it.get("sequencial_compra")
    ni = str(it.get("numero_item") or "").strip()
    return len(cnpj) == 14 and bool(ano) and bool(seq) and bool(ni)


def merge_homologated_pricing_from_snap(it: Dict[str, Any], snap: Dict[str, Any]) -> bool:
    """Mescla preços de /resultados no item da busca (paridade Django save)."""
    if not isinstance(snap, dict):
        return False
    vu = _optional_positive(
        snap.get("valor_unitario_homologado") or snap.get("valorUnitarioHomologado")
    )
    vt = _optional_positive(snap.get("valor_total_homologado") or snap.get("valorTotalHomologado"))
    qh = _optional_positive(snap.get("quantidade_homologada") or snap.get("quantidadeHomologada"))
    if vu is None and vt is None:
        return False

    changed = False
    for key, val in (
        ("valor_unitario_homologado", vu),
        ("valor_total_homologado", vt),
        ("quantidade_homologada", qh),
    ):
        if val is not None and it.get(key) != val:
            it[key] = val
            changed = True

    if vu is not None and it.get("valor_unitario") != vu:
        it["valor_unitario"] = vu
        changed = True
    if vt is not None and it.get("valor_total") != vt:
        it["valor_total"] = vt
        changed = True
    elif vu is not None and vt is None:
        q = qh or _optional_positive(it.get("quantidade"))
        if q is not None:
            calc = vu * q
            if it.get("valor_total") != calc:
                it["valor_total"] = calc
                changed = True
    if changed:
        it["preco_homologado_pncp"] = True
    return changed


def row_unit_price_for_faixa_gate(
    it: Dict[str, Any],
    *,
    sentido: Optional[str] = None,
) -> float:
    """
    Preço para gate de faixa.

  - ``cima`` / ``baixo``: homologado sem preço vencedor não usa catálogo/estimado
    (evita passar com valor inflado antes do enrich PNCP).
    """
    sent = normalize_variacao_sentido(sentido) if sentido is not None else "ambos"
    hom = _optional_positive(it.get("valor_unitario_homologado"))
    if hom is not None:
        return hom
    if sent != "ambos" and it.get("item_homologado"):
        return 0.0
    return row_display_unit_price(it)


def item_matches_faixa_band(
    it: Dict[str, Any],
    lo: float,
    hi: float,
    *,
    sentido: Optional[str] = None,
) -> bool:
    """
    Gate de faixa na busca (regra rígida).

    Usa **somente** o preço canônico de exibição (homologado > unitário > estimado).
    Nunca aceita item cujo preço exibido está fora da banda — mesmo que outro
    campo (ex.: estimado) caia dentro da VAR.
    """
    p = row_unit_price_for_faixa_gate(it, sentido=sentido)
    return p > 0.0 and lo <= p <= hi


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


def filter_items_for_bulk_salvar_response(items: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    """Lote/autostart: só retorna linhas salváveis (CNPJ + preço + fornecedor não-placeholder)."""
    out: list[Dict[str, Any]] = []
    for row in items:
        item = dict(row)
        if not item_fornecedor_tem_cnpj_para_salvar(item):
            continue
        if not item_fornecedor_valido_para_busca(item):
            continue
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
