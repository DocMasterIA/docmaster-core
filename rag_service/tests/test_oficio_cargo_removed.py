"""Ofício: cargos ativos do destinatário vs cargos descontinuados em outras seções."""

from __future__ import annotations

from pathlib import Path

from docx import Document

from app.oficio_template import render_oficio_from_slots
from app.tr_template import TRTemplateSlots

TEMPLATE = (
    Path(__file__).resolve().parents[2]
    / "template_packages"
    / "lei_14133"
    / "dispensa_75_ii_compras"
    / "OFICIO_modelo_base.docx"
)


def _body_text(doc: Document) -> str:
    parts = []
    for p in doc.paragraphs:
        t = (p.text or "").strip()
        if t:
            parts.append(t)
    return "\n".join(parts)


def test_oficio_includes_destinatario_cargo_and_senhor_senhora(tmp_path):
    assert TEMPLATE.is_file(), f"Template ausente: {TEMPLATE}"
    slots = TRTemplateSlots(
        ao_senhor_genero="Ao senhor",
        sol_oficio_destinatario_nome="João Destinatário",
        sol_oficio_destinatario_cargo="Secretário Municipal",
        senhor_senhora_genero="Senhor",
        sol_oficio_responsavel_nome="Maria Responsável",
        cidade="Curitiba",
        data_termo="01/01/2026",
        objeto="Material de expediente",
        sol_oficio_artigo_inciso="Art. 75, Inciso II",
    )

    out = tmp_path / "oficio_com_cargo_destinatario.docx"
    render_oficio_from_slots(slots, template_path=TEMPLATE, output_path=out)

    doc = Document(str(out))
    body = _body_text(doc)
    assert "João Destinatário" in body
    assert "Secretário Municipal" in body
    assert "Senhor" in body


def test_oficio_omits_other_deprecated_cargos_and_orphan_commas(tmp_path):
    assert TEMPLATE.is_file(), f"Template ausente: {TEMPLATE}"
    slots = TRTemplateSlots(
        ao_senhor_genero="Ao senhor",
        sol_oficio_destinatario_nome="João Destinatário",
        sol_oficio_destinatario_cargo="Secretário Municipal",
        sol_oficio_responsavel_nome="Maria Responsável",
        sol_oficio_responsavel_cargo="Coordenadora",
        senhor_senhora_genero="Senhor",
        secretaria_usuario="Secretaria Fantasma",
        cidade="Curitiba",
        data_termo="01/01/2026",
        objeto="Material de expediente",
        sol_oficio_artigo_inciso="Art. 75, Inciso II",
    )

    out = tmp_path / "oficio_sem_cargo_responsavel.docx"
    render_oficio_from_slots(slots, template_path=TEMPLATE, output_path=out)

    doc = Document(str(out))
    body = _body_text(doc)
    assert "Secretário Municipal" in body
    assert "Coordenadora" not in body
    assert "Secretaria Fantasma" not in body

    for p in doc.paragraphs:
        t = (p.text or "").replace("\u00a0", " ").strip()
        assert t != ",", f"parágrafo só com vírgula órfã: {p.text!r}"
