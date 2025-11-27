

from docx import Document
import uuid
from pathlib import Path
from .services import _ensure_media_subdir
from docxtpl import DocxTemplate
import os 

# Renderização SIMPLIFICADA: usa renderização básica com tokens {{ }}
def render_docx_from_template(template_file_path: str, context: dict, dest_dir: str | None = None) -> str:
    """
    Gera um .docx modificado usando renderização básica com tokens {{ }}.
    Funcionalidade de IA foi removida.
    """
    if dest_dir is None:
        dest_dir = _ensure_media_subdir("documents", "docx")
    
    # Usar renderização básica com tokens
    return render_docx_fallback(template_file_path, context, dest_dir)


def render_docx_fallback(template_file_path: str, context: dict, dest_dir: str) -> str:
    """
    Renderização básica com tokens {{ }}.
    """
    filename = f"{Path(template_file_path).stem}_{uuid.uuid4().hex[:8]}.docx"
    out_path = os.path.join(dest_dir, filename)
    
    # Verificar se o template tem tokens {{ }}
    has_tokens = False
    try:
        from docx import Document
        doc = Document(template_file_path)
        for p in doc.paragraphs[:20]:
            if '{{' in p.text and '}}' in p.text:
                has_tokens = True
                break
    except:
        pass
    
    if has_tokens:
        # Usar docxtpl se tem tokens
        try:
            doc = DocxTemplate(template_file_path)
            doc.render(context)
            doc.save(out_path)
            print(f"✅ Fallback com docxtpl bem-sucedido")
            return out_path
        except Exception as e:
            print(f"❌ Fallback docxtpl falhou: {e}")
            # Copiar arquivo original se tudo falhar
            import shutil
            shutil.copy2(template_file_path, out_path)
            return out_path
    else:
        # Copiar arquivo original se não tem tokens
        import shutil
        shutil.copy2(template_file_path, out_path)
        print(f"✅ Arquivo original copiado como fallback")
        return out_path

# Geração opcional de HTML de preview (pode ser usado com render_to_string em views).
def render_preview_html(template_obj, context: dict) -> str:
    """
    Retorna HTML de preview. Se o template_obj tiver preview_html (string),
    você pode renderizá-lo como um template Django (render_to_string) na view.
    Aqui assumimos que a view já chama render_to_string se quiser.
    """
    # pode implementar render_to_string('documents/preview_base.html', {...})
    return ""  # opcional, use render_to_string na view


# Renderização por estratégia "index": substitui conteúdo de parágrafos por índices de blocos.
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

# Renderização por tokens: usa docxtpl com {{ chaves }} dentro do DOCX.
def render_docx_with_tokens(template_path: str, output_path: str, values: dict):
    """
    Gera um DOCX a partir de um template com marcações {{ }} via docxtpl.
    """
    tpl = DocxTemplate(template_path)
    tpl.render(values)
    tpl.save(output_path)
    return output_path

