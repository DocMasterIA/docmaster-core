"""Testes de tipografia DOCX (justificação e listas romanas)."""
import unittest

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

from app.docx_typography import (
    apply_default_justify_to_document,
    paragraph_is_contract_instrument_substitution_block,
    paragraph_is_roman_enumerated_list,
    paragraph_is_roman_item_line,
    paragraph_is_short_roman_item_line,
    paragraph_is_tr_numbered_subsection_prose,
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

    def test_apply_justify_preserves_explicit_justify(self):
        doc = Document()
        p_justify = doc.add_paragraph("Justificativa longa do termo de referência com alinhamento justificado no modelo.")
        p_justify.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_none = doc.add_paragraph("Texto corrido sem alinhamento explícito no parágrafo.")
        apply_default_justify_to_document(doc)
        self.assertEqual(p_justify.alignment, WD_ALIGN_PARAGRAPH.JUSTIFY)
        self.assertEqual(p_none.alignment, WD_ALIGN_PARAGRAPH.JUSTIFY)

    def test_apply_justify_preserves_explicit_left(self):
        doc = Document()
        p_left = doc.add_paragraph("Parágrafo com alinhamento explícito à esquerda no modelo.")
        p_left.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p_none = doc.add_paragraph("Texto corrido sem alinhamento explícito no parágrafo.")
        apply_default_justify_to_document(doc)
        self.assertEqual(p_left.alignment, WD_ALIGN_PARAGRAPH.LEFT)
        self.assertEqual(p_none.alignment, WD_ALIGN_PARAGRAPH.JUSTIFY)

    def test_apply_justify_keeps_15_1_intro_left_roman_items_justified(self):
        doc = Document()
        intro = doc.add_paragraph(
            "15.1. O instrumento de contrato poderá ser substituído por instrumento equivalente, "
            "tais como carta-contrato, nota de empenho, nos casos de:"
        )
        item_i = doc.add_paragraph(
            "I – Nota Fiscal devidamente emitida em nome da Contratante, contendo a descrição precisa dos serviços."
        )
        item_i.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        item_ii = doc.add_paragraph(
            "II – Certidões Negativas ou Positivas com efeito de Negativa de Débitos Relativos aos Tributos."
        )
        item_ii.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        apply_default_justify_to_document(doc)
        self.assertEqual(intro.alignment, WD_ALIGN_PARAGRAPH.LEFT)
        self.assertEqual(item_i.alignment, WD_ALIGN_PARAGRAPH.JUSTIFY)
        self.assertEqual(item_ii.alignment, WD_ALIGN_PARAGRAPH.JUSTIFY)
        self.assertTrue(paragraph_should_remain_left_aligned(intro.text))
        self.assertFalse(paragraph_should_remain_left_aligned(item_i.text))

    def test_contract_15_1_long_block_still_left_aligned(self):
        # Bloco real do TR compras (425+ chars no modelo) — não pode cair na regra de corpo longo.
        text = (
            "15.1. O instrumento de contrato poderá ser substituído por instrumento equivalente, "
            "tais como, nota de empenho, autorização de fornecimento, nos casos de:\n"
            "I – dispensa de licitação em razão do valor;\n"
            "II – compras com entrega imediata e integral dos bens;\n"
            "III – serviços de natureza continuada ou por escopo definido, conforme o caso."
        )
        self.assertTrue(paragraph_is_contract_instrument_substitution_block(text))
        self.assertTrue(paragraph_should_remain_left_aligned(text))

    def test_manutencao_sec21_roman_block_not_forced_left(self):
        text = (
            "I – Manutenção preventiva;\n"
            "II – Manutenção corretiva;\n"
            "III – Diagnóstico mecânico, elétrico e eletrônico;\n"
            "IV – Substituição de peças, componentes e acessórios;"
        )
        self.assertTrue(paragraph_is_roman_enumerated_list(text))
        self.assertFalse(paragraph_should_remain_left_aligned(text))

    def test_manutencao_terms_in_long_justificativa_not_treated_as_list(self):
        text = (
            "Trata-se de Manutenção preventiva e Manutenção corretiva da frota municipal, "
            "alinhada à necessidade de preservar o patrimônio e reduzir custos futuros. "
            "A medida garante continuidade do atendimento e conformidade com o plano de conservação. "
        ) * 3
        self.assertFalse(paragraph_should_remain_left_aligned(text))
        self.assertFalse(paragraph_is_roman_enumerated_list(text))

    def test_long_roman_like_prose_not_short_list_line(self):
        text = "I – " + ("texto dissertativo " * 40)
        self.assertFalse(paragraph_is_short_roman_item_line(text))
        self.assertFalse(paragraph_should_remain_left_aligned(text))

    def test_roman_nf_lines_justified_after_tr_render(self):
        from pathlib import Path

        from app.tr_template import TRTemplateSlots, render_tr_from_slots

        tpl = (
            Path(__file__).resolve().parents[2]
            / "template_packages/lei_14133/dispensa_75_ii_compras/TR_modelo_base.docx"
        )
        slots = TRTemplateSlots(
            objeto="Aquisição de material de expediente.",
            justificativa="Justificativa de teste com texto suficiente para o termo de referência.",
            cidade="Goiânia",
            codigo_uf="GO",
        )
        out = render_tr_from_slots(slots, template_path=tpl)
        doc = Document(out)
        nf = next(p for p in doc.paragraphs if "Nota Fiscal devidamente" in (p.text or ""))
        cert = next(p for p in doc.paragraphs if "Certidões Negativas" in (p.text or ""))
        self.assertEqual(nf.alignment, WD_ALIGN_PARAGRAPH.JUSTIFY)
        self.assertEqual(cert.alignment, WD_ALIGN_PARAGRAPH.JUSTIFY)

    def test_tr_secao_6_subsection_prose_is_justified_even_if_template_left(self):
        text = (
            "6.1. A formalização da contratação decorrente deste procedimento poderá ocorrer mediante "
            "CONTRATO, ATA DE REGISTRO DE PREÇOS ou INSTRUMENTO EQUIVALENTE, conforme o caso e a "
            "natureza da contratação, nos termos do art. 95 da Lei nº 14.133/2021."
        )
        self.assertTrue(paragraph_is_tr_numbered_subsection_prose(text))
        doc = Document()
        p = doc.add_paragraph(text)
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        apply_default_justify_to_document(doc)
        self.assertEqual(p.alignment, WD_ALIGN_PARAGRAPH.JUSTIFY)

    def test_manutencao_veiculos_sec61_sec62_justified_after_render(self):
        from pathlib import Path

        from app.tr_template import TRTemplateSlots, render_tr_from_slots

        tpl = (
            Path(__file__).resolve().parents[2]
            / "template_packages/lei_14133/dispensa_75_i_manutencao_veiculos/TR_modelo_base.docx"
        )
        slots = TRTemplateSlots(
            objeto="Prestação de serviços de manutenção veicular.",
            justificativa="Justificativa de teste com texto suficiente para o termo de referência.",
            cidade="Goiânia",
            codigo_uf="GO",
            slot_package_key="dispensa_75_i_manutencao_veiculos",
        )
        out = render_tr_from_slots(slots, template_path=tpl)
        doc = Document(out)
        sec6 = [
            p
            for p in doc.paragraphs
            if (p.text or "").strip().startswith(("6.1.", "6.2."))
        ]
        assert len(sec6) >= 2, "§6.1/6.2 não encontrados no TR manutenção veículos"
        for p in sec6[:2]:
            self.assertEqual(
                p.alignment,
                WD_ALIGN_PARAGRAPH.JUSTIFY,
                msg=(p.text or "")[:80],
            )


if __name__ == "__main__":
    unittest.main()
