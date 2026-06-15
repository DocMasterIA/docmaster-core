from django.test import SimpleTestCase

from backend.app.pncp_cotacao_api import _build_items_from_import_rows, _normalize_column_id


class PncpImportColumnTests(SimpleTestCase):
    def test_id_header_maps_to_numero_item(self):
        self.assertEqual(_normalize_column_id("ID"), "numero_item")
        self.assertEqual(_normalize_column_id("N°"), "numero_item")

    def test_descricao_do_item_header(self):
        self.assertEqual(_normalize_column_id("Descrição do Item"), "descricao_item")

    def test_build_items_preserves_spreadsheet_numero_item(self):
        rows = [
            {"ID": "22", "Descricao Item": "Medicamento A"},
            {"ID": "23", "Descricao Item": "Medicamento B"},
        ]
        items, errors = _build_items_from_import_rows(rows, {})
        self.assertEqual(errors, [])
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["numero_item"], "22")
        self.assertEqual(items[1]["numero_item"], "23")
