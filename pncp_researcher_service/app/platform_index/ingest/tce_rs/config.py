from __future__ import annotations

import os
from pathlib import Path

PLATFORM_ID = "tce_rs"

TCE_RS_CKAN_BASE_URL: str = os.getenv(
    "TCE_RS_CKAN_BASE_URL",
    "https://dados.tce.rs.gov.br",
).strip().rstrip("/")

TCE_RS_INGEST_DATA_DIR: str = os.getenv("TCE_RS_INGEST_DATA_DIR", "").strip()

# Stems LicitaCon (case-insensitive via find_csv_file).
TCE_RS_FILE_LICITACAO = "licitacao"
TCE_RS_FILE_ITEM = "item"
TCE_RS_FILE_ITEM_ALIASES = ("item", "itemw")
TCE_RS_FILE_ITEM_PROP = "item_prop"
TCE_RS_FILE_PROPOSTA = "proposta"  # fallback processo / fixtures antigas
TCE_RS_FILE_PESSOAS = "pessoas"

FIXTURES_DIR = Path(__file__).resolve().parents[4] / "fixtures" / "tce_rs"
# Pasta local com subpastas por ano (2025/, 2026/, …).
RAW_ROOT_DIR = Path(__file__).resolve().parents[4] / "data" / "tce_rs" / "raw"
