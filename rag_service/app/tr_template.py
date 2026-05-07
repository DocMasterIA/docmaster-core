from __future__ import annotations

import re

"""
Geração de Termo de Referência a partir do modelo fixo
`template_packages/tr_base/TR_modelo_base.docx`, preenchendo apenas os slots
marcados entre parênteses.

Este módulo NÃO chama IA – ele só aplica um dicionário de slots em cima
do template. Quem monta os slots (usuário ou LLM) é outra camada.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

TR_ITEMS_TABLE_ANCHOR = "(TR_TABELA_ITENS)"
SLOT_TEXT_FONT_FAMILY = "Times New Roman"
TR_ITEMS_LEGACY_CELL_PLACEHOLDERS = {
    "(Descrever o item de acordo com o solicitado)",
    "(Inserir unidade de medida ex: caixa, litro, unidade etc)",
    "(Inserir quantidade solicitada)",
}


def _apply_times_new_roman(paragraph) -> None:
    for run in paragraph.runs:
        run.font.name = SLOT_TEXT_FONT_FAMILY
        r_pr = run._element.get_or_add_rPr()
        r_fonts = r_pr.find(qn("w:rFonts"))
        if r_fonts is None:
            r_fonts = OxmlElement("w:rFonts")
            r_pr.append(r_fonts)
        r_fonts.set(qn("w:ascii"), SLOT_TEXT_FONT_FAMILY)
        r_fonts.set(qn("w:hAnsi"), SLOT_TEXT_FONT_FAMILY)
        r_fonts.set(qn("w:cs"), SLOT_TEXT_FONT_FAMILY)
        r_fonts.set(qn("w:eastAsia"), SLOT_TEXT_FONT_FAMILY)


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
    numero_processo: str = ""
    marca: str = ""
    modelo: str = ""
    numero_placa: str = ""
    orgao: str = ""
    valor_total: str = ""
    fornecedor: str = ""
    cnpj_fornecedor: str = ""


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


def _configure_items_table_columns(table, doc: Document) -> None:
    """
    Mantém colunas curtas compactas, mas largas o suficiente
    para não quebrar títulos como "Item" e "Quantidade".
    """
    if not table.columns:
        return

    # Ajuste fino: continua priorizando "Descrição", sem esmagar cabeçalhos.
    item_w = Cm(1.3)
    unidade_w = Cm(1.9)
    quantidade_w = Cm(2.5)

    section = doc.sections[0] if doc.sections else None
    if section is not None:
        content_w = section.page_width - section.left_margin - section.right_margin
    else:
        # fallback seguro caso não haja metadados de seção
        content_w = Cm(16.0)

    descricao_w = content_w - (item_w + unidade_w + quantidade_w)
    if descricao_w < Cm(6.0):
        descricao_w = Cm(6.0)

    table.autofit = False
    # Força layout fixo no Word para respeitar larguras definidas.
    tbl_pr = table._tbl.tblPr
    tbl_layout = tbl_pr.find(qn("w:tblLayout")) if tbl_pr is not None else None
    if tbl_layout is None:
        tbl_layout = OxmlElement("w:tblLayout")
        tbl_pr.append(tbl_layout)
    tbl_layout.set(qn("w:type"), "fixed")
    widths = [item_w, descricao_w, unidade_w, quantidade_w]
    for idx, width in enumerate(widths):
        if idx < len(table.columns):
            table.columns[idx].width = width
        for row in table.rows:
            if idx < len(row.cells):
                row.cells[idx].width = width


def _set_cell_no_wrap(cell) -> None:
    """
    Impede quebra automática de linha na célula (Word w:noWrap).
    """
    tc_pr = cell._tc.get_or_add_tcPr()
    no_wrap = tc_pr.find(qn("w:noWrap"))
    if no_wrap is None:
        no_wrap = OxmlElement("w:noWrap")
        tc_pr.append(no_wrap)


def _replace_placeholders_in_paragraphs(doc: Document, mapping: Dict[str, str]) -> None:
    """
    Substitui textos exatos dos placeholders em todos os parágrafos do documento.

    Observação: mexer em paragraph.text simplifica os runs, mas é aceitável
    para este uso (template fixo).
    """
    for p in doc.paragraphs:
        if not p.text:
            continue
        text = p.text
        changed = False
        for ph, val in mapping.items():
            if ph in text:
                text = text.replace(ph, val)
                changed = True
        if changed:
            p.text = text
            _apply_times_new_roman(p)


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

    # Remove todas as linhas existentes para reconstruir a tabela do zero
    for row in list(target_table.rows):
        target_table._tbl.remove(row._tr)

    # Aplica estilo e bordas fixas à tabela
    _style_items_table(target_table)
    _configure_items_table_columns(target_table, doc)

    # Cria cabeçalho padronizado
    header_row = target_table.add_row()
    header_cells = header_row.cells
    header_labels = ["Item", "Descrição", "Unidade", "Quantidade"]
    for idx, label in enumerate(header_labels):
        if idx < len(header_cells):
            cell = header_cells[idx]
            cell.text = label
            _set_cell_no_wrap(cell)
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
            _apply_times_new_roman(para)

    for i, item in enumerate(itens):
        row = target_table.add_row()
        cells = row.cells
        # Coluna 0: número do item (01, 02, 03...)
        if len(cells) > 0:
            _set_cell(cells[0], f"{i+1:02d}")
            if cells[0].paragraphs:
                cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        # Coluna 1: descrição (sempre escreve o valor do slot, ignorando texto anterior)
        if len(cells) > 1:
            _set_cell(cells[1], str(item.descricao) or "")
        # Coluna 2: unidade
        if len(cells) > 2:
            _set_cell(cells[2], str(item.unidade) or "")
            if cells[2].paragraphs:
                cells[2].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        # Coluna 3: quantidade
        if len(cells) > 3:
            _set_cell(cells[3], str(item.quantidade) or "")
            if cells[3].paragraphs:
                cells[3].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT


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


def _remove_paragraph_if_contains(doc: Document, needle: str) -> None:
    target = _normalize_text_for_match(needle)
    if not target:
        return
    for para in list(doc.paragraphs):
        text = _normalize_text_for_match(para.text or "")
        if target in text:
            p = para._element
            p.getparent().remove(p)


def _is_manutencao_veiculos_template(template_path: Path) -> bool:
    name = _normalize_text_for_match(template_path.name)
    return "manutencao de veiculos" in name


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

    doc = Document(str(tpl_path))

    # Remove cabeçalho padrão do modelo (ex.: timbre de prefeitura),
    # deixando o TR gerado sem esse cabeçalho fixo.
    _clear_headers(doc)

    # Regra de negócio (Art. 74 I - Manutenção de Veículos):
    # Se houver número de dotação, remove o texto alternativo "dotação própria".
    # Assim, o documento não apresenta as duas redações ao mesmo tempo.
    if _is_manutencao_veiculos_template(tpl_path) and str(slots.dotacao or "").strip():
        _remove_paragraph_if_contains(
            doc,
            "correrão à conta de dotação orçamentária própria, prevista no orçamento vigente do órgão contratante",
        )

    def _normalize_slot_block(text: str) -> str:
        t = str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
        # Evita "double space"/linhas em branco duplas entre blocos
        t = re.sub(r"\n{2,}", "\n", t)
        return t

    justificativa_text = _normalize_slot_block(slots.justificativa or "")
    problema_text = _normalize_slot_block(slots.problema_administrativo or slots.justificativa or "")
    beneficio_text = _normalize_slot_block(slots.beneficio_esperado or slots.justificativa or "")

    # Entre blocos sequenciais, garante no máximo uma quebra de linha.
    if justificativa_text and (problema_text or beneficio_text):
        justificativa_text = f"{justificativa_text}\n"
    if problema_text and beneficio_text:
        problema_text = f"{problema_text}\n"

    mapping = {
        # Placeholders padronizados (preferenciais)
        "(TR_OBJETO)": slots.objeto or "",
        "(TR_OBJETO_ESCOPO)": slots.objeto_escopo or slots.objeto or "",
        "(TR_OBJETO_ENTREGAS)": slots.objeto_entregas or slots.objeto or "",
        "(TR_OBJETO_RESULTADOS_ESPERADOS)": slots.objeto_resultados or slots.objeto or "",
        "(TR_DISPENSA_INCISO)": slots.dispensa.inciso or "",
        "(TR_JUSTIFICATIVA)": justificativa_text,
        "(TR_FISCAL_NOME)": slots.fiscal.nome or "",
        "(TR_DOTACAO)": slots.dotacao or "",
        "(DOTACAO_NUMERO)": slots.dotacao or "",
        "( DOTACAO_NUMERO )": slots.dotacao or "",
        "(TR_SECRETARIA_USUARIO)": slots.secretaria_usuario or "",
        "(TR_NOME_USUARIO)": slots.nome_usuario or "",
        "(TR_CIDADE_ESTADO)": slots.cidade_estado or "",
        "(TR_CIDADE)": slots.cidade or "",
        "(TR_CODIGO_UF)": slots.codigo_uf or "",
        "(TR_ENDERECO_ENTREGA)": slots.endereco_entrega or "",
        "(TR_EMAIL_ENVIO_PROPOSTAS)": slots.email_envio_propostas or "",
        "(TR_DATA_TERMO)": slots.data_termo or "",
        "(TR_NOME_ASSINANTE_TERMO)": slots.nome_assinante_termo or "",
        "(TR_CARGO_ASSINANTE_TERMO)": slots.cargo_assinante_termo or "",
        "(NUMERO_PROCESSO)": slots.numero_processo or "",
        "( NUMERO_PROCESSO )": slots.numero_processo or "",
        "(MARCA)": slots.marca or "",
        "( MARCA )": slots.marca or "",
        "(MODELO)": slots.modelo or "",
        "( MODELO )": slots.modelo or "",
        "(NUMERO_PLACA)": slots.numero_placa or "",
        "( NUMERO_PLACA )": slots.numero_placa or "",
        "(ORGAO)": slots.orgao or slots.secretaria_usuario or "",
        "( ORGAO )": slots.orgao or slots.secretaria_usuario or "",
        "(VALOR_TOTAL)": slots.valor_total or "",
        "( VALOR_TOTAL )": slots.valor_total or "",
        "(FORNECEDOR)": slots.fornecedor or "",
        "( FORNECEDOR )": slots.fornecedor or "",
        "(CNPJ FORNECEDOR)": slots.cnpj_fornecedor or "",
        "( CNPJ FORNECEDOR )": slots.cnpj_fornecedor or "",
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
        "(Feito direto pelo usuário)": "",
        "(SECRETARIA DO USUARIO)": slots.secretaria_usuario or "",
        "(Nome do USUARIO)": slots.nome_usuario or "",
        "(CIDADE - ESTADO)": slots.cidade_estado or "",
        "(CIDADE)": slots.cidade or "",
        "(HORARIO E DIAS PARA ENTREGA)": slots.horario_entrega or "Preencher horário, dias da semana e outras informações de entrega",
        "(CÓDIGO UF)": slots.codigo_uf or "",
        "(ENDERECO ENTREGA)": slots.endereco_entrega or "",
        "(E-mail de envio de propostas)": slots.email_envio_propostas or "",
        "(DATA DO TERMO)": slots.data_termo or "",
        "(NOME DO ASSINANTE DO TERMO)": slots.nome_assinante_termo or "",
        "(CARGO DO ASSINANTE DO TERMO)": slots.cargo_assinante_termo or "",
    }

    _replace_placeholders_in_paragraphs(doc, mapping)
    # Também substituir placeholders em células de tabelas (fora da linha de itens)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text = cell.text
                changed = False
                for ph, val in mapping.items():
                    if ph in text:
                        text = text.replace(ph, val)
                        changed = True
                if changed:
                    cell.text = text
                    for para in cell.paragraphs:
                        _apply_times_new_roman(para)

    _fill_items_table(doc, slots.itens)

    out_path = Path(output_path) if output_path else None
    if out_path is None:
        import tempfile
        tmp_dir = Path(tempfile.gettempdir())
        out_path = tmp_dir / f"tr_preenchido_{Path(tpl_path).stem}.docx"

    doc.save(str(out_path))
    return str(out_path)

