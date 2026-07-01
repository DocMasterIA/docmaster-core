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
_ROMAN_ITEM_LINE_START = re.compile(r"^\s*[IVXLC]+\s*[–—\-]\s*.+")

# Inciso I – … em linha curta (heurística auxiliar).
_SHORT_ROMAN_LINE_MAX_CHARS = 280


def paragraph_is_roman_item_line(text: str) -> bool:
    """Um inciso I – … / II – … em parágrafo próprio (comum no §15.1 e listas do TR)."""
    t = (text or "").replace("\r\n", "\n").strip()
    if not t:
        return False
    return bool(_ROMAN_ITEM_LINE_START.match(t))


def paragraph_is_short_roman_item_line(text: str) -> bool:
    """Inciso romano em linha curta — não confundir com justificativa/objeto longos."""
    t = (text or "").replace("\r\n", "\n").strip()
    if not t or len(t) > _SHORT_ROMAN_LINE_MAX_CHARS:
        return False
    return bool(_ROMAN_ITEM_LINE_START.match(t))


def paragraph_is_roman_enumerated_list(text: str) -> bool:
    """
    Lista I – …; II – …; III – … em um único parágrafo (ex.: §2.1 manutenção).
    Usado para não dividir blocos em split_paragraphs_on_double_newline — não força alinhamento.
    """
    t = (text or "").replace("\r\n", "\n").strip()
    if not t:
        return False
    if paragraph_is_short_roman_item_line(t):
        return True
    lines = [ln.strip() for ln in t.split("\n") if ln.strip()]
    if len(lines) < 3:
        return False
    roman = sum(1 for ln in lines if _ROMAN_ITEM_LINE.match(ln))
    return roman >= 3


def paragraph_is_contract_instrument_substitution_block(text: str) -> bool:
    """
    §15.1 (e equivalentes): instrumento de contrato / carta-contrato / nota de empenho.
    No modelo .docx costuma vir alinhado à esquerda; não justificar.
    """
    t = (text or "").replace("\r\n", "\n").strip()
    if not t:
        return False
    tl = t.lower()
    if "instrumento de contrato" in tl and (
        "carta-contrato" in tl
        or "nota de empenho" in tl
        or "substituído por instrumento equivalente" in tl
        or "substituido por instrumento equivalente" in tl
    ):
        return True
    if re.search(r"^\s*15\s*\.\s*1\s*\.", t, re.IGNORECASE) and "instrumento" in tl:
        return True
    if re.search(r"^\s*13\s*\.\s*1\s*\.", t, re.IGNORECASE) and "instrumento" in tl:
        return True
    tail = tl.rstrip(":")
    if tail.endswith("nos casos de"):
        return True
    return False


def paragraph_is_tr_numbered_subsection_prose(text: str) -> bool:
    """
    Subitens dissertativos do TR (ex.: «6.1. A formalização…», «6.2. Quando formalizada…»).
    Devem ficar justificados mesmo que o .docx traga w:jc left por engano no modelo.
    """
    t = (text or "").replace("\r\n", "\n").strip()
    if not t or len(t) < 80:
        return False
    if not re.match(r"^\d+\.\d+\.\s+\S", t):
        return False
    if paragraph_is_contract_instrument_substitution_block(text):
        return False
    if paragraph_is_short_roman_item_line(t):
        return False
    if paragraph_is_roman_enumerated_list(text):
        return False
    return True


