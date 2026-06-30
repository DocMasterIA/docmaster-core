"""Espaçamento fixo antes do nome na assinatura (TR / DFD / Ofício)."""
from __future__ import annotations

import unittest
from pathlib import Path

from docx import Document

from app.docx_typography import ensure_signature_nome_blank_lines

TEMPLATE_ROOT = Path(__file__).resolve().parents[2] / "template_packages" / "lei_14133"


def _blank_lines_before_paragraph_index(doc: Document, nome_idx: int) -> int:
    paras = list(doc.paragraphs)
    prev_idx = nome_idx - 1
    while prev_idx >= 0 and not (paras[prev_idx].text or "").replace("\xa0", " ").strip():
        prev_idx -= 1
    return nome_idx - prev_idx - 1


def _blank_lines_before_nome(doc: Document, nome_marker: str) -> int:
    paras = list(doc.paragraphs)
    nome_idx = next(i for i, p in enumerate(paras) if nome_marker in (p.text or ""))
    return _blank_lines_before_paragraph_index(doc, nome_idx)


class SignatureNomeSpacingTests(unittest.TestCase):
    def test_tr_template_gets_three_blank_lines(self):
        path = TEMPLATE_ROOT / "dispensa_75_ii_compras" / "TR_modelo_base.docx"
        doc = Document(str(path))
        self.assertEqual(_blank_lines_before_nome(doc, "(TR_NOME_ASSINANTE_TERMO)"), 5)
        ensure_signature_nome_blank_lines(doc)
        self.assertEqual(_blank_lines_before_nome(doc, "(TR_NOME_ASSINANTE_TERMO)"), 3)
        ensure_signature_nome_blank_lines(doc)
        self.assertEqual(_blank_lines_before_nome(doc, "(TR_NOME_ASSINANTE_TERMO)"), 3)

    def test_two_existing_blanks_becomes_three_not_five(self):
        doc = Document()
        doc.add_paragraph("Cidade - UF, 22 de junho de 2026")
        doc.add_paragraph("")
        doc.add_paragraph("")
        doc.add_paragraph("Maria da Silva")
        ensure_signature_nome_blank_lines(doc)
        paras = list(doc.paragraphs)
        nome_idx = next(i for i, p in enumerate(paras) if "Maria da Silva" in (p.text or ""))
        self.assertEqual(_blank_lines_before_paragraph_index(doc, nome_idx), 3)

    def test_dfd_template_gets_three_blank_lines(self):
        path = TEMPLATE_ROOT / "dispensa_75_ii_compras" / "DFD_modelo_base.docx"
        doc = Document(str(path))
        ensure_signature_nome_blank_lines(doc)
        self.assertEqual(_blank_lines_before_nome(doc, "(DFD_NOME_ASSINATURA)"), 3)

    def test_oficio_template_keeps_three_blank_lines(self):
        path = TEMPLATE_ROOT / "dispensa_75_ii_compras" / "OFICIO_modelo_base.docx"
        doc = Document(str(path))
        ensure_signature_nome_blank_lines(doc)
        self.assertEqual(_blank_lines_before_nome(doc, "(SOL_OFICIO_RESPONSAVEL_NOME)"), 3)

    def test_post_fill_fallback_by_cidade_line(self):
        doc = Document()
        doc.add_paragraph("Corpo do ofício com texto.")
        doc.add_paragraph("Cidade Exemplo - UF, 22 de junho de 2026")
        doc.add_paragraph("")
        doc.add_paragraph("Maria da Silva")
        ensure_signature_nome_blank_lines(doc)
        paras = list(doc.paragraphs)
        nome_idx = next(i for i, p in enumerate(paras) if "Maria da Silva" in (p.text or ""))
        self.assertEqual(_blank_lines_before_paragraph_index(doc, nome_idx), 3)

    def test_digital_date_tr_has_three_blank_lines_after_cidade(self):
        from app.tr_template import TRTemplateSlots, render_tr_from_slots

        path = TEMPLATE_ROOT / "dispensa_75_ii_compras" / "TR_modelo_base.docx"
        slots = TRTemplateSlots(
            cidade="São Paulo",
            codigo_uf="SP",
            data_termo="datado e assinado digitalmente",
            nome_assinante_termo="João Silva",
            objeto="Objeto teste",
            justificativa="Justificativa teste",
        )
        out = render_tr_from_slots(slots, template_path=path)
        doc = Document(out)
        paras = list(doc.paragraphs)
        cidade_idx = next(
            i
            for i, p in enumerate(paras)
            if "datado e assinado digitalmente" in (p.text or "").lower()
        )
        nome_idx = next(i for i, p in enumerate(paras) if "João Silva" in (p.text or ""))
        self.assertEqual(nome_idx - cidade_idx - 1, 3)


if __name__ == "__main__":
    unittest.main()
