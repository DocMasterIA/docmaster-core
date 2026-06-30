"""Seção 4 TR — exatamente 3 parágrafos Word (dispensa normal vs rápida)."""
from __future__ import annotations

import re
import unittest
import zipfile
from pathlib import Path

from app.justificativa_clause_sanitize import normalize_justificativa_tres_paragrafos
from app.tr_slots_llm import (
    _apply_dispensa_secao4_from_prefilled_override,
    _build_tr_slots_from_override_prefilled,
)
from app.tr_template import DispensaSlots, TRTemplateSlots, render_tr_from_slots

SAMPLE_TRES = """Parágrafo um sobre necessidade da contratação para atender demanda urgente da secretaria municipal de saúde e garantir continuidade dos serviços essenciais à população.

Parágrafo dois sobre riscos administrativos da não realização incluindo interrupção de serviços e passivos trabalhistas que comprometeriam a eficiência operacional do órgão.

Parágrafo três sobre benefícios esperados com preservação do patrimônio público e melhoria da eficiência administrativa em conformidade com o interesse coletivo."""

TPL = Path(__file__).resolve().parents[2] / "template_packages/lei_14133/dispensa_75_ii_compras/TR_modelo_base.docx"


def _secao4_paragraphs(docx_path: str) -> list[str]:
    z = zipfile.ZipFile(docx_path)
    xml = z.read("word/document.xml").decode("utf-8")
    paras = re.findall(r"<w:p[ >].*?</w:p>", xml, re.DOTALL)
    texts = [
        "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p)).strip() for p in paras
    ]
    start = next(i for i, t in enumerate(texts) if "4. DA JUSTIFICATIVA" in t)
    end = next(i for i, t in enumerate(texts[start + 1 :], start + 1) if t.startswith("5."))
    return [t for t in texts[start + 1 : end] if t]


class TrSecao4JustificativaParagraphsTests(unittest.TestCase):
    def test_prefilled_rapida_splits_tres_paragrafos_em_tres_slots(self):
        jus = normalize_justificativa_tres_paragrafos(SAMPLE_TRES)
        parts = jus.split("\n\n")
        slots = _build_tr_slots_from_override_prefilled(
            {
                "objeto": "Objeto longo o suficiente para o teste de skip.",
                "justificativa": jus,
                "problema_administrativo": parts[1],
                "beneficio_esperado": parts[2],
                "dispensa_fluxo_ui": "rapida",
            },
            None,
        )
        self.assertEqual(slots.justificativa, parts[0])
        self.assertEqual(slots.problema_administrativo, parts[1])
        self.assertEqual(slots.beneficio_esperado, parts[2])

    def test_prefilled_normal_limpa_problema_beneficio(self):
        jus = normalize_justificativa_tres_paragrafos(SAMPLE_TRES)
        parts = jus.split("\n\n")
        slots = _build_tr_slots_from_override_prefilled(
            {
                "objeto": "Objeto longo o suficiente para o teste de skip.",
                "justificativa": jus,
                "problema_administrativo": parts[1],
                "beneficio_esperado": parts[2],
                "dispensa_fluxo_ui": "normal",
            },
            None,
        )
        self.assertEqual(slots.justificativa, jus)
        self.assertEqual(slots.problema_administrativo, "")
        self.assertEqual(slots.beneficio_esperado, "")

    def test_render_rapida_tres_paragrafos_no_word(self):
        jus = normalize_justificativa_tres_paragrafos(SAMPLE_TRES)
        parts = jus.split("\n\n")
        base = TRTemplateSlots(
            objeto="Aquisição de materiais de escritório para a administração municipal.",
            justificativa=jus,
            problema_administrativo=parts[1],
            beneficio_esperado=parts[2],
            dispensa=DispensaSlots(artigo="75", inciso="II"),
            dispensa_fluxo_ui="rapida",
            slot_package_key="dispensa_rapida_75_ii_compras",
        )
        slots = _apply_dispensa_secao4_from_prefilled_override(
            base,
            {"dispensa_fluxo_ui": "rapida"},
            None,
        )
        out = render_tr_from_slots(slots, template_path=TPL)
        sec4 = _secao4_paragraphs(out)
        self.assertEqual(len(sec4), 3, msg=f"parágrafos: {sec4}")

    def test_render_normal_tres_paragrafos_no_word(self):
        jus = normalize_justificativa_tres_paragrafos(SAMPLE_TRES)
        parts = jus.split("\n\n")
        slots = TRTemplateSlots(
            objeto="Aquisição de materiais de escritório para a administração municipal.",
            justificativa=jus,
            problema_administrativo=parts[1],
            beneficio_esperado=parts[2],
            dispensa=DispensaSlots(artigo="75", inciso="II"),
            dispensa_fluxo_ui="normal",
        )
        out = render_tr_from_slots(slots, template_path=TPL)
        sec4 = _secao4_paragraphs(out)
        self.assertEqual(len(sec4), 3, msg=f"parágrafos: {sec4}")


if __name__ == "__main__":
    unittest.main()
