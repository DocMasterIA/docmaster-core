#!/usr/bin/env python3
"""
Baixa CSVs mensais Compras.gov (SEGES) do repositorio.dados.gov.br.

Padrão:
  - 2026: todos os meses disponíveis
  - 2025: a partir de 06/ (06, 07, …)

Destino padrão (compatível com discover_ingest_dirs):
  pncp_researcher_service/data/compras_gov/raw/{YYYY}/{MM}/

Uso:
  python3 scripts/download-comprasgov-mensal.py
  python3 scripts/download-comprasgov-mensal.py --all-files
  python3 scripts/download-comprasgov-mensal.py --dry-run
  python3 scripts/download-comprasgov-mensal.py --out /caminho/raw
"""
from __future__ import annotations

import argparse
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

BASE = "https://repositorio.dados.gov.br/seges/comprasgov/mensal"
HREF_RE = re.compile(r'href="([^"]+)"', re.IGNORECASE)

# Necessários para o ingest DocMaster (VW_FT_PNCP_COMPRA + ITEM).
DEFAULT_NAME_MARKERS = (
    "VW_FT_PNCP_COMPRA_ITEM",
    "VW_FT_PNCP_COMPRA",
)

USER_AGENT = "DocMaster-comprasgov-downloader/1.0 (+local)"


def _repo_raw_default() -> Path:
    root = Path(__file__).resolve().parents[1]
    return root / "pncp_researcher_service" / "data" / "compras_gov" / "raw"


