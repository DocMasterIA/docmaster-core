from __future__ import annotations

import os
from pathlib import Path

PLATFORM_ID = "notas_fiscais"

# Diretório de CSVs Portal da Transparência (host ou volume). Vazio = RAW_ROOT_DIR.
NOTAS_FISCAIS_INGEST_DATA_DIR: str = os.getenv("NOTAS_FISCAIS_INGEST_DATA_DIR", "").strip()

# Stems oficiais do dump mensal (portaldatransparencia.gov.br/download-de-dados/notas-fiscais).
# Item = tabela-mãe da busca; Nota = join de evento/órgão; Evento = opcional.
NF_FILE_ITEM_MARKERS = (
    "NFe_NotaFiscalItem",
    "nfe_notafiscalitem",
    "NotaFiscalItem",
)
NF_FILE_NOTA_MARKERS = (
    "NFe_NotaFiscal",
    "nfe_notafiscal",
    "NotaFiscal",
)
NF_FILE_EVENTO_MARKERS = (
    "NFe_NotaFiscalEvento",
    "nfe_notafiscalevento",
    "NotaFiscalEvento",
)

FIXTURES_DIR = Path(__file__).resolve().parents[4] / "fixtures" / "notas_fiscais"
# Pasta local: raw/YYYY/MM/ com *NotaFiscalItem*.csv (+ NotaFiscal opcional).
RAW_ROOT_DIR = Path(__file__).resolve().parents[4] / "data" / "notas_fiscais" / "raw"
