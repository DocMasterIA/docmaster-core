#!/usr/bin/env python3
"""
Benchmark busca inteligente: heurístico vs rerank local (sem Qwen) no índice PNCP real.

Uso:
  PNCP_LOCAL_DB_PATH=/path/pncp_researcher_local.db python3 scripts/benchmark-pncp-local-rerank.py
  python3 scripts/benchmark-pncp-local-rerank.py --samples 15 --bulk
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PNCP_ROOT = ROOT / "pncp_researcher_service"
if str(PNCP_ROOT) not in sys.path:
    sys.path.insert(0, str(PNCP_ROOT))

DEFAULT_DB = ROOT / "pncp_researcher_local.db"


def pick_sample_terms(db_path: str, n: int) -> list[str]:
    con = sqlite3.connect(db_path)
    try:
        cur = con.execute(
            """
            SELECT descricao FROM pncp_itens
            WHERE length(trim(descricao)) BETWEEN 20 AND 120
            ORDER BY RANDOM()
            LIMIT ?
            """,
            (n,),
        )
        return [str(r[0]).strip() for r in cur.fetchall() if r and r[0]]
    finally:
        con.close()


async def run_one(termo: str, *, busca_lote: bool, local_on: bool) -> dict:
    from app import config
    from app.schemas import MarketSearchRequest
    from app.service import market_search_intelligent

    config.PNCP_LOCAL_DB_PATH = os.environ["PNCP_LOCAL_DB_PATH"]
    config.PNCP_LOCAL_RERANK_ENABLED = local_on
    config.PNCP_IA_RERANK_ENABLED = False
    config.PNCP_IA_RERANK_BULK_ENABLED = False
    config.PNCP_IA_ITEM_RESUMO_ENABLED = False
    config.PNCP_HYBRID_FALLBACK_ENABLED = False

    payload = MarketSearchRequest(
        termo_busca=termo,
        busca_lote=busca_lote,
        max_paginas=3,
        tamanho_pagina=80,
        somente_homologados=False,
    )
    t0 = time.perf_counter()
    out = await market_search_intelligent(payload)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    stats = out.get("stats") or {}
    itens = out.get("itens") or []
    return {
        "termo": termo[:70],
        "ms": round(elapsed_ms, 1),
        "n": len(itens),
        "local_rerank_usado": stats.get("local_rerank_usado"),
        "ia_rerank_usado": stats.get("ia_rerank_usado"),
        "top1": (itens[0].get("descricao_item") or "")[:80] if itens else "",
        "scores": [it.get("score_aprovacao") for it in itens[:3]],
    }


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--samples", type=int, default=12)
    parser.add_argument("--bulk", action="store_true", help="busca_lote=true")
    args = parser.parse_args()

    db = Path(args.db)
    if not db.is_file():
        print(f"DB não encontrado: {db}", file=sys.stderr)
        return 1

    os.environ["PNCP_LOCAL_DB_PATH"] = str(db.resolve())
    os.environ.setdefault("PNCP_FTS5_ENABLED", "1")

    terms = pick_sample_terms(str(db), args.samples)
    if not terms:
        print("Nenhum termo amostra no DB.", file=sys.stderr)
        return 1

    print(f"DB: {db} ({db.stat().st_size / 1e9:.2f} GB) — {len(terms)} termos — bulk={args.bulk}\n")

    rows_heur: list[dict] = []
    rows_local: list[dict] = []

    for termo in terms:
        h = await run_one(termo, busca_lote=args.bulk, local_on=False)
        l = await run_one(termo, busca_lote=args.bulk, local_on=True)
        rows_heur.append(h)
        rows_local.append(l)
        changed = h.get("top1") != l.get("top1") or h.get("scores") != l.get("scores")
        flag = " *" if changed else ""
        print(
            f"{termo[:55]:55} | sem local {h['ms']:7.0f}ms n={h['n']} "
            f"| com local {l['ms']:7.0f}ms lr={l['local_rerank_usado']}{flag}"
        )

    avg_h = sum(r["ms"] for r in rows_heur) / len(rows_heur)
    avg_l = sum(r["ms"] for r in rows_local) / len(rows_local)
    changed_n = sum(
        1
        for h, l in zip(rows_heur, rows_local)
        if h.get("top1") != l.get("top1") or h.get("scores") != l.get("scores")
    )
    print(f"\nMédia sem local rerank: {avg_h:.0f} ms")
    print(f"Média com local rerank: {avg_l:.0f} ms (+{avg_l - avg_h:.0f} ms)")
    print(f"Top3 alterado em {changed_n}/{len(terms)} buscas")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
