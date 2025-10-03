# apps/documents/services.py
import os
from pathlib import Path
from django.conf import settings
from django.core.files import File
from weasyprint import HTML  # se usar WeasyPrint para PDF (pode trocar)
import subprocess
from docx import Document

# util: garante pasta dentro do MEDIA_ROOT
def _ensure_media_subdir(*parts) -> str:
    base = Path(settings.MEDIA_ROOT)
    target = base.joinpath(*parts)
    target.mkdir(parents=True, exist_ok=True)
    return str(target)

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

from app.models import TemplateSchema

def save_template_schema(template, mapping_json, strategy='index'):
    schema_obj, _ = TemplateSchema.objects.update_or_create(
        template=template,
        defaults={"strategy": strategy, "schema": mapping_json}
    )
    return schema_obj

