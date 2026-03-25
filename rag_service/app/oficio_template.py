from __future__ import annotations

"""
Geração de Solicitação/Ofício a partir do modelo fixo
`template_packages/tr_base/OFICIO_modelo_base.docx`, preenchendo apenas os slots.
"""

from pathlib import Path
from typing import Optional

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from .tr_template import TRTemplateSlots


TEMPLATE_OFICIO_PATH_DEFAULT = (
    Path(__file__).resolve().parents[2] / "template_packages" / "tr_base" / "OFICIO_modelo_base.docx"
)
SLOT_TEXT_FONT_FAMILY = "Times New Roman"


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


def _replace_placeholders(doc: Document, mapping: dict[str, str]) -> None:
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

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text = cell.text
                if not text:
                    continue
                changed = False
                for ph, val in mapping.items():
                    if ph in text:
                        text = text.replace(ph, val)
                        changed = True
                if changed:
                    cell.text = text
                    for para in cell.paragraphs:
                        _apply_times_new_roman(para)


def render_oficio_from_slots(
    slots: TRTemplateSlots,
    template_path: Optional[Path | str] = None,
    output_path: Optional[Path | str] = None,
) -> str:
    tpl_path = Path(template_path) if template_path else TEMPLATE_OFICIO_PATH_DEFAULT
    if not tpl_path.exists():
        raise FileNotFoundError(f"Template OFICIO não encontrado: {tpl_path}")

    doc = Document(str(tpl_path))

    mapping = {
        "(SOL_OFICIO_ARTIGO_INCISO)": slots.sol_oficio_artigo_inciso or "",
        "(SOL_OFICIO_DESTINATARIO_NOME)": slots.sol_oficio_destinatario_nome or "",
        "(SOL_OFICIO_DESTINATARIO_CARGO)": slots.sol_oficio_destinatario_cargo or "",
        "(SOL_OFICIO_DESTINATARIO_ORGAO)": slots.sol_oficio_destinatario_orgao or "",
        "(SOL_OFICIO_ASSUNTO)": slots.sol_oficio_assunto or "",
        "(SOL_OFICIO_OBJETO)": slots.sol_oficio_objeto or slots.objeto or "",
        "(SOL_OFICIO_JUSTIFICATIVA)": slots.sol_oficio_justificativa or slots.justificativa or "",
        "(SOL_OFICIO_PRAZO_RESPOSTA)": slots.sol_oficio_prazo_resposta or "",
        "(SOL_OFICIO_RESPONSAVEL_NOME)": slots.sol_oficio_responsavel_nome or "",
        "(SOL_OFICIO_RESPONSAVEL_CARGO)": slots.sol_oficio_responsavel_cargo or "",
        "(SOL_OFICIO_RESPONSAVEL_SETOR)": slots.sol_oficio_responsavel_setor or slots.secretaria_usuario or "",
        "(SOL_OFICIO_CIDADE)": slots.cidade or "",
        "(SOL_OFICIO_DATA)": slots.data_termo or "",
    }

    _replace_placeholders(doc, mapping)

    out_path = Path(output_path) if output_path else None
    if out_path is None:
        import tempfile

        tmp_dir = Path(tempfile.gettempdir())
        out_path = tmp_dir / f"oficio_preenchido_{Path(tpl_path).stem}.docx"

    doc.save(str(out_path))
    return str(out_path)
