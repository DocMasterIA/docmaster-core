"""Filtro de exibição em local_item_search (preço vs fornecedor)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.pricing_display import filter_items_for_search_display, filter_items_with_display_price


class LocalSearchDisplayFilterBranchTests(unittest.TestCase):
    """Espelha o ramo final de local_item_search (sem SQLite)."""

    def _apply_branch(self, itens: list[dict], *, filtrar_fornecedor: bool) -> list[dict]:
        if filtrar_fornecedor:
            return filter_items_for_search_display(itens)
        return filter_items_with_display_price(itens)

    def test_bulk_branch_keeps_price_with_placeholder_supplier(self):
        rows = [
            {"valor_unitario_estimado": 5.0, "fornecedor": "Não se aplica"},
            {"valor_unitario_estimado": 8.0, "fornecedor": "FORNECEDORA OK LTDA"},
        ]
        out = self._apply_branch(rows, filtrar_fornecedor=False)
        self.assertEqual(len(out), 2)

    def test_manual_branch_drops_placeholder_supplier(self):
        rows = [
            {"valor_unitario_estimado": 5.0, "fornecedor": "Não se aplica"},
            {"valor_unitario_estimado": 8.0, "fornecedor": "FORNECEDORA OK LTDA"},
        ]
        out = self._apply_branch(rows, filtrar_fornecedor=True)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["fornecedor"], "FORNECEDORA OK LTDA")

    def test_price_only_branch_still_drops_zero_price(self):
        rows = [
            {"valor_unitario": 0, "fornecedor": "FORNECEDORA OK LTDA"},
            {"valor_unitario_estimado": 3.0, "fornecedor": "OUTRA LTDA"},
        ]
        out = self._apply_branch(rows, filtrar_fornecedor=False)
        self.assertEqual(len(out), 1)

    def test_cnpj_only_passes_manual_filter(self):
        rows = [{"valor_unitario_estimado": 4.0, "cnpj_fornecedor": "12.345.678/0001-95"}]
        out = self._apply_branch(rows, filtrar_fornecedor=True)
        self.assertEqual(len(out), 1)


if __name__ == "__main__":
    unittest.main()