def paragraph_should_remain_left_aligned(text: str) -> bool:
    """Parágrafos que devem permanecer à esquerda (cabeçalho processo, bloco §15.1 intro)."""
    t = (text or "").replace("\r\n", "\n").strip()
    # Cabeçalho do TR: «PROCESSO: 123/2026» (estilo Heading 1 no modelo — não centralizar).
    if t.upper().startswith("PROCESSO:"):
        return True
    if re.search(r"\(\s*NUMERO[\s_]*PROCESSO\s*\)", t, re.I):
        return True
    # §15.1 (instrumento de contrato) — intro «nos casos de:», não os incisos I/II/III.
    if paragraph_is_contract_instrument_substitution_block(text):
        return True
    return False

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
    """
    Justifica parágrafos sem alinhamento explícito (None).
    Preserva centro/direita/justificado já definidos no .docx.
    §15.1 intro e cabeçalho PROCESSO permanecem à esquerda; incisos romanos (I –, II –) seguem o modelo.
    """
    if container is None:
        return
    try:
        for p in _iter_paragraphs_deep(container):
            if paragraph_is_tr_numbered_subsection_prose(p.text or ""):
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                continue
            if paragraph_should_remain_left_aligned(p.text or ""):
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                pf = p.paragraph_format
                pf.space_before = Pt(0)
                pf.space_after = Pt(0)
                pf.line_spacing = 1.0
                continue
            if not justify_heading_styles:
                try:
                    sn = (p.style and p.style.name) or ""
                    if sn.startswith("Heading"):
                        continue
                except Exception:
                    pass
            al = p.alignment
            if al is None:
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    except Exception:
        pass


