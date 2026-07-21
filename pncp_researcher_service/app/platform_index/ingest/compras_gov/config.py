from __future__ import annotations

import os
from pathlib import Path

PLATFORM_ID = "compras_gov"

# Diretório de CSVs Dados Abertos (host ou volume). Vazio = usa RAW_ROOT_DIR.
COMPRAS_GOV_INGEST_DATA_DIR: str = os.getenv("COMPRAS_GOV_INGEST_DATA_DIR", "").strip()

# Views oficiais (export CSV do portal Dados Abertos Compras.gov).
# COMPRA = cabeçalho do processo; COMPRA_ITEM = item + preço/fornecedor.
COMPRAS_GOV_VIEW_COMPRA = "VW_FT_PNCP_COMPRA"
COMPRAS_GOV_VIEW_COMPRA_ITEM = "VW_FT_PNCP_COMPRA_ITEM"

# Stems aceitos no discover (case-insensitive; prefixos tipo comprasGOV-*-VW_…).
COMPRAS_GOV_FILE_COMPRA_MARKERS = (
    "VW_FT_PNCP_COMPRA",
    "vw_ft_pncp_compra",
)
COMPRAS_GOV_FILE_ITEM_MARKERS = (
    "VW_FT_PNCP_COMPRA_ITEM",
    "vw_ft_pncp_compra_item",
)

FIXTURES_DIR = Path(__file__).resolve().parents[4] / "fixtures" / "compras_gov"
# Pasta local: raw/anual/, raw/mensal/YYYY-MM/, ou CSVs soltos em raw/.
RAW_ROOT_DIR = Path(__file__).resolve().parents[4] / "data" / "compras_gov" / "raw"
