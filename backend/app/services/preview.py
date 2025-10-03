import os
from pathlib import Path
from docx2pdf import convert  # converte docx -> pdf
from pdf2image import convert_from_path  # converte pdf -> imagens
from django.conf import settings


def generate_docx_preview(template):
    """
    Gera imagem PNG borrada do primeiro page do docx para preview.
    Retorna caminho relativo da imagem.
    """
    if not template.file:
        return None

    preview_dir = Path(settings.MEDIA_ROOT) / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)

    docx_path = template.file.path
    pdf_path = preview_dir / f"{template.id}.pdf"
    img_path = preview_dir / f"{template.id}.png"

    # 1️ converte docx -> pdf
    convert(docx_path, str(pdf_path))  # docx2pdf

    # 2️converte PDF -> imagem (primeira página)
    pages = convert_from_path(str(pdf_path), first_page=1, last_page=1, dpi=150)
    if pages:
        pages[0].save(img_path, "PNG")
        return f"previews/{img_path.name}"
    return None