from __future__ import annotations

"""
Geração de Solicitação/Ofício a partir do modelo fixo
`template_packages/tr_base/OFICIO_modelo_base.docx`, preenchendo apenas os slots.
"""

import re
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Optional

from docx import Document

from .deprecated_cargo_slots import clear_deprecated_cargo_fields
from .docx_typography import (
    apply_default_justify_to_document,
    apply_standard_body_font_to_document,
    ensure_signature_nome_blank_lines,
)
from .tr_deixis import adapt_text_for_dfd_or_oficio
from .tr_template import (
    TRTemplateSlots,
    format_date_pt_br_extenso,
    numero_processo_valor_placeholder_tr,
    replace_placeholder_in_paragraph,
    slots_numero_processo_display,
    split_paragraphs_on_double_newline,
    _normalize_multiline_signature_text,
)


TEMPLATE_OFICIO_PATH_DEFAULT = (
    Path(__file__).resolve().parents[2] / "template_packages" / "tr_base" / "OFICIO_modelo_base.docx"
)


def _replace_placeholder_in_paragraph_runs(paragraph, placeholder: str, replacement: str) -> bool:
    changed = replace_placeholder_in_paragraph(paragraph, placeholder, replacement)
    if changed and placeholder == "(SOL_OFICIO_DESTINATARIO_NOME)" and str(replacement or "").strip():
        for idx, run in enumerate(paragraph.runs):
            if (run.text or "").strip():
                _inherit_neighbor_run_style(paragraph, idx)
                break
    return changed


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


def _remove_paragraph_element(paragraph) -> None:
    el = paragraph._element
    parent = el.getparent()
    if parent is not None:
        parent.remove(el)


def _para_visible_text(paragraph) -> str:
    return (paragraph.text or "").replace("\u00a0", " ").strip()


def _is_punctuation_only_paragraph(text: str) -> bool:
    t = (text or "").strip()
    return bool(t) and not re.search(r"\w", t, re.UNICODE)


def _remove_oficio_deprecated_cargo_artifacts(doc: Document) -> None:
    """Remove linhas fantasma de cargo/função e vírgulas órfãs após placeholders vazios."""
    from .docx_typography import _find_signature_nome_paragraph

    paras = list(doc.paragraphs)
    nome_para = _find_signature_nome_paragraph(paras)
    nome_idx = None
    if nome_para is not None:
        try:
            nome_idx = paras.index(nome_para)
        except ValueError:
            nome_idx = None

    if nome_idx is None:
        # Sem âncora detectada: não apagar parágrafos vazios (podem ser espaçamento multilinha).
        for p in list(doc.paragraphs):
            t = _para_visible_text(p)
            if _is_punctuation_only_paragraph(t):
                _remove_paragraph_element(p)
    else:
        for i, p in enumerate(list(doc.paragraphs)):
            if i >= nome_idx:
                break
            t = _para_visible_text(p)
            if not t or _is_punctuation_only_paragraph(t):
                _remove_paragraph_element(p)

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


def render_oficio_from_slots(
    slots: TRTemplateSlots,
    template_path: Optional[Path | str] = None,
    output_path: Optional[Path | str] = None,
) -> str:
    tpl_path = Path(template_path) if template_path else TEMPLATE_OFICIO_PATH_DEFAULT
    if not tpl_path.exists():
        raise FileNotFoundError(f"Template OFICIO não encontrado: {tpl_path}")

    slots = clear_deprecated_cargo_fields(slots)

    doc = Document(str(tpl_path))

    num_proc = slots_numero_processo_display(slots)
    num_proc_tr_placeholder = numero_processo_valor_placeholder_tr(num_proc)

    data_oficio_extenso = format_date_pt_br_extenso(slots.data_termo)

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
        "(SOL_OFICIO_OBJETO)": adapt_text_for_dfd_or_oficio(
            (slots.sol_oficio_objeto or slots.objeto or "").strip()
        ),
        "(SOL_OFICIO_JUSTIFICATIVA)": adapt_text_for_dfd_or_oficio(
            (slots.sol_oficio_justificativa or slots.justificativa or "").strip()
        ),
        "(SOL_OFICIO_PRAZO_RESPOSTA)": slots.sol_oficio_prazo_resposta or "",
        "(SOL_OFICIO_RESPONSAVEL_NOME)": _normalize_multiline_signature_text(
            slots.sol_oficio_responsavel_nome or ""
        ),
        "(SOL_OFICIO_RESPONSAVEL_CARGO)": slots.sol_oficio_responsavel_cargo or "",
        "(SOL_OFICIO_RESPONSAVEL_SETOR)": slots.sol_oficio_responsavel_setor or "",
        "(SOL_OFICIO_CIDADE)": slots.cidade or "",
        "(SOL_OFICIO_DATA)": data_oficio_extenso,
    }

    _replace_placeholders(doc, mapping)
    split_paragraphs_on_double_newline(doc)
    _remove_oficio_deprecated_cargo_artifacts(doc)

    apply_standard_body_font_to_document(doc)
    apply_default_justify_to_document(doc)

    ensure_signature_nome_blank_lines(doc)

    out_path = Path(output_path) if output_path else None
    if out_path is None:
        import tempfile

        tmp_dir = Path(tempfile.gettempdir())
        out_path = tmp_dir / f"oficio_preenchido_{Path(tpl_path).stem}_{uuid.uuid4().hex}.docx"

    doc.save(str(out_path))
    return str(out_path)
