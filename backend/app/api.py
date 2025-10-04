from backend.app.services.services import extract_docx_structure, validate_mapping_response, save_template_schema, generate_pdf_from_docx
from backend.app.services.ia import call_llm_for_mapping
from backend.app.services.render import render_docx_by_index, render_docx_with_tokens
from backend.app.services.preview import generate_docx_preview, generate_docx_preview_pdf
from django.contrib.auth.decorators import login_required
import json, tempfile, traceback
from django.http import JsonResponse, FileResponse
from backend.app.models import Template, TemplateSchema
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
import os
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET



@login_required
def upload_template_and_request_mapping_api(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Use POST"}, status=405)

    if "template_file" not in request.FILES:
        return JsonResponse({"ok": False, "error": "Nenhum arquivo enviado"}, status=400)

    uploaded = request.FILES["template_file"]
    name = request.POST.get("name") or uploaded.name
    mapping_instructions = request.POST.get("mapping_instructions", "")

    # salvar template
    tpl = Template.objects.create(name=name, file=uploaded)
    
    preview_rel_path = generate_docx_preview(tpl)
    tpl.preview_image = preview_rel_path
    tpl.save()

    # extrair estrutura e chamar LLM
    try:
        doc_struct = extract_docx_structure(tpl.file.path)
        mapping = call_llm_for_mapping(doc_struct, user_instructions=mapping_instructions, llm_api_key=None)  # passe chave conforme config
        ok, err = validate_mapping_response(mapping)
        if not ok:
            # opcional: salvar Template sem schema e retornar mapping para revisão
            return JsonResponse({"ok": False, "error": f"Mapping inválido: {err}", "raw_mapping": mapping}, status=422)

        schema_obj = save_template_schema(tpl, mapping, strategy="index")
        return JsonResponse({"ok": True, "template_id": str(tpl.id), "schema": mapping})

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"ok": False, "error": str(e)}, status=500)

@login_required
def get_template_list_api(request):
    template_id = request.GET.get("id")
    if template_id:
        try:
            t = Template.objects.get(id=template_id)
            item = {
                "id": str(t.id),
                "name": t.name,
                "has_schema": hasattr(t, "schema"),
                "preview_image": t.preview_image.url if t.preview_image else None,
            }
            return JsonResponse({"template": item})
        except Template.DoesNotExist:
            return JsonResponse({"error": "Template não encontrado"}, status=404)

    # fallback: lista de templates
    qs = Template.objects.all().order_by("-created_at")[:10]
    items = [
        {
            "id": str(t.id),
            "name": t.name,
            "has_schema": hasattr(t, "schema"),
            "preview_image": t.preview_image.url if t.preview_image else None,
        }
        for t in qs
    ]
    return JsonResponse({"templates": items})


@login_required
@csrf_exempt  # se for API token-based, prefira auth token em header e remova csrf_exempt
def generate_document_with_values_api(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Use POST"}, status=405)

    payload = json.loads(request.body)
    template_id = payload.get("template_id")
    values = payload.get("values", {})
    output = payload.get("output", "pdf")

    if not template_id:
        return JsonResponse({"ok": False, "error": "template_id obrigatório"}, status=400)

    tpl = get_object_or_404(Template, pk=template_id)
    schema = getattr(tpl, "schema", None)
    tmpdir = tempfile.gettempdir()
    out_docx = os.path.join(tmpdir, f"doc_{tpl.id}.docx")

    try:
        if schema and schema.strategy == "index":
            render_docx_by_index(tpl.file.path, out_docx, schema.schema, values)
        else:
            # fallback: if schema missing but template was jinja-based, use docxtpl via render_docx_with_tokens
            render_docx_with_tokens(tpl.file.path, out_docx, values)

        if output == "pdf":
            out_pdf = os.path.splitext(out_docx)[0] + ".pdf"
            generate_pdf_from_docx(out_docx, out_pdf)
            return FileResponse(open(out_pdf, "rb"), as_attachment=True, filename=os.path.basename(out_pdf))
        else:
            return FileResponse(open(out_docx, "rb"), as_attachment=True, filename=os.path.basename(out_docx))

    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)

@require_GET
@login_required
def template_list_api(request):
    """
    Retorna até 10 templates em JSON.
    Se `q` vazio => retorna 10 templates mais recentes (do usuário ou todos, ajustar).
    """
    q = request.GET.get("q", "").strip()
    # Se quiser limitar a templates do usuário: use owner=request.user
    base_qs = Template.objects.all().order_by("-created_at")

    if q:
        qs = base_qs.filter(name__icontains=q)[:10]
    else:
        qs = base_qs[:10]

    data = []
    for t in qs:
        data.append({
            "id": str(t.id),
            "name": t.name,
            # opcional: adicionar url de preview se tiver view
            # "preview_url": request.build_absolute_uri(reverse('template_preview', args=[t.id])),
        })

    return JsonResponse({"templates": data})

@login_required
def template_preview_pdf_api(request, template_id):
    tpl = get_object_or_404(Template, id=template_id)
    if tpl.preview_pdf and tpl.preview_pdf.name:
        url = tpl.preview_pdf.url
        return JsonResponse({"ok": True, "pdf_url": url})

    # se não existir, gera
    url = generate_docx_preview_pdf(tpl)
    if url:
        return JsonResponse({"ok": True, "pdf_url": url})
    return JsonResponse({"ok": False, "error": "Não foi possível gerar preview PDF"}, status=500)
