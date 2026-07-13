"""Substituição de ( NUMERO_PROCESSO ) no TR — placeholder manual no .docx."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from docx import Document

from docx.enum.text import WD_ALIGN_PARAGRAPH

from app.tr_template import (
    TRTemplateSlots,
    is_numero_processo_placeholder,
    numero_processo_valor_placeholder_tr,
    render_tr_from_slots,
    slots_numero_processo_display,
)

TEMPLATE_PACKAGES_ROOT = Path(__file__).resolve().parents[2] / "template_packages"

ALL_TR_TEMPLATES = sorted(TEMPLATE_PACKAGES_ROOT.rglob("TR_modelo_base.docx"))

# Modelo com placeholder manual (como o usuário coloca no Word)
TEMPLATE_COM_PLACEHOLDER = (
    TEMPLATE_PACKAGES_ROOT
    / "lei_14133"
    / "inexigibilidade_74_i_manutencao_de_veiculos"
    / "TR_modelo_base.docx"
)


class TrNumeroProcessoPlaceholderTests(unittest.TestCase):
    def _processo_paragraphs_bold(self, doc: Document) -> list[str]:
        failures: list[str] = []
        for p in doc.paragraphs:
            text = (p.text or "").strip().upper()
            if not text.startswith("PROCESSO:"):
                continue
            for run in p.runs:
                if (run.text or "").strip() and not run.bold:
                    failures.append(f"run não negrito: {run.text!r} em {p.text!r}")
        return failures

    def test_numero_processo_placeholder_detection(self):
        self.assertTrue(is_numero_processo_placeholder("( NUMERO_PROCESSO )"))
        self.assertTrue(is_numero_processo_placeholder("(NUMERO PROCESSO)"))
        self.assertTrue(is_numero_processo_placeholder("(DFD_NUMERO_PROCESSO)"))
        self.assertFalse(is_numero_processo_placeholder("(TR_OBJETO)"))

    def test_all_tr_templates_have_numero_processo_placeholder(self):
        self.assertTrue(ALL_TR_TEMPLATES, "Nenhum TR_modelo_base.docx encontrado")
        missing: list[str] = []
        for path in ALL_TR_TEMPLATES:
            doc = Document(str(path))
            full = "\n".join(p.text or "" for p in doc.paragraphs)
            if not re.search(r"\(\s*NUMERO_PROCESSO\s*\)", full, re.I):
                missing.append(str(path.relative_to(TEMPLATE_PACKAGES_ROOT)))
        self.assertEqual(
            missing,
            [],
            f"TR(s) sem ( NUMERO_PROCESSO ): {missing}",
        )

    def test_numero_processo_replaced_in_every_tr_template(self):
        slots = TRTemplateSlots(
            numero_processo="1231/2026",
            objeto="Objeto teste",
            justificativa="Justificativa teste.",
            cidade="Cidade Teste",
            codigo_uf="GO",
        )
        failures: list[str] = []
        for path in ALL_TR_TEMPLATES:
            out = render_tr_from_slots(slots, template_path=path)
            doc = Document(out)
            head = doc.paragraphs[:12]
            if not any("PROCESSO: 1231/2026" in (p.text or "") for p in head):
                failures.append(f"{path.relative_to(TEMPLATE_PACKAGES_ROOT)}: PROCESSO não substituído")
            if any("( NUMERO_PROCESSO )" in (p.text or "") for p in head):
                failures.append(f"{path.relative_to(TEMPLATE_PACKAGES_ROOT)}: placeholder bruto permaneceu")
            proc_paras = [p for p in head if (p.text or "").strip().upper().startswith("PROCESSO:")]
            for proc_para in proc_paras:
                if proc_para.alignment != WD_ALIGN_PARAGRAPH.LEFT:
                    failures.append(
                        f"{path.relative_to(TEMPLATE_PACKAGES_ROOT)}: PROCESSO não está à esquerda "
                        f"(align={proc_para.alignment})"
                    )
                for run in proc_para.runs:
                    if (run.text or "").strip() and not run.bold:
                        failures.append(
                            f"{path.relative_to(TEMPLATE_PACKAGES_ROOT)}: PROCESSO não está em negrito "
                            f"(run={run.text!r})"
                        )
        self.assertEqual(failures, [], "\n".join(failures))

    def test_numero_processo_only_on_slots_still_renders_tr(self):
        """Override só com numero_processo (sem dfd_numero_processo) preenche o TR."""
        slots = TRTemplateSlots(
            numero_processo="4567/2026",
            objeto="Objeto teste",
            justificativa="Justificativa teste.",
            cidade="Cidade Teste",
            codigo_uf="GO",
        )
        self.assertEqual(slots_numero_processo_display(slots), "4567/2026")
        out = render_tr_from_slots(slots, template_path=TEMPLATE_COM_PLACEHOLDER)
        doc = Document(out)
        self.assertTrue(
            any("PROCESSO: 4567/2026" in (p.text or "") for p in doc.paragraphs[:8]),
        )

    def test_merge_coalesces_numero_processo_pair(self):
        from app.tr_slots_llm import _merge_slots

        llm_slots = TRTemplateSlots(objeto="Obj", justificativa="Just.")
        merged = _merge_slots(llm_slots, {"numero_processo": "7890/2026"})
        self.assertEqual(merged.numero_processo, "7890/2026")
        self.assertEqual(merged.dfd_numero_processo, "7890/2026")

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
        self.assertEqual(self._processo_paragraphs_bold(doc), [])
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
