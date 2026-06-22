#!/usr/bin/env python3
"""Auditoria em lote: planilha XLSX/CSV → busca inteligente PNCP → relatório CSV."""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
PNCP_ROOT = ROOT / "pncp_researcher_service"
if str(PNCP_ROOT) not in sys.path:
    sys.path.insert(0, str(PNCP_ROOT))

COLUMN_ALIASES: Dict[str, str] = {
    "numero_do_item": "numero_item",
    "numero_item": "numero_item",
    "n": "numero_item",
    "id": "numero_item",
    "item": "numero_item",
    "nome_do_item": "descricao_item",
    "descricao_item": "descricao_item",
    "descricao": "descricao_item",
    "descricao_do_item": "descricao_item",
    "qtd": "quantidade",
    "qtd.": "quantidade",
    "quantidade": "quantidade",
    "und": "unidade_medida",
    "und.": "unidade_medida",
    "unidade": "unidade_medida",
    "unidade_medida": "unidade_medida",
    "faixa_regional_base": "valor_base",
    "faixa_base": "valor_base",
    "valor_base": "valor_base",
    "faixa_variacao": "variacao_percentual",
    "faixa_variacao_percentual": "variacao_percentual",
    "variacao_percentual": "variacao_percentual",
}


def _norm_header(value: Any) -> str:
    s = unicodedata.normalize("NFKD", str(value or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().strip()
    s = re.sub(r"[^\w]+", "_", s)
    return s.strip("_")


def _to_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def load_rows(path: Path) -> List[Dict[str, Any]]:
    if path.suffix.lower() == ".csv":
        import csv as csv_mod

        with path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv_mod.DictReader(f)
            raw_rows = list(reader)
        if not raw_rows:
            return []
        headers = {_norm_header(h): h for h in raw_rows[0].keys()}
    else:
        from openpyxl import load_workbook

        wb = load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        values = list(ws.iter_rows(values_only=True))
        wb.close()
        if not values:
            return []
        headers = {_norm_header(h): i for i, h in enumerate(values[0])}
        raw_rows = []
        for row in values[1:]:
            raw_rows.append({k: row[i] if i < len(row) else None for k, i in headers.items()})

    mapped: List[Dict[str, Any]] = []
    for raw in raw_rows:
        item: Dict[str, Any] = {}
        for key, val in raw.items():
            canon = COLUMN_ALIASES.get(_norm_header(key))
            if canon:
                item[canon] = val
        desc = str(item.get("descricao_item") or "").strip()
        if not desc:
            continue
        item["descricao_item"] = desc
        item["numero_item"] = item.get("numero_item")
        item["quantidade"] = _to_float(item.get("quantidade"))
        item["unidade_medida"] = str(item.get("unidade_medida") or "").strip() or None
        item["valor_base"] = _to_float(item.get("valor_base"))
        item["variacao_percentual"] = _to_float(item.get("variacao_percentual"))
        mapped.append(item)
    return mapped


def _price_ok(val: Any) -> bool:
    try:
        return val is not None and float(val) > 0
    except (TypeError, ValueError):
        return False


def _flags_for_result(termo: str, it: Dict[str, Any]) -> List[str]:
    from app.product_category_match import product_category_strict_reject
    from app.product_spec_match import product_line_strict_reject, product_spec_rerank_adjustment

    flags: List[str] = []
    if product_category_strict_reject(termo, it):
        flags.append("categoria_errada")
    if product_line_strict_reject(termo, it):
        flags.append("linha_errada")
    adj = product_spec_rerank_adjustment(termo, it)
    if adj < -15:
        flags.append("spec_ruim")
    elif adj < 0:
        flags.append("spec_fraca")
    if not _price_ok(it.get("valor_unitario")):
        flags.append("preco_zero")
    return flags


async def audit_row(row: Dict[str, Any], *, variacao_default: Optional[float]) -> Dict[str, Any]:
    from app import config
    from app.product_spec_match import extract_product_spec_from_item, extract_product_spec_from_term
    from app.schemas import MarketSearchRequest
    from app.service import market_search_intelligent

    termo = row["descricao_item"]
    valor_base = row.get("valor_base")
    variacao = row.get("variacao_percentual")
    if variacao is None:
        variacao = variacao_default

    payload = MarketSearchRequest(
        termo_busca=termo,
        busca_lote=True,
        max_paginas=3,
        tamanho_pagina=80,
        somente_homologados=False,
        quantidade_referencia=row.get("quantidade"),
        unidade_medida_referencia=row.get("unidade_medida"),
        valor_base_referencia=valor_base,
        variacao_percentual_referencia=variacao,
    )
    out = await market_search_intelligent(payload)
    top3 = out.get("itens") or []
    funil = (out.get("stats") or {}).get("funil_busca") or {}
    term_spec = extract_product_spec_from_term(termo)

    def fmt_top(it: Optional[Dict[str, Any]], rank: int) -> Dict[str, Any]:
        if not it:
            return {"rank": rank, "descricao": "", "valor_unitario": None, "uf": "", "flags": ["vazio"]}
        spec = extract_product_spec_from_item(it)
        return {
            "rank": rank,
            "descricao": (it.get("descricao_item") or it.get("descricao") or "")[:140],
            "valor_unitario": it.get("valor_unitario"),
            "uf": it.get("uf"),
            "score": it.get("score_aprovacao"),
            "spec_adj": it.get("spec_adj") or None,
            "flags": _flags_for_result(termo, it),
            "spec_item": {
                k: v
                for k, v in {
                    "dose_mg": spec.dose_mg,
                    "conc_mg_per_ml": spec.conc_mg_per_ml,
                    "vol_l": spec.vol_l,
                    "vol_ml": spec.vol_ml,
                    "percent": spec.percent,
                    "volumes": spec.volumes,
                    "width_cm": getattr(spec, "width_cm", None),
                    "length_m": getattr(spec, "length_m", None),
                }.items()
                if v is not None
            },
        }

    tops = [fmt_top(top3[i] if i < len(top3) else None, i + 1) for i in range(3)]
    top1_flags = tops[0]["flags"] if tops else ["vazio"]
    status = "ok"
    if not top3:
        status = "sem_resultado"
    elif any(f in top1_flags for f in ("categoria_errada", "linha_errada", "spec_ruim")):
        status = "suspeito"
    elif "preco_zero" in top1_flags or "spec_fraca" in top1_flags:
        status = "atencao"

    return {
        "numero_item": row.get("numero_item"),
        "termo": termo,
        "quantidade": row.get("quantidade"),
        "unidade": row.get("unidade_medida"),
        "valor_base": valor_base,
        "variacao_pct": variacao,
        "status": status,
        "n_resultados": len(top3),
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
        "funil": {
            "literal_pool": funil.get("literal_pool"),
            "similar_pool": funil.get("similar_pool"),
            "scored_final_pool": funil.get("scored_final_pool"),
            "top3_final": funil.get("top3_final"),
        },
        "top3": tops,
        "top1_flags": ",".join(top1_flags),
    }


def write_csv(results: List[Dict[str, Any]], path: Path) -> None:
    fields = [
        "numero_item",
        "status",
        "n_resultados",
        "termo",
        "valor_base",
        "variacao_pct",
        "top1_descricao",
        "top1_preco",
        "top1_uf",
        "top1_flags",
        "top2_descricao",
        "top2_preco",
        "top3_descricao",
        "top3_preco",
        "literal_pool",
        "similar_pool",
        "scored_final_pool",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in results:
            t1, t2, t3 = (r["top3"] + [{}, {}, {}])[:3]
            w.writerow(
                {
                    "numero_item": r.get("numero_item"),
                    "status": r.get("status"),
                    "n_resultados": r.get("n_resultados"),
                    "termo": r.get("termo"),
                    "valor_base": r.get("valor_base"),
                    "variacao_pct": r.get("variacao_pct"),
                    "top1_descricao": t1.get("descricao"),
                    "top1_preco": t1.get("valor_unitario"),
                    "top1_uf": t1.get("uf"),
                    "top1_flags": r.get("top1_flags"),
                    "top2_descricao": t2.get("descricao"),
                    "top2_preco": t2.get("valor_unitario"),
                    "top3_descricao": t3.get("descricao"),
                    "top3_preco": t3.get("valor_unitario"),
                    "literal_pool": (r.get("funil") or {}).get("literal_pool"),
                    "similar_pool": (r.get("funil") or {}).get("similar_pool"),
                    "scored_final_pool": (r.get("funil") or {}).get("scored_final_pool"),
                }
            )


async def main_async(args: argparse.Namespace) -> int:
    xlsx = Path(args.input).resolve()
    if not xlsx.is_file():
        print(f"Arquivo não encontrado: {xlsx}", file=sys.stderr)
        return 1

    db = Path(args.db or os.environ.get("PNCP_LOCAL_DB_PATH") or "/home/adryan/pncp_researcher_local.db")
    if not db.is_file():
        print(f"DB não encontrado: {db}", file=sys.stderr)
        return 1
    os.environ["PNCP_LOCAL_DB_PATH"] = str(db.resolve())

    from app import config

    config.PNCP_LOCAL_DB_PATH = str(db.resolve())
    config.PNCP_LOCAL_RERANK_ENABLED = True
    config.PNCP_IA_RERANK_ENABLED = False
    config.PNCP_IA_RERANK_BULK_ENABLED = False
    config.PNCP_IA_ITEM_RESUMO_ENABLED = False
    config.PNCP_HYBRID_FALLBACK_ENABLED = False
    os.environ.setdefault("PNCP_FTS5_ENABLED", "1")

    rows = load_rows(xlsx)
    if not rows:
        print("Nenhuma linha com descrição encontrada.", file=sys.stderr)
        return 1

    out_dir = Path(args.output_dir or ROOT / "scripts" / "output")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    base = out_dir / f"audit_pncp_{stamp}"
    json_path = base.with_suffix(".json")
    csv_path = base.with_suffix(".csv")

    print(f"DB: {db} ({db.stat().st_size / 1e9:.2f} GB)")
    print(f"Planilha: {xlsx.name} ({len(rows)} itens)")
    print(f"Saída: {csv_path}\n")

    results: List[Dict[str, Any]] = []
    for i, row in enumerate(rows, 1):
        num = row.get("numero_item") or i
        print(f"[{i}/{len(rows)}] #{num} {row['descricao_item'][:60]}...", flush=True)
        try:
            r = await audit_row(row, variacao_default=args.variacao_default)
        except Exception as e:
            r = {
                "numero_item": num,
                "termo": row["descricao_item"],
                "status": "erro",
                "n_resultados": 0,
                "top3": [],
                "top1_flags": f"erro:{e}",
                "funil": {},
            }
            print(f"  ERRO: {e}", flush=True)
        results.append(r)
        if r.get("top3"):
            t1 = r["top3"][0]
            print(
                f"  → {r['status']} | {r['n_resultados']} res | top1: {t1.get('descricao','')[:70]} | "
                f"R$ {t1.get('valor_unitario')} | {r.get('top1_flags')}",
                flush=True,
            )
        else:
            print(f"  → {r['status']} | sem resultados", flush=True)

    write_csv(results, csv_path)
    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    counts: Dict[str, int] = {}
    for r in results:
        counts[r.get("status", "?")] = counts.get(r.get("status", "?"), 0) + 1

    print("\n" + "=" * 60)
    print("RESUMO")
    for k in ("ok", "atencao", "suspeito", "sem_resultado", "erro"):
        if counts.get(k):
            print(f"  {k}: {counts[k]}")
    print(f"\nRelatórios:\n  {csv_path}\n  {json_path}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Auditoria PNCP a partir de planilha XLSX/CSV")
    p.add_argument("input", help="Caminho do .xlsx ou .csv")
    p.add_argument("--db", help="Caminho do pncp_researcher_local.db")
    p.add_argument("--output-dir", help="Pasta de saída (default: scripts/output)")
    p.add_argument(
        "--variacao-default",
        type=float,
        default=None,
        help="Variação %% quando a planilha não tiver coluna (omitido = sem filtro de faixa)",
    )
    args = p.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