def _http_get(url: str, *, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _http_headers(url: str, *, timeout: int = 60) -> dict:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {k.lower(): v for k, v in resp.headers.items()}
    except Exception:
        return {}


def list_index(url: str) -> List[str]:
    """Retorna hrefs relativos de um Index of /…/."""
    if not url.endswith("/"):
        url += "/"
    html = _http_get(url, timeout=60).decode("utf-8", errors="replace")
    out: List[str] = []
    for href in HREF_RE.findall(html):
        href = href.strip()
        if not href or href in ("../", "./") or href.startswith("?"):
            continue
        if href.startswith("http://") or href.startswith("https://"):
            continue
        out.append(urllib.parse.unquote(href))
    return out


def list_month_dirs(year: int) -> List[str]:
    url = f"{BASE}/{year}/"
    months: List[str] = []
    for href in list_index(url):
        name = href.rstrip("/")
        if re.fullmatch(r"\d{2}", name):
            months.append(name)
    return sorted(months)


def list_month_files(year: int, month: str) -> List[str]:
    url = f"{BASE}/{year}/{month}/"
    files: List[str] = []
    for href in list_index(url):
        if href.endswith("/") or ".." in href:
            continue
        if href.lower().endswith(".csv"):
            files.append(href.split("/")[-1])
    return sorted(set(files))


def select_files(names: Sequence[str], *, all_files: bool) -> List[str]:
    if all_files:
        return list(names)
    # COMPRA_ITEM antes de COMPRA (substring).
    picked: List[str] = []
    for marker in ("VW_FT_PNCP_COMPRA_ITEM", "VW_FT_PNCP_COMPRA"):
        for name in names:
            low = name.upper()
            if marker == "VW_FT_PNCP_COMPRA":
                if "VW_FT_PNCP_COMPRA_ITEM" in low:
                    continue
                if "VW_FT_PNCP_COMPRA" in low and name not in picked:
                    picked.append(name)
            elif marker in low and name not in picked:
                picked.append(name)
    return picked


def plan_targets(
    *,
    year_2025_from: int = 6,
    all_files: bool = False,
) -> List[Tuple[int, str, str]]:
    """Lista (ano, mês, filename)."""
    targets: List[Tuple[int, str, str]] = []

    # 2025 a partir de MM
    for month in list_month_dirs(2025):
        if int(month) < year_2025_from:
            continue
        for name in select_files(list_month_files(2025, month), all_files=all_files):
            targets.append((2025, month, name))

    # 2026 todos
    for month in list_month_dirs(2026):
        for name in select_files(list_month_files(2026, month), all_files=all_files):
            targets.append((2026, month, name))

    return targets


def download_file(
    url: str,
    dest: Path,
    *,
    dry_run: bool = False,
    force: bool = False,
    retries: int = 3,
) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    headers = _http_headers(url)
    remote_len = None
    try:
        remote_len = int(headers.get("content-length") or 0) or None
    except ValueError:
        remote_len = None

    if dest.is_file() and not force:
        local = dest.stat().st_size
        if remote_len is None or local == remote_len:
            return f"skip (exists {local:,} B)"
        # tamanho diverge → rebaixa

    if dry_run:
        size = f"{remote_len:,} B" if remote_len else "?"
        return f"dry-run ({size})"

    tmp = dest.with_suffix(dest.suffix + ".part")
    last_err: Optional[BaseException] = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=600) as resp, tmp.open("wb") as out:
                while True:
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
            if remote_len is not None:
                got = tmp.stat().st_size
                if got != remote_len:
                    raise IOError(f"tamanho incompleto: {got} != {remote_len}")
            tmp.replace(dest)
            return f"ok ({dest.stat().st_size:,} B)"
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, IOError) as exc:
            last_err = exc
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
            if attempt < retries:
                time.sleep(min(30, 2 ** attempt))
                continue
            break
    raise RuntimeError(f"falha ao baixar {url}: {last_err}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Download mensal Compras.gov (SEGES dados.gov.br)")
    ap.add_argument(
        "--out",
        type=Path,
        default=_repo_raw_default(),
        help="Pasta raiz raw (default: …/data/compras_gov/raw)",
    )
    ap.add_argument(
        "--from-2025-month",
        type=int,
        default=6,
        help="Mês inicial inclusivo em 2025 (default: 6)",
    )
    ap.add_argument(
        "--all-files",
        action="store_true",
        help="Baixa todos os CSV do mês (inclui VW_DM_PNCP_ITEM_RESULTADO)",
    )
    ap.add_argument("--dry-run", action="store_true", help="Só lista o que seria baixado")
    ap.add_argument("--force", action="store_true", help="Rebaixa mesmo se arquivo existir")
    args = ap.parse_args(argv)

    out_root: Path = args.out.expanduser().resolve()
    print(f"Base: {BASE}")
    print(f"Destino: {out_root}")
    print(f"2025: meses >= {args.from_2025_month:02d} | 2026: todos")
    print(f"Arquivos: {'TODOS .csv' if args.all_files else 'COMPRA + COMPRA_ITEM'}")
    print()

    try:
        targets = plan_targets(
            year_2025_from=max(1, min(12, int(args.from_2025_month))),
            all_files=bool(args.all_files),
        )
    except Exception as exc:
        print(f"ERRO ao listar índice remoto: {exc}", file=sys.stderr)
        return 1

    if not targets:
        print("Nenhum arquivo encontrado no índice remoto.", file=sys.stderr)
        return 2

    # resumo por mês
    by_month = {}
    for y, m, name in targets:
        by_month.setdefault(f"{y}-{m}", []).append(name)
    for key in sorted(by_month):
        print(f"  {key}: {len(by_month[key])} arquivo(s)")
    print(f"\nTotal: {len(targets)} download(s)\n")

    ok = skip = fail = 0
    for year, month, name in targets:
        url = f"{BASE}/{year}/{month}/{urllib.parse.quote(name)}"
        dest = out_root / str(year) / month / name
        label = f"{year}/{month}/{name}"
        try:
            status = download_file(
                url,
                dest,
                dry_run=bool(args.dry_run),
                force=bool(args.force),
            )
            print(f"[{status}] {label}")
            if status.startswith("skip"):
                skip += 1
            else:
                ok += 1
        except Exception as exc:
            fail += 1
            print(f"[FAIL] {label}: {exc}", file=sys.stderr)

    print(f"\nConcluído: ok={ok} skip={skip} fail={fail}")
    return 0 if fail == 0 else 3


if __name__ == "__main__":
    raise SystemExit(main())
