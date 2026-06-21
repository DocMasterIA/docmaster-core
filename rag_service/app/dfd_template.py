from __future__ import annotations

"""
Geração de Documento de Formalização da Demanda (DFD) a partir do modelo fixo
(`DFD_modelo_base.docx` ou, sem número de processo quando existir no pacote,
`DFD_modelo_base_v2.docx`), preenchendo os mesmos slots.

Este módulo NÃO chama IA – aplica os dados já gerados para o TR em cima do template de DFD.
"""

import re
import uuid
from pathlib import Path
from typing import Optional

from docx import Document

from .docx_typography import (
    apply_default_justify_to_document,
    apply_dfd_inclusive_role_labels,
    apply_standard_body_font_to_document,
    clamp_docx_paragraph_indents,
)
from .tr_deixis import adapt_text_for_dfd_or_oficio
from .tr_template import (
    TRTemplateSlots,
    format_date_pt_br_extenso,
    numero_processo_valor_placeholder_tr,
    slots_numero_processo_display,
    split_paragraphs_on_double_newline,
    _append_multiline_to_run,
    _normalize_slot_block,
)


TEMPLATE_DFD_PATH_DEFAULT = (
    Path(__file__).resolve().parents[2] / "template_packages" / "tr_base" / "DFD_modelo_base.docx"
)


def _dfd_numero_processo_display(slots: TRTemplateSlots) -> str:
    """Número exibido no DFD (mesma regra que TR/ofício: dfd_numero_processo, depois numero_processo)."""
    return slots_numero_processo_display(slots)


def dfd_numero_processo_filled(slots: Optional[TRTemplateSlots]) -> bool:
    """True quando há número de processo (DFD ou TR); controla escolha v1 vs `DFD_modelo_base_v2.docx`."""
    if slots is None:
        return True
    return bool(_dfd_numero_processo_display(slots).strip())


def _strip_invisible(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"[\s\u00a0\u200b-\u200d\ufeff]+", "", s)


def _element_xml_lower(el) -> str:
    """Serialização XML do elemento em minúsculas (compatível com bytes ou XmlString/lxml)."""
    raw = getattr(el, "xml", None) or ""
    if isinstance(raw, (bytes, bytearray)):
        return raw.decode("utf-8", errors="ignore").lower()
    return str(raw).lower()


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
        before = txt[:start_off]
        after = txt[end_off:]
        run = runs[start_idx]
        run.text = before
        if "\n" in replacement:
            _append_multiline_to_run(run, replacement)
            if after:
                run.add_text(after)
        else:
            run.text = before + replacement + after
    else:
        prefix = (runs[start_idx].text or "")[:start_off]
        suffix = (runs[end_idx].text or "")[end_off:]
        run = runs[start_idx]
        run.text = prefix
        if "\n" in replacement:
            _append_multiline_to_run(run, replacement)
            if suffix:
                run.add_text(suffix)
        else:
            run.text = prefix + replacement + suffix
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


def _remove_paragraph_element(paragraph) -> None:
    el = paragraph._element
    parent = el.getparent()
    if parent is not None:
        parent.remove(el)


def _table_has_process_line_sem_numero(table) -> bool:
    """Há linha de «processo» sem dígito (rótulo vazio / só texto) — usado para decidir remoção de linhas em branco."""
    for row in table.rows:
        joined = " ".join((c.text or "") for c in row.cells)
        j = re.sub(r"\s+", " ", joined).strip()
        if not j:
            continue
        low = j.lower()
        if "processo" not in low:
            continue
        if re.search(r"\d", j):
            continue
        return True
    return False


def _remove_nonempty_process_row_without_number(table, row) -> bool:
    raw_join = " ".join((c.text or "") for c in row.cells)
    t_show = re.sub(r"\s+", " ", raw_join).strip()
    if not _strip_invisible(raw_join):
        return False
    if re.search(r"\d", t_show):
        return False
    low = t_show.lower()
    if "processo" not in low:
        return False
    if re.fullmatch(r"N[º°o\.]?\s*Processo\s*:?", t_show, re.IGNORECASE):
        return True
    return len(t_show) <= 48


