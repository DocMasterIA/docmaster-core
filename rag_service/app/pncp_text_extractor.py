from __future__ import annotations

"""
Extração de texto de anexos PNCP (PDF/DOCX) para posterior criação de chunks.
"""

from pathlib import Path

from .loaders import load_document_text


def extract_text_from_attachment(path: Path) -> str:
    """
    Extrai texto de um anexo PNCP suportado (PDF ou DOCX).

    Args:
        path: Caminho do arquivo baixado.

    Returns:
        Texto extraído (string).

    Raises:
        ValueError se o formato não for suportado.
    """
    return load_document_text(str(path))

