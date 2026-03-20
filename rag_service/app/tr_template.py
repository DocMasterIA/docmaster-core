from __future__ import annotations

"""
Geração de Termo de Referência a partir do modelo fixo
`templates/tr_base/TR_modelo_base.docx`, preenchendo apenas os slots
marcados entre parênteses.

Este módulo NÃO chama IA – ele só aplica um dicionário de slots em cima
do template. Quem monta os slots (usuário ou LLM) é outra camada.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


# Template base: templates/tr_base/TR_modelo_base.docx (raiz do projeto)
TEMPLATE_PATH_DEFAULT = (
    Path(__file__).resolve().parents[2] / "templates" / "tr_base" / "TR_modelo_base.docx"
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

    # Tenta reaproveitar uma tabela existente com 4 colunas; caso não encontre, cria uma nova.
    target_table = None
    for table in doc.tables:
        if not table.rows:
            continue
        if len(table.rows[0].cells) >= 4:
            target_table = table
            break

    if target_table is None:
        target_table = doc.add_table(rows=0, cols=4)

    # Remove todas as linhas existentes para reconstruir a tabela do zero
    for row in list(target_table.rows):
        target_table._tbl.remove(row._tr)

    # Aplica estilo e bordas fixas à tabela
    _style_items_table(target_table)

    # Cria cabeçalho padronizado
    header_row = target_table.add_row()
    header_cells = header_row.cells
    header_labels = ["Item", "Descrição", "Unidade", "Quantidade"]
    for idx, label in enumerate(header_labels):
        if idx < len(header_cells):
            cell = header_cells[idx]
            cell.text = label
            for para in cell.paragraphs:
                for run in para.runs:
                    run.bold = True

    def _set_cell(cell, text: str) -> None:
        cell.text = str(text) if text is not None else ""

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

    mapping = {
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

    _fill_items_table(doc, slots.itens)

    out_path = Path(output_path) if output_path else None
    if out_path is None:
        import tempfile
        tmp_dir = Path(tempfile.gettempdir())
        out_path = tmp_dir / f"tr_preenchido_{Path(tpl_path).stem}.docx"

    doc.save(str(out_path))
    return str(out_path)

