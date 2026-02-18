"""
Módulo de geração de DOCX e PDF a partir de JSON.

Recebe o JSON retornado por generate_full_document (structure + section_texts)
e gera documento Word com:
- Títulos de seção/subseção (níveis hierárquicos)
- Formatação de tabelas
- Textos de cláusulas

Futuro: cabeçalho e rodapé configuráveis pelo usuário.
"""
from __future__ import annotations

import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

FONT_NAME = "Times New Roman"
FONT_COLOR = RGBColor(0, 0, 0)


def _apply_document_styles(doc: Document) -> None:
    """Define fonte Times New Roman e cor preta em todos os estilos do documento."""
    for style_name in ("Normal", "Title", "Heading 1", "Heading 2", "Heading 3", "List Paragraph"):
        try:
            style = doc.styles[style_name]
            style.font.name = FONT_NAME
            style.font.color.rgb = FONT_COLOR
        except KeyError:
            pass


def _add_table_borders(table, style: str = "single") -> None:
    """Aplica bordas à tabela."""
    tbl = table._tbl
    tblPr = tbl.tblPr
    if tblPr is None:
        tblPr = OxmlElement("w:tblPr")
        tbl.insert(0, tblPr)
    tblBorders = OxmlElement("w:tblBorders")
    for border_name in ["top", "left", "bottom", "right", "insideH", "insideV"]:
        border = OxmlElement(f"w:{border_name}")
        border.set(qn("w:val"), style)
        border.set(qn("w:sz"), "4")
        border.set(qn("w:space"), "0")
        border.set(qn("w:color"), "000000")
        tblBorders.append(border)
    tblPr.append(tblBorders)


def _render_section(
    doc: Document,
    node: Dict[str, Any],
    section_texts: Dict[str, Any],
    table_data: Dict[str, List[Dict]],
    level: int,
) -> None:
    """Renderiza recursivamente uma seção (título + conteúdo)."""
    key = node.get("key", "")
    title = node.get("title", key)
    content_type = node.get("content_type", "text")
    children = node.get("children") or []

    # Título (Heading 1, 2, 3 conforme nível)
    heading_level = min(level + 1, 3)
    heading = doc.add_heading(title, level=heading_level)

    if content_type == "text":
        text = section_texts.get(key)
        if isinstance(text, str) and text.strip():
            for para in text.strip().split("\n\n"):
                p = doc.add_paragraph(para.strip())
                p.paragraph_format.space_after = Pt(6)
        elif not text or (isinstance(text, str) and not text.strip()):
            doc.add_paragraph("[Conteúdo a preencher]").paragraph_format.space_after = Pt(6)

    elif content_type == "table":
        schema = node.get("table_schema") or {}
        columns = schema.get("columns") or []
        if not columns:
            doc.add_paragraph("[Tabela sem definição de colunas]")
        else:
            # Linhas: table_data[key] ou placeholder
            rows_data = table_data.get(key) if isinstance(table_data.get(key), list) else []
            if not rows_data:
                rows_data = [{}]  # Uma linha vazia como placeholder
            num_rows = len(rows_data) + 1  # +1 para cabeçalho
            num_cols = len(columns)
            table = doc.add_table(rows=num_rows, cols=num_cols)
            table.style = "Table Grid"
            _add_table_borders(table)
            # Cabeçalho
            hdr_cells = table.rows[0].cells
            for i, col in enumerate(columns):
                if i < len(hdr_cells):
                    cell = hdr_cells[i]
                    cell.text = str(col.get("label", col.get("key", "")))
                    for paragraph in cell.paragraphs:
                        for run in paragraph.runs:
                            run.bold = True
            # Dados
            col_keys = [c.get("key") for c in columns]
            for row_idx, row_dict in enumerate(rows_data):
                if row_idx + 1 >= len(table.rows):
                    break
                cells = table.rows[row_idx + 1].cells
                for col_idx, col_key in enumerate(col_keys):
                    if col_idx < len(cells):
                        val = row_dict.get(col_key, row_dict.get(columns[col_idx].get("label", ""), ""))
                        cells[col_idx].text = str(val) if val is not None else ""
            doc.add_paragraph()  # Espaço após tabela

    elif content_type == "list":
        text = section_texts.get(key)
        if isinstance(text, str) and text.strip():
            for line in text.strip().split("\n"):
                doc.add_paragraph(line.strip(), style="List Bullet")
        else:
            doc.add_paragraph("[Lista a preencher]", style="List Bullet")

    # Subseções
    for child in children:
        _render_section(doc, child, section_texts, table_data, level + 1)


