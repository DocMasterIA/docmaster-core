from __future__ import annotations

"""
Geração de Solicitação/Ofício a partir do modelo fixo
`template_packages/tr_base/OFICIO_modelo_base.docx`, preenchendo apenas os slots.
"""

from pathlib import Path
from typing import Optional

from docx import Document

from .docx_slot_replace import replace_placeholders_in_document
from .tr_template import TRTemplateSlots


TEMPLATE_OFICIO_PATH_DEFAULT = (
    Path(__file__).resolve().parents[2] / "template_packages" / "tr_base" / "OFICIO_modelo_base.docx"
)


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

    replace_placeholders_in_document(doc, mapping)

    out_path = Path(output_path) if output_path else None
    if out_path is None:
        import tempfile

        tmp_dir = Path(tempfile.gettempdir())
        out_path = tmp_dir / f"oficio_preenchido_{Path(tpl_path).stem}.docx"

    doc.save(str(out_path))
    return str(out_path)
