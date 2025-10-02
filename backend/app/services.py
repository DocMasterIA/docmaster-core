# apps/documents/services.py
import os
import uuid
import tempfile
from pathlib import Path
from django.conf import settings
from django.core.files import File
from docxtpl import DocxTemplate
from weasyprint import HTML  # se usar WeasyPrint para PDF (pode trocar)
from typing import Tuple

# util: garante pasta dentro do MEDIA_ROOT
def _ensure_media_subdir(*parts) -> str:
    base = Path(settings.MEDIA_ROOT)
    target = base.joinpath(*parts)
    target.mkdir(parents=True, exist_ok=True)
    return str(target)

def render_docx_from_template(template_file_path: str, context: dict, dest_dir: str | None = None) -> str:
    """
    Gera um .docx preenchido a partir de um template .docx (docxtpl).
    Retorna o caminho absoluto do arquivo gerado.
    """
    if dest_dir is None:
        dest_dir = _ensure_media_subdir("documents", "docx")

    filename = f"{Path(template_file_path).stem}_{uuid.uuid4().hex[:8]}.docx"
    out_path = os.path.join(dest_dir, filename)

    doc = DocxTemplate(template_file_path)
    doc.render(context)
    doc.save(out_path)
    return out_path

def render_preview_html(template_obj, context: dict) -> str:
    """
    Retorna HTML de preview. Se o template_obj tiver preview_html (string),
    você pode renderizá-lo como um template Django (render_to_string) na view.
    Aqui assumimos que a view já chama render_to_string se quiser.
    """
    # pode implementar render_to_string('documents/preview_base.html', {...})
    return ""  # opcional, use render_to_string na view

def convert_html_to_pdf(html_string: str, out_path: str) -> str:
    """
    Gera PDF a partir de HTML via WeasyPrint.
    Retorna o caminho do PDF gerado.
    """
    HTML(string=html_string).write_pdf(out_path)
    return out_path

def save_file_to_field(instance, field_name: str, file_path: str, save_instance: bool = True):
    """
    Salva um arquivo do disk em um FileField do modelo.
    Ex: save_file_to_field(doc_inst, 'file_docx', '/tmp/my.docx')
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)
    with open(file_path, "rb") as f:
        django_file = File(f)
        basename = os.path.basename(file_path)
        getattr(instance, field_name).save(basename, django_file, save=save_instance)

def generate_docx_and_pdf_from_template_model(template_model, context: dict, owner=None) -> Tuple[str, str]:
    """
    Helper que recebe um Template model (que tem .file.path) e gera docx e pdf,
    retornando (docx_path, pdf_path).
    """
    tpl_path = template_model.file.path
    tmp_dir = tempfile.mkdtemp(prefix="mdlic_")
    docx_path = render_docx_from_template(tpl_path, context, dest_dir=tmp_dir)

    # generate preview HTML in view or fallback empty string
    # here we try to use a minimal HTML preview from context (the view should generate better)
    preview_html = context.get("_preview_html", "")
    pdf_path = os.path.splitext(docx_path)[0] + ".pdf"

    if preview_html:
        convert_html_to_pdf(preview_html, pdf_path)
    else:
        # fallback: try to convert docx -> pdf via LibreOffice (optional) or create empty pdf
        # Implementação simples: criar pdf vazio (melhore para produção)
        open(pdf_path, "wb").close()

    return docx_path, pdf_path
