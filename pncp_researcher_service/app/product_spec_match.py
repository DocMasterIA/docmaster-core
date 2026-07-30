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
# Xarope/suspensão: 30MG/5ML = 30 mg por 5 ml de apresentação (≠ 30 mg/ml).
_MG_PER_DOSE_VOL_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*mg\s*/\s*(\d+(?:[.,]\d+)?)\s*ml\b",
    re.IGNORECASE,
)
_MAX_PRESENTATION_DOSE_VOL_ML = 30.0
_PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:%|pct\b)", re.IGNORECASE)
_VOLUMES_RE = re.compile(r"(\d+)\s*(?:volumes?|vol\.?)\b", re.IGNORECASE)
_VOL_ML_RE = re.compile(r"(\d+(?:\.\d+)?)\s*ml\b", re.IGNORECASE)
_VOL_LITRO_RE = re.compile(r"(\d+(?:\.\d+)?)\s*litros?\b", re.IGNORECASE)
_VOL_L_SHORT_RE = re.compile(r"(?:^|[\s(])(\d+(?:\.\d+)?)\s+l(?:\s|$|itro)", re.IGNORECASE)
_DOSE_MG_RE = re.compile(r"(\d+(?:\.\d+)?)\s*mg\b", re.IGNORECASE)
_DIM_CM_X_M_RAW = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*cm\s*[xX×]\s*(\d+(?:[.,]\d+)?)\s*(?:m|mt|metros?)\b",
    re.IGNORECASE,
)
_DIM_CM_X_M_NORM = re.compile(r"(\d+(?:p\d+)?)cmx(\d+(?:p\d+)?)m\b")
_WIDTH_CM_RE = re.compile(
    r"(?:largura|boca|faixa)\s*:?\s*(\d+(?:[.,]\d+)?)\s*cm\b",
    re.IGNORECASE,
)
_WIDTH_CM_LOOSE = re.compile(r"(\d+(?:[.,]\d+)?)\s*cm\b", re.IGNORECASE)
_LENGTH_M_EXPLICIT = re.compile(
    r"(?:comprimento|comp)\s*:?\s*(\d+(?:[.,]\d+)?)\s*(?:m|mt|metros?)\b",
    re.IGNORECASE,
)
_LENGTH_MT_LOOSE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:mt|metros?)\b", re.IGNORECASE)
_NEEDLE_CM_RE = re.compile(
    r"agulh[ao]s?\s*(\d+(?:[.,]\d+)?)\s*cm\b",
    re.IGNORECASE,
)
_CALIBRE_NORM_TOKEN_RE = re.compile(r"\bn(\d+(?:p\d+)?)\b")
_AGULHADO_CALIBRE_RE = re.compile(
    r"\bagulhad[oa]?\s*(\d+(?:[.,]\d+)?)\b",
    re.IGNORECASE,
)
_NYLON_CALIBRE_RE = re.compile(
    r"\bnylon\s+(\d+(?:[.,]\d+)?)\b",
    re.IGNORECASE,
)
_LUVA_ESTERIL_SIZE_RE = re.compile(
    r"\bluva\b[^.]{0,96}?\besteril\w*\s+(\d+(?:[.,]\d+)?)\b",
    re.IGNORECASE,
)
_LUVA_TAMANHO_RE = re.compile(r"\btamanho\s+(\d{2})\b", re.IGNORECASE)
_SUTURE_ZERO_RE = re.compile(r"\b(\d+)\s*-\s*0\b", re.IGNORECASE)
_UNITS_PER_G_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*u\s*/\s*g\b", re.IGNORECASE)
_COMBO_SPLIT_RE = re.compile(r"\s*\+\s*")

_EXCIPIENT_TOKENS = frozenset(
    {
        "cloridrato",
        "sodica",
        "sodico",
        "bissulfato",
        "ampola",
        "solucao",
        "injetavel",
        "comprimido",
        "pomada",
        "frasco",
    }
)

_PRODUCT_LINE_EXCLUSIVE: Dict[str, frozenset] = {
    "smarch": frozenset({"kinesio", "knesio", "cinesio"}),
    "kinesio": frozenset({"smarch"}),
    "knesio": frozenset({"smarch"}),
}


