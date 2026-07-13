from __future__ import annotations

import re
import uuid
from copy import deepcopy
from datetime import date, datetime

"""
Geração de Termo de Referência a partir do modelo fixo
`template_packages/tr_base/TR_modelo_base.docx`, preenchendo apenas os slots
marcados entre parênteses.

Este módulo NÃO chama IA – ele só aplica um dicionário de slots em cima
do template. Quem monta os slots (usuário ou LLM) é outra camada.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.table import Table as DocxTable
from docx.text.paragraph import Paragraph

from .docx_typography import (
    apply_default_justify_to_document,
    apply_standard_body_font_to_document,
    ensure_signature_nome_blank_lines,
    paragraph_is_roman_enumerated_list,
)
from .justificativa_clause_sanitize import finalize_rapida_secao4_tres_blocos

TR_ITEMS_TABLE_ANCHOR = "(TR_TABELA_ITENS)"


_MESES_PT_BR = (
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)


def format_date_pt_br_extenso(value: Any) -> str:
    """
    Converte datas numéricas para «29 de maio de 2026».
    Mantém texto original quando não reconhecer um formato de data.
    """
    raw = str(value or "").strip()
    if not raw:
        return ""

    parsed: Optional[date] = None

    try:
        if "T" in raw:
            parsed = datetime.fromisoformat(raw).date()
        else:
            parsed = datetime.fromisoformat(raw).date()
    except ValueError:
        parsed = None

    if parsed is None:
        m = re.fullmatch(r"(\d{1,4})[/-](\d{1,2})[/-](\d{1,4})", raw)
        if m:
            a, b, c = (int(x) for x in m.groups())
            year = month = day = 0
            if a >= 1000:
                year, month, day = a, b, c
            elif c >= 1000:
                year = c
                # Aceita dd/mm e mm/dd. Quando ambíguo (<=12), prioriza dd/mm.
                if a > 12 and b <= 12:
                    day, month = a, b
                elif b > 12 and a <= 12:
                    day, month = b, a
                else:
                    day, month = a, b
            try:
                parsed = date(year, month, day)
            except ValueError:
                parsed = None

    if parsed is None:
        return raw

    mes = _MESES_PT_BR[parsed.month - 1]
    return f"{parsed.day} de {mes} de {parsed.year}"


def _valor_total_sem_rs(valor: str) -> str:
    """Texto para placeholders ( VALOR_TOTAL ): modelo costuma já incluir 'R$' no rótulo."""
    s = str(valor or "").strip()
    return re.sub(r"(?i)^\s*R\$\s*", "", s).strip()


def slots_numero_processo_display(slots: TRTemplateSlots) -> str:
    """
    Número de processo para exibição nos documentos (TR, DFD, ofício).
    Mesma ordem que o DFD: `dfd_numero_processo`, com fallback a `numero_processo`.
    """
    return (
        str(getattr(slots, "dfd_numero_processo", "") or "").strip()
        or str(getattr(slots, "numero_processo", "") or "").strip()
    )


def numero_processo_valor_placeholder_tr(raw: str) -> str:
    """Substituição de `( NUMERO_PROCESSO )` no modelo: «PROCESSO: <número>» ou vazio."""
    s = str(raw or "").strip()
    if not s:
        return ""
    return f"PROCESSO: {s}"


_NUMERO_PROCESSO_PLACEHOLDER_RE = re.compile(
    r"^\(\s*(?:DFD_)?NUMERO[\s_]PROCESSO\s*\)$",
    re.IGNORECASE,
)


def is_numero_processo_placeholder(placeholder: str) -> bool:
    """True para `(NUMERO_PROCESSO)`, `( NUMERO PROCESSO )`, `(DFD_NUMERO_PROCESSO)`, etc."""
    return bool(_NUMERO_PROCESSO_PLACEHOLDER_RE.match(str(placeholder or "").strip()))


def numero_processo_bold_targets(num_proc: str) -> list[str]:
    """Textos a destacar em negrito no TR após substituir `(NUMERO_PROCESSO)`."""
    s = str(num_proc or "").strip()
    if not s:
        return []
    targets: list[str] = []
    tr_style = numero_processo_valor_placeholder_tr(s)
    if tr_style:
        targets.append(tr_style)
    if s not in targets:
        targets.append(s)
    return targets


def _insert_run_after(reference_run, text: str):
    from docx.text.run import Run

    new_r = OxmlElement("w:r")
    reference_run._element.addnext(new_r)
    new_run = Run(new_r, reference_run._parent)
    new_run.text = text
    return new_run


def _bold_char_range_in_paragraph(paragraph: Paragraph, start: int, end: int) -> None:
    """Aplica negrito ao intervalo [start, end) em paragraph.text (índices UTF-16-like / Python str)."""
    if start >= end:
        return
    cursor = 0
    idx = 0
    while idx < len(paragraph.runs):
        run = paragraph.runs[idx]
        txt = run.text or ""
        run_start = cursor
        run_end = cursor + len(txt)
        cursor = run_end
        if run_end <= start or run_start >= end:
            idx += 1
            continue
        local_start = max(0, start - run_start)
        local_end = min(len(txt), end - run_start)
        if local_start == 0 and local_end == len(txt):
            run.bold = True
            idx += 1
            continue
        before = txt[:local_start]
        middle = txt[local_start:local_end]
        after = txt[local_end:]
        font_ref = run
        run.text = before
        prev = run
        if middle:
            mid_run = _insert_run_after(prev, middle)
            _copy_run_font(font_ref, mid_run)
            mid_run.bold = True
            prev = mid_run
        if after:
            aft_run = _insert_run_after(prev, after)
            _copy_run_font(font_ref, aft_run)
        idx += 1


def _bold_substring_in_paragraph(paragraph: Paragraph, needle: str) -> bool:
    if not needle:
        return False
    hay = paragraph.text or ""
    pos = hay.find(needle)
    if pos < 0:
        return False
    _bold_char_range_in_paragraph(paragraph, pos, pos + len(needle))
    return True


def _apply_numero_processo_bold_to_paragraph(paragraph: Paragraph, num_proc: str) -> None:
    for needle in numero_processo_bold_targets(num_proc):
        if _bold_substring_in_paragraph(paragraph, needle):
            return


def apply_numero_processo_bold_to_document(doc: Document, num_proc: str) -> None:
    """Garante negrito no número de processo do TR mesmo quando o modelo .docx não formata o placeholder."""
    if not str(num_proc or "").strip():
        return
    for p in _iter_all_document_paragraphs(doc):
        _apply_numero_processo_bold_to_paragraph(p, num_proc)


def _parse_br_money_to_float(value: Any) -> Optional[float]:
    """Interpreta valor monetário BR (R$, milhar com ponto, decimal com vírgula). None se vazio ou inválido."""
    raw = str(value or "").strip()
    if not raw:
        return None
    cleaned = re.sub(r"(?i)^\s*R\$\s*", "", raw).replace(" ", "").strip()
    if not cleaned:
        return None
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _money_field_is_positive(value: Any) -> bool:
    n = _parse_br_money_to_float(value)
    return n is not None and n > 0.0


def _iter_all_document_paragraphs(doc: Document) -> Iterator[Paragraph]:
    """
    Parágrafos do documento principal e de todas as tabelas (incl. aninhadas).

    `Document.paragraphs` só cobre `w:p` filhos diretos do corpo — conteúdo em células
    não aparece e quebrava remoção/substituição do §1.1 (valor total / VALOR_TOTAL).
    """

    def walk(container) -> Iterator[Paragraph]:
        for item in container.iter_inner_content():
            if isinstance(item, Paragraph):
                yield item
            elif isinstance(item, DocxTable):
                for row in item.rows:
                    for cell in row.cells:
                        yield from walk(cell)

    yield from walk(doc)


TR_ITEMS_LEGACY_CELL_PLACEHOLDERS = {
    "(Descrever o item de acordo com o solicitado)",
    "(Inserir unidade de medida ex: caixa, litro, unidade etc)",
    "(Inserir quantidade solicitada)",
}


# Template base legado: template_packages/tr_base/TR_modelo_base.docx (raiz do projeto)
TEMPLATE_PATH_DEFAULT = (
    Path(__file__).resolve().parents[2] / "template_packages" / "tr_base" / "TR_modelo_base.docx"
)


@dataclass
class DispensaSlots:
    artigo: str = ""
    inciso: str = ""


@dataclass
class FiscalSlots:
    nome: str = ""


@dataclass
class ItemSlot:
    descricao: str
    unidade: str
    quantidade: Any  # pode ser int/str; será convertido para str
    valor_unitario: Any = ""
    valor_total: Any = ""


def normalize_item_unidade(unidade: Any) -> str:
    """Garante inicial maiúscula na unidade (ex.: un → Un, m² → M²)."""
    s = str(unidade or "").strip()
    if not s:
        return s
    lower = s.lower()
    m = re.search(r"[a-zà-ÿ]", lower)
    if not m:
        return s
    i = m.start()
    return lower[:i] + lower[i].upper() + lower[i + 1:]


@dataclass
class TRTemplateSlots:
    objeto: str = ""
    objeto_escopo: str = ""
    objeto_entregas: str = ""
    objeto_resultados: str = ""
    dispensa: DispensaSlots = field(default_factory=DispensaSlots)
    itens: List[ItemSlot] = field(default_factory=list)
    justificativa: str = ""
    fiscal: FiscalSlots = field(default_factory=FiscalSlots)
    dotacao: str = ""
    secretaria_usuario: str = ""
    nome_usuario: str = ""
    cidade_estado: str = ""
    cidade: str = ""
    horario_entrega: str = ""
    codigo_uf: str = ""
    endereco_entrega: str = ""
    email_envio_propostas: str = ""
    data_termo: str = ""
    nome_assinante_termo: str = ""
    cargo_assinante_termo: str = ""
    problema_administrativo: str = ""
    beneficio_esperado: str = ""
    sol_oficio_artigo_inciso: str = ""
    sol_oficio_destinatario_nome: str = ""
    sol_oficio_destinatario_cargo: str = ""
    sol_oficio_destinatario_orgao: str = ""
    sol_oficio_assunto: str = ""
    sol_oficio_objeto: str = ""
    sol_oficio_justificativa: str = ""
    sol_oficio_prazo_resposta: str = ""
    sol_oficio_responsavel_nome: str = ""
    sol_oficio_responsavel_cargo: str = ""
    sol_oficio_responsavel_setor: str = ""
    dfd_setor_requisitante: str = ""
    dfd_numero_processo: str = ""
    dfd_responsavel_demanda: str = ""
    dfd_email: str = ""
    dfd_gestor_contratos: str = ""
    dfd_fiscal_contratos: str = ""
    dfd_assinatura_cargo: str = ""
    dfd_assinatura_nome: str = ""
    dfd_data: str = ""
    # Texto exclusivo do DFD (ex.: inexigibilidade Art. 74.I — manutenção de veículos).
    # Quando vazios, render_dfd_from_tr_slots usa objeto/justificativa como fallback.
    dfd_objeto_referencia: str = ""
    dfd_justificativa: str = ""
    numero_processo: str = ""
    marca: str = ""
    modelo: str = ""
    numero_placa: str = ""
    orgao: str = ""
    valor_total: str = ""
    fornecedor: str = ""
    cnpj_fornecedor: str = ""
    ao_senhor_genero: str = ""
    senhor_senhora_genero: str = ""
    # Inexigibilidade Art. 74.I — fornecedor exclusivo (placeholders no .docx com espaços).
    objeto_especifico: str = ""
    equipamento: str = ""
    # Pacote Django (ex.: inexigibilidade_74_i_fornecedor_exclusivo) — usado quando o caminho do .docx
    # é genérico (fallback tr_base) e as regras Art. 74.I ainda devem aplicar-se.
    slot_package_key: str = ""
    # UI: "normal" | "rapida" — controla seção 4 do TR (1 vs 3 blocos de justificativa).
    dispensa_fluxo_ui: str = ""


def _resolve_dispensa_fluxo_ui(slots: TRTemplateSlots) -> str:
    fluxo = str(getattr(slots, "dispensa_fluxo_ui", "") or "").strip().lower()
    if fluxo:
        return fluxo
    pkg = str(getattr(slots, "slot_package_key", "") or "").strip().lower()
    if pkg.startswith("dispensa_rapida_"):
        return "rapida"
    return ""


def _style_items_table(table) -> None:
    """
    Aplica estilo fixo à tabela de itens:
    - Estilo de tabela padrão (Table Grid ou equivalente).
    - Bordas simples em todas as direções com espessura ~0,5pt.
    """
    # Estilo base de tabela (deve existir no template/Word)
    try:
        table.style = "Table Grid"
    except Exception:
        # Se o estilo não existir, segue com o padrão do documento.
        pass

    tbl = table._tbl
    tblPr = tbl.tblPr
    if tblPr is None:
        tblPr = OxmlElement("w:tblPr")
        tbl.insert(0, tblPr)

    # Remove bordas anteriores, se houver, para evitar duplicação
    for el in list(tblPr):
        if el.tag == qn("w:tblBorders"):
            tblPr.remove(el)

    tblBorders = OxmlElement("w:tblBorders")
    for border_name in ("top", "left", "bottom", "right", "insideH", "insideV"):
        border = OxmlElement(f"w:{border_name}")
        border.set(qn("w:val"), "single")
        # w:sz é medido em 1/8 de ponto. 8 ≈ 1pt; usamos 4 para ~0,5pt visual.
        border.set(qn("w:sz"), "4")
        border.set(qn("w:space"), "0")
        border.set(qn("w:color"), "000000")
        tblBorders.append(border)
    tblPr.append(tblBorders)

    # Margem superior padrão das células costuma ser grande; reduzimos sem colar no texto de cima.
    tcm = tblPr.find(qn("w:tblCellMar"))
    if tcm is None:
        tcm = OxmlElement("w:tblCellMar")
        tblPr.append(tcm)
    top = tcm.find(qn("w:top"))
    if top is None:
        top = OxmlElement("w:top")
        tcm.insert(0, top)
    top.set(qn("w:w"), "40")
    top.set(qn("w:type"), "dxa")


# ~uma linha simples (11 pt) entre o bloco anterior e a tabela de itens
_ITEMS_TABLE_GAP_AFTER_PREV_PT = 11


def _tighten_vertical_space_above_items_table(doc: Document, table) -> None:
    """
    Tira o «buraco» extra acima da tabela de itens no corpo do documento, mas deixa
    o equivalente a cerca de uma linha: remove parágrafos vazios em excesso e aplica
    space_after moderado no último parágrafo com texto antes da tabela.
    """
    tbl_el = table._tbl
    parent = tbl_el.getparent()
    if parent is None or parent.tag != qn("w:body"):
        return
    body_el = parent
    while True:
        prev = tbl_el.getprevious()
        if prev is None or prev.tag != qn("w:p"):
            break
        p_graph = Paragraph(prev, doc._body)
        if (p_graph.text or "").strip():
            break
        body_el.remove(prev)
    prev = tbl_el.getprevious()
    if prev is not None and prev.tag == qn("w:p"):
        p_graph = Paragraph(prev, doc._body)
        pf = p_graph.paragraph_format
        pf.space_before = Pt(0)
        pf.line_spacing = 1.0
        if (p_graph.text or "").strip():
            pf.space_after = Pt(_ITEMS_TABLE_GAP_AFTER_PREV_PT)


def _table_column_count(table) -> int:
    """Número de colunas da tabela (funciona mesmo com 0 linhas)."""
    try:
        cols = getattr(table, "columns", None)
        if cols is not None:
            n = len(cols)
            if n:
                return n
    except Exception:
        pass
    if table.rows:
        return len(table.rows[0].cells)
    return 0


def _ensure_items_table_columns(doc: Document, target_table, required_cols: int):
    """
    Substitui a tabela por outra com `required_cols` colunas na mesma posição XML,
    quando o modelo legado tem 4 colunas mas há valores monetários (6 colunas).
    """
    cur = _table_column_count(target_table)
    if cur == required_cols:
        return target_table
    tbl_el = target_table._tbl
    parent = tbl_el.getparent()
    if parent is None:
        return target_table
    siblings = list(parent)
    try:
        idx = siblings.index(tbl_el)
    except ValueError:
        return target_table
    parent.remove(tbl_el)
    # doc.add_table acrescenta ao documento; movemos o elemento para o sítio original.
    new_table = doc.add_table(rows=0, cols=required_cols)
    new_el = new_table._tbl
    new_el.getparent().remove(new_el)
    parent.insert(idx, new_el)
    return new_table


def _configure_items_table_columns(table, doc: Document, use_price_layout: bool = False) -> None:
    """
    Mantém colunas curtas compactas, mas largas o suficiente
    para não quebrar títulos como "Item" e "Quantidade".
    """
    if not table.columns:
        return

    # Ajuste fino: continua priorizando "Descrição", sem esmagar cabeçalhos.
    # Coluna «Item» (01, 02…) um pouco mais larga para alinhar texto e evitar aperto visual.
    if use_price_layout:
        item_w = Cm(1.5)
        quantidade_w = Cm(1.8)
        unidade_w = Cm(1.6)
        valor_unit_w = Cm(2.4)
        valor_total_w = Cm(2.4)
    else:
        item_w = Cm(1.55)
        unidade_w = Cm(1.9)
        quantidade_w = Cm(2.5)

    section = doc.sections[0] if doc.sections else None
    if section is not None:
        content_w = section.page_width - section.left_margin - section.right_margin
    else:
        # fallback seguro caso não haja metadados de seção
        content_w = Cm(16.0)

    if use_price_layout:
        descricao_w = content_w - (item_w + quantidade_w + unidade_w + valor_unit_w + valor_total_w)
    else:
        descricao_w = content_w - (item_w + unidade_w + quantidade_w)
    if descricao_w < Cm(6.0):
        descricao_w = Cm(6.0)

    table.autofit = False
    # Força layout fixo no Word para respeitar larguras definidas.
    tbl_pr = table._tbl.tblPr
    if tbl_pr is None:
        tbl_pr = OxmlElement("w:tblPr")
        table._tbl.insert(0, tbl_pr)
    tbl_layout = tbl_pr.find(qn("w:tblLayout"))
    if tbl_layout is None:
        tbl_layout = OxmlElement("w:tblLayout")
        tbl_pr.append(tbl_layout)
    tbl_layout.set(qn("w:type"), "fixed")
    widths = (
        [item_w, quantidade_w, unidade_w, descricao_w, valor_unit_w, valor_total_w]
        if use_price_layout
        else [item_w, descricao_w, unidade_w, quantidade_w]
    )
    for idx, width in enumerate(widths):
        if idx < len(table.columns):
            table.columns[idx].width = width
        for row in table.rows:
            if idx < len(row.cells):
                row.cells[idx].width = width


def _normalize_multiline_signature_text(text: str) -> str:
    """Preserva todas as quebras digitadas (incl. linhas em branco duplas entre blocos)."""
    return str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def _normalize_slot_block(text: str) -> str:
    t = _normalize_multiline_signature_text(text)
    # Preserva um par de quebras (parágrafo lógico); só colapsa 3+ linhas vazias a \n\n.
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t


def _append_multiline_to_run(run, text: str) -> None:
    """Insere texto com quebras de linha Word (w:br) a partir de \\n."""
    normalized = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    parts = normalized.split("\n")
    if not parts:
        return
    run.text = (run.text or "") + parts[0]
    for part in parts[1:]:
        run.add_break()
        run.add_text(part)


def _split_multiline_signature_blocks(text: str) -> list[tuple[list[str], int]]:
    """
    Agrupa linhas não vazias em blocos (ex.: nome + secretaria).
    Linhas em branco separam blocos; retorna (linhas, parágrafos_vazios_após).
    """
    normalized = str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []
    blocks: list[tuple[list[str], int]] = []
    current: list[str] = []
    blank_run = 0
    for line in normalized.split("\n"):
        if line.strip():
            if blank_run > 0 and current:
                blocks.append((current, blank_run))
                current = []
                blank_run = 0
            elif blank_run > 0:
                blank_run = 0
            current.append(line.strip())
        else:
            blank_run += 1
    if current:
        blocks.append((current, 0))
    return blocks


def _set_tight_paragraph_spacing(paragraph: Paragraph) -> None:
    """Evita espaço extra entre linhas do mesmo bloco (nome + cargo/setor)."""
    try:
        pf = paragraph.paragraph_format
        pf.space_before = Pt(0)
        pf.space_after = Pt(0)
        pf.line_spacing = 1.0
    except Exception:
        pass


def _append_block_lines_to_run(run, lines: list[str], font_ref) -> None:
    for line in lines:
        run.add_break()
        run.add_text(line)
    if font_ref is not None:
        _copy_run_font(font_ref, run)


def _fill_signature_block_paragraph(
    paragraph: Paragraph, lines: list[str], font_ref
) -> None:
    """Preenche parágrafo com a primeira linha já inserida + demais via w:br."""
    if len(lines) <= 1:
        _set_tight_paragraph_spacing(paragraph)
        return
    run = paragraph.runs[-1] if paragraph.runs else paragraph.add_run()
    _append_block_lines_to_run(run, lines[1:], font_ref)
    _set_tight_paragraph_spacing(paragraph)


# Campos de assinatura: blocos (nome + setor) com w:br; linha vazia = novo bloco.
SIGNATURE_MULTILINE_PLACEHOLDERS: frozenset[str] = frozenset(
    {
        "(TR_NOME_ASSINANTE_TERMO)",
        "(NOME DO ASSINANTE DO TERMO)",
        "(DFD_NOME_ASSINATURA)",
        "(NOME ASSINATURA DFD)",
        "(SOL_OFICIO_RESPONSAVEL_NOME)",
    }
)


def _insert_paragraph_after(paragraph: Paragraph) -> Paragraph:
    new_el = OxmlElement("w:p")
    paragraph._p.addnext(new_el)
    new_para = Paragraph(new_el, paragraph._parent)
    try:
        if paragraph.style:
            new_para.style = paragraph.style
    except Exception:
        pass
    return new_para


def _copy_paragraph_layout(source: Paragraph, target: Paragraph) -> None:
    try:
        target.alignment = source.alignment
        spf, tpf = source.paragraph_format, target.paragraph_format
        tpf.space_before = spf.space_before
        tpf.space_after = spf.space_after
        tpf.line_spacing = spf.line_spacing
    except Exception:
        pass


def _font_reference_run(paragraph: Paragraph):
    """Run com tamanho de fonte explícito (ex. placeholder 12 pt no modelo)."""
    for run in paragraph.runs:
        if run.font.size is not None:
            return run
    for run in paragraph.runs:
        if (run.text or "").strip():
            return run
    return paragraph.runs[0] if paragraph.runs else None


def _copy_run_font(source, target) -> None:
    if source is None or target is None:
        return
    try:
        if source.font.size is not None:
            target.font.size = source.font.size
        if source.font.name:
            target.font.name = source.font.name
        src_rpr = source._element.rPr
        if src_rpr is not None:
            tgt_el = target._element
            old_rpr = tgt_el.rPr
            if old_rpr is not None:
                tgt_el.remove(old_rpr)
            tgt_el.insert(0, deepcopy(src_rpr))
    except Exception:
        pass


def _locate_placeholder_span(runs, placeholder: str) -> tuple[int, int, int, int] | None:
    full_text = "".join(run.text or "" for run in runs)
    start = full_text.find(placeholder)
    if start < 0:
        return None
    end = start + len(placeholder)
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
        return None
    return start_idx, start_off, end_idx, end_off


def replace_placeholder_in_paragraph(
    paragraph: Paragraph,
    placeholder: str,
    replacement: str,
    *,
    multiline_as_paragraphs: bool | None = None,
) -> bool:
    """
    Substitui placeholder no parágrafo (texto pode estar dividido em vários runs).
    Campos de assinatura multilinha: blocos (nome + cargo/setor) com w:br;
    linhas em branco separam blocos em parágrafos distintos.
    """
    if multiline_as_paragraphs is None:
        multiline_as_paragraphs = placeholder in SIGNATURE_MULTILINE_PLACEHOLDERS
    normalized = (
        _normalize_multiline_signature_text(replacement)
        if multiline_as_paragraphs
        else str(replacement or "")
    )
    if multiline_as_paragraphs and "\n" in normalized:
        blocks = _split_multiline_signature_blocks(normalized)
        if not blocks:
            return _replace_placeholder_in_paragraph_inline(paragraph, placeholder, "")
        font_ref = _font_reference_run(paragraph)
        first_lines, _ = blocks[0]
        if not _replace_placeholder_in_paragraph_inline(paragraph, placeholder, first_lines[0]):
            return False
        if font_ref is None:
            font_ref = _font_reference_run(paragraph)
        _fill_signature_block_paragraph(paragraph, first_lines, font_ref)
        current = paragraph
        for i in range(1, len(blocks)):
            block_lines, _ = blocks[i]
            gap = blocks[i - 1][1]
            for _ in range(gap):
                spacer = _insert_paragraph_after(current)
                _copy_paragraph_layout(current, spacer)
                _set_tight_paragraph_spacing(spacer)
                current = spacer
            new_p = _insert_paragraph_after(current)
            _copy_paragraph_layout(current, new_p)
            run = new_p.add_run(block_lines[0])
            _copy_run_font(font_ref, run)
            _fill_signature_block_paragraph(new_p, block_lines, font_ref)
            current = new_p
        return True
    return _replace_placeholder_in_paragraph_inline(paragraph, placeholder, replacement)


def _replace_placeholder_in_paragraph_inline(
    paragraph: Paragraph, placeholder: str, replacement: str
) -> bool:
    runs = paragraph.runs
    if not runs:
        return False
    span = _locate_placeholder_span(runs, placeholder)
    if span is None:
        return False
    start_idx, start_off, end_idx, end_off = span

    if start_idx == end_idx:
        txt = runs[start_idx].text or ""
        before = txt[:start_off]
        after = txt[end_off:]
        run = runs[start_idx]
        run.text = before
        repl = "" if replacement is None else str(replacement)
        if "\n" in repl:
            _append_multiline_to_run(run, repl)
            if after:
                run.add_text(after)
        else:
            run.text = before + repl + after
    else:
        prefix = (runs[start_idx].text or "")[:start_off]
        suffix = (runs[end_idx].text or "")[end_off:]
        run = runs[start_idx]
        run.text = prefix
        repl = "" if replacement is None else str(replacement)
        if "\n" in repl:
            _append_multiline_to_run(run, repl)
            if suffix:
                run.add_text(suffix)
        else:
            run.text = prefix + repl + suffix
        for idx in range(start_idx + 1, end_idx + 1):
            runs[idx].text = ""
    return True


def set_paragraph_multiline_text(paragraph: Paragraph, text: str) -> None:
    """Substitui o conteúdo do parágrafo preservando \\n como quebras Word (w:br)."""
    normalized = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    paragraph.clear()
    if not normalized:
        return
    run = paragraph.add_run()
    _append_multiline_to_run(run, normalized)


def _replace_placeholders_in_paragraphs(doc: Document, mapping: Dict[str, str]) -> None:
    def _replace_in_paragraph(paragraph) -> None:
        for ph, val in mapping.items():
            if not ph:
                continue
            replacement = "" if val is None else str(val)
            max_iters = 100
            iters = 0
            while iters < max_iters and replace_placeholder_in_paragraph(paragraph, ph, replacement):
                iters += 1
                if ph and ph in replacement:
                    break

    for p in _iter_all_document_paragraphs(doc):
        _replace_in_paragraph(p)


def split_paragraphs_on_double_newline(doc: Document, *, space_after_pt: float = 10.0) -> None:
    """
    Onde o texto tiver linha em branco dupla (\\n\\n), divide em parágrafos Word distintos
    e aplica espaço vertical mínimo (space_after) entre blocos — usado p.ex. na justificativa
    da inexigibilidade (fornecedor exclusivo) gerada com partes.join('\\n\\n') no frontend.
    """
    gap = Pt(space_after_pt)

    def process_para(para: Paragraph) -> None:
        t = para.text or ""
        if paragraph_is_roman_enumerated_list(t):
            return
        if "\n\n" not in t:
            return
        parts = [p.strip() for p in t.split("\n\n") if p.strip()]
        if len(parts) <= 1:
            return
        set_paragraph_multiline_text(para, parts[0])
        n = len(parts)
        parent_align = para.alignment
        if n >= 2:
            para.paragraph_format.space_after = gap
        ref_el = para._p
        for idx, chunk in enumerate(parts[1:]):
            new_p = OxmlElement("w:p")
            ref_el.addnext(new_p)
            new_para = Paragraph(new_p, para._parent)
            set_paragraph_multiline_text(new_para, chunk)
            if parent_align is not None:
                new_para.alignment = parent_align
            if idx < n - 2:
                new_para.paragraph_format.space_after = gap
            ref_el = new_p

    for p in list(_iter_all_document_paragraphs(doc)):
        process_para(p)


def _set_paragraph_left_aligned(paragraph: Paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    try:
        pf = paragraph.paragraph_format
        pf.space_before = Pt(0)
        pf.space_after = Pt(0)
        pf.line_spacing = 1.0
    except Exception:
        pass


def _left_align_tr_user_dotacao_paragraphs(doc: Document, dotacao: str) -> None:
    """
    Dotação opcional inserida pelo usuário (§20/21 do TR): sempre à esquerda.
    Só atua quando há texto em slots.dotacao — não altera o modelo sem dotação informada.
    """
    dot = _normalize_slot_block(dotacao)
    if not dot:
        return

    needle_lines = [ln.strip() for ln in dot.split("\n") if ln.strip()]
    if not needle_lines:
        return

    paras = list(_iter_all_document_paragraphs(doc))
    matched_indices: list[int] = []

    for i, p in enumerate(paras):
        raw = (p.text or "").replace("\xa0", " ")
        if not raw.strip():
            continue
        if needle_lines[0] in raw or raw.strip() in needle_lines:
            matched_indices.append(i)
        elif matched_indices and any(ln in raw for ln in needle_lines[1:]):
            matched_indices.append(i)

    if not matched_indices:
        for i, p in enumerate(paras):
            tl = (p.text or "").lower()
            if "seguinte dotação orçamentária" not in tl and "seguinte dotacao orcamentaria" not in tl:
                continue
            j = i + 1
            while j < len(paras):
                tj = (paras[j].text or "").strip()
                if not tj:
                    matched_indices.append(j)
                    j += 1
                    continue
                if re.match(r"^\d+\.\s", tj) and "dotação" not in tj.lower() and "dotacao" not in tj.lower():
                    break
                matched_indices.append(j)
                j += 1
            break

    for i in matched_indices:
        _set_paragraph_left_aligned(paras[i])


def _fill_items_table(doc: Document, itens: List[ItemSlot]) -> None:
    """
    Preenche a tabela de Quantitativo e Descritivo com base em slots.itens.

    Estratégia:
    - Localiza a tabela cujo cabeçalho contenha as colunas:
      'Item', 'Descrição', 'Unidade', 'Quantidade'.
    - Localiza a primeira linha de dados que contenha os placeholders
      de descrição/unidade/quantidade.
    - Usa essa linha como molde: para o primeiro item, sobrescreve;
      para demais, adiciona novas linhas.
    """
    if not itens:
        return

    # 1) Prioriza tabela que contenha o marcador explícito de ancoragem.
    target_table = None
    for table in doc.tables:
        found_anchor_in_table = False
        for row in table.rows:
            for cell in row.cells:
                if TR_ITEMS_TABLE_ANCHOR in (cell.text or ""):
                    cell.text = (cell.text or "").replace(TR_ITEMS_TABLE_ANCHOR, "").strip()
                    found_anchor_in_table = True
                    break
            if found_anchor_in_table:
                break
        if found_anchor_in_table:
            target_table = table
            break

    # 2) Se não houver tabela com marcador, tenta marcador em parágrafo:
    # insere a tabela imediatamente após o parágrafo âncora.
    if target_table is None:
        anchor_paragraph = None
        for p in doc.paragraphs:
            if TR_ITEMS_TABLE_ANCHOR in (p.text or ""):
                p.text = (p.text or "").replace(TR_ITEMS_TABLE_ANCHOR, "").strip()
                anchor_paragraph = p
                break
        if anchor_paragraph is not None:
            target_table = doc.add_table(rows=0, cols=4)
            anchor_paragraph._p.addnext(target_table._tbl)

    # 3) Fallback legado: reutiliza tabela que tenha placeholders antigos
    # de itens ou cabeçalho típico (Item/Descrição/Unidade/Quantidade).
    if target_table is None:
        for table in doc.tables:
            if not table.rows:
                continue
            has_legacy_item_placeholder = False
            for row in table.rows:
                for cell in row.cells:
                    cell_text = (cell.text or "")
                    if any(ph in cell_text for ph in TR_ITEMS_LEGACY_CELL_PLACEHOLDERS):
                        has_legacy_item_placeholder = True
                        break
                if has_legacy_item_placeholder:
                    break

            header = [(c.text or "").strip().lower() for c in table.rows[0].cells]
            has_item_header = (
                len(header) >= 4
                and "item" in header[0]
                and "descr" in header[1]
                and "unidade" in header[2]
                and "quantidade" in header[3]
            )

            if has_legacy_item_placeholder or has_item_header:
                target_table = table
                break

    # 4) Sem âncora explícita ou tabela legada reconhecida, não injeta tabela.
    # Isso evita criar tabela indevida no final do documento.
    if target_table is None:
        return

    existing_cols_count = _table_column_count(target_table)
    # Só colunas «Valor unit.» e «Valor total» quando houver valor unitário informado
    # em algum item. Só «valor total» por linha (sem unitário) não ativa essas colunas.
    has_valor_unitario_em_algum_item = any(
        str(getattr(item, "valor_unitario", "") or "").strip() for item in itens
    )
    use_price_layout = has_valor_unitario_em_algum_item
    required_cols = 6 if use_price_layout else 4

    if existing_cols_count != required_cols:
        target_table = _ensure_items_table_columns(doc, target_table, required_cols)

    # Remove todas as linhas existentes para reconstruir a tabela do zero
    for row in list(target_table.rows):
        target_table._tbl.remove(row._tr)

    # Aplica estilo e bordas fixas à tabela
    _style_items_table(target_table)
    _configure_items_table_columns(target_table, doc, use_price_layout=use_price_layout)

    # Cria cabeçalho padronizado
    header_row = target_table.add_row()
    header_cells = header_row.cells
    header_labels = (
        ["ITEM", "QTD", "UNID.", "DESCRIÇÃO DO OBJETO", "VALOR UNIT.", "VALOR TOTAL"]
        if use_price_layout
        else ["Item", "Descrição", "Unidade", "Quantidade"]
    )
    for idx, label in enumerate(header_labels):
        if idx < len(header_cells):
            cell = header_cells[idx]
            cell.text = label
            for para in cell.paragraphs:
                para.paragraph_format.space_before = Pt(0)
                para.paragraph_format.space_after = Pt(0)
                para.paragraph_format.line_spacing = 1.0
                for run in para.runs:
                    run.bold = True

    def _set_cell(cell, text: str) -> None:
        cell.text = str(text) if text is not None else ""
        for para in cell.paragraphs:
            para.paragraph_format.space_before = Pt(0)
            para.paragraph_format.space_after = Pt(0)
            para.paragraph_format.line_spacing = 1.0

    def _to_float_br(value: Any) -> float:
        raw = str(value or "").strip()
        if not raw:
            return 0.0
        cleaned = raw.replace("R$", "").replace(" ", "")
        if "," in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        try:
            return float(cleaned)
        except Exception:
            return 0.0

    def _to_currency_br(value: Any) -> str:
        n = _to_float_br(value)
        s = f"{n:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
        return f"R$ {s}"

    def _qty_to_float(value: Any) -> float:
        raw = str(value or "").strip().replace(",", ".")
        if not raw:
            return 0.0
        try:
            return float(raw)
        except Exception:
            return 0.0

    total_geral = 0.0
    for i, item in enumerate(itens):
        row = target_table.add_row()
        cells = row.cells
        if use_price_layout:
            vu_raw = str(getattr(item, "valor_unitario", "") or "").strip()
            vt_raw = str(getattr(item, "valor_total", "") or "").strip()
            qtd_f = _qty_to_float(item.quantidade)
            vu_f = _to_float_br(vu_raw)
            vt_f = _to_float_br(vt_raw)
            if vt_f == 0.0 and qtd_f > 0 and vu_f > 0:
                vt_f = qtd_f * vu_f

            if len(cells) > 0:
                _set_cell(cells[0], f"{i + 1:02d}")
                if cells[0].paragraphs:
                    cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            if len(cells) > 1:
                _set_cell(cells[1], str(item.quantidade) or "")
                if cells[1].paragraphs:
                    cells[1].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
            if len(cells) > 2:
                _set_cell(cells[2], normalize_item_unidade(item.unidade))
                if cells[2].paragraphs:
                    cells[2].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            if len(cells) > 3:
                _set_cell(cells[3], str(item.descricao) or "")
            if len(cells) > 4:
                _set_cell(cells[4], vu_raw if vu_raw else "")
                if cells[4].paragraphs:
                    cells[4].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
            if len(cells) > 5:
                display_tot = _to_currency_br(vt_f)
                _set_cell(cells[5], display_tot)
                if cells[5].paragraphs:
                    cells[5].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
            total_geral += vt_f
        else:
            # Coluna 0: número do item (01, 02, 03...)
            if len(cells) > 0:
                _set_cell(cells[0], f"{i+1:02d}")
                if cells[0].paragraphs:
                    cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            # Coluna 1: descrição
            if len(cells) > 1:
                _set_cell(cells[1], str(item.descricao) or "")
            # Coluna 2: unidade
            if len(cells) > 2:
                _set_cell(cells[2], normalize_item_unidade(item.unidade))
                if cells[2].paragraphs:
                    cells[2].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            # Coluna 3: quantidade
            if len(cells) > 3:
                _set_cell(cells[3], str(item.quantidade) or "")
                if cells[3].paragraphs:
                    cells[3].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT

    if use_price_layout:
        total_row = target_table.add_row()
        total_cells = total_row.cells
        if len(total_cells) >= 6:
            try:
                total_cells[0].merge(total_cells[4])
            except Exception:
                pass
        if len(total_cells) > 0:
            _set_cell(total_cells[0], "VALOR TOTAL GERAL")
            if total_cells[0].paragraphs:
                total_cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
                for run in total_cells[0].paragraphs[0].runs:
                    run.bold = True
        if len(total_cells) > 5:
            _set_cell(total_cells[5], _to_currency_br(total_geral))
            if total_cells[5].paragraphs:
                total_cells[5].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
                for run in total_cells[5].paragraphs[0].runs:
                    run.bold = True

    _tighten_vertical_space_above_items_table(doc, target_table)


def _clear_headers(doc: Document) -> None:
    """
    Remove todo conteúdo de cabeçalho do documento (texto, tabelas, logotipos).

    Útil quando o modelo DOCX traz cabeçalho padrão de prefeitura que não deve
    aparecer no TR gerado automaticamente.
    """
    for section in doc.sections:
        header = section.header
        # Remove parágrafos
        for para in list(header.paragraphs):
            p = para._element
            p.getparent().remove(p)
        # Remove tabelas (caso logotipo ou layout estejam em tabela no cabeçalho)
        for table in list(header.tables):
            tbl = table._element
            tbl.getparent().remove(tbl)


def _normalize_text_for_match(text: str) -> str:
    t = str(text or "").strip().lower()
    return "".join(ch for ch in t if ch.isalnum() or ch.isspace())


def _remove_body_paragraphs_matching_needle(doc: Document, needle: str) -> int:
    """Remove parágrafos (corpo ou células de tabela) cujo texto normalizado contém `needle`. Retorna quantos removeu."""
    target = _normalize_text_for_match(needle)
    if not target:
        return 0
    n = 0
    for para in list(_iter_all_document_paragraphs(doc)):
        text = _normalize_text_for_match(para.text or "")
        if target in text:
            el = para._element
            parent = el.getparent()
            if parent is not None:
                parent.remove(el)
                n += 1
    return n


def _collapse_consecutive_empty_body_paragraphs(doc: Document) -> None:
    """Remove parágrafos vazios duplicados consecutivos no corpo (só `w:body`, não tabelas)."""
    body = doc.element.body
    changed = True
    while changed:
        changed = False
        els = [e for e in body if e.tag == qn("w:p")]
        last_nonempty = True
        for el in els:
            para = Paragraph(el, doc._body)
            empty = not (para.text or "").strip()
            if empty and not last_nonempty:
                body.remove(el)
                changed = True
                break
            last_nonempty = not empty


def _normalize_art74_sec15_1_15_2_spacing(doc: Document) -> None:
    """
    Entre o bloco «despesas / dotação» e o §…2 (omissos / Lei 14.133/2021), remove parágrafos
    vazios intermédios e reduz espaço vertical.

    - inexigibilidade **manutenção de veículos**: §15.1 → §15.2;
    - inexigibilidade **fornecedor exclusivo**: §13.1 → §13.2 (o modelo não usa §15.x nessa parte).

    Também zera `space_before` / `space_after` nos parágrafos entre os dois (ex.: linha só com
    `( DOTACAO_NUMERO )`), onde o .docx costuma trazer `w:before` alto.
    """
    body = doc.element.body

    def _is_art74_tr_dotacao_heading_para(para: Paragraph) -> bool:
        t = (para.text or "").strip()
        if not t:
            return False
        tl = t.lower()
        if not re.search(r"(?:13|15)\s*\.\s*1", t):
            return False
        return "despesas" in tl and ("dotação" in tl or "dotacao" in tl)

    def _is_art74_tr_omissos_heading_para(para: Paragraph) -> bool:
        t = (para.text or "").strip()
        if not t:
            return False
        tl = t.lower()
        if not re.search(r"(?:13|15)\s*\.\s*2", t):
            return False
        return "omissos" in tl

    def _body_paragraph_elements():
        return [el for el in body if el.tag == qn("w:p")]

    wps = _body_paragraph_elements()
    idx_dot = None
    idx_omissos = None
    for i, el in enumerate(wps):
        p = Paragraph(el, doc._body)
        if idx_dot is None and _is_art74_tr_dotacao_heading_para(p):
            idx_dot = i
            continue
        if idx_dot is not None and _is_art74_tr_omissos_heading_para(p):
            idx_omissos = i
            break

    if idx_dot is None or idx_omissos is None or idx_omissos <= idx_dot:
        return

    # Remove todos os parágrafos vazios estritamente entre §…1 e §…2 (de trás para a frente).
    for j in range(idx_omissos - 1, idx_dot, -1):
        el = wps[j]
        p = Paragraph(el, doc._body)
        if not (p.text or "").strip():
            parent = el.getparent()
            if parent is not None:
                parent.remove(el)

    wps_mid = _body_paragraph_elements()
    idx_a = idx_b = None
    for i, el in enumerate(wps_mid):
        p = Paragraph(el, doc._body)
        if idx_a is None and _is_art74_tr_dotacao_heading_para(p):
            idx_a = i
            continue
        if idx_a is not None and _is_art74_tr_omissos_heading_para(p):
            idx_b = i
            break
    if idx_a is not None and idx_b is not None and idx_b > idx_a + 1:
        for j in range(idx_a + 1, idx_b):
            pm = Paragraph(wps_mid[j], doc._body)
            pm.paragraph_format.space_before = Pt(0)
            pm.paragraph_format.space_after = Pt(0)

    # Um único «respiro» após o §…1 da dotação; sem espaço extra antes do §…2 omissos.
    for el in _body_paragraph_elements():
        p = Paragraph(el, doc._body)
        if _is_art74_tr_dotacao_heading_para(p):
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(6)
        elif _is_art74_tr_omissos_heading_para(p):
            p.paragraph_format.space_before = Pt(0)


def _fix_respetiva_typo_in_paragraph(paragraph) -> None:
    for run in paragraph.runs:
        t = run.text or ""
        if not t or "respet" not in t.lower():
            continue
        run.text = re.sub(r"(?i)respetiva", "respectiva", t)


def _fix_respetiva_typo_in_document(doc: Document) -> None:
    """Corrige grafia «respetiva» → «respectiva» em parágrafos do corpo e em células."""
    for p in doc.paragraphs:
        _fix_respetiva_typo_in_paragraph(p)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    _fix_respetiva_typo_in_paragraph(p)


def _is_manutencao_veiculos_template(template_path: Path) -> bool:
    name = _normalize_text_for_match(template_path.name)
    return "manutencao de veiculos" in name


def _tr_is_lei14133_art74_i_inexigibilidade_pack(
    template_path: Path, slots: Optional[TRTemplateSlots] = None
) -> bool:
    """
    TR dos pacotes Lei 14.133 Art. 74, I (manutenção de veículos ou fornecedor exclusivo):
    dotação alternativa, remoção do §1.1 sem preços, etc.

    Reconhece pelo caminho do modelo ou por `slots.slot_package_key` (útil se o .docx veio do fallback
    `tr_base/TR_modelo_base.docx`, sem «inexigibilidade» no path).
    """
    if _is_manutencao_veiculos_template(template_path):
        return True
    n = _normalize_text_for_match(str(template_path))
    if "inexigibilidade" in n and "74" in n:
        if any(x in n for x in ("fornecedor", "exclusivo", "manutencao", "veiculo")):
            return True
    if slots is not None:
        k = _normalize_text_for_match(getattr(slots, "slot_package_key", "") or "")
        if "inexigibilidade" in k and "74" in k:
            if any(x in k for x in ("fornecedor", "exclusivo", "manutencao", "veiculo")):
                return True
    return False


def _apply_art74_i_dotacao_paragraph_branch(
    doc: Document, tpl_path: Path, dotacao: str | None, slots: TRTemplateSlots
) -> None:
    """
    - Com dotação preenchida: remove o bloco «dotação orçamentária própria…» (15.1 alternativo).
    - Sem dotação: remove o bloco «…seguinte dotação orçamentária…» (15.1 com campo numérico).
    Em ambos os casos, comprime parágrafos vazios extras no corpo.
    """
    if not _tr_is_lei14133_art74_i_inexigibilidade_pack(tpl_path, slots):
        return
    has_dot = bool(str(dotacao or "").strip())
    removed = 0
    if has_dot:
        removed += _remove_body_paragraphs_matching_needle(
            doc,
            "correrão à conta de dotação orçamentária própria, prevista no orçamento vigente do órgão contratante",
        )
        removed += _remove_body_paragraphs_matching_needle(
            doc,
            "dotação orçamentária própria, prevista no orçamento vigente do órgão contratante",
        )
    else:
        removed += _remove_body_paragraphs_matching_needle(
            doc,
            "seguinte dotação orçamentária",
        )
    if removed:
        _collapse_consecutive_empty_body_paragraphs(doc)


def _tr_precos_comerciais_informados(slots: TRTemplateSlots) -> bool:
    """
    Há preço de referência nos itens (unitário ou total por linha) ou valor total global no TR.
    Alinhado à regra da tabela de itens: sem isto, o modelo não deve exibir o §1.1 do valor do processo.
    Valores zero ou «R$ 0,00» não contam como preço informado.
    """
    for item in slots.itens or []:
        if _money_field_is_positive(getattr(item, "valor_unitario", "")):
            return True
        if _money_field_is_positive(getattr(item, "valor_total", "")):
            return True
    if _money_field_is_positive(getattr(slots, "valor_total", "")):
        return True
    return False


def _apply_art74_i_remove_valor_total_processo_sem_precos(
    doc: Document, _tpl_path: Path, slots: TRTemplateSlots
) -> None:
    """
    Modelos Art. 74, I (fornecedor exclusivo / manutenção de veículos) trazem o §1.1 sobre
    valor total obtido por proposta comercial. Se nenhum preço foi informado, remove o parágrafo
    (evita «R$0,00» e texto desnecessário).

    A frase-gatilho é exclusiva desses modelos; não depende de reconhecer o pacote pelo path
    (fallback `tr_base` + `slot_package_key` vazio deixava o §1.1 no documento).
    """
    if _tr_precos_comerciais_informados(slots):
        return
    removed = _remove_body_paragraphs_matching_needle(
        doc,
        "proposta comercial fornecida pelo fornecedor exclusivo",
    )
    if removed:
        _collapse_consecutive_empty_body_paragraphs(doc)


def _scrub_valor_total_placeholders_sem_preco(doc: Document, slots: TRTemplateSlots) -> None:
    """Remove tokens «( VALOR_TOTAL )» residuais se nenhum preço foi informado (runs que impedem o match do mapping)."""
    if _tr_precos_comerciais_informados(slots):
        return
    pat = re.compile(r"\(\s*VALOR\s*_?\s*TOTAL\s*\)", re.IGNORECASE)
    for p in list(_iter_all_document_paragraphs(doc)):
        t = p.text or ""
        if not pat.search(t):
            continue
        p.text = pat.sub("", t).strip()


def _remove_paragraph_element(paragraph: Paragraph) -> None:
    el = paragraph._element
    parent = el.getparent()
    if parent is not None:
        parent.remove(el)


def _para_visible_text(paragraph: Paragraph) -> str:
    return (paragraph.text or "").replace("\u00a0", " ").strip()


def _remove_tr_assinatura_cargo_line(doc: Document) -> None:
    """Remove linha vazia abaixo do nome (ex-(TR_SECRETARIA_USUARIO) / cargo do assinante)."""
    paras = list(doc.paragraphs)
    last_text_idx = -1
    for i, p in enumerate(paras):
        if _para_visible_text(p):
            last_text_idx = i
    if last_text_idx < 0:
        return
    for i in range(len(paras) - 1, last_text_idx, -1):
        if not _para_visible_text(paras[i]):
            _remove_paragraph_element(paras[i])


def render_tr_from_slots(
    slots: TRTemplateSlots,
    template_path: Optional[Path | str] = None,
    output_path: Optional[Path | str] = None,
) -> str:
    """
    Preenche o modelo de TR com os slots informados e gera um novo DOCX.

    - Usa apenas o template fixo (texto congelado).
    - Substitui os placeholders de objeto, artigo, justificativa, inciso,
      fiscal e dotação.
    - Preenche a tabela de itens com base em slots.itens (podendo ser N itens).
    """
    tpl_path = Path(template_path) if template_path else TEMPLATE_PATH_DEFAULT
    if not tpl_path.exists():
        raise FileNotFoundError(f"Template TR não encontrado: {tpl_path}")

    from .deprecated_cargo_slots import clear_deprecated_cargo_fields

    slots = clear_deprecated_cargo_fields(slots)

    doc = Document(str(tpl_path))

    # Remove cabeçalho padrão do modelo (ex.: timbre de prefeitura),
    # deixando o TR gerado sem esse cabeçalho fixo.
    _clear_headers(doc)

    fluxo_ui = _resolve_dispensa_fluxo_ui(slots)
    justificativa_text = _normalize_slot_block(slots.justificativa or "")
    problema_text = _normalize_slot_block(slots.problema_administrativo or "")
    beneficio_text = _normalize_slot_block(slots.beneficio_esperado or "")

    # Evita repetir o mesmo parágrafo 3× no Word (placeholders no mesmo fluxo).
    if fluxo_ui in ("normal", "rapida"):
        jus_cmp = justificativa_text.strip()
        if problema_text.strip() == jus_cmp:
            problema_text = ""
        if beneficio_text.strip() == jus_cmp:
            beneficio_text = ""

    if fluxo_ui == "normal" and "\n\n" in justificativa_text.strip():
        problema_text = ""
        beneficio_text = ""
    elif fluxo_ui == "rapida" and "\n\n" in justificativa_text.strip():
        p1, p2, p3 = finalize_rapida_secao4_tres_blocos(
            justificativa_text,
            problema_text,
            beneficio_text,
        )
        justificativa_text = p1
        problema_text = p2
        beneficio_text = p3

    valor_total_placeholder = _valor_total_sem_rs(slots.valor_total or "")

    if justificativa_text and (problema_text or beneficio_text):
        justificativa_text = f"{justificativa_text}\n"
    elif justificativa_text:
        justificativa_text = f"{justificativa_text}\n"
    if problema_text and beneficio_text:
        problema_text = f"{problema_text}\n"

    num_proc_display = slots_numero_processo_display(slots)
    num_proc_tr_placeholder = numero_processo_valor_placeholder_tr(num_proc_display)

    # Cargo/função abaixo do nome na assinatura foi descontinuado no produto.
    cargo_assinatura_tr = ""
    nome_assinante_tr = _normalize_multiline_signature_text(slots.nome_assinante_termo or "")

    data_termo_extenso = format_date_pt_br_extenso(slots.data_termo)

    mapping = {
        # Placeholders padronizados (preferenciais)
        "(TR_OBJETO)": slots.objeto or "",
        "(TR_OBJETO_ESCOPO)": slots.objeto_escopo or slots.objeto or "",
        "(TR_OBJETO_ENTREGAS)": slots.objeto_entregas or slots.objeto or "",
        "(TR_OBJETO_RESULTADOS_ESPERADOS)": slots.objeto_resultados or slots.objeto or "",
        "(TR_DISPENSA_INCISO)": slots.dispensa.inciso or "",
        "(TR_JUSTIFICATIVA)": justificativa_text,
        # Mesmo texto da justificativa; modelos Art. 74.I usam token com espaços.
        "( JUSTIFICATIVA )": justificativa_text,
        "(JUSTIFICATIVA)": justificativa_text,
        "( OBJETO_ESPECIFICO )": (slots.objeto_especifico or "").strip(),
        "(OBJETO_ESPECIFICO)": (slots.objeto_especifico or "").strip(),
        "( EQUIPAMENTO )": (slots.equipamento or "").strip(),
        "(EQUIPAMENTO)": (slots.equipamento or "").strip(),
        "(TR_FISCAL_NOME)": slots.fiscal.nome or "",
        "(TR_DOTACAO)": slots.dotacao or "",
        "(DOTACAO_NUMERO)": slots.dotacao or "",
        "( DOTACAO_NUMERO )": slots.dotacao or "",
        "(TR_SECRETARIA_USUARIO)": "",
        "(TR_NOME_USUARIO)": slots.nome_usuario or "",
        "(TR_CIDADE_ESTADO)": slots.cidade_estado or "",
        "(TR_CIDADE)": slots.cidade or "",
        "(TR_CODIGO_UF)": slots.codigo_uf or "",
        "(TR_ENDERECO_ENTREGA)": slots.endereco_entrega or "",
        "(TR_EMAIL_ENVIO_PROPOSTAS)": slots.email_envio_propostas or "",
        "(TR_DATA_TERMO)": data_termo_extenso,
        "(TR_NOME_ASSINANTE_TERMO)": nome_assinante_tr,
        "(TR_CARGO_ASSINANTE_TERMO)": cargo_assinatura_tr,
        "(NUMERO_PROCESSO)": num_proc_tr_placeholder,
        "( NUMERO_PROCESSO )": num_proc_tr_placeholder,
        "(NUMERO PROCESSO)": num_proc_tr_placeholder,
        "( NUMERO PROCESSO )": num_proc_tr_placeholder,
        "(MARCA)": slots.marca or "",
        "( MARCA )": slots.marca or "",
        "(MODELO)": slots.modelo or "",
        "( MODELO )": slots.modelo or "",
        "(NUMERO_PLACA)": slots.numero_placa or "",
        "( NUMERO_PLACA )": slots.numero_placa or "",
        "(ORGAO)": slots.orgao or "",
        "( ORGAO )": slots.orgao or "",
        "(VALOR_TOTAL)": valor_total_placeholder,
        "( VALOR_TOTAL )": valor_total_placeholder,
        "(FORNECEDOR)": slots.fornecedor or "",
        "( FORNECEDOR )": slots.fornecedor or "",
        # TR inexigibilidade manutenção de veículos: «( FORNECEDOR), CNPJ…» (sem espaço antes do «)»).
        "( FORNECEDOR)": slots.fornecedor or "",
        "(CNPJ FORNECEDOR)": slots.cnpj_fornecedor or "",
        "( CNPJ FORNECEDOR )": slots.cnpj_fornecedor or "",
        # inexigibilidade fornecedor exclusivo: token com underscore no .docx.
        "(CNPJ_FORNECEDOR)": slots.cnpj_fornecedor or "",
        "( CNPJ_FORNECEDOR )": slots.cnpj_fornecedor or "",
        "(AO_SENHOR_GENERO)": slots.ao_senhor_genero or "",
        "( AO_SENHOR_GENERO )": slots.ao_senhor_genero or "",
        "(SENHOR_SENHORA_GENERO)": slots.senhor_senhora_genero or "",
        "( SENHOR_SENHORA_GENERO )": slots.senhor_senhora_genero or "",
        # Compatibilidade entre variantes de pacotes TR_modelo_base
        "(TR_OBJETO_MANUAL)": slots.objeto or "",
        "(TR_BENEFICIO_ESPERADO)": beneficio_text,
        "(TR_PROBLEMA_ADMINISTRATIVO)": problema_text,
        # Compatibilidade com placeholders legados
        "(descrever o objeto solicitado)": slots.objeto or "",
        # No modelo, este placeholder está associado ao texto logo após "inciso".
        # Embora o rótulo mencione "artigo", na prática ele representa o INCISO
        # do art. 75, por isso usamos sempre slots.dispensa.inciso aqui.
        "(descrever o artigo de acordo com objeto)": slots.dispensa.inciso or "",
        "(Formalizar justificava de acordo com objeto solicitado)": slots.justificativa or "",
        "(Inserir o inciso de acordo com o objeto solicitado)": slots.dispensa.inciso or "",
        "(inserir nome do fiscal)": slots.fiscal.nome or "",
        # Dotação: não é preenchida pela IA; sempre deixar em branco aqui.
        # O backend/sistema pode sobrescrever via slots_override.dotacao no futuro.
        "(Inserir Dotação)": slots.dotacao or "",
        "(Inserir Dotação)(Feito direto pelo usuário)": slots.dotacao or "",
        "(Feito direto pelo usuário)": "",
        "(SECRETARIA DO USUARIO)": "",
        "(Nome do USUARIO)": slots.nome_usuario or "",
        "(CIDADE - ESTADO)": slots.cidade_estado or "",
        "(CIDADE)": slots.cidade or "",
        "(HORARIO E DIAS PARA ENTREGA)": slots.horario_entrega or "Preencher horário, dias da semana e outras informações de entrega",
        "(CÓDIGO UF)": slots.codigo_uf or "",
        "(ENDERECO ENTREGA)": slots.endereco_entrega or "",
        "(E-mail de envio de propostas)": slots.email_envio_propostas or "",
        "(DATA DO TERMO)": data_termo_extenso,
        "(NOME DO ASSINANTE DO TERMO)": nome_assinante_tr,
        "(CARGO DO ASSINANTE DO TERMO)": "",
    }

    _replace_placeholders_in_paragraphs(doc, mapping)
    split_paragraphs_on_double_newline(doc)
    if str(slots.dotacao or "").strip():
        _left_align_tr_user_dotacao_paragraphs(doc, slots.dotacao)
    _remove_tr_assinatura_cargo_line(doc)
    _fix_respetiva_typo_in_document(doc)
    _apply_art74_i_dotacao_paragraph_branch(doc, tpl_path, slots.dotacao, slots)
    _apply_art74_i_remove_valor_total_processo_sem_precos(doc, tpl_path, slots)
    _scrub_valor_total_placeholders_sem_preco(doc, slots)
    if _tr_is_lei14133_art74_i_inexigibilidade_pack(tpl_path, slots):
        _normalize_art74_sec15_1_15_2_spacing(doc)
    _fill_items_table(doc, slots.itens)

    apply_standard_body_font_to_document(doc)
    apply_numero_processo_bold_to_document(doc, num_proc_display)
    apply_default_justify_to_document(doc)

    ensure_signature_nome_blank_lines(doc)

    out_path = Path(output_path) if output_path else None
    if out_path is None:
        import tempfile

        tmp_dir = Path(tempfile.gettempdir())
        # Nome único por geração: o caminho fixo por stem causava corrupção quando
        # duas requisições TR/DFD/Ofício coincidiam (multi-worker, outro utilizador
        # ou segundo clique antes de terminar a primeira).
        out_path = tmp_dir / f"tr_preenchido_{Path(tpl_path).stem}_{uuid.uuid4().hex}.docx"

    doc.save(str(out_path))
    return str(out_path)

