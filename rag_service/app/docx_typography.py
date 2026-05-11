"""
Tipografia padrão para DOCX gerados pelo serviço (TR, DFD, ofício, JSON→Word).

Modelos e runs criados pelo python-docx podem herdar tema Calibri; forçamos
Times New Roman em estilos comuns e em **cada run** do documento (incl. tabelas
e cabeçalhos/rodapés).
"""
from __future__ import annotations

from typing import Iterator

from docx.document import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.shared import RGBColor

STANDARD_BODY_FONT = "Times New Roman"
STANDARD_FONT_COLOR = RGBColor(0, 0, 0)

_DOCUMENT_STYLE_NAMES = (
    "Normal",
    "Title",
    "Heading 1",
    "Heading 2",
    "Heading 3",
    "List Paragraph",
    "List Bullet",
    "Quote",
    "Intense Quote",
)


def set_run_standard_body_font(run) -> None:
    """Força Times New Roman no run (ascii/hAnsi no OOXML — evita Calibri do tema)."""
    name = STANDARD_BODY_FONT
    run.font.name = name
    try:
        run.font.color.rgb = STANDARD_FONT_COLOR
    except Exception:
        pass
    try:
        rPr = run._element.get_or_add_rPr()
        rFonts = rPr.get_or_add_rFonts()
        rFonts.ascii = name
        rFonts.hAnsi = name
    except Exception:
        pass


def _iter_paragraphs_deep(container) -> Iterator[Paragraph]:
    """Parágrafos no corpo de `container` e dentro de tabelas (células podem ter tabelas aninhadas)."""
    if container is None:
        return
    for item in container.iter_inner_content():
        if isinstance(item, Paragraph):
            yield item
        elif isinstance(item, Table):
            for row in item.rows:
                for cell in row.cells:
                    yield from _iter_paragraphs_deep(cell)


def _apply_font_to_header_footer_part(part) -> None:
    if part is None:
        return
    try:
        for p in _iter_paragraphs_deep(part):
            for run in p.runs:
                set_run_standard_body_font(run)
    except Exception:
        pass


def apply_standard_body_font_to_document(doc: Document) -> None:
    """
    1) Ajusta estilos built-in usados na geração.
    2) Percorre todos os runs do corpo, tabelas, cabeçalhos e rodapés e aplica a fonte.
    """
    for style_name in _DOCUMENT_STYLE_NAMES:
        try:
            st = doc.styles[style_name]
            st.font.name = STANDARD_BODY_FONT
            try:
                st.font.color.rgb = STANDARD_FONT_COLOR
            except Exception:
                pass
        except KeyError:
            pass

    for p in _iter_paragraphs_deep(doc):
        for run in p.runs:
            set_run_standard_body_font(run)

    for section in doc.sections:
        _apply_font_to_header_footer_part(section.header)
        _apply_font_to_header_footer_part(section.footer)
        try:
            if section.different_first_page_header_footer:
                _apply_font_to_header_footer_part(section.first_page_header)
                _apply_font_to_header_footer_part(section.first_page_footer)
        except Exception:
            pass
        try:
            _apply_font_to_header_footer_part(section.even_page_header)
            _apply_font_to_header_footer_part(section.even_page_footer)
        except Exception:
            pass
