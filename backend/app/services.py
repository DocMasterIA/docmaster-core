# apps/documents/services.py
import os
import uuid
import tempfile
from pathlib import Path
from django.conf import settings
from django.core.files import File
from docxtpl import DocxTemplate
from weasyprint import HTML  # se usar WeasyPrint para PDF (pode trocar)
import subprocess
from docx import Document

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

def generate_pdf_from_docx(docx_path):
    pdf_path = os.path.splitext(docx_path)[0] + ".pdf"
    subprocess.run([
        "libreoffice",
        "--headless",
        "--convert-to", "pdf",
        "--outdir", os.path.dirname(docx_path),
        docx_path
    ], check=True)
    return pdf_path


from docx import Document
import re, json

def extract_docx_structure(path):
    """
    Retorna uma lista ordenada de blocos com metadados para enviar ao LLM.
    Cada bloco: {'index': int, 'type': 'heading'|'paragraph'|'table', 'text': str, 'style': 'Heading 1'...}
    """
    doc = Document(path)
    blocks = []
    idx = 0
    for p in doc.paragraphs:
        style = getattr(p.style, "name", "")
        bl_type = 'heading' if style and style.lower().startswith('heading') else 'paragraph'
        blocks.append({"index": idx, "type": bl_type, "style": style, "text": p.text})
        idx += 1

    # tabelas: inserir como blocos com tipo 'table' onde text = concatenacao de celulas
    for t in doc.tables:
        # converte tabela em texto resumido
        rows = []
        for r in t.rows:
            cells = [c.text.strip() for c in r.cells]
            rows.append(" | ".join(cells))
        blocks.append({"index": idx, "type": "table", "text": "\n".join(rows)})
        idx += 1

    return {"blocks": blocks, "n_blocks": idx}

def validate_mapping_response(resp):
    """
    Espera resp = {'fields':[{'key','label','block_indices':[...],'type','required','confidence'}], 'notes':...}
    Retorna (ok, errors)
    """
    if not isinstance(resp, dict): 
        return False, "Resposta não é um dict"
    fields = resp.get("fields")
    if not isinstance(fields, list):
        return False, "fields não é lista"
    # validar cada campo minimamente
    for f in fields:
        if not f.get("key") or not f.get("block_indices"):
            return False, f"Field inválido: {f}"
    return True, None

from .models import TemplateSchema

def save_template_schema(template, mapping_json, strategy='index'):
    schema_obj, _ = TemplateSchema.objects.update_or_create(
        template=template,
        defaults={"strategy": strategy, "schema": mapping_json}
    )
    return schema_obj

def render_docx_by_index(template_path, out_path, mapping_schema, values: dict):
    """
    mapping_schema: TemplateSchema.schema
    values: dict {key: value}
    strategy index: for each field, replace text in block_indices with value
    """
    doc = Document(template_path)
    blocks = []  # map paragraph index -> paragraph object
    for i, p in enumerate(doc.paragraphs):
        blocks.append(p)

    # aplicar substituições
    for field in mapping_schema.get("fields", []):
        key = field["key"]
        indices = field.get("block_indices", [])
        val = values.get(key, "")
        for idx in indices:
            if idx < len(blocks):
                p = blocks[idx]
                # simplificar: limpar runs e inserir new text
                for r in list(p.runs):
                    p._p.remove(r._r)  # remove run (docx internals) - careful
                p.add_run(str(val))

    doc.save(out_path)
    return out_path
