"""Substituição de ( NUMERO_PROCESSO ) no TR — placeholder manual no .docx."""
from __future__ import annotations

import unittest
from pathlib import Path

from docx import Document

from app.tr_template import (
    TRTemplateSlots,
    numero_processo_valor_placeholder_tr,
    render_tr_from_slots,
)

# Modelo com placeholder manual (como o usuário coloca no Word)
TEMPLATE_COM_PLACEHOLDER = (
    Path(__file__).resolve().parents[2]
    / "template_packages"
    / "lei_14133"
    / "inexigibilidade_74_i_manutencao_de_veiculos"
    / "TR_modelo_base.docx"
)


class TrNumeroProcessoPlaceholderTests(unittest.TestCase):
    def test_mapping_formats_processo_prefix(self):
        self.assertEqual(numero_processo_valor_placeholder_tr("1231/2026"), "PROCESSO: 1231/2026")
        self.assertEqual(numero_processo_valor_placeholder_tr(""), "")

    def test_manual_placeholder_replaced_on_render(self):
        slots = TRTemplateSlots(
            numero_processo="1231/2026",
            objeto="Objeto teste",
            justificativa="Justificativa teste.",
        )
        out = render_tr_from_slots(slots, template_path=TEMPLATE_COM_PLACEHOLDER)
        doc = Document(out)
        self.assertTrue(
            any("PROCESSO: 1231/2026" in (p.text or "") for p in doc.paragraphs[:8]),
            "Esperado PROCESSO: no parágrafo do placeholder",
        )
        self.assertFalse(
            any("( NUMERO_PROCESSO )" in (p.text or "") for p in doc.paragraphs[:8]),
            "Placeholder não deve permanecer no DOCX",
        )

    def test_empty_processo_clears_placeholder_paragraph(self):
        slots = TRTemplateSlots(objeto="Objeto", justificativa="Just.")
        out = render_tr_from_slots(slots, template_path=TEMPLATE_COM_PLACEHOLDER)
        doc = Document(out)
        for p in doc.paragraphs[:8]:
            self.assertNotIn("PROCESSO:", (p.text or "").upper())


if __name__ == "__main__":
    unittest.main()
