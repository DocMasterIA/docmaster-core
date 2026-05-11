from __future__ import annotations

"""
Geração de Solicitação/Ofício a partir do modelo fixo
`template_packages/tr_base/OFICIO_modelo_base.docx`, preenchendo apenas os slots.
"""

import uuid
from copy import deepcopy
from pathlib import Path
from typing import Optional

from docx import Document

from .docx_typography import apply_default_justify_to_document, apply_standard_body_font_to_document

from .tr_template import (
    TRTemplateSlots,
    numero_processo_valor_placeholder_tr,
    slots_numero_processo_display,
    split_paragraphs_on_double_newline,
)


TEMPLATE_OFICIO_PATH_DEFAULT = (
    Path(__file__).resolve().parents[2] / "template_packages" / "tr_base" / "OFICIO_modelo_base.docx"
)


def _replace_placeholder_in_paragraph_runs(paragraph, placeholder: str, replacement: str) -> bool:
    runs = paragraph.runs
    if not runs:
        return False
    full_text = "".join(run.text or "" for run in runs)
    start = full_text.find(placeholder)
    if start < 0:
        return False
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
        return False

    if start_idx == end_idx:
        txt = runs[start_idx].text or ""
        runs[start_idx].text = txt[:start_off] + replacement + txt[end_off:]
        target_idx = start_idx
    else:
        prefix = (runs[start_idx].text or "")[:start_off]
        suffix = (runs[end_idx].text or "")[end_off:]
        runs[start_idx].text = prefix + replacement + suffix
        for idx in range(start_idx + 1, end_idx + 1):
            runs[idx].text = ""
        target_idx = start_idx

    if placeholder == "(SOL_OFICIO_DESTINATARIO_NOME)" and replacement.strip():
        _inherit_neighbor_run_style(paragraph, target_idx)
    return True


def _inherit_neighbor_run_style(paragraph, target_idx: int) -> None:
    runs = paragraph.runs
    if target_idx < 0 or target_idx >= len(runs):
        return
    target = runs[target_idx]
    if not (target.text or "").strip():
        return

    source = None
    for delta in range(1, len(runs)):
        left = target_idx - delta
        if left >= 0:
            candidate = runs[left]
            if (candidate.text or "").strip():
                source = candidate
                break
        right = target_idx + delta
        if right < len(runs):
            candidate = runs[right]
            if (candidate.text or "").strip():
                source = candidate
                break

    if source is None:
        return

    src_rpr = source._element.rPr
    if src_rpr is None:
        return

    tgt_el = target._element
    old_rpr = tgt_el.rPr
    if old_rpr is not None:
        tgt_el.remove(old_rpr)
    tgt_el.insert(0, deepcopy(src_rpr))


def _replace_placeholders_in_paragraph(paragraph, mapping: dict[str, str]) -> bool:
    changed = False
    for ph, val in mapping.items():
        if not ph:
            continue
        replacement = "" if val is None else str(val)
        max_iters = 100
        iters = 0
        while iters < max_iters and _replace_placeholder_in_paragraph_runs(paragraph, ph, replacement):
            changed = True
            iters += 1
            if ph and ph in replacement:
                break
    return changed


def _replace_placeholders(doc: Document, mapping: dict[str, str]) -> None:
    for p in doc.paragraphs:
        _replace_placeholders_in_paragraph(p, mapping)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    _replace_placeholders_in_paragraph(p, mapping)


def render_oficio_from_slots(
    slots: TRTemplateSlots,
    template_path: Optional[Path | str] = None,
    output_path: Optional[Path | str] = None,
) -> str:
    tpl_path = Path(template_path) if template_path else TEMPLATE_OFICIO_PATH_DEFAULT
    if not tpl_path.exists():
        raise FileNotFoundError(f"Template OFICIO não encontrado: {tpl_path}")

    doc = Document(str(tpl_path))

    num_proc = slots_numero_processo_display(slots)
    num_proc_tr_placeholder = numero_processo_valor_placeholder_tr(num_proc)

    mapping = {
        "(NUMERO_PROCESSO)": num_proc_tr_placeholder,
        "( NUMERO_PROCESSO )": num_proc_tr_placeholder,
        "(NUMERO PROCESSO)": num_proc_tr_placeholder,
        "( NUMERO PROCESSO )": num_proc_tr_placeholder,
        "(AO_SENHOR_GENERO)": slots.ao_senhor_genero or "",
        "( AO_SENHOR_GENERO )": slots.ao_senhor_genero or "",
        "(SENHOR_SENHORA_GENERO)": slots.senhor_senhora_genero or "",
        "( SENHOR_SENHORA_GENERO )": slots.senhor_senhora_genero or "",
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
    split_paragraphs_on_double_newline(doc)

    apply_standard_body_font_to_document(doc)
    apply_default_justify_to_document(doc)

    out_path = Path(output_path) if output_path else None
    if out_path is None:
        import tempfile

        tmp_dir = Path(tempfile.gettempdir())
        out_path = tmp_dir / f"oficio_preenchido_{Path(tpl_path).stem}_{uuid.uuid4().hex}.docx"

    doc.save(str(out_path))
    return str(out_path)
