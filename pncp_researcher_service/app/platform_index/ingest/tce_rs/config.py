from __future__ import annotations

import os
from pathlib import Path

PLATFORM_ID = "tce_rs"

TCE_RS_CKAN_BASE_URL: str = os.getenv(
    "TCE_RS_CKAN_BASE_URL",
    "https://dados.tce.rs.gov.br",
).strip().rstrip("/")

TCE_RS_INGEST_DATA_DIR: str = os.getenv("TCE_RS_INGEST_DATA_DIR", "").strip()

# Arquivos LicitaCon (nomes aproximados — mapeamento flexível no parser).
TCE_RS_FILE_LICITACAO = "LICITACAO"
TCE_RS_FILE_ITEM = "ITEM"
TCE_RS_FILE_PROPOSTA = "PROPOSTA"

FIXTURES_DIR = Path(__file__).resolve().parents[4] / "fixtures" / "tce_rs"
