"""
Tipografia padrão para DOCX gerados pelo serviço (TR, DFD, ofício, JSON→Word).

Modelos e runs criados pelo python-docx podem herdar tema Calibri; forçamos
Times New Roman em estilos comuns e em **cada run** do documento (incl. tabelas
e cabeçalhos/rodapés).
"""
from __future__ import annotations

import re
from typing import Iterator

from docx.document import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.shared import Pt, RGBColor

_ROMAN_ITEM_LINE = re.compile(r"^[IVXLC]+\s*[–—\-]\s*.+", re.MULTILINE)


def paragraph_is_roman_enumerated_list(text: str) -> bool:
    """
    Lista I – …; II – … no TR dispensa manutenção (§2.1).
    Deve permanecer alinhada à esquerda, sem justificação (linhas curtas esticam).
    """
    t = (text or "").replace("\r\n", "\n").strip()
    if not t:
        return False
    if "Manutenção preventiva" in t and "Manutenção corretiva" in t:
        return True
    lines = [ln.strip() for ln in t.split("\n") if ln.strip()]
    if len(lines) < 3:
        return False
    roman = sum(1 for ln in lines if _ROMAN_ITEM_LINE.match(ln))
    return roman >= 3

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


def _clamp_indents_on_p_el(p_el) -> None:
    """
    OOXML: w:ind com w:right ou w:left negativos alarga a caixa de texto para fora da margem
    (ex.: modelo DFD com w:right=\"-144\" na célula do objeto).
    """
    try:
        pPr = p_el.find(qn("w:pPr"))
        if pPr is None:
            return
        ind = pPr.find(qn("w:ind"))
        if ind is None:
            return
        for attr in ("right", "left", "start", "end"):
            key = qn(f"w:{attr}")
            raw = ind.get(key)
            if raw is None:
                continue
            try:
                n = int(raw)
            except (TypeError, ValueError):
                continue
            if n < 0:
                ind.set(key, "0")
    except Exception:
        pass


def _clamp_indents_on_container(container) -> None:
    if container is None:
        return
    try:
        for p in _iter_paragraphs_deep(container):
            _clamp_indents_on_p_el(p._element)
    except Exception:
        pass


def clamp_docx_paragraph_indents(doc: Document) -> None:
    """
    Percorre corpo, tabelas e cabeçalhos/rodapés e zera indentações negativas que fazem texto
    transbordar para fora da área imprimível (margens).
    """
    _clamp_indents_on_container(doc)
    for section in doc.sections:
        _clamp_indents_on_container(section.header)
        _clamp_indents_on_container(section.footer)
        try:
            if section.different_first_page_header_footer:
                _clamp_indents_on_container(section.first_page_header)
                _clamp_indents_on_container(section.first_page_footer)
        except Exception:
            pass
        try:
            _clamp_indents_on_container(section.even_page_header)
            _clamp_indents_on_container(section.even_page_footer)
        except Exception:
            pass


def _apply_font_to_header_footer_part(part) -> None:
    if part is None:
        return
    try:
        for p in _iter_paragraphs_deep(part):
            for run in p.runs:
                set_run_standard_body_font(run)
    except Exception:
        pass


def _justify_paragraphs_in_container(container, *, justify_heading_styles: bool) -> None:
    """Justifica parágrafos alinhados à esquerda (ou sem alinhamento explícito); preserva centro/direita."""
    if container is None:
        return
    try:
        for p in _iter_paragraphs_deep(container):
            if not justify_heading_styles:
                try:
                    sn = (p.style and p.style.name) or ""
                    if sn.startswith("Heading"):
                        continue
                except Exception:
                    pass
            if paragraph_is_roman_enumerated_list(p.text or ""):
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                pf = p.paragraph_format
                pf.space_before = Pt(0)
                pf.space_after = Pt(0)
                pf.line_spacing = 1.0
                continue
            al = p.alignment
            if al in (None, WD_ALIGN_PARAGRAPH.LEFT):
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    except Exception:
        pass


def apply_default_justify_to_document(doc: Document, *, justify_heading_styles: bool = False) -> None:
    """
    Alinha em justificado o texto corrido (blocos que estavam à esquerda).
    Mantém CENTRO e DIREITA (títulos, algumas células de tabela).
    Por omissão não altera estilos «Heading N» (títulos gerados por add_heading no JSON→DOCX).
    """
    _justify_paragraphs_in_container(doc, justify_heading_styles=justify_heading_styles)
    for section in doc.sections:
        _justify_paragraphs_in_container(section.header, justify_heading_styles=justify_heading_styles)
        _justify_paragraphs_in_container(section.footer, justify_heading_styles=justify_heading_styles)
        try:
            if section.different_first_page_header_footer:
                _justify_paragraphs_in_container(
                    section.first_page_header, justify_heading_styles=justify_heading_styles
                )
                _justify_paragraphs_in_container(
                    section.first_page_footer, justify_heading_styles=justify_heading_styles
                )
        except Exception:
            pass
        try:
            _justify_paragraphs_in_container(section.even_page_header, justify_heading_styles=justify_heading_styles)
            _justify_paragraphs_in_container(section.even_page_footer, justify_heading_styles=justify_heading_styles)
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
