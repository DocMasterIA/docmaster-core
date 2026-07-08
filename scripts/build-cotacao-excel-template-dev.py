#!/usr/bin/env python3
"""Gera planilha-modelo mínima para desenvolvimento (substituir pelo XLSM oficial)."""
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

ROOT = Path(__file__).resolve().parents[1] / "backend"
OUT = ROOT / "template_packages" / "pncp" / "cotacao_pesquisa_precos.xlsx"

ROWS = [
    ("Pesquisa de preços", ""),
    ("Prefeitura / data", "{PREFEITURA_E_DATA}"),
    ("Prefeitura (UF)", "{PREFEITURA_ESTADO}"),
    ("Responsável", "{RESPONSAVEL_PESQUISA_PREÇOS}"),
    ("Gerado em", "{DATA_HORARIO_GERACAO}"),
    ("Valor por extenso", "{VALOR_EXTENSO}"),
    ("", ""),
    ("Item", "Descrição"),
    ("{ID_ITEM}", "{NOME_ITEM}"),
]


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "Pesquisa"
    bold = Font(bold=True)
    for r, (a, b) in enumerate(ROWS, start=1):
        ws.cell(row=r, column=1, value=a)
        ws.cell(row=r, column=2, value=b)
        if a in ("Item", "Descrição", "Pesquisa de preços"):
            ws.cell(row=r, column=1).font = bold
            if b:
                ws.cell(row=r, column=2).font = bold
    wb.save(OUT)
    print(f"Modelo dev gravado em {OUT}")


if __name__ == "__main__":
    main()
