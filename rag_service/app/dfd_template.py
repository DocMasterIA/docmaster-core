from __future__ import annotations

"""
Geração de Documento de Formalização da Demanda (DFD) a partir do modelo fixo
`templates/tr_base/DFD_modelo_base.docx`, preenchendo apenas os slots
marcados entre parênteses.

Este módulo NÃO chama IA – ele só aplica os dados já gerados para o TR
em cima do template de DFD.
"""

from pathlib import Path
from typing import Optional

from docx import Document

from .tr_template import TRTemplateSlots


TEMPLATE_DFD_PATH_DEFAULT = (
    Path(__file__).resolve().parents[2] / "templates" / "tr_base" / "DFD_modelo_base.docx"
)


def _replace_placeholders(doc: Document, mapping: dict[str, str]) -> None:
    """Substitui placeholders em parágrafos e células de tabelas."""
    # Parágrafos
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

    # Células de tabela
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


def render_dfd_from_tr_slots(
    slots: TRTemplateSlots,
    template_path: Optional[Path | str] = None,
    output_path: Optional[Path | str] = None,
) -> str:
    """
    Gera o DFD a partir:
    - do objeto e da justificativa já gerados para o TR; e
    - da cidade do usuário (preenchida em slots.cidade pelo backend).

    Mapeamento de placeholders no DFD_modelo_base.docx:
    - (Descrever objeto do termo de referencia)           -> slots.objeto
    - (descrever a justificativa usada no termo de referencias) -> slots.justificativa
    - (CIDADE)                                            -> slots.cidade
    """
    tpl_path = Path(template_path) if template_path else TEMPLATE_DFD_PATH_DEFAULT
    if not tpl_path.exists():
        raise FileNotFoundError(f"Template DFD não encontrado: {tpl_path}")

    doc = Document(str(tpl_path))

    mapping = {
        "(Descrever objeto do termo de referencia)": slots.objeto or "",
        "(descrever a justificativa usada no termo de referencias)": slots.justificativa or "",
        "(CIDADE)": slots.cidade or "",
    }

    _replace_placeholders(doc, mapping)

    out_path = Path(output_path) if output_path else None
    if out_path is None:
        import tempfile

        tmp_dir = Path(tempfile.gettempdir())
        out_path = tmp_dir / f"dfd_preenchido_{Path(tpl_path).stem}.docx"

    doc.save(str(out_path))
    return str(out_path)

