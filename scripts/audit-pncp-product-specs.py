#!/usr/bin/env python3
"""Auditoria de busca inteligente PNCP — pool vs top3 vs specs."""
from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PNCP_ROOT = ROOT / "pncp_researcher_service"
if str(PNCP_ROOT) not in sys.path:
    sys.path.insert(0, str(PNCP_ROOT))

CASES = [
    "AGUA OXIGENADA 10 VOLUMES",
    "ACETATO DE MEDROXIPROGESTERONA SUSPENSAO INJETAVEL 50MG/ML",
    "ADENOSINA 6 MG SOLUCAO INJETAVEL",
    "ALCOOL 70% FRASCO COM 1 LITRO",
]


def sql_like_count(db: str, term: str) -> int:
    con = sqlite3.connect(db)
    try:
        q = f"%{term.split()[0]}%"
        return int(
            con.execute(
                "SELECT COUNT(*) FROM pncp_itens WHERE descricao LIKE ? COLLATE NOCASE",
                (q,),
            ).fetchone()[0]
        )
    finally:
        con.close()


async def audit_term(termo: str) -> dict:
    from app import config
    from app.local_index import local_item_search
    from app.product_spec_match import (
        extract_product_spec_from_item,
        extract_product_spec_from_term,
        product_spec_rerank_adjustment,
    )
    from app.schemas import MarketSearchRequest
    from app.service import market_search_intelligent

    db = os.environ["PNCP_LOCAL_DB_PATH"]
    config.PNCP_LOCAL_DB_PATH = db
    config.PNCP_LOCAL_RERANK_ENABLED = True
    config.PNCP_IA_RERANK_ENABLED = False
    config.PNCP_IA_RERANK_BULK_ENABLED = False
    config.PNCP_IA_ITEM_RESUMO_ENABLED = False
    config.PNCP_HYBRID_FALLBACK_ENABLED = False
    os.environ.setdefault("PNCP_FTS5_ENABLED", "1")

    term_spec = extract_product_spec_from_term(termo)

    raw = local_item_search(
        termo,
        somente_homologados=False,
        limit=500,
        cleanup_for_display=False,
    )
    pool = raw.get("itens") or []
    stats = raw.get("stats") or {}

    payload = MarketSearchRequest(
        termo_busca=termo,
        busca_lote=True,
        max_paginas=3,
        tamanho_pagina=80,
        somente_homologados=False,
    )
    out = await market_search_intelligent(payload)
    top3 = out.get("itens") or []
    funil = (out.get("stats") or {}).get("funil_busca") or {}

    def row_summary(it: dict, rank: int | None = None) -> dict:
        desc = (it.get("descricao_item") or it.get("descricao") or "")[:120]
        spec = extract_product_spec_from_item(it)
        adj = product_spec_rerank_adjustment(termo, it)
        return {
            "rank": rank,
            "descricao": desc,
            "valor_unitario": it.get("valor_unitario"),
            "uf": it.get("uf"),
            "spec_item": {
                k: v
                for k, v in {
                    "dose_mg": spec.dose_mg,
                    "conc_mg_per_ml": spec.conc_mg_per_ml,
                    "vol_l": spec.vol_l,
                    "vol_ml": spec.vol_ml,
                    "percent": spec.percent,
                    "volumes": spec.volumes,
                }.items()
                if v is not None
            },
            "spec_adj": round(adj, 1),
            "score": it.get("score_aprovacao"),
            "literal_match": it.get("literal_match"),
        }

    # Melhores candidatos no pool por spec_adj
    ranked_pool = sorted(pool, key=lambda x: product_spec_rerank_adjustment(termo, x), reverse=True)

    return {
        "termo": termo,
        "term_spec": {
            k: v
            for k, v in {
                "dose_mg": term_spec.dose_mg,
                "conc_mg_per_ml": term_spec.conc_mg_per_ml,
                "vol_l": term_spec.vol_l,
                "vol_ml": term_spec.vol_ml,
                "percent": term_spec.percent,
                "volumes": term_spec.volumes,
            }.items()
            if v is not None
        },
        "sql_like_primeira_palavra": sql_like_count(db, termo),
        "indice_stats": {
            "total_registros": stats.get("total_registros"),
            "sql_rows_fetched": stats.get("sql_rows_fetched"),
            "filtrados_token_match": stats.get("filtrados_token_match"),
            "filtrados_nao_homologados": stats.get("filtrados_nao_homologados"),
        },
        "funil": {
            "literal_pool": funil.get("literal_pool"),
            "similar_pool": funil.get("similar_pool"),
            "scored_final_pool": funil.get("scored_final_pool"),
            "top3_final": funil.get("top3_final"),
            "local_rerank_usado": (out.get("stats") or {}).get("local_rerank_usado"),
        },
        "top3": [row_summary(it, i + 1) for i, it in enumerate(top3)],
        "melhores_5_no_pool_por_spec": [row_summary(it) for it in ranked_pool[:5]],
    }


async def main() -> int:
    db = os.environ.get("PNCP_LOCAL_DB_PATH") or str(ROOT / "pncp_researcher_local.db")
    if not Path(db).is_file():
        print(f"DB não encontrado: {db}", file=sys.stderr)
        return 1
    os.environ["PNCP_LOCAL_DB_PATH"] = str(Path(db).resolve())
    print(f"DB: {db} ({Path(db).stat().st_size / 1e9:.2f} GB)\n")

    for termo in CASES:
        print("=" * 72)
        print(termo)
        print("=" * 72)
        try:
            r = await audit_term(termo)
        except Exception as e:
            print(f"ERRO: {e}\n")
            continue
        print(json.dumps(r, ensure_ascii=False, indent=2))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
