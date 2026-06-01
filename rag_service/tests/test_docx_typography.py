"""Testes de tipografia DOCX (justificação e listas romanas)."""
import unittest

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

from app.docx_typography import (
    apply_default_justify_to_document,
    paragraph_is_contract_instrument_substitution_block,
    paragraph_is_roman_item_line,
    paragraph_should_remain_left_aligned,
)


class DocxTypographyTests(unittest.TestCase):
    def test_roman_item_line_single_paragraph(self):
        self.assertTrue(paragraph_is_roman_item_line("I – dispensa de licitação em razão do valor;"))
        self.assertTrue(paragraph_is_roman_item_line("II – compras com entrega imediata"))

    def test_contract_instrument_15_1_block(self):
        text = (
            "15.1. O instrumento de contrato poderá ser substituído por instrumento equivalente, "
            "tais como carta-contrato, nota de empenho, autorização de fornecimento ou ordem de "
            "execução de serviço, nos casos de:"
        )
        self.assertTrue(paragraph_is_contract_instrument_substitution_block(text))

    def test_apply_justify_preserves_explicit_left(self):
        doc = Document()
        p_left = doc.add_paragraph("Parágrafo com alinhamento explícito à esquerda no modelo.")
        p_left.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p_none = doc.add_paragraph("Texto corrido sem alinhamento explícito no parágrafo.")
        apply_default_justify_to_document(doc)
        self.assertEqual(p_left.alignment, WD_ALIGN_PARAGRAPH.LEFT)
        self.assertEqual(p_none.alignment, WD_ALIGN_PARAGRAPH.JUSTIFY)

    def test_apply_justify_keeps_15_1_and_roman_items_left(self):
        doc = Document()
        intro = doc.add_paragraph(
            "15.1. O instrumento de contrato poderá ser substituído por instrumento equivalente, "
            "tais como carta-contrato, nota de empenho, nos casos de:"
        )
        item_i = doc.add_paragraph("I – dispensa de licitação em razão do valor;")
        item_ii = doc.add_paragraph("II – compras com entrega imediata e integral dos bens.")
        apply_default_justify_to_document(doc)
        self.assertEqual(intro.alignment, WD_ALIGN_PARAGRAPH.LEFT)
        self.assertEqual(item_i.alignment, WD_ALIGN_PARAGRAPH.LEFT)
        self.assertEqual(item_ii.alignment, WD_ALIGN_PARAGRAPH.LEFT)
        self.assertTrue(paragraph_should_remain_left_aligned(intro.text))


if __name__ == "__main__":
    unittest.main()