@dataclass
class ProductSpecHints:
    conc_mg_per_ml: Optional[float] = None
    dose_mg: Optional[float] = None
    presentation_vol_ml: Optional[float] = None
    vol_ml: Optional[float] = None
    vol_l: Optional[float] = None
    percent: Optional[float] = None
    volumes: Optional[int] = None
    width_cm: Optional[float] = None
    length_m: Optional[float] = None
    calibre: Optional[float] = None
    needle_cm: Optional[float] = None
    units_per_g: Optional[float] = None
    sources: List[str] = field(default_factory=list)

    def has_constraints(self) -> bool:
        return any(
            v is not None
            for v in (
                self.conc_mg_per_ml,
                self.dose_mg,
                self.presentation_vol_ml,
                self.vol_ml,
                self.vol_l,
                self.percent,
                self.volumes,
                self.width_cm,
                self.length_m,
                self.calibre,
                self.needle_cm,
                self.units_per_g,
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


def _parse_dim_num(raw: str) -> Optional[float]:
    try:
        return float(str(raw).replace(",", ".").replace("p", "."))
    except (TypeError, ValueError):
        return None


def _parse_calibre_token(tok: str) -> Optional[float]:
    m = re.match(r"^n(\d+(?:p\d+)?)$", (tok or "").strip().lower())
    if not m:
        return None
    return _parse_dim_num(m.group(1))


def _extract_calibre(raw: str, norm: str, srcs: List[str], *, source: str) -> Optional[float]:
    for tok in norm.split():
        val = _parse_calibre_token(tok)
        if val is not None:
            srcs.append(f"{source}:calibre_norm")
            return val
    for am in _AGULHADO_CALIBRE_RE.finditer(raw):
        val = _parse_num(am.group(1))
        if val is not None:
            srcs.append(f"{source}:agulhado")
            return val
    for nm in _NYLON_CALIBRE_RE.finditer(raw):
        val = _parse_num(nm.group(1))
        if val is not None:
            srcs.append(f"{source}:nylon_num")
            return val
    for sm in _SUTURE_ZERO_RE.finditer(raw):
        val = _parse_num(sm.group(1))
        if val is not None:
            srcs.append(f"{source}:suture_zero")
            return val
    if "luva" in norm:
        for lm in _LUVA_ESTERIL_SIZE_RE.finditer(raw):
            val = _parse_num(lm.group(1))
            if val is not None:
                srcs.append(f"{source}:luva_esteril")
                return val
        for tm in _LUVA_TAMANHO_RE.finditer(raw):
            val = _parse_num(tm.group(1))
            if val is not None and val >= 50:
                srcs.append(f"{source}:luva_tamanho")
                return val / 10.0
    return None


def _extract_needle_cm(raw: str, srcs: List[str], *, source: str) -> Optional[float]:
    for nm in _NEEDLE_CM_RE.finditer(raw):
        val = _parse_num(nm.group(1))
        if val is not None:
            srcs.append(f"{source}:needle_cm")
            return val
    return None


def _extract_units_per_g(raw: str, srcs: List[str], *, source: str) -> Optional[float]:
    for um in _UNITS_PER_G_RE.finditer(raw):
        val = _parse_num(um.group(1))
        if val is not None:
            srcs.append(f"{source}:u_per_g")
            return val
    return None


def _calibre_close(a: float, b: float) -> bool:
    return _float_close(a, b, rel=0.02, abs_tol=0.25)


def _extract_dimensions(
    raw: str, norm: str, srcs: List[str], *, source: str
) -> tuple[Optional[float], Optional[float]]:
    width: Optional[float] = None
    length: Optional[float] = None
    for dm in _DIM_CM_X_M_RAW.finditer(raw):
        width = _parse_dim_num(dm.group(1))
        length = _parse_dim_num(dm.group(2))
        srcs.append(f"{source}:dim_raw")
        return width, length
    for dm in _DIM_CM_X_M_NORM.finditer(norm):
        width = _parse_dim_num(dm.group(1))
        length = _parse_dim_num(dm.group(2))
        srcs.append(f"{source}:dim_norm")
        return width, length
    for wm in _WIDTH_CM_RE.finditer(raw):
        width = _parse_dim_num(wm.group(1))
        srcs.append(f"{source}:width")
        break
    if width is None:
        for wm in _WIDTH_CM_LOOSE.finditer(raw):
            prefix = raw[max(0, wm.start() - 24) : wm.start()].lower()
            if "agulh" in prefix:
                continue
            width = _parse_dim_num(wm.group(1))
            srcs.append(f"{source}:width_loose")
            break
    for lm in _LENGTH_M_EXPLICIT.finditer(raw):
        length = _parse_dim_num(lm.group(1))
        srcs.append(f"{source}:length")
        break
    if length is None:
        for lm in _LENGTH_MT_LOOSE.finditer(raw):
            length = _parse_dim_num(lm.group(1))
            srcs.append(f"{source}:length_mt")
            break
    return width, length


def _term_primary_actives(term_n: str) -> List[str]:
    skip = frozenset(
        {
            "de",
            "da",
            "do",
            "com",
            "para",
            "em",
            "solucao",
            "injetavel",
            "comprimido",
            "pomada",
            "estéril",
            "esteril",
            "suspensao",
            "xarope",
            "ampola",
            "litro",
            "litros",
            "galao",
        }
    )
    out: List[str] = []
    for tok in term_n.split():
        if len(tok) < 4 or tok in skip or re.match(r"^\d", tok):
            continue
        if tok.endswith("mg") or tok.endswith("ml") or tok.endswith("pct"):
            continue
        out.append(tok)
        if len(out) >= 3:
            break
    return out


def product_combo_strict_reject(termo_raw: str, item: Dict[str, Any]) -> bool:
    """Rejeita associação medicamentosa quando o pedido cita um único princípio."""
    raw = _item_blob(item)
    if "+" not in raw:
        return False
    term_n = _norm_text(termo_raw)
    primaries = _term_primary_actives(term_n)
    if len(primaries) != 1:
        return False
    anchor = primaries[0]
    if anchor not in term_n:
        return False
    item_n = _norm_text(raw)
    for part in _COMBO_SPLIT_RE.split(raw):
        part_n = _norm_text(part)
        if not part_n or anchor in part_n:
            continue
        lead = part_n.split()[0] if part_n.split() else ""
        if len(lead) >= 4 and lead not in _EXCIPIENT_TOKENS and lead not in term_n:
            return True
    return False


def product_line_strict_reject(termo_raw: str, item: Dict[str, Any]) -> bool:
    """Rejeita linha de produto incompatível (ex.: pedido Smarch, resultado Kinesio)."""
    term_n = _norm_text(termo_raw)
    item_n = _norm_text(_item_blob(item))
    for anchor, excludes in _PRODUCT_LINE_EXCLUSIVE.items():
        if anchor not in term_n:
            continue
        for ex in excludes:
            if ex in item_n and anchor not in item_n:
                return True
    return False


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

    dose_vol_ml_exclude: set[float] = set()
    for dm in _MG_PER_DOSE_VOL_RE.finditer(raw):
        dose = _parse_num(dm.group(1))
        dose_vol = _parse_num(dm.group(2))
        if dose is None or dose_vol is None or dose_vol <= 0:
            continue
        tail = raw[dm.end() : dm.end() + 12].lower()
        if tail.lstrip().startswith("/"):
            continue
        if dose_vol > _MAX_PRESENTATION_DOSE_VOL_ML:
            continue
        if hints.dose_mg is None:
            hints.dose_mg = dose
        hints.presentation_vol_ml = dose_vol
        if hints.conc_mg_per_ml is None:
            hints.conc_mg_per_ml = dose / dose_vol
        dose_vol_ml_exclude.add(dose_vol)
        srcs.append(f"{source}:dose_per_vol")
        break

    for cm in re.finditer(r"(\d+(?:[.,]\d+)?)\s*mg\s*/\s*ml", raw, re.IGNORECASE):
        if hints.presentation_vol_ml is not None:
            break
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
        if val is None:
            continue
        if any(abs(val - ex) <= 0.05 for ex in dose_vol_ml_exclude):
            continue
        vol_ml_vals.append(val)
    if vol_ml_vals:
        # Frasco (ex.: 100 ml): ignorar ml da apresentação mg/5ml já excluído acima.
        hints.vol_ml = max(vol_ml_vals) if len(vol_ml_vals) > 1 else vol_ml_vals[0]
        srcs.append(f"{source}:ml")

    if hints.dose_mg is None and hints.conc_mg_per_ml is None:
        for dm in _DOSE_MG_RE.finditer(norm):
            end = dm.end()
            tail = norm[end : end + 8].lstrip()
            if tail.startswith("/"):
                continue
            hints.dose_mg = _parse_num(dm.group(1))
            srcs.append(f"{source}:dose")
            break

    w, ln = _extract_dimensions(raw, norm, srcs, source=source)
    if w is not None:
        hints.width_cm = w
    if ln is not None:
        hints.length_m = ln

    needle = _extract_needle_cm(raw, srcs, source=source)
    if needle is not None:
        hints.needle_cm = needle

    cal = _extract_calibre(raw, norm, srcs, source=source)
    if cal is not None:
        hints.calibre = cal

    u_g = _extract_units_per_g(raw, srcs, source=source)
    if u_g is not None:
        hints.units_per_g = u_g

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
            dose_ok = _float_close(term.dose_mg, got.dose_mg, abs_tol=0.1)
            if dose_ok:
                adj += 28.0
            elif (
                term.presentation_vol_ml is not None
                and got.presentation_vol_ml is not None
                and _float_close(term.presentation_vol_ml, got.presentation_vol_ml, abs_tol=1.0)
            ):
                adj -= 52.0
            else:
                adj -= 48.0
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

    if term.width_cm is not None:
        if got.width_cm is not None:
            adj += 24.0 if _float_close(term.width_cm, got.width_cm, abs_tol=0.5) else -42.0
        else:
            adj -= 10.0

    if term.length_m is not None:
        if got.length_m is not None:
            adj += 28.0 if _float_close(term.length_m, got.length_m, abs_tol=0.15) else -48.0
        elif got.width_cm is None:
            adj -= 12.0

    if term.calibre is not None:
        if got.calibre is not None:
            adj += 30.0 if _calibre_close(term.calibre, got.calibre) else -44.0
        else:
            adj -= 10.0

    if term.needle_cm is not None:
        if got.needle_cm is not None:
            adj += 22.0 if _float_close(term.needle_cm, got.needle_cm, abs_tol=0.4) else -40.0
        else:
            adj -= 8.0

    if term.units_per_g is not None:
        if got.units_per_g is not None:
            adj += 26.0 if _float_close(term.units_per_g, got.units_per_g, abs_tol=0.05) else -44.0
        else:
            adj -= 12.0

    return adj


def product_spec_strong_core_match(termo_raw: str, item: Dict[str, Any]) -> bool:
    """
    Specs numéricas do pedido batem com o item (ex.: 70% + 500 ml) mesmo quando a
    redação PNCP difere («álcool gel» vs «álcool etílico em gel hidratado»).
    """
    adj = product_spec_rerank_adjustment(termo_raw, item)
    if adj < 35.0:
        return False
    term = extract_product_spec_from_term(termo_raw)
    got = extract_product_spec_from_item(item)
    checks = 0
    hits = 0
    if term.percent is not None and got.percent is not None:
        checks += 1
        if _float_close(term.percent, got.percent, abs_tol=0.5):
            hits += 1
    if term.vol_ml is not None and got.vol_ml is not None:
        checks += 1
        if _float_close(term.vol_ml, got.vol_ml, abs_tol=1.0):
            hits += 1
    if term.vol_l is not None and got.vol_l is not None:
        checks += 1
        if _float_close(term.vol_l, got.vol_l, abs_tol=0.01):
            hits += 1
    if checks >= 2:
        return hits == checks
    if checks == 1 and hits == 1 and adj >= 40.0:
        return True
    return adj >= 42.0


def _dose_per_presentation_mismatch(term: ProductSpecHints, got: ProductSpecHints) -> bool:
    """Ex.: pedido 30MG/5ML vs item 15MG/5ML pediátrico."""
    if term.dose_mg is None or got.dose_mg is None:
        return False
    if term.presentation_vol_ml is None or got.presentation_vol_ml is None:
        return False
    if not _float_close(term.presentation_vol_ml, got.presentation_vol_ml, abs_tol=1.0):
        return False
    return not _float_close(term.dose_mg, got.dose_mg, abs_tol=0.1)


# Formas farmacêuticas mutuamente exclusivas (pedido vs item).
_PHARM_FORM_GROUPS: Dict[str, frozenset] = {
    "ocular": frozenset(
        {
            "colirio",
            "colirios",
            "oftalmic",
            "oftalmico",
            "oftalmica",
            "oftalmicos",
            "oftalmicas",
        }
    ),
    "oral_solido": frozenset(
        {
            "comprimido",
            "comprimidos",
            "capsula",
            "capsulas",
            "dragea",
            "drageas",
            "comprimidoefervescente",
        }
    ),
    "topico": frozenset({"pomada", "pomadas", "creme", "cremes", "unguento", "unguentos"}),
    "injetavel": frozenset(
        {
            "injetavel",
            "injetaveis",
            "ampola",
            "ampolas",
            "endovenoso",
            "endovenosa",
            "intravenoso",
            "intravenosa",
        }
    ),
}


def _detect_pharm_forms(norm: str) -> frozenset:
    if not norm:
        return frozenset()
    found: set[str] = set()
    for form_id, tokens in _PHARM_FORM_GROUPS.items():
        if any(re.search(rf"\b{re.escape(tok)}\b", norm) for tok in tokens):
            found.add(form_id)
    return frozenset(found)


def product_form_strict_reject(termo_raw: str, item: Dict[str, Any]) -> bool:
    """True se pedido e item citam formas farmacêuticas incompatíveis (ex.: colírio vs comprimido)."""
    term_n = _norm_text(termo_raw)
    item_n = _norm_text(_item_blob(item))
    term_forms = _detect_pharm_forms(term_n)
    item_forms = _detect_pharm_forms(item_n)
    if not term_forms or not item_forms:
        return False
    return term_forms.isdisjoint(item_forms)


def _percent_vs_oral_solid_mismatch(
    term: ProductSpecHints,
    got: ProductSpecHints,
    *,
    item_norm: str,
    term_norm: str,
) -> bool:
    """
    Pedido com concentração % (ex.: colírio 0,3%) vs item oral sólido com dose em mg
    e sem % compatível (ex.: comprimido 500 mg).
    """
    if term.percent is None:
        return False
    if got.percent is not None:
        return False
    if got.dose_mg is None:
        return False
    item_forms = _detect_pharm_forms(item_norm)
    if "oral_solido" in item_forms:
        return True
    term_forms = _detect_pharm_forms(term_norm)
    # Pedido ocular/tópico em % + item com dose alta em mg sem forma explícita.
    if term_forms & {"ocular", "topico"} and got.dose_mg >= 50.0:
        return True
    return False


def product_spec_strict_reject(termo_raw: str, item: Dict[str, Any]) -> bool:
    """True quando o item contradiz specs explícitas do pedido (filtro em modo strict)."""
    if product_line_strict_reject(termo_raw, item):
        return True
    if product_combo_strict_reject(termo_raw, item):
        return True
    if product_form_strict_reject(termo_raw, item):
        return True
    term = extract_product_spec_from_term(termo_raw)
    got = extract_product_spec_from_item(item)
    term_norm = _norm_text(termo_raw)
    item_norm = _norm_text(_item_blob(item))
    if _percent_vs_oral_solid_mismatch(term, got, item_norm=item_norm, term_norm=term_norm):
        return True
    if _dose_per_presentation_mismatch(term, got):
        return True
    if term.calibre is not None and got.calibre is not None:
        if not _calibre_close(term.calibre, got.calibre):
            return True
    if term.units_per_g is not None and got.units_per_g is not None:
        if not _float_close(term.units_per_g, got.units_per_g, abs_tol=0.05):
            return True
    if product_spec_strong_core_match(termo_raw, item):
        return False
    return product_spec_rerank_adjustment(termo_raw, item) <= -38.0
