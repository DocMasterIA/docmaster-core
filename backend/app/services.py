import os
from django.conf import settings
from docxtpl import DocxTemplate
from django.template.loader import render_to_string
from weasyprint import HTML
from pathlib import Path
import uuid
from .models import Template

def render_docx_from_template(template_obj: Template, context: dict, out_dir=None):
    """
    Gera um .docx preenchido a partir do Template.file (docx com placeholders Jinja).
    Retorna caminho do arquivo gerado.
    """
    tpl_path = template_obj.file.path
    doc = DocxTemplate(tpl_path)
    doc.render(context)
    out_dir = out_dir or settings.MEDIA_ROOT
    filename = f"{template_obj.slug}_{uuid.uuid4().hex[:8]}.docx"
    out_path = os.path.join(out_dir, 'documents', 'docx', filename)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    doc.save(out_path)
    return out_path

def convert_html_to_pdf(html_content: str, out_path: str):
    HTML(string=html_content).write_pdf(out_path)
    return out_path

def render_preview_html(template_obj: Template, context: dict):
    """
    Se o template tiver preview_html (Jinja), renderiza com Django template engine.
    Caso não, podemos criar um fallback que transforma o docx em HTML (mais trabalho).
    """
    # Use render_to_string com um template HTML padronizado
    return render_to_string('documents/preview_base.html', {'context': context, 'template': template_obj})