def apply_default_justify_to_document(doc: Document, *, justify_heading_styles: bool = False) -> None:
    """
    Alinha em justificado o texto corrido sem alinhamento explícito no parágrafo.
    Não sobrescreve justificado/centro/direita já definidos no modelo .docx.
    Listas romanas (I –, II –) e §15.1 intro: não forçar esquerda nos incisos; justificar quando o modelo não define alinhamento.
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


# Rótulos fixos nos modelos DFD (não são placeholders).
DFD_INCLUSIVE_ROLE_LABEL_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("Gestor de Contratos", "Gestor(a) de Contratos"),
    ("GESTOR DE CONTRATOS", "GESTOR(A) DE CONTRATOS"),
    ("Gestor Contratos", "Gestor(a) de Contratos"),
)


def _replace_substring_in_paragraph_runs(paragraph, needle: str, replacement: str) -> bool:
    """Substitui `needle` em um parágrafo mesmo quando o texto está dividido em vários runs."""
    from .tr_template import _append_multiline_to_run

    runs = paragraph.runs
    if not runs or not needle:
        return False
    full_text = "".join(run.text or "" for run in runs)
    start = full_text.find(needle)
    if start < 0:
        return False
    end = start + len(needle)

    cursor = 0
    start_idx = start_off = end_idx = end_off = None
    for idx, run in enumerate(runs):
        txt = run.text or ""
        next_cursor = cursor + len(txt)
        if start_idx is None and start < next_cursor:
            start_idx = idx
            start_off = start - cursor
        if end_idx is None and end <= next_cursor:
            end_idx = idx
            end_off = end - cursor
            break
        cursor = next_cursor

    if start_idx is None or end_idx is None or start_off is None or end_off is None:
        return False

    if start_idx == end_idx:
        txt = runs[start_idx].text or ""
        before = txt[:start_off]
        after = txt[end_off:]
        run = runs[start_idx]
        run.text = before
        if "\n" in replacement:
            _append_multiline_to_run(run, replacement)
            if after:
                run.add_text(after)
        else:
            run.text = before + replacement + after
    else:
        prefix = (runs[start_idx].text or "")[:start_off]
        suffix = (runs[end_idx].text or "")[end_off:]
        run = runs[start_idx]
        run.text = prefix
        if "\n" in replacement:
            _append_multiline_to_run(run, replacement)
            if suffix:
                run.add_text(suffix)
        else:
            run.text = prefix + replacement + suffix
        for idx in range(start_idx + 1, end_idx + 1):
            runs[idx].text = ""
    return True


def apply_literal_text_replacements_in_document(
    doc: Document,
    replacements: tuple[tuple[str, str], ...] | list[tuple[str, str]],
) -> None:
    """Aplica substituições literais em parágrafos do corpo e tabelas (preserva formatação por run)."""
    for paragraph in _iter_paragraphs_deep(doc):
        for needle, repl in replacements:
            max_iters = 20
            while max_iters > 0 and _replace_substring_in_paragraph_runs(paragraph, needle, repl):
                max_iters -= 1
                if needle and needle in repl:
                    break


def apply_dfd_inclusive_role_labels(doc: Document) -> None:
    """Normaliza rótulos de cargo no DFD (ex.: Gestor de Contratos → Gestor(a) de Contratos)."""
    apply_literal_text_replacements_in_document(doc, DFD_INCLUSIVE_ROLE_LABEL_REPLACEMENTS)


# --- Espaçamento da assinatura (TR / DFD / Ofício) ---------------------------------

SIGNATURE_NOME_MARKERS: tuple[str, ...] = (
    "(TR_NOME_ASSINANTE_TERMO)",
    "(NOME DO ASSINANTE DO TERMO)",
    "(DFD_NOME_ASSINATURA)",
    "(NOME ASSINATURA DFD)",
    "(SOL_OFICIO_RESPONSAVEL_NOME)",
)

_CIDADE_DATA_MARKERS: tuple[str, ...] = (
    "(TR_CIDADE)",
    "(DFD_CIDADE)",
    "(SOL_OFICIO_CIDADE)",
    "(TR_DATA_TERMO)",
    "(DFD_DATA)",
    "(SOL_OFICIO_DATA)",
)

_SIGNATURE_NOME_BLANK_LINES_DEFAULT = 3


def _paragraph_visible_text(paragraph: Paragraph) -> str:
    return (paragraph.text or "").replace("\u00a0", " ").strip()


def _is_empty_paragraph(paragraph: Paragraph) -> bool:
    return not _paragraph_visible_text(paragraph)


def _remove_paragraph_element(paragraph: Paragraph) -> None:
    el = paragraph._element
    parent = el.getparent()
    if parent is not None:
        parent.remove(el)


def _insert_empty_paragraph_after(ref_para: Paragraph) -> Paragraph:
    from docx.oxml import OxmlElement

    new_p = OxmlElement("w:p")
    ref_para._p.addnext(new_p)
    return Paragraph(new_p, ref_para._parent)


def _insert_empty_paragraph_before(ref_para: Paragraph) -> Paragraph:
    from docx.oxml import OxmlElement

    new_p = OxmlElement("w:p")
    ref_para._p.addprevious(new_p)
    return Paragraph(new_p, ref_para._parent)


def _is_removable_gap_paragraph(paragraph: Paragraph) -> bool:
    """Parágrafo vazio (ou só pontuação) entre cidade/data e nome — não é conteúdo."""
    if _is_empty_paragraph(paragraph):
        return True
    t = _paragraph_visible_text(paragraph)
    return bool(t) and not re.search(r"\w", t, re.UNICODE)


def _paragraph_has_signature_nome_marker(paragraph: Paragraph) -> bool:
    t = (paragraph.text or "").replace("\u00a0", " ")
    return any(marker in t for marker in SIGNATURE_NOME_MARKERS)


def _paragraph_looks_like_cidade_data_line(paragraph: Paragraph) -> bool:
    t = _paragraph_visible_text(paragraph)
    if not t:
        return False
    raw = paragraph.text or ""
    if any(marker in raw for marker in _CIDADE_DATA_MARKERS):
        return True
    tl = t.lower()
    if "datado e assinado digitalmente" in tl:
        return True
    # «Cidade - UF, 22 de junho de 2026» ou «Cidade, 22/06/2026»
    if "," in t and re.search(r"\b(19|20)\d{2}\b", t) and len(t) <= 160:
        return True
    # «Cidade - UF, datado e assinado digitalmente»
    if re.search(r"\s-\s*[A-Z]{2}\s*,", t) and "," in t and len(t) <= 160:
        return True
    # «Cidade, » ou «Cidade - UF, » após preenchimento (data opcional / vazia).
    if t.rstrip().endswith(",") and len(t) <= 100 and re.search(r"[A-Za-zÀ-ú]", t):
        return True
    return False


def _find_signature_anchor_structural(paragraphs: list[Paragraph]) -> Paragraph | None:
    """Linha cidade/data no final do documento (varre só o rodapé)."""
    for i in range(len(paragraphs) - 1, max(-1, len(paragraphs) - 28), -1):
        if _paragraph_looks_like_cidade_data_line(paragraphs[i]):
            return paragraphs[i]
    return None


def _find_signature_nome_paragraph(paragraphs: list[Paragraph]) -> Paragraph | None:
    for p in paragraphs:
        if _paragraph_has_signature_nome_marker(p):
            return p
    anchor = _find_signature_anchor_structural(paragraphs)
    if anchor is None:
        return None
    try:
        anchor_idx = paragraphs.index(anchor)
    except ValueError:
        return None
    j = anchor_idx + 1
    while j < len(paragraphs) and _is_removable_gap_paragraph(paragraphs[j]):
        j += 1
    if j < len(paragraphs) and _paragraph_visible_text(paragraphs[j]):
        return paragraphs[j]
    return None


def _find_signature_anchor_paragraph(paragraphs: list[Paragraph], nome_para: Paragraph) -> Paragraph | None:
    """
    Âncora = parágrafo com texto imediatamente antes do bloco de linhas vazias
  que precede o nome (em geral cidade/data).
    """
    try:
        nome_idx = paragraphs.index(nome_para)
    except ValueError:
        return None

    prev_idx = nome_idx - 1
    while prev_idx >= 0 and _is_removable_gap_paragraph(paragraphs[prev_idx]):
        prev_idx -= 1
    if prev_idx >= 0:
        return paragraphs[prev_idx]

    return _find_signature_anchor_structural(paragraphs)


def _remove_gap_paragraphs_between(anchor_para: Paragraph, nome_para: Paragraph) -> int:
    """Remove todos os parágrafos entre a âncora (cidade/data) e o nome — retorna quantos removeu."""
    removed = 0
    anchor_el = anchor_para._p
    nome_el = nome_para._p
    if anchor_el.getparent() is not nome_el.getparent():
        return 0

    el = anchor_el.getnext()
    while el is not None and el is not nome_el:
        nxt = el.getnext()
        if el.tag == qn("w:p"):
            gap_p = Paragraph(el, anchor_para._parent)
            if _is_removable_gap_paragraph(gap_p):
                parent = el.getparent()
                if parent is not None:
                    parent.remove(el)
                    removed += 1
            else:
                break
        el = nxt
    return removed


def _set_signature_gap_paragraph_spacing(paragraph: Paragraph) -> None:
    """Evita «linhas fantasma» via space_before/space_after no Word."""
    pf = paragraph.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.line_spacing = 1.0


def _normalize_signature_blank_gap(
    anchor_para: Paragraph,
    nome_para: Paragraph,
    *,
    blank_lines: int,
) -> bool:
    """
    Zera o intervalo entre cidade/data e nome e recria com exatamente N parágrafos vazios.
    Não soma em cima dos vazios já existentes no .docx.
    """
    if blank_lines < 0:
        return False
    if anchor_para._p is nome_para._p:
        return False

    changed = _remove_gap_paragraphs_between(anchor_para, nome_para) > 0

    for _ in range(blank_lines):
        inserted = _insert_empty_paragraph_before(nome_para)
        _set_signature_gap_paragraph_spacing(inserted)
        changed = True

    _set_signature_gap_paragraph_spacing(anchor_para)
    _set_signature_gap_paragraph_spacing(nome_para)
    return changed


def ensure_signature_nome_blank_lines(
    doc: Document,
    *,
    blank_lines: int = _SIGNATURE_NOME_BLANK_LINES_DEFAULT,
) -> None:
    """
    Exatamente N parágrafos vazios entre a linha cidade/data e o nome do signatário.

    Remove qualquer vazio já existente nesse intervalo antes de inserir os N — evita
    2 no modelo + 3 do código = 5 linhas.
    """
    if blank_lines < 0:
        return
    paras = list(doc.paragraphs)
    nome_para = _find_signature_nome_paragraph(paras)
    if nome_para is None:
        return
    anchor_para = _find_signature_anchor_paragraph(paras, nome_para)
    if anchor_para is None:
        return
    _normalize_signature_blank_gap(anchor_para, nome_para, blank_lines=blank_lines)
