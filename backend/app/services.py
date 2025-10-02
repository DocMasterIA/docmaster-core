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
from jinja2 import Template as JinjaTemplate
from .models import Snippet, Rule
from collections import defaultdict
import logging

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

import subprocess
import os

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



logger = logging.getLogger(__name__)

def get_label_for_choice(field_name, value):
    """
    Mapas simples para label legível (pode extrair de DB se tiver)
    """
    maps = {
        'modalidade': {
            'pregao_eletronico': 'Pregão Eletrônico',
            'concorrencia': 'Concorrência',
            'tomada_precos': 'Tomada de Preços',
            'convite': 'Convite',
            'dispensa': 'Dispensa de Licitação',
            'etp': 'Estudo Técnico Preliminar'
        }
    }
    return maps.get(field_name, {}).get(value, value)

def select_snippets_for_data(data: dict):
    """
    Seleciona snippets seguindo regras simples.
    - Busca regras com field_name em data and match_value == data[field_name]
    - Também pega regras com match_value == '*' (default)
    - Retorna dict area -> list[Snippet ordered]
    """
    area_map = defaultdict(list)
    # carregar todas as regras ordenadas por order
    rules = Rule.objects.all().order_by('order')
    for r in rules:
        field = r.field_name
        match_val = r.match_value
        value = data.get(field)
        if value is None and match_val != '*':
            continue
        if match_val == '*' or str(value) == str(match_val):
            for s in r.snippets.all().order_by('order'):
                if s.active:
                    area_map[s.area].append(s)
    return area_map

def render_snippet(snippet: Snippet, context: dict) -> str:
    """
    Renderiza um snippet com Jinja2 usando o contexto.
    """
    try:
        jtpl = JinjaTemplate(snippet.content)
        return jtpl.render(**context)
    except Exception as e:
        logger.exception("Erro renderizando snippet %s: %s", snippet.slug, e)
        return f"[ERRO AO RENDERIZAR {snippet.slug}]"

def assemble_document_context(base_data: dict) -> dict:
    """
    Monta o context final para o template principal.
    Retorna um dict com campos simples (objeto, orgao, etc.) + blocos como 'intro' e 'clausulas_padroes'.
    """
    data = dict(base_data)  # copia
    # adicionar labels legíveis
    for fld in list(data.keys()):
        data[f"{fld}_label"] = get_label_for_choice(fld, data.get(fld))

    # selecionar snippets por regra
    area_map = select_snippets_for_data(data)

    # renderizar e concatenar por area (ordem definida pelos snippet.order)
    assembled = {}
    for area, snippets in area_map.items():
        parts = []
        for sn in snippets:
            parts.append(render_snippet(sn, data))
        # junta com duas quebras de linha entre cláusulas
        assembled[area] = "\n\n".join(parts)

    # construir context que o docxtpl espera
    context = dict(data)
    # por convenção: intro, clausulas_padroes, conclusion
    context['intro'] = assembled.get('intro', '')
    context['clausulas_padroes'] = assembled.get('clause', '')
    context['conclusion'] = assembled.get('conclusion', '')

    return context
