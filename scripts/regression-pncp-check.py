#!/usr/bin/env python3
"""Checagem de regressão: busca manual vs lote + casos da planilha medicamentos."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PNCP_ROOT = ROOT / "pncp_researcher_service"
if str(PNCP_ROOT) not in sys.path:
    sys.path.insert(0, str(PNCP_ROOT))

CASES = [
    ("ADENOSINA 6 MG SOLUÇAO INJETAVEL", 13.5),
    ("ÁGUA OXIGENADA 10 VOLUMES", 7.93),
    ("ÁLCOOL 70% FRASCO COM 1 LITRO", 5.26),
    ("BANDAGEM ELASTICA (FAIXA DE SMARCH) 15CM X 2M", 20.61),
    ("DRENO DE PEN ROSE ESTÉRIL N. 2", 2.38),
    ("FIO NYLON N° 4.0 COR PRETA COM AGULHA 2,5 CM", 2.02),
    ("GLICOSE 50 % - 10 ML SOLUÇÃO INJETAVEL", 1.0),
    ("LUVA CIRÚRGICA ESTÉRIL Nº 6,5", 1.32),
    ("COLAGENASE 0,6 U/G POMADA DERMATOLÓGICA 30G", 15.0),
    ("FORMOL 4% 1 LITRO", 29.97),
    ("CARVAO ATIVADO EM PO POTE C/250 G", 36.44),
]


async def main() -> int:
    db = os.environ.get("PNCP_LOCAL_DB_PATH") or "/home/adryan/pncp_researcher_local.db"
    if not Path(db).is_file():
        print(f"DB não encontrado: {db}")
        return 1
    os.environ["PNCP_LOCAL_DB_PATH"] = str(Path(db).resolve())

    from app import config
    from app.schemas import MarketSearchRequest
    from app.service import market_search_intelligent

    config.PNCP_LOCAL_DB_PATH = os.environ["PNCP_LOCAL_DB_PATH"]
    config.PNCP_IA_RERANK_ENABLED = False
    config.PNCP_IA_ITEM_RESUMO_ENABLED = False
    config.PNCP_HYBRID_BULK_ENABLED = True
    os.environ.setdefault("PNCP_FTS5_ENABLED", "1")

    print(f"DB: {db}\n")
    print(f"{'STATUS':8} {'MAN':>3} {'LOT':>3}  ITEM")
    print("-" * 72)

    ok = warn = fail = 0
    for termo, base in CASES:
        manual = await market_search_intelligent(
            MarketSearchRequest(termo_busca=termo, busca_lote=False, max_paginas=3, somente_homologados=False)
        )
        bulk = await market_search_intelligent(
            MarketSearchRequest(
                termo_busca=termo,
                busca_lote=True,
                max_paginas=3,
                somente_homologados=False,
                valor_base_referencia=base,
                variacao_percentual_referencia=20,
            )
        )
        nm = len(manual.get("itens") or [])
        nb = len(bulk.get("itens") or [])
        bstats = bulk.get("stats") or {}
        timeout = bool(bstats.get("busca_lote_timeout"))
        hybrid = bool(bstats.get("hybrid_fallback_used"))

        if timeout:
            status = "TIMEOUT"
            fail += 1
        elif nm >= 1 and nb == 0:
            status = "REGRESS"
            fail += 1
        elif nm == 0 and nb == 0:
            status = "VAZIO"
            warn += 1
        elif nb < nm and nb < 3:
            status = "MENOS"
            warn += 1
        else:
            status = "OK"
            ok += 1

        flags = []
        if timeout:
            flags.append("timeout")
        if hybrid:
            flags.append("hybrid")
        extra = f" [{','.join(flags)}]" if flags else ""
        print(f"{status:8} {nm:3} {nb:3}  {termo[:48]}{extra}")

    print("-" * 72)
    print(f"OK={ok}  AVISO={warn}  FALHA={fail}  (total={len(CASES)})")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
