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

# Parágrafos dissertativos (justificativa, objeto) — não aplicar heurísticas de lista.
_BODY_PROSE_MIN_CHARS = 420
# Inciso I – … em linha curta (§15.1 / listas do TR).
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
    Lista I – …; II – …; III – … no TR (§2.1 manutenção, §15.1 incisos).
    Linhas curtas; não justificar. Não usar menções soltas a «manutenção preventiva/corretiva»
    em texto dissertativo da justificativa.
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


def paragraph_should_remain_left_aligned(text: str) -> bool:
    """Parágrafos de lista/inciso curtos que não devem receber justificação automática."""
    t = (text or "").replace("\r\n", "\n").strip()
    # §15.1 (instrumento de contrato) — sempre exceção, mesmo em parágrafo longo do modelo.
    if paragraph_is_contract_instrument_substitution_block(text):
        return True
    if len(t) >= _BODY_PROSE_MIN_CHARS:
        return False
    return paragraph_is_roman_enumerated_list(text)

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
    Preserva centro/direita/justificado já definidos no .docx; listas romanas curtas e §15.1
    só recebem esquerda quando ainda não tinham alinhamento explícito.
    """
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
            if paragraph_should_remain_left_aligned(p.text or ""):
                if p.alignment is None:
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    pf = p.paragraph_format
                    pf.space_before = Pt(0)
                    pf.space_after = Pt(0)
                    pf.line_spacing = 1.0
                continue
            al = p.alignment
            if al is None:
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    except Exception:
        pass


def apply_default_justify_to_document(doc: Document, *, justify_heading_styles: bool = False) -> None:
    """
    Alinha em justificado o texto corrido sem alinhamento explícito no parágrafo.
    Não sobrescreve justificado/centro/direita já definidos no modelo .docx.
    Listas romanas curtas e o bloco §15.1 só recebem esquerda se ainda não tinham alinhamento.
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
        runs[start_idx].text = txt[:start_off] + replacement + txt[end_off:]
    else:
        prefix = (runs[start_idx].text or "")[:start_off]
        suffix = (runs[end_idx].text or "")[end_off:]
        runs[start_idx].text = prefix + replacement + suffix
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


def _paragraph_has_signature_nome_marker(paragraph: Paragraph) -> bool:
    t = (paragraph.text or "").replace("\u00a0", " ")
    return any(marker in t for marker in SIGNATURE_NOME_MARKERS)


def _paragraph_looks_like_cidade_data_line(paragraph: Paragraph) -> bool:
    t = _paragraph_visible_text(paragraph)
    if not t:
        return False
    if any(marker in (paragraph.text or "") for marker in _CIDADE_DATA_MARKERS):
        return True
    # Pós-substituição: «Cidade - UF, 22 de junho de 2026» ou «Cidade, 22/06/2026»
    if "," in t and re.search(r"\b(19|20)\d{2}\b", t) and len(t) <= 160:
        return True
    return False


def _find_signature_nome_paragraph_index(paragraphs: list[Paragraph]) -> int | None:
    for i, p in enumerate(paragraphs):
        if _paragraph_has_signature_nome_marker(p):
            return i
    # Fallback estrutural (placeholders já substituídos): 1.º parágrafo com texto após cidade/data.
    for i in range(len(paragraphs) - 1, max(-1, len(paragraphs) - 24), -1):
        if not _paragraph_looks_like_cidade_data_line(paragraphs[i]):
            continue
        j = i + 1
        while j < len(paragraphs) and _is_empty_paragraph(paragraphs[j]):
            j += 1
        if j < len(paragraphs) and _paragraph_visible_text(paragraphs[j]):
            return j
        return None
    return None


def _normalize_blank_gap_before_index(
    paragraphs: list[Paragraph],
    nome_idx: int,
    *,
    blank_lines: int,
) -> bool:
    """Garante exatamente `blank_lines` parágrafos vazios antes do nome da assinatura."""
    prev_idx = nome_idx - 1
    while prev_idx >= 0 and _is_empty_paragraph(paragraphs[prev_idx]):
        prev_idx -= 1
    if prev_idx < 0:
        return False

    gap_start = prev_idx + 1
    empty_paras = [paragraphs[j] for j in range(gap_start, nome_idx) if _is_empty_paragraph(paragraphs[j])]
    n_empty = len(empty_paras)

    if n_empty > blank_lines:
        for ep in empty_paras[blank_lines:]:
            _remove_paragraph_element(ep)
        return True

    if n_empty < blank_lines:
        ref = paragraphs[prev_idx]
        for _ in range(blank_lines - n_empty):
            ref = _insert_empty_paragraph_after(ref)
        return True

    return False


def ensure_signature_nome_blank_lines(
    doc: Document,
    *,
    blank_lines: int = _SIGNATURE_NOME_BLANK_LINES_DEFAULT,
) -> None:
    """
    Mantém exatamente N linhas em branco entre o último texto antes da assinatura
    (em geral cidade/data) e o parágrafo do nome do signatário.

    Aplica a (TR_NOME_ASSINANTE_TERMO), (DFD_NOME_ASSINATURA) e (SOL_OFICIO_RESPONSAVEL_NOME)
    em qualquer pacote — evita ajustar cada .docx manualmente quando o corpo cresce.
    """
    if blank_lines < 0:
        return
    changed = True
    guard = 0
    while changed and guard < 8:
        guard += 1
        changed = False
        paras = list(doc.paragraphs)
        nome_idx = _find_signature_nome_paragraph_index(paras)
        if nome_idx is None:
            break
        if _normalize_blank_gap_before_index(paras, nome_idx, blank_lines=blank_lines):
            changed = True
