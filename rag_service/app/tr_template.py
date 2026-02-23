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

    target_table = None
    for table in doc.tables:
        if not table.rows:
            continue
        header_cells = table.rows[0].cells
        header_texts = [c.text.strip().lower() for c in header_cells]
        if (
            len(header_texts) >= 4
            and "item" in header_texts[0]
            and "descri" in header_texts[1]
            and "unidade" in header_texts[2]
            and "quantidade" in header_texts[3]
        ):
            target_table = table
            break

    if target_table is None:
        return

    # Localiza linha molde (primeira linha após cabeçalho com placeholders)
    desc_ph = "(Descrever o item de acordo com o solicitado)"
    unid_ph = "(Inserir unidade de medida ex: caixa, litro, unidade etc)"
    qtd_ph = "(Inserir quantidade solicitada)"

    template_row_idx: Optional[int] = None
    for idx, row in enumerate(target_table.rows[1:], start=1):
        row_text = " | ".join(c.text for c in row.cells)
        if any(ph in row_text for ph in (desc_ph, unid_ph, qtd_ph)):
            template_row_idx = idx
            break

    if template_row_idx is None:
        return

    # Mantém a tabela "maleável":
    # - preserva apenas o cabeçalho e a linha molde com placeholders
    # - remove quaisquer outras linhas pré-existentes do template,
    #   evitando sobrar linhas vazias/placeholder quando houver poucos itens.
    header_row = target_table.rows[0]
    template_row = target_table.rows[template_row_idx]
    # Remove demais linhas (de baixo para cima para não quebrar índices)
    for row in list(target_table.rows)[::-1]:
        if row is header_row or row is template_row:
            continue
        target_table._tbl.remove(row._tr)

    def _set_cell(cell, text: str) -> None:
        cell.text = str(text) if text is not None else ""

    for i, item in enumerate(itens):
        if i == 0:
            row = template_row
        else:
            row = target_table.add_row()
        cells = row.cells
        # Coluna 0: número do item (01, 02, 03...)
        if len(cells) > 0:
            _set_cell(cells[0], f"{i+1:02d}")
        # Coluna 1: descrição (sempre escreve o valor do slot, ignorando texto anterior)
        if len(cells) > 1:
            _set_cell(cells[1], str(item.descricao) or "")
        # Coluna 2: unidade
        if len(cells) > 2:
            _set_cell(cells[2], str(item.unidade) or "")
        # Coluna 3: quantidade
        if len(cells) > 3:
            _set_cell(cells[3], str(item.quantidade) or "")


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

    mapping = {
        "(descrever o objeto solicitado)": slots.objeto or "",
        "(descrever o artigo de acordo com objeto)": slots.dispensa.artigo or "",
        "(Formalizar justificava de acordo com objeto solicitado)": slots.justificativa or "",
        "(Inserir o inciso de acordo com o objeto solicitado)": slots.dispensa.inciso or "",
        "(inserir nome do fiscal)": slots.fiscal.nome or "",
        "(Inserir Dotação)": slots.dotacao or "",
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

