"""
Loaders para diferentes formatos de documento (PDF, DOCX).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional


def load_pdf_text(path: str) -> str:
    """
    Extrai texto de um arquivo PDF.
    
    Args:
        path: Caminho do arquivo PDF.
    
    Returns:
        Texto extraído.
    """
    from pypdf import PdfReader
    
    reader = PdfReader(path)
    text_parts = []
    
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text_parts.append(page_text)
    
    return "\n\n".join(text_parts)


def load_docx_text(path: str) -> str:
    """
    Extrai texto de um arquivo DOCX.
    
    Args:
        path: Caminho do arquivo DOCX.
    
    Returns:
        Texto extraído.
    """
    import docx2txt
    
    return docx2txt.process(path)


def load_document_text(path: str) -> str:
    """
    Detecta tipo e extrai texto do documento.
    
    Args:
        path: Caminho do arquivo (PDF ou DOCX).
    
    Returns:
        Texto extraído.
    
    Raises:
        ValueError: Se o formato não for suportado.
    """
    p = Path(path)
    suffix = p.suffix.lower()
    
    if suffix == ".pdf":
        return load_pdf_text(path)
    elif suffix in (".docx", ".doc"):
        return load_docx_text(path)
    else:
        raise ValueError(f"Formato não suportado: {suffix}. Use PDF ou DOCX.")


def get_file_metadata(path: str) -> dict:
    """
    Extrai metadados básicos do arquivo.
    
    Args:
        path: Caminho do arquivo.
    
    Returns:
        Dict com nome, extensão, tamanho.
    """
    p = Path(path)
    
    return {
        "source_file": p.name,
        "file_extension": p.suffix.lower(),
        "file_size_bytes": p.stat().st_size if p.exists() else 0,
    }
