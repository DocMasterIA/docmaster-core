#!/usr/bin/env python3
"""Auditoria Compras.gov: UNION de IDs nos CSVs mensais vs SQLite.

Uso (dentro do container feed):
  python /tmp/audit_compras_gov_coverage.py
"""
from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path("/data/compras_gov/raw")
DB_PATH = Path("/data/platforms/compras_gov_local.db")


def pick(row: dict, *keys: str):
    norm = {(k or "").strip().lower().replace(" ", "_"): v for k, v in row.items()}
    for key in keys:
        val = norm.get(key)
        if val is None:
            continue
        s = str(val).strip()
        if s and s.lower() not in {"null", "none", "nan"}:
            return s
    return None


def to_float(s):
    if not s:
        return None
    cleaned = str(s).replace("R$", "").replace(" ", "").strip()
    if not cleaned:
        return None
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        n = float(cleaned)
        return n if n > 0 else None
    except ValueError:
        return None


def main() -> int:
    if not ROOT.is_dir():
        print("ERRO: raw ausente:", ROOT, file=sys.stderr)
        return 1
    if not DB_PATH.is_file():
        print("ERRO: db ausente:", DB_PATH, file=sys.stderr)
        return 1

    db = sqlite3.connect(str(DB_PATH))
    db_n = int(db.execute("SELECT COUNT(*) FROM platform_itens_leitura").fetchone()[0])
    print("DB itens_leitura:", db_n)
    print("raw:", ROOT)
    print("---")

    union: set[str] = set()
    item_files = sorted(ROOT.glob("*/*/*COMPRA_ITEM*.csv"))
    if not item_files:
        print("ERRO: nenhum *COMPRA_ITEM*.csv em YYYY/MM/", file=sys.stderr)
        return 1

    for item in item_files:
        month = f"{item.parts[-3]}/{item.parts[-2]}"
        rows = priced = skipped_meta = skipped_price = 0
        keys: set[str] = set()
        with item.open("r", encoding="utf-8-sig", errors="replace", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                rows += 1
                cod = pick(row, "cod_compra")
                num = pick(
                    row,
                    "numero_item_pncp",
                    "numero_item",
                    "numero_item_compra",
                    "cod_item_compra",
                )
                desc = pick(row, "descricao_resumida", "descricao_detalhada", "descricao") or ""
                if not cod or not num or not desc.strip():
                    skipped_meta += 1
                    continue
                hom = to_float(pick(row, "valor_unitario_resultado"))
                est = to_float(pick(row, "valor_unitario_estimado"))
                if not hom and not est:
                    skipped_price += 1
                    continue
                priced += 1
                kid = f"compras_gov:{cod}:{num}"
                keys.add(kid)
        union |= keys
        print(
            f"{month}: csv_rows={rows} unique_com_preco={len(keys)} "
            f"priced_rows={priced} skip_meta={skipped_meta} skip_preco={skipped_price}"
        )

    print("---")
    print("UNION unique_com_preco:", len(union))
    print("DB:", db_n)
    print("diff UNION-DB:", len(union) - db_n)

    missing = 0
    sample_miss: list[str] = []
    # Checagem por amostragem se UNION for enorme (mais rápido / suficiente)
    check = list(union)
    step = max(1, len(check) // 50000)  # ~50k checks
    checked = 0
    for i in range(0, len(check), step):
        kid = check[i]
        checked += 1
        ok = db.execute(
            "SELECT 1 FROM platform_itens_leitura "
            "WHERE plataforma=? AND plataforma_item_id=? LIMIT 1",
            ("compras_gov", kid),
        ).fetchone()
        if not ok:
            missing += 1
            if len(sample_miss) < 20:
                sample_miss.append(kid)
        if checked % 5000 == 0:
            print(f"…amostra {checked}/{((len(check)-1)//step)+1}")

    print("---")
    print(f"checados (amostra 1/{step}):", checked)
    print("faltando na amostra:", missing)
    print("amostra_miss:", sample_miss)
    if missing == 0:
        print("VEREDITO: amostra OK — sem evidência de item faltando")
    else:
        rate = missing / max(checked, 1)
        print(f"VEREDITO: ~{rate:.2%} da amostra ausente no DB — investigar")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
