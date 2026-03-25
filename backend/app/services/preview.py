import os
from pathlib import Path
from docx2pdf import convert  # converte docx -> pdf
from pdf2image import convert_from_path  # converte pdf -> imagens
from django.conf import settings
import subprocess
from PIL import Image, ImageFilter
from django.conf import settings
from django.core.files.base import ContentFile
import tempfile


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

    # 1️⃣ Converter DOCX -> PDF via LibreOffice (opcional: se não instalado, não gera preview)
    try:
        subprocess.run([
            "libreoffice",
            "--headless",
            "--convert-to", "pdf",
            "--outdir", str(tmp_dir),
            str(docx_path)
        ], check=True, timeout=60)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        # FileNotFoundError = LibreOffice não instalado; CalledProcessError = falha na conversão
        if isinstance(e, FileNotFoundError):
            print("LibreOffice não encontrado. Instale com: apt-get install libreoffice (preview de template desabilitado)")
        else:
            print("Erro ao converter DOCX para PDF:", e)
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

def generate_docx_preview_pdf(template):
    """
    Gera PDF de preview a partir do .docx do template usando LibreOffice headless.
    Salva no campo template.preview_pdf e retorna a url (template.preview_pdf.url).
    """
    if not template.file:
        return None

    docx_path = Path(template.file.path)
    tmp_dir = Path(tempfile.mkdtemp(prefix="tpl_preview_"))
    try:
        # Converter DOCX -> PDF via libreoffice (opcional)
        subprocess.run([
            "libreoffice",
            "--headless",
            "--convert-to", "pdf",
            "--outdir", str(tmp_dir),
            str(docx_path)
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
        generated_pdf = tmp_dir / f"{docx_path.stem}.pdf"
        if not generated_pdf.exists():
            # fallback: procura qualquer .pdf gerado no tmp_dir
            pdfs = list(tmp_dir.glob("*.pdf"))
            if pdfs:
                generated_pdf = pdfs[0]
            else:
                return None

        # Salvar no campo preview_pdf (Django storage)
        with open(generated_pdf, "rb") as f:
            fname = f"{docx_path.stem}_preview.pdf"
            template.preview_pdf.save(fname, ContentFile(f.read()), save=True)

        return template.preview_pdf.url
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        # LibreOffice ausente / timeout / falha na conversão
        return None
    finally:
        # cleanup temporário (não remove o arquivo salvo no storage)
        try:
            for p in tmp_dir.glob("*"):
                p.unlink()
            tmp_dir.rmdir()
        except Exception:
            pass