def _remove_processo_visual_block_when_empty(doc: Document) -> None:
    """
    Após substituir placeholders, remove linhas/parágrafos do bloco «Nº Processo»
    quando não há número, evitando linha vazia com bordas ou só com formatação.
    Duas passagens em tabelas: primeiro linhas em branco ligadas ao campo, depois
    a linha do rótulo (caso contrário o helper deixa de ver «processo» e a linha
    em branco não seria detectada).
    """
    proc_label = re.compile(r"^N[º°o\.]?\s*Processo\s*:?\s*$", re.IGNORECASE)

    for table in list(doc.tables):
        for row in list(table.rows):
            raw_join = " ".join((c.text or "") for c in row.cells)
            if not _strip_invisible(raw_join) and _table_has_process_line_sem_numero(table):
                table._tbl.remove(row._tr)
        for row in list(table.rows):
            if _remove_nonempty_process_row_without_number(table, row):
                table._tbl.remove(row._tr)

    for p in list(doc.paragraphs):
        t = (p.text or "").replace("\u00a0", " ").strip()
        if proc_label.fullmatch(t):
            _remove_paragraph_element(p)
            continue
        if not t:
            xml_l = _element_xml_lower(p._element)
            if "processo" in xml_l and not re.search(r"\d", xml_l):
                _remove_paragraph_element(p)

    # Tabela de uma linha que ficou só com células vazias (ex.: só o placeholder do processo).
    for table in list(doc.tables):
        if len(table.rows) != 1:
            continue
        r0 = table.rows[0]
        if _strip_invisible(" ".join((c.text or "") for c in r0.cells)):
            continue
        tbl_el = table._tbl
        parent = tbl_el.getparent()
        if parent is not None:
            parent.remove(tbl_el)


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
    - (NUMERO PROCESSO)                                            -> dfd_numero_processo ou numero_processo
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

    dfd_data_text = format_date_pt_br_extenso(slots.dfd_data or slots.data_termo or "")

    dfd_obj = adapt_text_for_dfd_or_oficio(
        (slots.dfd_objeto_referencia or slots.objeto or "").strip()
    )
    dfd_just = adapt_text_for_dfd_or_oficio(
        (slots.dfd_justificativa or slots.justificativa or "").strip()
    )
    num_proc = _dfd_numero_processo_display(slots)
    num_proc_tr_style = numero_processo_valor_placeholder_tr(num_proc)
    mapping = {
        # Placeholders padronizados (preferenciais)
        "(DFD_OBJETO_REFERENCIA)": dfd_obj,
        "(DFD_JUSTIFICATIVA)": dfd_just,
        "(DFD_CIDADE)": slots.cidade or "",
        "(DFD_SETOR_REQUISITANTE)": slots.dfd_setor_requisitante or "",
        "(DFD_NUMERO_PROCESSO)": num_proc,
        "(NUMERO_PROCESSO)": num_proc_tr_style,
        "( NUMERO_PROCESSO )": num_proc_tr_style,
        "(NUMERO PROCESSO)": num_proc_tr_style,
        "( NUMERO PROCESSO )": num_proc_tr_style,
        "(DFD_RESPONSAVEL_DEMANDA)": slots.dfd_responsavel_demanda or "",
        "(DFD_EMAIL)": slots.dfd_email or "",
        "(DFD_GESTOR_CONTRATOS)": slots.dfd_gestor_contratos or "",
        "(DFD_FISCAL_CONTRATOS)": slots.dfd_fiscal_contratos or "",
        "(DFD_CARGO_ASSINATURA)": slots.dfd_assinatura_cargo or "",
        "(DFD_NOME_ASSINATURA)": _normalize_slot_block(slots.dfd_assinatura_nome or ""),
        "(DFD_DATA)": dfd_data_text,
        # Placeholders legados (mesmo conteúdo que DFD_OBJETO_REFERENCIA / DFD_JUSTIFICATIVA)
        "(Descrever objeto do termo de referencia)": dfd_obj,
        "(descrever a justificativa usada no termo de referencias)": dfd_just,
        "(CIDADE)": slots.cidade or "",
        # Placeholders novos de identificação/assinatura do DFD
        "(SETOR REQUISITANTE)": slots.dfd_setor_requisitante or "",
        "(RESPONSAVEL DEMANDA)": slots.dfd_responsavel_demanda or "",
        "(EMAIL DFD)": slots.dfd_email or "",
        "(GESTORA CONTRATOS)": slots.dfd_gestor_contratos or "",
        "(FISCAL CONTRATOS)": slots.dfd_fiscal_contratos or "",
        "(CARGO ASSINATURA DFD)": slots.dfd_assinatura_cargo or "",
        "(NOME ASSINATURA DFD)": _normalize_slot_block(slots.dfd_assinatura_nome or ""),
        "(DATA DFD)": dfd_data_text,
    }

    # Quando o número de processo não for informado, remove também o rótulo textual
    # para não deixar "Nº Processo:" vazio no DFD.
    if not num_proc:
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
    apply_dfd_inclusive_role_labels(doc)
    split_paragraphs_on_double_newline(doc)
    if not num_proc:
        _remove_processo_visual_block_when_empty(doc)

    clamp_docx_paragraph_indents(doc)

    apply_standard_body_font_to_document(doc)
    apply_default_justify_to_document(doc)

    out_path = Path(output_path) if output_path else None
    if out_path is None:
        import tempfile

        tmp_dir = Path(tempfile.gettempdir())
        out_path = tmp_dir / f"dfd_preenchido_{Path(tpl_path).stem}_{uuid.uuid4().hex}.docx"

    doc.save(str(out_path))
    return str(out_path)

