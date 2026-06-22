"""
Match de variáveis de produto (dose, concentração, %, volume, volumes) para rerank/scoring PNCP.

Complementa pack_size_match (embalagem C/100 UN) com specs farmacêuticas e apresentação.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .search_text_clean import normalize_for_search

_CONC_MG_ML_RE = re.compile(r"(\d+(?:\.\d+)?)\s*mg\s*/\s*ml\b", re.IGNORECASE)
_PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:%|pct\b)", re.IGNORECASE)
_VOLUMES_RE = re.compile(r"(\d+)\s*(?:volumes?|vol\.?)\b", re.IGNORECASE)
_VOL_ML_RE = re.compile(r"(\d+(?:\.\d+)?)\s*ml\b", re.IGNORECASE)
_VOL_LITRO_RE = re.compile(r"(\d+(?:\.\d+)?)\s*litros?\b", re.IGNORECASE)
_VOL_L_SHORT_RE = re.compile(r"(?:^|[\s(])(\d+(?:\.\d+)?)\s+l(?:\s|$|itro)", re.IGNORECASE)
_DOSE_MG_RE = re.compile(r"(\d+(?:\.\d+)?)\s*mg\b", re.IGNORECASE)


@dataclass
class ProductSpecHints:
    conc_mg_per_ml: Optional[float] = None
    dose_mg: Optional[float] = None
    vol_ml: Optional[float] = None
    vol_l: Optional[float] = None
    percent: Optional[float] = None
    volumes: Optional[int] = None
    sources: List[str] = field(default_factory=list)

    def has_constraints(self) -> bool:
        return any(
            v is not None
            for v in (
                self.conc_mg_per_ml,
                self.dose_mg,
                self.vol_ml,
                self.vol_l,
                self.percent,
                self.volumes,
            )
        )


def _parse_num(raw: str) -> Optional[float]:
    try:
        return float(str(raw).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _parse_int(raw: str) -> Optional[int]:
    n = _parse_num(raw)
    if n is None:
        return None
    return int(round(n))


def _norm_text(text: str) -> str:
    return normalize_for_search(text or "")


def _item_blob(item: Dict[str, Any]) -> str:
    parts = [
        str(item.get("descricao_item") or item.get("descricao") or ""),
        str(item.get("descricao_item_original") or ""),
        str(item.get("material_servico") or item.get("material_servico_original") or ""),
        str(item.get("unidade_medida") or ""),
    ]
    return " ".join(p for p in parts if p.strip())


def extract_product_spec_from_text(text: str, *, source: str = "text") -> ProductSpecHints:
    raw = (text or "").strip()
    norm = _norm_text(text)
    if not raw and not norm:
        return ProductSpecHints()

    hints = ProductSpecHints()
    srcs: List[str] = []

    # % e mg/ml no bruto — normalize_for_search remove % e /
    for pm in re.finditer(r"(\d+(?:[.,]\d+)?)\s*%", raw, re.IGNORECASE):
        val = _parse_num(pm.group(1))
        if val is not None and 0 < val <= 100:
            hints.percent = val
            srcs.append(f"{source}:pct_raw")
            break

    for cm in re.finditer(r"(\d+(?:[.,]\d+)?)\s*mg\s*/\s*ml", raw, re.IGNORECASE):
        hints.conc_mg_per_ml = _parse_num(cm.group(1))
        srcs.append(f"{source}:conc_raw")
        break
    if hints.conc_mg_per_ml is None:
        for cm in re.finditer(r"(\d+(?:\.\d+)?)\s*mgml\b", norm):
            hints.conc_mg_per_ml = _parse_num(cm.group(1))
            srcs.append(f"{source}:conc_norm")
            break
        if hints.conc_mg_per_ml is None:
            for cm in re.finditer(r"(\d+(?:\.\d+)?)\s*mg\s+ml\b", norm):
                hints.conc_mg_per_ml = _parse_num(cm.group(1))
                srcs.append(f"{source}:conc_spaced")
                break

    if hints.percent is None:
        for pm in _PERCENT_RE.finditer(norm):
            val = _parse_num(pm.group(1))
            if val is not None and 0 < val <= 100:
                hints.percent = val
                srcs.append(f"{source}:pct")
                break

    for vm in _VOLUMES_RE.finditer(norm):
        hints.volumes = _parse_int(vm.group(1))
        srcs.append(f"{source}:volumes")
        break
    if hints.volumes is None:
        for vm in re.finditer(r"(\d+)\s*(?:volumes?|vol)\b", raw, re.IGNORECASE):
            hints.volumes = _parse_int(vm.group(1))
            srcs.append(f"{source}:volumes_raw")
            break

    if not norm:
        hints.sources = srcs
        return hints

    for vl in _VOL_LITRO_RE.finditer(norm):
        hints.vol_l = _parse_num(vl.group(1))
        srcs.append(f"{source}:litro")
        break
    if hints.vol_l is None:
        for vl in _VOL_L_SHORT_RE.finditer(norm):
            hints.vol_l = _parse_num(vl.group(1))
            srcs.append(f"{source}:l")
            break

    vol_ml_vals: List[float] = []
    for vml in _VOL_ML_RE.finditer(norm):
        val = _parse_num(vml.group(1))
        if val is not None:
            vol_ml_vals.append(val)
    if vol_ml_vals:
        # Apresentação injetável: menor ml costuma ser frasco; concentração usa mg/ml separado.
        hints.vol_ml = min(vol_ml_vals) if len(vol_ml_vals) == 1 else vol_ml_vals[0]
        srcs.append(f"{source}:ml")

    if hints.conc_mg_per_ml is None:
        for dm in _DOSE_MG_RE.finditer(norm):
            end = dm.end()
            tail = norm[end : end + 8].lstrip()
            if tail.startswith("/"):
                continue
            hints.dose_mg = _parse_num(dm.group(1))
            srcs.append(f"{source}:dose")
            break

    hints.sources = srcs
    return hints


def extract_product_spec_from_term(termo: str) -> ProductSpecHints:
    return extract_product_spec_from_text(termo, source="termo")


def extract_product_spec_from_item(item: Dict[str, Any]) -> ProductSpecHints:
    return extract_product_spec_from_text(_item_blob(item), source="item")


def product_spec_has_constraints(termo: str) -> bool:
    return extract_product_spec_from_term(termo).has_constraints()


def _float_close(a: float, b: float, *, rel: float = 0.02, abs_tol: float = 0.5) -> bool:
    if abs(a - b) <= abs_tol:
        return True
    denom = max(abs(a), abs(b), 1e-9)
    return abs(a - b) / denom <= rel


def product_spec_rerank_adjustment(termo_raw: str, item: Dict[str, Any]) -> float:
    """
    Bônus/penalidade quando dose, concentração, %, volume ou volumes divergem do pedido.
    Retorno típico: -48..+28.
    """
    term = extract_product_spec_from_term(termo_raw)
    if not term.has_constraints():
        return 0.0

    got = extract_product_spec_from_item(item)
    adj = 0.0

    pct_match = (
        term.percent is not None
        and got.percent is not None
        and _float_close(term.percent, got.percent, abs_tol=0.5)
    )
    vol_l_match = (
        term.vol_l is not None
        and got.vol_l is not None
        and _float_close(term.vol_l, got.vol_l, abs_tol=0.05)
    )
    vol_l_conflict = (
        term.vol_l is not None
        and got.vol_l is not None
        and not _float_close(term.vol_l, got.vol_l, abs_tol=0.05)
    )

    if term.volumes is not None:
        if got.volumes == term.volumes:
            adj += 26.0
        elif got.volumes is not None:
            adj -= 44.0
        else:
            adj -= 14.0

    if term.percent is not None:
        if pct_match and not vol_l_conflict:
            adj += 22.0
        elif got.percent is not None and not pct_match:
            adj -= 42.0
        elif got.percent is None:
            adj -= 12.0

    if term.conc_mg_per_ml is not None:
        if got.conc_mg_per_ml is not None:
            adj += 20.0 if _float_close(term.conc_mg_per_ml, got.conc_mg_per_ml, abs_tol=0.1) else -38.0
        else:
            adj -= 8.0

    if term.dose_mg is not None:
        if got.dose_mg is not None:
            adj += 28.0 if _float_close(term.dose_mg, got.dose_mg, abs_tol=0.1) else -48.0
        elif got.conc_mg_per_ml is None:
            adj -= 10.0

    if term.vol_l is not None:
        if vol_l_match:
            adj += 26.0
        elif vol_l_conflict:
            adj -= 48.0
        elif got.vol_ml is not None:
            expected_ml = term.vol_l * 1000.0
            adj += 22.0 if _float_close(expected_ml, got.vol_ml, rel=0.05, abs_tol=50) else -40.0
        else:
            adj -= 14.0

    if term.vol_ml is not None and term.conc_mg_per_ml is None:
        if got.vol_ml is not None:
            adj += 24.0 if _float_close(term.vol_ml, got.vol_ml, rel=0.08, abs_tol=2) else -40.0
        else:
            adj -= 10.0

    return adj


def product_spec_strict_reject(termo_raw: str, item: Dict[str, Any]) -> bool:
    """True quando o item contradiz specs explícitas do pedido (filtro em modo strict)."""
    return product_spec_rerank_adjustment(termo_raw, item) <= -38.0
