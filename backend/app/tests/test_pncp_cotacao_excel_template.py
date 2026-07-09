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
            quantidade = 10
            unidade_medida = "UN"
            valor_unitario = None
            valor_total = None

        ctx = build_item_slot_context(
            Item(),
            refletido={
                "valor_unitario_refletido": 6.34,
                "valor_total_refletido": 63.4,
                "unidade_medida_refletida": "UN",
                "quantidade_refletida": 10,
            },
            fontes={
                "governamentais": 2,
                "entesPublicos": 1,
                "dominioAmplo": 0,
                "cotacaoDireta": 0,
                "notasFiscais": 0,
            },
        )
        self.assertEqual(ctx["ID_ITEM"], "22")
        self.assertEqual(ctx["NOME_ITEM"], "Caneta azul")
        self.assertEqual(ctx["UNIDADE"], "UN")
        self.assertEqual(ctx["QUANTIDADE"], "10")
        self.assertEqual(ctx["COTACOES_VALIDAS"], "3")
        self.assertEqual(ctx["VALOR_MEDIO"], "R$ 6,34")
        self.assertEqual(ctx["VALOR_TOTAL_HOMOLOGADO"], "R$ 63,40")

    def test_item_slot_names(self):
        self.assertIn("ID_ITEM", ITEM_SLOT_NAMES)
        self.assertIn("NOME_ITEM", ITEM_SLOT_NAMES)
        self.assertIn("VALOR_MEDIO", ITEM_SLOT_NAMES)
        self.assertIn("VALOR_TOTAL_HOMOLOGADO", ITEM_SLOT_NAMES)
        self.assertIn("RESPONSAVEL_PESQUISA_PREÇOS", SLOT_ALIASES.values())
