"""
Substituição de placeholders em DOCX preservando o w:rPr do modelo (tamanho, negrito,
itálico, fonte), evitando que `paragraph.text =` / `cell.text =` recriem runs com
estilo padrão do Word (fontes enormes ou inconsistentes).
"""

from __future__ import annotations

from copy import deepcopy
from typing import Dict

from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph


def _first_non_empty_rpr(paragraph: Paragraph):
    """Primeiro w:rPr encontrado nos runs do parágrafo (cópia profunda para reuso)."""
    for run in paragraph.runs:
        el = run._element
        r_pr = el.find(qn("w:rPr"))
        if r_pr is not None:
            return deepcopy(r_pr)
    return None


def _strip_and_apply_rpr(paragraph: Paragraph, r_pr_clone) -> None:
    if r_pr_clone is None:
        return
    for run in paragraph.runs:
        r_el = run._element
        old = r_el.find(qn("w:rPr"))
        if old is not None:
            r_el.remove(old)
        r_el.insert(0, deepcopy(r_pr_clone))


def _apply_style_font_when_no_rpr(paragraph: Paragraph) -> None:
    """Se não há rPr no modelo, replica fonte explícita do estilo do parágrafo nos runs."""
    if not paragraph.runs:
        return
    try:
        stf = paragraph.style.font
        for run in paragraph.runs:
            if stf.size is not None:
                run.font.size = stf.size
            if stf.name is not None:
                run.font.name = stf.name
            if stf.bold is not None:
                run.font.bold = stf.bold
            if stf.italic is not None:
                run.font.italic = stf.italic
    except Exception:
        pass


def replace_text_in_paragraph_preserving_rpr(paragraph: Paragraph, mapping: Dict[str, str]) -> bool:
    """
    Substitui placeholders no texto do parágrafo e reaplica o primeiro w:rPr existente
    a todos os runs resultantes.
    """
    text = paragraph.text or ""
    if not text:
        return False
    new_text = text
    for ph, val in mapping.items():
        if ph in new_text:
            new_text = new_text.replace(ph, val)
    if new_text == text:
        return False
    ref_rpr = _first_non_empty_rpr(paragraph)
    paragraph.text = new_text
    if ref_rpr is not None:
        _strip_and_apply_rpr(paragraph, ref_rpr)
    else:
        _apply_style_font_when_no_rpr(paragraph)
    return True


def replace_placeholders_in_document(doc: Document, mapping: Dict[str, str]) -> None:
    """Parágrafos do corpo, tabelas, cabeçalhos e rodapés."""
    for p in doc.paragraphs:
        replace_text_in_paragraph_preserving_rpr(p, mapping)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                _replace_placeholders_in_cell(cell, mapping)

    for section in doc.sections:
        header = section.header
        if header:
            for p in header.paragraphs:
                replace_text_in_paragraph_preserving_rpr(p, mapping)
            for table in header.tables:
                for row in table.rows:
                    for cell in row.cells:
                        _replace_placeholders_in_cell(cell, mapping)
        footer = section.footer
        if footer:
            for p in footer.paragraphs:
                replace_text_in_paragraph_preserving_rpr(p, mapping)
            for table in footer.tables:
                for row in table.rows:
                    for cell in row.cells:
                        _replace_placeholders_in_cell(cell, mapping)


def _replace_placeholders_in_cell(cell, mapping: Dict[str, str]) -> None:
    text = cell.text or ""
    if not text:
        return
    new_text = text
    changed = False
    for ph, val in mapping.items():
        if ph in new_text:
            new_text = new_text.replace(ph, val)
            changed = True
    if not changed or new_text == text:
        return
    ref_rpr = None
    for para in cell.paragraphs:
        ref_rpr = _first_non_empty_rpr(para)
        if ref_rpr is not None:
            break
    cell.text = new_text
    if ref_rpr is not None:
        for para in cell.paragraphs:
            _strip_and_apply_rpr(para, ref_rpr)
    else:
        for para in cell.paragraphs:
            _apply_style_font_when_no_rpr(para)
