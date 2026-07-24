from __future__ import annotations

import re
import unicodedata
from typing import Iterable, List, Tuple

from .contracts import MarketPriceHit


def _norm_text(v: str) -> str:
    s = unicodedata.normalize("NFKD", str(v or ""))
    s = s.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", s).strip()


def _dedupe_key(hit: MarketPriceHit, *, price_epsilon: float = 0.01) -> str:
    """
    Chave sempre escopada por plataforma.

    Crosslink pode anotar o mesmo canonical_key em PNCP + TCE, mas a união justa
    exige que as fontes continuem competindo no scoring/top-3 — não que uma apague
    a outra no dedup.
    """
    plat = str(hit.plataforma or "").strip().lower() or "unknown"
    ext_id = str(hit.plataforma_item_id or "").strip().lower()
    if ext_id:
        return f"{plat}|id|{ext_id}"
    cnpj = re.sub(r"\D", "", str(hit.fornecedor_cnpj or ""))
    orgao = _norm_text(hit.orgao or "")
    desc = _norm_text(hit.descricao_item or "")[:120]
    price = hit.valor_unitario_homologado if hit.valor_unitario_homologado is not None else hit.valor_unitario
    bucket = int(round(float(price or 0) / price_epsilon))
    return f"{plat}|{orgao}|{cnpj}|{bucket}|{desc}"


def _hit_keep_score(hit: MarketPriceHit) -> Tuple[int, int, int, int, float]:
    """
    Qualidade de identidade para escolher entre duplicatas da MESMA plataforma.
    Não usa preço alto como vitória (evita inflar a referência).
    """
    cnpj = 1 if len(re.sub(r"\D", "", str(hit.fornecedor_cnpj or ""))) >= 14 else 0
    nome = 1 if str(hit.fornecedor_nome or "").strip() else 0
    has_hom = (
        1
        if hit.valor_unitario_homologado is not None and float(hit.valor_unitario_homologado or 0) > 0
        else 0
    )
    desc_len = min(500, len(_norm_text(hit.descricao_item or "")))
    price = float(
        hit.valor_unitario_homologado
        if hit.valor_unitario_homologado is not None
        else (hit.valor_unitario or 0)
    )
    # Preço menor vence em empate de qualidade (referência mais competitiva).
    price_rank = -price if price > 0 else -1e18
    return (cnpj, nome, has_hom, desc_len, price_rank)


def dedupe_hits(hits: Iterable[MarketPriceHit]) -> List[MarketPriceHit]:
    """
    Remove duplicatas *dentro* de cada plataforma.
    Mantém a linha com melhor identidade (CNPJ/nome/homologado), não o maior preço.
    Fontes distintas com o mesmo canonical_key permanecem (união justa).
    """
    best: dict[str, MarketPriceHit] = {}
    for hit in hits:
        key = _dedupe_key(hit)
        prev = best.get(key)
        if prev is None:
            best[key] = hit
            continue
        if _hit_keep_score(hit) > _hit_keep_score(prev):
            best[key] = hit
    return list(best.values())