def _document_type_to_title(document_type: str) -> str:
    """Mapeia document_type (snake_case) para título formatado com acentuação."""
    dt = (document_type or "").strip().lower()
    mapping = {
        "documento_formalizacao_demanda": "Documento de Formalização da Demanda",
        "dfd": "Documento de Formalização da Demanda",
        "termo_referencia": "Termo de Referência",
        "termo de referência": "Termo de Referência",
        "estudo_tecnico_preliminar": "Estudo Técnico Preliminar",
        "etp": "Estudo Técnico Preliminar",
    }
    return mapping.get(dt) or dt.replace("_", " ").title()


def json_to_docx(
    data: Dict[str, Any],
    output_path: Optional[str] = None,
    table_data: Optional[Dict[str, List[Dict]]] = None,
) -> str:
    """
    Gera arquivo DOCX a partir do JSON de documento.

    Args:
        data: Dict com structure (document_type, root_sections) e section_texts.
        output_path: Caminho do arquivo de saída. Se None, usa tempfile.
        table_data: Opcional. Dict {section_key: [{"col_key": "value", ...}, ...]}
                   para preencher tabelas. Se ausente, tabelas ficam com placeholder.

    Returns:
        Caminho do arquivo DOCX gerado.
    """
    structure = data.get("structure") or {}
    section_texts = data.get("section_texts") or {}
    table_data = table_data or {}

    # Permite structure aninhado (resposta do llm_agent)
    if isinstance(structure, dict) and "structure" in structure:
        structure = structure["structure"]
    root_sections = structure.get("root_sections") or []

    doc = Document()
    _apply_document_styles(doc)
    doc_type = structure.get("document_type", "documento")
    title_para = doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_para.add_run(_document_type_to_title(doc_type))
    title_run.font.name = FONT_NAME
    title_run.font.size = Pt(16)
    title_run.font.bold = True
    title_run.font.color.rgb = FONT_COLOR
    title_para.paragraph_format.space_after = Pt(6)

    for node in root_sections:
        _render_section(doc, node, section_texts, table_data, level=0)

    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=".docx")
        import os
        os.close(fd)
    else:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    doc.save(output_path)
    return output_path


def docx_to_pdf(docx_path: str, pdf_path: Optional[str] = None) -> Optional[str]:
    """
    Converte DOCX para PDF usando LibreOffice (headless).

    Requer LibreOffice instalado: apt-get install libreoffice

    Returns:
        Caminho do PDF gerado ou None se conversão falhar.
    """
    docx_path = str(Path(docx_path).resolve())
    out_dir = Path(docx_path).parent
    if pdf_path is None:
        pdf_path = str(out_dir / (Path(docx_path).stem + ".pdf"))

    try:
        subprocess.run(
            [
                "libreoffice",
                "--headless",
                "--convert-to", "pdf",
                "--outdir", str(out_dir),
                docx_path,
            ],
            check=True,
            capture_output=True,
            timeout=60,
        )
        expected_pdf = out_dir / (Path(docx_path).stem + ".pdf")
        if expected_pdf.exists():
            return str(expected_pdf)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def json_to_docx_and_pdf(
    data: Dict[str, Any],
    output_dir: Optional[str] = None,
    base_name: Optional[str] = None,
    table_data: Optional[Dict[str, List[Dict]]] = None,
) -> Dict[str, Any]:
    """
    Gera DOCX e, se possível, PDF a partir do JSON.

    Args:
        data: JSON com structure e section_texts.
        output_dir: Diretório de saída. Se None, usa tempfile.gettempdir().
        base_name: Nome base dos arquivos (sem extensão). Se None, usa UUID.
        table_data: Dados opcionais para tabelas.

    Returns:
        {
            "docx_path": str,
            "pdf_path": str | None,
            "pdf_available": bool,
        }
    """
    import os
    output_dir = output_dir or tempfile.gettempdir()
    base_name = base_name or f"docmaster_{uuid.uuid4().hex[:8]}"
    docx_path = str(Path(output_dir) / f"{base_name}.docx")

    docx_path = json_to_docx(data, output_path=docx_path, table_data=table_data)
    pdf_path = docx_to_pdf(docx_path)

    return {
        "docx_path": docx_path,
        "pdf_path": pdf_path,
        "pdf_available": pdf_path is not None,
    }
