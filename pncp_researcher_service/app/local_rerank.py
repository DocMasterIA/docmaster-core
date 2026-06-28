"""
Rerank top-3 local (sem LLM): milissegundos por busca, usa scoring composto sobre o índice PNCP.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def rerank_worth_it_ambiguous(pool_mode: str, selection_pool: List[Dict[str, Any]]) -> bool:
    """Chama rerank (local ou LLM) só quando o top heurístico está incerto."""
    from . import config as cfg
    from .service import _filter_ia_rerank_candidates

    if not cfg.PNCP_LOCAL_RERANK_ONLY_AMBIGUOUS:
        return True
    if pool_mode in {"mixed_fallback", "similar_only"}:
        return True
    if pool_mode != "literal_only":
        return True
    rows = _filter_ia_rerank_candidates(selection_pool)[:8]
    if len(rows) < 2:
        return False
    top_scores = [float(x.get("score_aprovacao") or 0) for x in rows[:6]]
    top_literals = [float(x.get("literal_match") or 0) for x in rows[:6]]
    if len(top_scores) >= 3 and (max(top_scores[:3]) - min(top_scores[:3])) <= 12:
        return True
    if len(top_literals) >= 3 and (max(top_literals[:3]) - min(top_literals[:3])) <= 15:
        return True
    return False


def _generic_penalty(desc_norm: str, term_tokens: List[str]) -> float:
    pen = 0.0
    if not desc_norm:
        return -20.0
    if any(k in desc_norm for k in ("diversos", "variados", "sortido", "miscelanea", "miscelane")):
        pen -= 14.0
    if " kit " in f" {desc_norm} " or desc_norm.startswith("kit "):
        pen -= 6.0
    words = desc_norm.split()
    if len(words) > 55:
        pen -= 10.0
    elif len(words) > 40:
        pen -= 5.0
    if term_tokens and words:
        lead = words[:14]
        core = term_tokens[0]
        if len(core) >= 3 and not any(
            w == core or w.startswith(core[:4]) or core.startswith(w[:4]) for w in lead
        ):
            pen -= 12.0
    return pen


def compute_local_rerank_score(
    termo_busca: str,
    item: Dict[str, Any],
    query_groups: List[List[str]],
    *,
    termo_raw: Optional[str] = None,
) -> float:
    from .pack_size_match import pack_size_rerank_adjustment
    from .product_spec_match import product_spec_rerank_adjustment
    from .service import (
        _aggressive_similarity_score,
        _context_penalty,
        _literal_match_score,
        _normalize_text,
        _row_price_for_faixa,
        _safe_float,
    )

    lit = float(item.get("literal_match") or 0.0)
    if lit <= 0:
        lit = _literal_match_score(termo_busca, item)
    sim = _aggressive_similarity_score(termo_busca, item) * 38.0
    ctx = _context_penalty(item, query_groups)
    base = _safe_float(item.get("score_aprovacao")) * 0.22
    desc = _normalize_text(str(item.get("descricao_item") or item.get("descricao") or ""))
    term_tokens = [t for t in _normalize_text(termo_busca).split() if len(t) >= 2]
    gen = _generic_penalty(desc, term_tokens)
    pack_adj = pack_size_rerank_adjustment(termo_raw or termo_busca, item)
    spec_adj = product_spec_rerank_adjustment(termo_raw or termo_busca, item)
    pen = -18.0 if bool(item.get("match_agressivo")) else 0.0
    bon = 0.0
    if str(item.get("cnpj_fornecedor") or "").strip():
        bon += 9.0
    if _row_price_for_faixa(item) > 0:
        bon += 5.0
    if item.get("item_homologado") is True or item.get("temResultado") is True:
        bon += 4.0
    return lit * 1.2 + sim + ctx + base + gen + pack_adj + spec_adj + pen + bon


def apply_local_rerank_top3(
    termo_busca: str,
    selection_pool: List[Dict[str, Any]],
    *,
    query_groups: List[List[str]],
    min_ok: int,
    max_candidates: int,
    faixa_min: Optional[float] = None,
    faixa_max: Optional[float] = None,
    faixa_sentido: Optional[str] = None,
    termo_raw: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Reordena candidatos e devolve top 3. Retorna (itens, usado).
    """
    from .service import (
        _classify_confiabilidade,
        _classify_risco,
        _filter_ia_rerank_candidates,
        _is_federal_item,
        _preco_dentro_faixa,
        _safe_float,
    )

    pool = _filter_ia_rerank_candidates(selection_pool)
    if not pool:
        return [], False
    if faixa_min is not None and faixa_max is not None:
        in_band = [
            x for x in pool
            if _preco_dentro_faixa(x, faixa_min, faixa_max, sentido=faixa_sentido)
        ]
        if len(in_band) >= 3:
            pool = in_band
    cap = max(6, min(int(max_candidates), len(pool)))
    raw_term = (termo_raw or termo_busca or "").strip()
    ranked: List[Tuple[float, Dict[str, Any]]] = []
    for raw in pool[:cap]:
        row = dict(raw)
        lr = compute_local_rerank_score(
            termo_busca, row, query_groups, termo_raw=raw_term or None
        )
        row["_local_rerank_score"] = round(lr, 3)
        ranked.append((lr, row))
    if not ranked:
        return [], False
    ranked.sort(key=lambda x: x[0], reverse=True)
    scored_rows: List[Dict[str, Any]] = []
    top_lr = ranked[0][0]
    for lr, row in ranked:
        out = dict(row)
        rel = lr / max(top_lr, 1.0)
        final = int(max(40, min(95, 42 + rel * 48)))
        out["score_aprovacao"] = final
        out["local_rerank_score"] = round(lr, 3)
        out["confiabilidade"] = _classify_confiabilidade(final)
        out["risco"] = _classify_risco(final)
        out["status"] = "Aprovado" if final >= min_ok else "Revisar"
        out["local_rerank_usado"] = True
        scored_rows.append(out)

    # Mantém ordem do rerank; regra federal só quando há 3+ federais fortes (>=80).
    federais_fortes = [
        x
        for x in scored_rows
        if _is_federal_item(x) and _safe_float(x.get("score_aprovacao")) >= 80.0
    ]
    if len(federais_fortes) >= 3:
        federais = [x for x in scored_rows if _is_federal_item(x)]
        demais = [x for x in scored_rows if not _is_federal_item(x)]
        top3 = (federais + demais)[:3]
    else:
        top3 = scored_rows[:3]
    return top3, len(top3) > 0
