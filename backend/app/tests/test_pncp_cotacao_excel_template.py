"""Testes do motor de slots da planilha-modelo de cotação."""
from unittest import TestCase

from backend.app.services.pncp_cotacao_excel_template import (
    ITEM_SLOT_NAMES,
    SLOT_ALIASES,
    _canonical_slot,
    _substitute_slots,
    build_item_slot_context,
)


class CotacaoExcelSlotTests(TestCase):
    def test_canonical_slot_aliases(self):
        self.assertEqual(_canonical_slot("responsavel_pesquisa_precos"), "RESPONSAVEL_PESQUISA_PREÇOS")
        self.assertEqual(_canonical_slot("VALOR_POR_EXTENSO"), "VALOR_EXTENSO")

    def test_substitute_global_slots(self):
        ctx = {
            "DATA_HORARIO_GERACAO": "08/07/2026 às 20:00",
            "VALOR_EXTENSO": "cem reais",
        }
        out = _substitute_slots("Gerado em {DATA_HORARIO_GERACAO} — {VALOR_EXTENSO}", ctx)
        self.assertEqual(out, "Gerado em 08/07/2026 às 20:00 — cem reais")

    def test_substitute_alias_slot(self):
        ctx = {"RESPONSAVEL_PESQUISA_PREÇOS": "Ana Costa"}
        out = _substitute_slots("Resp.: {RESPONSAVEL_PESQUISA_PRECOS}", ctx)
        self.assertEqual(out, "Resp.: Ana Costa")

    def test_item_slot_context(self):
        class Item:
            id = 99
            numero_item = "22"
            descricao_item = "Caneta azul"

        ctx = build_item_slot_context(Item())
        self.assertEqual(ctx["ID_ITEM"], "22")
        self.assertEqual(ctx["NOME_ITEM"], "Caneta azul")

    def test_item_slot_names(self):
        self.assertIn("ID_ITEM", ITEM_SLOT_NAMES)
        self.assertIn("NOME_ITEM", ITEM_SLOT_NAMES)
        self.assertIn("RESPONSAVEL_PESQUISA_PREÇOS", SLOT_ALIASES.values())
