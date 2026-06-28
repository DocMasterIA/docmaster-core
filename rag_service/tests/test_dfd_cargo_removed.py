"""DFD não deve exibir linha de cargo/função quando o slot foi descontinuado."""

from __future__ import annotations

from pathlib import Path

from docx import Document

from rag_service.app.deprecated_cargo_slots import clear_deprecated_cargo_fields
from rag_service.app.dfd_template import render_dfd_from_tr_slots
from rag_service.app.tr_template import TRTemplateSlots

TEMPLATE = (
    Path(__file__).resolve().parents[2]
    / "template_packages"
    / "lei_14133"
    / "dispensa_75_ii_compras"
    / "DFD_modelo_base.docx"
)


def _body_text(doc: Document) -> str:
    parts = []
    for p in doc.paragraphs:
        t = (p.text or "").strip()
        if t:
            parts.append(t)
    return "\n".join(parts)


def test_dfd_omits_cargo_line_when_slot_empty(tmp_path):
    assert TEMPLATE.is_file(), f"Template ausente: {TEMPLATE}"
    slots = clear_deprecated_cargo_fields(
        TRTemplateSlots(
            objeto="Aquisição de material de expediente.",
            justificativa="Necessidade administrativa.",
            cidade="Curitiba",
            dfd_assinatura_nome="Maria Silva",
            dfd_assinatura_cargo="Secretária Municipal",
            dfd_setor_requisitante="Secretaria de Administração",
            dfd_responsavel_demanda="João Souza",
            dfd_email="compras@prefeitura.gov.br",
            dfd_gestor_contratos="Ana Gestora",
            dfd_fiscal_contratos="Carlos Fiscal",
            data_termo="01/01/2026",
        )
    )
    assert not slots.dfd_assinatura_cargo

    out = tmp_path / "dfd_sem_cargo.docx"
    render_dfd_from_tr_slots(slots, template_path=TEMPLATE, output_path=out)

    doc = Document(str(out))
    body = _body_text(doc)
    assert "Maria Silva" in body
    assert "Secretária Municipal" not in body
    # Não deve sobrar parágrafo vazio extra entre nome e fim (assinatura compacta).
    empty_after_nome = False
    seen_nome = False
    for p in doc.paragraphs:
        t = (p.text or "").replace("\u00a0", " ").strip()
        if "Maria Silva" in t:
            seen_nome = True
            continue
        if seen_nome and not t:
            empty_after_nome = True
            break
    assert not empty_after_nome
