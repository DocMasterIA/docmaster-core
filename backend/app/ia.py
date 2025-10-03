from django.core.files import File
import tempfile, os

def create_document_from_ai(template, owner, ai_data):
    """
    Cria DocumentInstance a partir dos dados fornecidos pela IA.
    ai_data deve ser um dict contendo:
      - campos como tipo_documento, modalidade, objeto, orgao, valor_estimado, etc.
      - snippets: {"intro": [...], "clause": [...], "conclusion": [...]}
    """
    from .models import DocumentInstance
    from .services import render_docx_from_template, generate_pdf_from_docx

    # Cria draft inicial
    inst = DocumentInstance.objects.create(
        template=template,
        owner=owner,
        data=ai_data,
        status="draft"
    )

    # Monta contexto completo incluindo snippets
    context = ai_data.copy()
    context.setdefault("snippets_intro", ai_data.get("snippets", {}).get("intro", []))
    context.setdefault("snippets_clause", ai_data.get("snippets", {}).get("clause", []))
    context.setdefault("snippets_conclusion", ai_data.get("snippets", {}).get("conclusion", []))

    tmpdir = tempfile.gettempdir()
    docx_path = render_docx_from_template(template.file.path, context, dest_dir=tmpdir)
    pdf_path = generate_pdf_from_docx(docx_path)

    # Salva arquivos
    with open(docx_path, "rb") as f:
        inst.file_docx.save(os.path.basename(docx_path), File(f), save=False)
    with open(pdf_path, "rb") as f:
        inst.file_pdf.save(os.path.basename(pdf_path), File(f), save=False)

    inst.status = "final"
    inst.save()

    # Limpa temporários
    try:
        os.remove(docx_path)
        os.remove(pdf_path)
    except OSError:
        pass

    return inst
