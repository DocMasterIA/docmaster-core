from __future__ import annotations

import re
import unicodedata
from typing import Iterable, List

from .contracts import MarketPriceHit


def _norm_text(v: str) -> str:
    s = unicodedata.normalize("NFKD", str(v or ""))
    s = s.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", s).strip()


def _dedupe_key(hit: MarketPriceHit, *, price_epsilon: float = 0.01) -> str:
    cnpj = re.sub(r"\D", "", str(hit.fornecedor_cnpj or ""))
    orgao = _norm_text(hit.orgao or "")
    desc = _norm_text(hit.descricao_item or "")[:120]
    price = hit.valor_unitario_homologado if hit.valor_unitario_homologado is not None else hit.valor_unitario
    bucket = int(round(float(price or 0) / price_epsilon))
    plat = str(hit.plataforma or "").strip().lower()
    ext_id = str(hit.plataforma_item_id or "").strip().lower()
    if ext_id:
        return f"{plat}|id|{ext_id}"
    return f"{plat}|{orgao}|{cnpj}|{bucket}|{desc}"


def dedupe_hits(hits: Iterable[MarketPriceHit]) -> List[MarketPriceHit]:
    """
    Remove duplicatas cross-platform.
    Mantém o hit com maior valor_unitario_homologado ou valor_unitario.
    """
    best: dict[str, MarketPriceHit] = {}
    for hit in hits:
        key = _dedupe_key(hit)
        prev = best.get(key)
        if prev is None:
            best[key] = hit
            continue
        prev_score = float(prev.valor_unitario_homologado or prev.valor_unitario or 0)
        cur_score = float(hit.valor_unitario_homologado or hit.valor_unitario or 0)
        if cur_score > prev_score:
            best[key] = hit
    return list(best.values())
