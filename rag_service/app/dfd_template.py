from __future__ import annotations

"""
Geração de Documento de Formalização da Demanda (DFD) a partir do modelo fixo
`template_packages/tr_base/DFD_modelo_base.docx`, preenchendo apenas os slots
marcados entre parênteses.

Este módulo NÃO chama IA – ele só aplica os dados já gerados para o TR
em cima do template de DFD.
"""

import re
from pathlib import Path
from typing import Optional

from docx import Document

from .tr_template import TRTemplateSlots


TEMPLATE_DFD_PATH_DEFAULT = (
    Path(__file__).resolve().parents[2] / "template_packages" / "tr_base" / "DFD_modelo_base.docx"
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
    else:
        prefix = (runs[start_idx].text or "")[:start_off]
        suffix = (runs[end_idx].text or "")[end_off:]
        runs[start_idx].text = prefix + replacement + suffix
        for idx in range(start_idx + 1, end_idx + 1):
            runs[idx].text = ""
    return True


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
    """Substitui placeholders em parágrafos e células de tabelas."""
    for p in doc.paragraphs:
        _replace_placeholders_in_paragraph(p, mapping)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    _replace_placeholders_in_paragraph(p, mapping)


def _remove_processo_visual_block_when_empty(doc: Document) -> None:
    """
    Remove o bloco textual de processo quando não informado, incluindo o rótulo
    e eventual placeholder, para não sobrar trilha de formatação no DFD.
    """
    patterns = [
        re.compile(r"\s*N[º°o]\s*Processo\s*:\s*\((?:DFD_NUMERO_PROCESSO|NUMERO PROCESSO)\)\s*", re.IGNORECASE),
        re.compile(r"\s*N[º°o]\s*Processo\s*:\s*", re.IGNORECASE),
    ]

    def _clean_paragraph(p) -> None:
        text = p.text or ""
        if not text:
            return
        cleaned = text
        for pat in patterns:
            cleaned = pat.sub(" ", cleaned)
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
        if cleaned != text:
            p.text = cleaned

    # 1) Remove linhas inteiras de tabela que contenham o bloco de processo
    # (no template de inexigibilidade esse campo vive em uma linha própria).
    row_tokens = (
        "DFD_NUMERO_PROCESSO",
        "NUMERO PROCESSO",
        "Nº Processo",
        "N° Processo",
        "No Processo",
    )
    for table in doc.tables:
        for row in list(table.rows):
            row_text = " ".join((cell.text or "") for cell in row.cells)
            if any(token in row_text for token in row_tokens):
                table._tbl.remove(row._tr)

    # 2) Limpa eventuais parágrafos fora de tabela com o mesmo bloco
    for p in doc.paragraphs:
        _clean_paragraph(p)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    _clean_paragraph(p)


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
    - (Descrever objeto do termo de referencia)                    -> slots.objeto
    - (descrever a justificativa usada no termo de referencias)    -> slots.justificativa
    - (CIDADE)                                                     -> slots.cidade
    - (SETOR REQUISITANTE)                                         -> slots.dfd_setor_requisitante
    - (NUMERO PROCESSO)                                            -> slots.dfd_numero_processo
    - (RESPONSAVEL DEMANDA)                                        -> slots.dfd_responsavel_demanda
    - (EMAIL DFD)                                                  -> slots.dfd_email
    - (GESTORA CONTRATOS)                                          -> slots.dfd_gestor_contratos
    - (FISCAL CONTRATOS)                                           -> slots.dfd_fiscal_contratos
    - (CARGO ASSINATURA DFD)                                       -> slots.dfd_assinatura_cargo
    - (NOME ASSINATURA DFD)                                        -> slots.dfd_assinatura_nome
    - (DATA DFD)                                                   -> slots.dfd_data
    """
    tpl_path = Path(template_path) if template_path else TEMPLATE_DFD_PATH_DEFAULT
    if not tpl_path.exists():
        raise FileNotFoundError(f"Template DFD não encontrado: {tpl_path}")

    doc = Document(str(tpl_path))
    dfd_data_text = slots.dfd_data or slots.data_termo or ""

    dfd_obj = (slots.dfd_objeto_referencia or slots.objeto or "").strip()
    dfd_just = (slots.dfd_justificativa or slots.justificativa or "").strip()
    mapping = {
        # Placeholders padronizados (preferenciais)
        "(DFD_OBJETO_REFERENCIA)": dfd_obj,
        "(DFD_JUSTIFICATIVA)": dfd_just,
        "(DFD_CIDADE)": slots.cidade or "",
        "(DFD_SETOR_REQUISITANTE)": slots.dfd_setor_requisitante or "",
        "(DFD_NUMERO_PROCESSO)": slots.dfd_numero_processo or "",
        "(DFD_RESPONSAVEL_DEMANDA)": slots.dfd_responsavel_demanda or "",
        "(DFD_EMAIL)": slots.dfd_email or "",
        "(DFD_GESTOR_CONTRATOS)": slots.dfd_gestor_contratos or "",
        "(DFD_FISCAL_CONTRATOS)": slots.dfd_fiscal_contratos or "",
        "(DFD_CARGO_ASSINATURA)": slots.dfd_assinatura_cargo or "",
        "(DFD_NOME_ASSINATURA)": slots.dfd_assinatura_nome or "",
        "(DFD_DATA)": dfd_data_text,
        # Placeholders legados (mesmo conteúdo que DFD_OBJETO_REFERENCIA / DFD_JUSTIFICATIVA)
        "(Descrever objeto do termo de referencia)": dfd_obj,
        "(descrever a justificativa usada no termo de referencias)": dfd_just,
        "(CIDADE)": slots.cidade or "",
        # Placeholders novos de identificação/assinatura do DFD
        "(SETOR REQUISITANTE)": slots.dfd_setor_requisitante or "",
        "(NUMERO PROCESSO)": slots.dfd_numero_processo or "",
        "(RESPONSAVEL DEMANDA)": slots.dfd_responsavel_demanda or "",
        "(EMAIL DFD)": slots.dfd_email or "",
        "(GESTORA CONTRATOS)": slots.dfd_gestor_contratos or "",
        "(FISCAL CONTRATOS)": slots.dfd_fiscal_contratos or "",
        "(CARGO ASSINATURA DFD)": slots.dfd_assinatura_cargo or "",
        "(NOME ASSINATURA DFD)": slots.dfd_assinatura_nome or "",
        "(DATA DFD)": dfd_data_text,
    }

    # Quando o número de processo não for informado, remove também o rótulo textual
    # para não deixar "Nº Processo:" vazio no DFD.
    if not str(slots.dfd_numero_processo or "").strip():
        process_cleanup = {
            "Nº Processo: (DFD_NUMERO_PROCESSO)": "",
            "N° Processo: (DFD_NUMERO_PROCESSO)": "",
            "No Processo: (DFD_NUMERO_PROCESSO)": "",
            "Nº Processo :(DFD_NUMERO_PROCESSO)": "",
            "N° Processo :(DFD_NUMERO_PROCESSO)": "",
            "No Processo :(DFD_NUMERO_PROCESSO)": "",
            "Nº Processo: (NUMERO PROCESSO)": "",
            "N° Processo: (NUMERO PROCESSO)": "",
            "No Processo: (NUMERO PROCESSO)": "",
            "Nº Processo : (NUMERO PROCESSO)": "",
            "N° Processo : (NUMERO PROCESSO)": "",
            "No Processo : (NUMERO PROCESSO)": "",
            "Nº Processo:": "",
            "N° Processo:": "",
            "No Processo:": "",
        }
        mapping = {**process_cleanup, **mapping}

    _replace_placeholders(doc, mapping)
    if not str(slots.dfd_numero_processo or "").strip():
        _remove_processo_visual_block_when_empty(doc)

    out_path = Path(output_path) if output_path else None
    if out_path is None:
        import tempfile

        tmp_dir = Path(tempfile.gettempdir())
        out_path = tmp_dir / f"dfd_preenchido_{Path(tpl_path).stem}.docx"

    doc.save(str(out_path))
    return str(out_path)

