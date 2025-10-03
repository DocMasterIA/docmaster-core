import os
from pathlib import Path
from docx2pdf import convert  # converte docx -> pdf
from pdf2image import convert_from_path  # converte pdf -> imagens
from django.conf import settings
import subprocess
from PIL import Image, ImageFilter
from django.conf import settings
from django.core.files.base import ContentFile


def generate_docx_preview(template):
    """
    Gera uma miniatura PNG borrada do template .docx usando LibreOffice + pdf2image + Pillow
    Salva no campo `preview_image` do template.
    """
    if not template.file:
        return None

    # Paths temporários
    tmp_dir = Path(settings.MEDIA_ROOT) / "tmp_previews"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    docx_path = Path(template.file.path)
    pdf_path = tmp_dir / f"{docx_path.stem}.pdf"

    # 1️⃣ Converter DOCX -> PDF via LibreOffice
    try:
        subprocess.run([
            "libreoffice",
            "--headless",
            "--convert-to", "pdf",
            "--outdir", str(tmp_dir),
            str(docx_path)
        ], check=True)
    except subprocess.CalledProcessError:
        print("Erro ao converter DOCX para PDF")
        return None

    if not pdf_path.exists():
        print("PDF não foi gerado")
        return None

    # 2️⃣ Converter PDF -> imagem
    try:
        images = convert_from_path(str(pdf_path), first_page=1, last_page=1, dpi=150)
        if not images:
            return None
        img = images[0]

        # 3️⃣ Aplicar efeito borrado
        img = img.filter(ImageFilter.GaussianBlur(radius=4))

        # 4️⃣ Salvar PNG no campo preview_image
        preview_filename = f"{docx_path.stem}_preview.png"
        preview_path = f"previews/{preview_filename}"

        # Salva no storage do Django
        from django.core.files.storage import default_storage
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        template.preview_image.save(preview_filename, ContentFile(buffer.read()), save=True)

        return preview_path

    except Exception as e:
        print("Erro ao gerar imagem do PDF:", e)
        return None
