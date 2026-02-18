from backend.app.services.services import extract_docx_structure, validate_mapping_response, save_template_schema, generate_pdf_from_docx
from backend.app.services.llm_context import build_llm_context_from_request
from backend.app.services.render import render_docx_by_index, render_docx_with_tokens
from backend.app.services.preview import generate_docx_preview, generate_docx_preview_pdf
from django.contrib.auth.decorators import login_required
import json, tempfile, traceback
from django.http import JsonResponse, FileResponse, HttpResponse
from backend.app.models import Template, TemplateSchema, DocumentInstance, Prefeitura
from backend.app.forms import UserProfileForm, LoginForm
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login as auth_login, logout as auth_logout
from backend.app.utils.utils import get_client_ip, is_locked, clear_failed_attempts, record_failed_attempt
from django.conf import settings as django_settings
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
import os
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
import requests


def api_login_required(view_func):
    """Decorator que retorna 401 JSON para APIs quando o usuário não está autenticado (em vez de redirect)."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Não autenticado. Faça login."}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper


# API: upload de Template (DOCX) e solicitação de mapeamento de campos via IA.
@api_login_required
@csrf_exempt
def upload_template_and_request_mapping_api(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Use POST"}, status=405)

    if "template_file" not in request.FILES:
        return JsonResponse({"ok": False, "error": "Nenhum arquivo enviado"}, status=400)

    uploaded = request.FILES["template_file"]
    name = request.POST.get("name") or uploaded.name
    mapping_instructions = request.POST.get("mapping_instructions", "")

    # Salva Template e gera preview (imagem) imediatamente
    tpl = Template.objects.create(name=name, file=uploaded)
    
    preview_rel_path = generate_docx_preview(tpl)
    tpl.preview_image = preview_rel_path
    tpl.save()

    # extrair estrutura (sem IA)
    try:
        doc_struct = extract_docx_structure(tpl.file.path)
        # Retornar estrutura básica sem mapeamento automático
        mapping = {
            "fields": [],
            "notes": "Mapeamento automático via IA foi removido. Use tokens {{ }} no template."
        }
        ok, err = validate_mapping_response(mapping)
        if not ok:
            return JsonResponse({"ok": False, "error": f"Mapping inválido: {err}", "raw_mapping": mapping}, status=422)

        schema_obj = save_template_schema(tpl, mapping, strategy="index")
        return JsonResponse({"ok": True, "template_id": str(tpl.id), "schema": mapping})

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"ok": False, "error": str(e)}, status=500)

# API: lista templates (ou um específico por id) com info de preview e existência de schema.
@api_login_required
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


# API: gerar documento (DOCX/PDF) a partir de valores recebidos, usando schema (index) ou fallback tokens.
@api_login_required
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


# API: gerar documento via LLM (rag_service) com contexto do usuário.
@api_login_required
@csrf_exempt
def gerar_via_llm_api(request):
    """
    Gera documento (ETP, DFD, TR) via serviço RAG/LLM.
    Usa contexto do usuário logado (nome, secretaria, prefeitura).
    """
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Use POST"}, status=405)

    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({"ok": False, "error": "Corpo JSON inválido"}, status=400)

    user_prompt = (payload.get("user_prompt") or "").strip()
    template_id = payload.get("template_id")
    output = (payload.get("output") or "docx").lower()

    if not user_prompt:
        return JsonResponse({"ok": False, "error": "user_prompt é obrigatório"}, status=400)

    context = build_llm_context_from_request(request)
    if template_id is not None:
        context["template_id"] = str(template_id)
    if payload.get("document_type_hint"):
        context["document_type_hint"] = payload["document_type_hint"]

    rag_url = getattr(django_settings, "RAG_SERVICE_URL", "http://127.0.0.1:8004").rstrip("/")
    url = f"{rag_url}/api/rag/generate-document"
    params = {}
    if output == "docx":
        params["output_docx"] = "true"

    body = {
        "user_prompt": user_prompt,
        "context": context,
    }

    try:
        resp = requests.post(url, json=body, params=params, timeout=180)
    except requests.exceptions.Timeout:
        return JsonResponse({"ok": False, "error": "Serviço de geração demorou para responder. Tente novamente."}, status=504)
    except requests.exceptions.ConnectionError:
        return JsonResponse({"ok": False, "error": "Serviço de geração indisponível. Verifique se o rag_service está em execução."}, status=503)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=502)

    if resp.status_code != 200:
        try:
            err = resp.json().get("detail", resp.text)
        except Exception:
            err = resp.text
        return JsonResponse({"ok": False, "error": err}, status=resp.status_code)

    content_type = resp.headers.get("content-type", "")
    if "json" in content_type:
        data = resp.json()
        if not data.get("ok"):
            return JsonResponse({"ok": False, "error": data.get("error", "Erro na geração")}, status=500)
        if output == "docx" and data.get("docx_path") and os.path.isfile(data["docx_path"]):
            return FileResponse(
                open(data["docx_path"], "rb"),
                as_attachment=True,
                filename="documento.docx",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        return JsonResponse({"ok": True, **{k: v for k, v in data.items() if k not in ("docx_path", "pdf_path")}})
    # Resposta é o arquivo DOCX diretamente (format=docx)
    if output == "docx" and resp.content:
        r = HttpResponse(resp.content, content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        r["Content-Disposition"] = 'attachment; filename="documento.docx"'
        return r
    return JsonResponse({"ok": False, "error": "Resposta inesperada do serviço"}, status=502)


# API: retorna até 10 templates para autocomplete/busca.
@require_GET
@api_login_required
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

# API: retorna URL do preview PDF, gerando se necessário.
@api_login_required
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


# API: login (POST) — aceita JSON e define sessão.
@csrf_exempt
def api_auth_login(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Use POST"}, status=405)
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({"ok": False, "error": "Corpo inválido"}, status=400)
    email_or_username = (data.get("email_or_username") or "").strip()
    password = data.get("password") or ""
    remember = bool(data.get("remember"))
    prefeitura_url = (data.get("prefeitura_url") or "").strip()

    if not email_or_username or not password:
        return JsonResponse({"ok": False, "error": "E-mail/usuário e senha são obrigatórios."}, status=400)

    if request.user.is_authenticated:
        return JsonResponse({"ok": True, "message": "Já autenticado."})

    prefeitura = None
    if prefeitura_url:
        try:
            prefeitura = Prefeitura.objects.get(url=prefeitura_url)
        except Prefeitura.DoesNotExist:
            return JsonResponse({"ok": False, "error": "Prefeitura inválida."}, status=400)
    else:
        prefeitura = Prefeitura.objects.first()
        if not prefeitura:
            return JsonResponse({"ok": False, "error": "Nenhuma prefeitura configurada."}, status=503)

    ip_key = f"ip:{get_client_ip(request)}"
    if is_locked(ip_key):
        return JsonResponse({"ok": False, "error": "Muitas tentativas deste IP. Tente novamente mais tarde."}, status=429)

    form = LoginForm(request=request, data={"email_or_username": email_or_username, "password": password, "remember": remember})
    if not form.is_valid():
        record_failed_attempt(ip_key)
        if email_or_username:
            record_failed_attempt(f"user:{email_or_username}")
        err = form.non_field_errors()
        if err:
            return JsonResponse({"ok": False, "error": err[0]}, status=401)
        return JsonResponse({"ok": False, "error": "E-mail/usuário ou senha inválidos."}, status=401)

    user = form.get_user()
    if not user.is_staff and not user.is_superuser:
        if user.prefeitura_id != prefeitura.id:
            return JsonResponse({"ok": False, "error": "Usuário não pertence a esta prefeitura."}, status=403)
    user_key = f"user:{user.get_username()}"
    if is_locked(user_key):
        return JsonResponse({"ok": False, "error": "Conta bloqueada temporariamente. Tente novamente mais tarde."}, status=429)
    clear_failed_attempts(ip_key)
    clear_failed_attempts(user_key)
    auth_login(request, user)
    if remember:
        request.session.set_expiry(60 * 60 * 24 * 30)
    else:
        request.session.set_expiry(0)
    return JsonResponse({"ok": True, "message": "Login realizado com sucesso.", "prefeitura_url": prefeitura.url})


# API: logout (encerra sessão e retorna OK para o front redirecionar ao login).
@csrf_exempt
def api_auth_logout(request):
    if request.method not in ("GET", "POST"):
        return JsonResponse({"ok": False, "error": "Use GET ou POST"}, status=405)
    auth_logout(request)
    return JsonResponse({"ok": True, "message": "Logout realizado."})


# API: perfil do usuário logado (GET) e atualização (POST).
@api_login_required
@csrf_exempt
def api_me(request):
    user = request.user
    if request.method == "GET":
        data = {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "full_name": f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email,
            "role": getattr(user, "role", "") or "",
            "date_joined": user.date_joined.strftime("%d/%m/%Y %H:%M") if user.date_joined else "",
            "is_staff": user.is_staff,
        }
        if user.profile_photo and user.profile_photo.name:
            data["profile_photo"] = user.profile_photo.url
        else:
            data["profile_photo"] = None
        if getattr(user, "secretaria", None):
            data["secretaria"] = str(user.secretaria)
        else:
            data["secretaria"] = None
        if getattr(user, "prefeitura", None):
            data["prefeitura"] = str(user.prefeitura)
        else:
            data["prefeitura"] = None
        return JsonResponse(data)
    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return JsonResponse({"ok": True, "message": "Dados atualizados com sucesso!"})
        return JsonResponse({"ok": False, "errors": form.errors}, status=400)
    return JsonResponse({"error": "Method not allowed"}, status=405)


# API: lista de documentos do usuário (paginação e busca).
@api_login_required
@require_GET
def api_me_documents(request):
    user = request.user
    query = request.GET.get("q", "").strip()
    page_number = request.GET.get("page", 1)
    docs = DocumentInstance.objects.filter(owner=user).select_related("template")
    if query:
        docs = docs.filter(template__name__icontains=query)
    docs = docs.order_by("-updated_at")
    paginator = Paginator(docs, 10)
    page_obj = paginator.get_page(page_number)
    results = []
    for doc in page_obj:
        item = {
            "id": str(doc.id),
            "template_name": doc.template.name if doc.template else "",
            "updated_at": doc.updated_at.strftime("%d/%m/%Y %H:%M") if doc.updated_at else "",
            "status": doc.status,
            "status_display": doc.get_status_display(),
        }
        if doc.file_docx and doc.file_docx.name:
            item["file_docx_url"] = doc.file_docx.url
        else:
            item["file_docx_url"] = None
        if doc.file_pdf and doc.file_pdf.name:
            item["file_pdf_url"] = doc.file_pdf.url
        else:
            item["file_pdf_url"] = None
        results.append(item)
    return JsonResponse({
        "results": results,
        "count": paginator.count,
        "num_pages": paginator.num_pages,
        "page": page_obj.number,
        "has_previous": page_obj.has_previous(),
        "has_next": page_obj.has_next(),
        "start_index": page_obj.start_index(),
        "end_index": page_obj.end_index(),
    })
