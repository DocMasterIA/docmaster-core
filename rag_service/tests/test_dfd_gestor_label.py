"""Rótulos inclusivos no DFD (Gestor de Contratos → Gestor(a) de Contratos)."""

from docx import Document

from app.docx_typography import (
    DFD_INCLUSIVE_ROLE_LABEL_REPLACEMENTS,
    apply_literal_text_replacements_in_document,
)


def test_gestor_de_contratos_replaced_in_paragraph():
    doc = Document()
    p = doc.add_paragraph("Responsável: Gestor de Contratos - Nome")
    apply_literal_text_replacements_in_document(doc, DFD_INCLUSIVE_ROLE_LABEL_REPLACEMENTS)
    assert "Gestor(a) de Contratos" in p.text
    assert "Gestor de Contratos" not in p.text


def test_gestor_split_across_runs():
    doc = Document()
    p = doc.add_paragraph()
    p.add_run("Campo: Gestor de ")
    p.add_run("Contratos")
    apply_literal_text_replacements_in_document(doc, DFD_INCLUSIVE_ROLE_LABEL_REPLACEMENTS)
    assert p.text == "Campo: Gestor(a) de Contratos"


def test_uppercase_label():
    doc = Document()
    p = doc.add_paragraph("GESTOR DE CONTRATOS")
    apply_literal_text_replacements_in_document(doc, DFD_INCLUSIVE_ROLE_LABEL_REPLACEMENTS)
    assert p.text == "GESTOR(A) DE CONTRATOS"
