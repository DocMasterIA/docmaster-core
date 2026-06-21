from backend.app.services.services import (
    extract_docx_structure,
    validate_mapping_response,
    save_template_schema,
    generate_pdf_from_docx,
    merge_docx_with_template_body,
)
from backend.app.services.llm_context import build_llm_context_from_request
from backend.app.services.render import render_docx_by_index, render_docx_with_tokens
from backend.app.services.preview import generate_docx_preview, generate_docx_preview_pdf
from django.contrib.auth.decorators import login_required
import json, tempfile, traceback
from django.http import JsonResponse, FileResponse, HttpResponse
from django.core.files.base import ContentFile
from backend.app.models import Template, TemplateSchema, DocumentInstance, Prefeitura, SubtopicoSecretaria, SlotValueCatalog, SlotFormState
from backend.app.forms import UserProfileForm, LoginForm, ChangePasswordForm
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login as auth_login, logout as auth_logout, update_session_auth_hash
from backend.app.utils.utils import get_client_ip, is_locked, clear_failed_attempts, record_failed_attempt
from django.conf import settings as django_settings
from django.core.paginator import Paginator
from django.utils import timezone
from django.shortcuts import get_object_or_404
import os
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
import requests
import re
from functools import wraps
from urllib.parse import urlparse

from backend.app.metrics import (
    prefeitura_label_from_instance,
    prefeitura_label_from_request,
    record_auth_login,
    record_llm_token_usage,
    record_document_instance_created,
    set_request_metrics,
    tenant_label,
    tenant_label_from_request,
    track_docmaster_view,
    track_platform,
)

def _rag_http_timeout_seconds() -> float:
    """Timeout HTTP do backend -> rag_service (pedidos genéricos; TR/DFD usa função dedicada)."""
    raw = (os.environ.get("RAG_HTTP_TIMEOUT") or "120").strip()
    try:
        val = float(raw)
    except Exception:
        val = 120.0
    return max(5.0, val)


def _rag_timeout_seconds_for_tr_dfd(body: dict) -> float:
    """
    Estende o timeout Django→rag_service em /gerar-tr-e-dfd quando há muitos itens
    ou prompt longo (LLM + DOCX), reduzindo ReadTimeout com payloads grandes.

    O reverse proxy (nginx, Cloudflare, etc.) tem de permitir *pelo menos* este
    tempo entre cliente e Django; caso contrário o browser vê «ligação interrompida»
    mesmo com o Gunicorn/Django ainda a trabalhar.

    Teto configurável: RAG_HTTP_TIMEOUT_TR_DFD_MAX (segundos, default 720).
    """
    base = _rag_http_timeout_seconds()
    slots = body.get("slots_override") if isinstance(body, dict) else None
    if not isinstance(slots, dict):
        slots = {}
    itens = slots.get("itens")
    n = len(itens) if isinstance(itens, list) else 0
    prompt_len = len(str((body or {}).get("user_prompt") or ""))
    # Antes: extra em itens capped em 360s → muitas linhas tinham o mesmo teto que ~20 itens.
    extra_items = min(580.0, max(0, n - 3) * 20.0)
    extra_prompt = min(240.0, max(0, prompt_len - 6000) / 25.0)
    raw_max = (os.environ.get("RAG_HTTP_TIMEOUT_TR_DFD_MAX") or "720").strip()
    try:
        cap = float(raw_max)
    except Exception:
        cap = 720.0
    cap = max(120.0, cap)
    return min(cap, base + extra_items + extra_prompt)


def _rag_post_json(url, body, *, params=None, timeout=None, headers=None):
    """POST JSON único ao rag_service (sem retry — retry duplicava tempo de LLM/TR)."""
    params = params if params is not None else {}
    t = float(timeout) if timeout is not None else _rag_http_timeout_seconds()
    hdrs = dict(headers or {})
    return requests.post(
        url,
        json=body,
        params=params,
        headers=hdrs,
        timeout=max(5.0, t),
    )


def _rag_prefeitura_headers(request) -> dict[str, str]:
    return {"X-DocMaster-Prefeitura": prefeitura_label_from_request(request)}


def _record_llm_usage_from_response(request, fluxo: str, *, usage=None, http_response=None) -> None:
    """Grava métricas de tokens (uma vez por request: JSON body ou header HTTP)."""
    pref = prefeitura_label_from_request(request)
    prompt_t = completion_t = 0
    if isinstance(usage, dict):
        prompt_t = int(usage.get("prompt_tokens") or 0)
        completion_t = int(usage.get("completion_tokens") or 0)
    if (not prompt_t and not completion_t) and http_response is not None:
        raw = (http_response.headers.get("X-DocMaster-LLM-Token-Usage") or "").strip()
        if raw:
            try:
                data = json.loads(raw)
                prompt_t = int(data.get("prompt_tokens") or 0)
                completion_t = int(data.get("completion_tokens") or 0)
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
        if not prompt_t and not completion_t:
            ctype = (http_response.headers.get("content-type") or "").lower()
            if "json" in ctype:
                try:
                    body = http_response.json()
                    if isinstance(body, dict):
                        tu = body.get("llm_token_usage")
                        if isinstance(tu, dict):
                            prompt_t = int(tu.get("prompt_tokens") or 0)
                            completion_t = int(tu.get("completion_tokens") or 0)
                except Exception:
                    pass
    meta = getattr(request, "docmaster_metrics", None) or {}
    # Sempre conta 1 invocação LLM (mesmo sem token_usage no JSON) — média tokens/chamada no Grafana.
    record_llm_token_usage(
        fluxo=fluxo,
        prefeitura=pref,
        package=str(meta.get("package") or "unknown"),
        prompt_tokens=max(0, prompt_t),
        completion_tokens=max(0, completion_t),
    )


def api_login_required(view_func):
    """Decorator que retorna 401 JSON para APIs quando o usuário não está autenticado (em vez de redirect)."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Não autenticado. Faça login."}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper


def _normalize_slot_value(v: str) -> str:
    s = re.sub(r"\s+", " ", (v or "").strip())
    return s.casefold()


def _resolve_slot_package_key(payload: dict, request) -> str:
    from backend.app.slot_package_keys import resolve_slot_package_key

    return resolve_slot_package_key(payload, request)


# Preset global do gerador (mesma chave do frontend: global_slots_preset_v1)
GLOBAL_SLOT_PRESET_KEY = "global_slots_preset_v1"
LIBRARY_TEMPLATE_ID_KEY = "__library_template_id__"
LIBRARY_TEMPLATE_NAME_KEY = "__library_template_name__"


def _can_user_access_template(user, template: Template) -> bool:
    """Regra de acesso por prefeitura para templates."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    user_pref_id = getattr(user, "prefeitura_id", None)
    tpl_pref_id = getattr(template, "prefeitura_id", None)
    # Template sem prefeitura continua global (compatibilidade legada).
    if tpl_pref_id is None:
        return True
    return user_pref_id is not None and str(user_pref_id) == str(tpl_pref_id)


def _templates_queryset_for_user(user):
    qs = Template.objects.all()
    if not user.is_superuser:
        user_pref_id = getattr(user, "prefeitura_id", None)
        if user_pref_id is None:
            # Sem prefeitura: apenas templates globais
            qs = qs.filter(prefeitura__isnull=True)
        else:
            qs = qs.filter(prefeitura_id=user_pref_id) | qs.filter(prefeitura__isnull=True)
    return qs.distinct()


def _resolve_merge_template_id(request, payload):
    """
    `template_id` no JSON tem prioridade. Caso contrário, usa o template da
    Biblioteca de Documentos salvo no preset global do usuário (cabeçalho/rodapé).
    """
    raw = payload.get("template_id")
    if raw not in (None, ""):
        tid = str(raw).strip()
        tpl = Template.objects.filter(id=tid).first()
        if tpl and _can_user_access_template(request.user, tpl):
            return tid
        # ID inválido no payload: tenta preset salvo (ex.: template removido do banco)

    if not getattr(request.user, "is_authenticated", False):
        return None

    try:
        obj = SlotFormState.objects.filter(
            owner=request.user,
            slot_package_key=GLOBAL_SLOT_PRESET_KEY,
        ).first()
        if not obj or not isinstance(obj.data, dict):
            return None
        lib = obj.data.get(LIBRARY_TEMPLATE_ID_KEY) or obj.data.get("_library_template_id")
        if not lib:
            return None
        tid = str(lib).strip()
        tpl = Template.objects.filter(id=tid).first() if tid else None
        if tpl and _can_user_access_template(request.user, tpl):
            return tid
    except Exception:
        pass
    return None


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
    tpl = Template.objects.create(name=name, file=uploaded, prefeitura=getattr(request.user, "prefeitura", None))
    
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

def _serialize_template_for_list(t: Template) -> dict:
    return {
        "id": str(t.id),
        "name": t.name,
        "has_schema": hasattr(t, "schema"),
        "preview_image": t.preview_image.url if t.preview_image else None,
        "prefeitura": {
            "id": str(t.prefeitura.id),
            "nome_municipio": t.prefeitura.nome_municipio,
            "estado": t.prefeitura.estado,
        } if t.prefeitura else None,
        "subtopico": {
            "id": str(t.related_subtopico.id),
            "nome": t.related_subtopico.nome,
        } if t.related_subtopico else None,
    }


# API: lista templates (ou um específico por id) com info de preview, prefeitura e subtopico.
@api_login_required
def get_template_list_api(request):
    template_id = request.GET.get("id")
    if template_id:
        try:
            t = Template.objects.get(id=template_id)
            if not _can_user_access_template(request.user, t):
                return JsonResponse({"error": "Acesso negado ao template desta prefeitura."}, status=403)
            item = _serialize_template_for_list(t)
            return JsonResponse({"template": item})
        except Template.DoesNotExist:
            return JsonResponse({"error": "Template não encontrado"}, status=404)

    # Filtros opcionais
    estado = request.GET.get("estado", "").strip()
    prefeitura_id = request.GET.get("prefeitura_id", "").strip()
    subtopico_id = request.GET.get("subtopico_id", "").strip()

    qs = _templates_queryset_for_user(request.user).order_by("-created_at")

    if estado:
        qs = qs.filter(prefeitura__estado=estado)
    if prefeitura_id:
        qs = qs.filter(prefeitura__id=prefeitura_id)
    if subtopico_id:
        qs = qs.filter(related_subtopico__id=subtopico_id)

    qs = qs[:50]
    items = [_serialize_template_for_list(t) for t in qs]
    return JsonResponse({"templates": items})


@api_login_required
def template_filters_api(request):
    """
    Retorna listas de Estados, Prefeituras e Subtópicos usados por Templates,
    para popular os filtros da Biblioteca de Templates.
    """
    # Estados e prefeituras apenas onde existem templates associados
    tpl_qs = _templates_queryset_for_user(request.user)
    pref_qs = Prefeitura.objects.filter(template__in=tpl_qs).distinct().order_by("estado", "nome_municipio")
    estados = sorted({p.estado for p in pref_qs if p.estado})
    prefeituras = [
        {
            "id": str(p.id),
            "nome_municipio": p.nome_municipio,
            "estado": p.estado,
        }
        for p in pref_qs
    ]

    sub_qs = SubtopicoSecretaria.objects.filter(template__in=tpl_qs).distinct().order_by("nome")
    subtopicos = [
        {
            "id": str(s.id),
            "nome": s.nome,
        }
        for s in sub_qs
    ]

    return JsonResponse(
        {
            "estados": estados,
            "prefeituras": prefeituras,
            "subtopicos": subtopicos,
        }
    )


# API: gerar documento (DOCX/PDF) a partir de valores recebidos, usando schema (index) ou fallback tokens.
@csrf_exempt  # se for API token-based, prefira auth token em header e remova csrf_exempt
@api_login_required
@track_docmaster_view("generate_values")
def generate_document_with_values_api(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Use POST"}, status=405)

    payload = json.loads(request.body)
    template_id = payload.get("template_id")
    values = payload.get("values", {})
    output = payload.get("output", "pdf")
    set_request_metrics(request, output=output or "pdf")

    if not template_id:
        return JsonResponse({"ok": False, "error": "template_id obrigatório"}, status=400)

    tpl = get_object_or_404(Template, pk=template_id)
    if not _can_user_access_template(request.user, tpl):
        return JsonResponse({"ok": False, "error": "Acesso negado ao template desta prefeitura."}, status=403)
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
@csrf_exempt
@api_login_required
@track_docmaster_view("gerar_llm")
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

    raw_template_id = payload.get("template_id")
    if raw_template_id not in (None, ""):
        tpl = Template.objects.filter(id=str(raw_template_id).strip()).first()
        if not tpl:
            return JsonResponse({"ok": False, "error": "template_id inválido."}, status=400)
        if not _can_user_access_template(request.user, tpl):
            return JsonResponse({"ok": False, "error": "Acesso negado ao template desta prefeitura."}, status=403)

    user_prompt = (payload.get("user_prompt") or "").strip()
    template_id = _resolve_merge_template_id(request, payload)
    output = (payload.get("output") or "docx").lower()
    slot_package_key = _resolve_slot_package_key(payload, request)
    metrics_package = slot_package_key or "unknown"
    if (payload.get("document_type_hint") or "").strip().lower() == "etp":
        metrics_package = "etp"
    set_request_metrics(request, package=metrics_package, output=output)

    if not user_prompt:
        return JsonResponse({"ok": False, "error": "user_prompt é obrigatório"}, status=400)

    # TR+DFD (modelo oficial): mesma URL que ETP, desvio interno para evitar 404 em rotas separadas
    if output == "tr_dfd":
        try:
            request._docmaster_skip_metrics = True
            return gerar_tr_e_dfd_api(request)
        except Exception as e:
            return JsonResponse({"ok": False, "error": str(e)}, status=500)

    context = build_llm_context_from_request(request)
    if template_id is not None:
        context["template_id"] = str(template_id)
    if payload.get("document_type_hint"):
        context["document_type_hint"] = payload["document_type_hint"]
    if slot_package_key:
        context["slot_package_key"] = slot_package_key

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
        resp = _rag_post_json(url, body, params=params)
    except requests.exceptions.ConnectionError:
        return JsonResponse({"ok": False, "error": "Serviço de geração indisponível. Verifique se o rag_service está em execução."}, status=503)
    except requests.exceptions.Timeout:
        return JsonResponse({"ok": False, "error": "Tempo limite na geração. O rag_service demorou para responder."}, status=504)
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
        _record_llm_usage_from_response(request, "gerar_llm", http_response=resp)
        # Caso especial: se no futuro usarmos docx_path compartilhado via volume, poderíamos salvar em DocumentInstance aqui.
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
        final_path_bytes = resp.content

        # Se houver template_id, combinar cabeçalho/footer do template com corpo do DOCX gerado pelo RAG.
        if template_id is not None:
            tpl = Template.objects.filter(id=template_id).first()
            if tpl:
                try:
                    tmpdir = tempfile.gettempdir()
                    rag_docx_path = os.path.join(tmpdir, f"rag_{tpl.id}.docx")
                    out_docx_path = os.path.join(tmpdir, f"doc_{tpl.id}.docx")
                    with open(rag_docx_path, "wb") as f:
                        f.write(resp.content)

                    merge_docx_with_template_body(
                        source_docx_path=rag_docx_path,
                        template_docx_path=tpl.file.path,
                        out_docx_path=out_docx_path,
                    )

                    with open(out_docx_path, "rb") as f:
                        final_path_bytes = f.read()

                    # Salva instância do documento para aparecer em "Meus Documentos"
                    try:
                        if request.user.is_authenticated:
                            inst = DocumentInstance(
                                template=tpl,
                                owner=request.user,
                                data={
                                    "user_prompt": user_prompt,
                                    "context": context,
                                    "document_type_hint": payload.get("document_type_hint") or "",
                                },
                                status="final",
                            )
                            inst.file_docx.save(
                                f"{inst.id}.docx",
                                ContentFile(final_path_bytes),
                                save=True,
                            )
                    except Exception:
                        # Não quebra a geração se falhar ao salvar o histórico
                        pass
                except Exception:
                    # Em caso de falha na mesclagem, volta a usar o DOCX original do RAG.
                    final_path_bytes = resp.content

            else:
                final_path_bytes = resp.content
        else:
            # Sem template_id: mantém fluxo original, salvando histórico se Template existir
            try:
                if template_id is not None:
                    tpl = Template.objects.filter(id=template_id).first()
                    if tpl and request.user.is_authenticated:
                        inst = DocumentInstance(
                            template=tpl,
                            owner=request.user,
                            data={
                                "user_prompt": user_prompt,
                                "context": context,
                                "document_type_hint": payload.get("document_type_hint") or "",
                            },
                            status="final",
                        )
                        inst.file_docx.save(
                            f"{inst.id}.docx",
                            ContentFile(resp.content),
                            save=True,
                        )
            except Exception:
                # Não quebra a geração se falhar ao salvar o histórico
                pass

        _record_llm_usage_from_response(request, "gerar_llm", http_response=resp)
        r = HttpResponse(
            final_path_bytes,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        r["Content-Disposition"] = 'attachment; filename=\"documento.docx\"'
        return r

    return JsonResponse({"ok": False, "error": "Resposta inesperada do serviço"}, status=502)


@csrf_exempt
@api_login_required
@track_docmaster_view("gerar_tr_modelo")
def gerar_tr_modelo_api(request):
    """
    Gera Termo de Referência a partir do modelo fixo do rag_service (/api/rag/generate-tr-from-model).
    Usado pelo frontend Vue quando o usuário escolhe TR com modelo fixo.
    """
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Use POST"}, status=405)

    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({"ok": False, "error": "Corpo JSON inválido"}, status=400)

    raw_template_id = payload.get("template_id")
    if raw_template_id not in (None, ""):
        tpl = Template.objects.filter(id=str(raw_template_id).strip()).first()
        if not tpl:
            return JsonResponse({"ok": False, "error": "template_id inválido."}, status=400)
        if not _can_user_access_template(request.user, tpl):
            return JsonResponse({"ok": False, "error": "Acesso negado ao template desta prefeitura."}, status=403)

    user_prompt = (payload.get("user_prompt") or "").strip()
    slots_override = payload.get("slots_override")  # opcional
    template_id = _resolve_merge_template_id(request, payload)
    slot_package_key = _resolve_slot_package_key(payload, request)
    set_request_metrics(request, package=slot_package_key, output="docx")

    if not user_prompt:
        return JsonResponse({"ok": False, "error": "user_prompt é obrigatório"}, status=400)

    context = build_llm_context_from_request(request)
    if slot_package_key:
        context["slot_package_key"] = slot_package_key

    rag_url = getattr(django_settings, "RAG_SERVICE_URL", "http://127.0.0.1:8004").rstrip("/")
    url = f"{rag_url}/api/rag/generate-tr-from-model"

    body = {
        "user_prompt": user_prompt,
        "slots_override": slots_override or None,
        "context": context if context else None,
    }

    try:
        resp = _rag_post_json(url, body)
    except requests.exceptions.ConnectionError:
        return JsonResponse({"ok": False, "error": "Serviço de geração de TR indisponível. Verifique se o rag_service está em execução."}, status=503)
    except requests.exceptions.Timeout:
        return JsonResponse({"ok": False, "error": "Tempo limite na geração de TR. O rag_service demorou para responder."}, status=504)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=502)

    content_type = resp.headers.get("content-type", "") or ""
    if resp.status_code != 200:
        if "json" in content_type:
            try:
                data = resp.json()
                err = data.get("detail") or data.get("error") or str(data)
            except Exception:
                err = resp.text
        else:
            err = resp.text
        return JsonResponse({"ok": False, "error": err}, status=resp.status_code)

    final_bytes = None

    # Esperado: DOCX diretamente (FileResponse do rag_service)
    if "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in content_type or "octet-stream" in content_type:
        final_bytes = resp.content
    else:
        # Fallback: tentar json e extrair docx_path, se houver
        try:
            data = resp.json()
        except Exception:
            return JsonResponse({"ok": False, "error": "Resposta inesperada do serviço de TR."}, status=502)

        docx_path = data.get("docx_path")
        if docx_path and os.path.isfile(docx_path):
            with open(docx_path, "rb") as f:
                final_bytes = f.read()

    if final_bytes is None:
        return JsonResponse({"ok": False, "error": "Resposta inesperada do serviço de TR (DOCX não retornado)."}, status=502)

    # Se houver template_id, aplicar cabeçalho/rodapé selecionado em cima do modelo oficial de TR
    if template_id is not None:
        tpl = Template.objects.filter(id=template_id).first()
        if tpl:
            try:
                tmpdir = tempfile.gettempdir()
                rag_docx_path = os.path.join(tmpdir, f"tr_modelo_{tpl.id}.docx")
                out_docx_path = os.path.join(tmpdir, f"tr_modelo_tpl_{tpl.id}.docx")
                with open(rag_docx_path, "wb") as f:
                    f.write(final_bytes)

                merge_docx_with_template_body(
                    source_docx_path=rag_docx_path,
                    template_docx_path=tpl.file.path,
                    out_docx_path=out_docx_path,
                )

                with open(out_docx_path, "rb") as f:
                    final_bytes = f.read()

                # Opcional: salvar em Meus Documentos, mantendo histórico
                try:
                    if request.user.is_authenticated:
                        inst = DocumentInstance(
                            template=tpl,
                            owner=request.user,
                            data={
                                "user_prompt": user_prompt,
                                "context": context,
                                "document_type_hint": "tr_modelo",
                            },
                            status="final",
                        )
                        inst.file_docx.save(
                            f"{inst.id}.docx",
                            ContentFile(final_bytes),
                            save=True,
                        )
                        record_document_instance_created(
                            doc_type="tr_modelo",
                            package=slot_package_key,
                            prefeitura=prefeitura_label_from_request(request),
                        )
                except Exception:
                    pass
            except Exception:
                # Em caso de falha na mesclagem, volta a usar o DOCX original do TR modelo.
                final_bytes = resp.content

    r = HttpResponse(
        final_bytes,
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    r["Content-Disposition"] = 'attachment; filename=\"termo_referencia_modelo.docx\"'
    return r


@csrf_exempt
@api_login_required
@track_docmaster_view("gerar_tr_e_dfd")
def gerar_tr_e_dfd_api(request):
    """
    Gera Termo de Referência e DFD a partir dos modelos fixos do rag_service,
    aplicando opcionalmente o template (cabeçalho/rodapé) selecionado, e retorna
    ambos em JSON com conteúdo em base64 (TR, DFD e ZIP TR+DFD).
    """
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Use POST"}, status=405)

    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({"ok": False, "error": "Corpo JSON inválido"}, status=400)

    slot_package_key = _resolve_slot_package_key(payload, request)
    set_request_metrics(request, package=slot_package_key, output="zip")

    raw_template_id = payload.get("template_id")
    if raw_template_id not in (None, ""):
        tpl = Template.objects.filter(id=str(raw_template_id).strip()).first()
        if not tpl:
            return JsonResponse({"ok": False, "error": "template_id inválido."}, status=400)
        if not _can_user_access_template(request.user, tpl):
            return JsonResponse({"ok": False, "error": "Acesso negado ao template desta prefeitura."}, status=403)

    user_prompt = (payload.get("user_prompt") or "").strip()
    slots_override = payload.get("slots_override")  # opcional
    template_id = _resolve_merge_template_id(request, payload)

    if not user_prompt:
        return JsonResponse({"ok": False, "error": "user_prompt é obrigatório"}, status=400)

    context = build_llm_context_from_request(request)
    if slot_package_key:
        context["slot_package_key"] = slot_package_key

    def _slug(v: str) -> str:
        s = re.sub(r"[^a-zA-Z0-9_\\-]+", "_", (v or "").strip().lower())
        s = re.sub(r"_+", "_", s).strip("_")
        return s or "tr_dfd_generico"

    now = timezone.localtime(timezone.now())
    stamp = now.strftime("%d_%m_%Y_%H-%M")
    package_slug = _slug(slot_package_key or "tr_dfd_generico")
    tr_filename = f"tr_{package_slug}_{stamp}_docmasteria.docx"
    dfd_filename = f"dfd_{package_slug}_{stamp}_docmasteria.docx"
    oficio_filename = f"oficio_{package_slug}_{stamp}_docmasteria.docx"
    zip_filename = f"tr_dfd_oficio_{package_slug}_{stamp}_docmasteria.zip"

    rag_url = getattr(django_settings, "RAG_SERVICE_URL", "http://127.0.0.1:8004").rstrip("/")
    url = f"{rag_url}/api/rag/generate-tr-and-dfd-zip"

    body = {
        "user_prompt": user_prompt,
        "slots_override": slots_override or None,
        "context": context if context else None,
        "skip_context_in_prompt": True,
    }

    try:
        resp = _rag_post_json(
            url,
            body,
            timeout=_rag_timeout_seconds_for_tr_dfd(body),
        )
    except requests.exceptions.ConnectionError:
        return JsonResponse({"ok": False, "error": "Serviço de geração de TR/DFD indisponível. Verifique se o rag_service está em execução."}, status=503)
    except requests.exceptions.Timeout:
        return JsonResponse(
            {
                "ok": False,
                "error": (
                    "Tempo limite na geração de TR/DFD (o serviço demorou além do permitido). "
                    "Com muitos itens tente de novo, reduza itens em branco ou peça ao administrador "
                    "para aumentar RAG_HTTP_TIMEOUT / RAG_HTTP_TIMEOUT_TR_DFD_MAX ou o limite do proxy (nginx/Cloudflare; ver deploy/nginx-gerar-tr-e-dfd-timeout.conf.example)."
                ),
            },
            status=504,
        )
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=502)

    if resp.status_code != 200:
        try:
            err = resp.json().get("detail", resp.json().get("error", resp.text))
        except Exception:
            err = resp.text
        return JsonResponse({"ok": False, "error": err}, status=resp.status_code)

    import base64
    import io
    import zipfile

    # Resposta é o ZIP (generate-tr-and-dfd-zip devolve arquivo único)
    zip_bytes_raw = resp.content
    if not zip_bytes_raw:
        return JsonResponse({"ok": False, "error": "Serviço retornou ZIP vazio."}, status=502)
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes_raw), "r") as zf:
            tr_bytes = zf.read("termo_referencia.docx")
            dfd_bytes = zf.read("dfd.docx")
            oficio_bytes = None
            for oficio_name in ("solicitacao_oficio.docx", "oficio.docx"):
                try:
                    oficio_bytes = zf.read(oficio_name)
                    break
                except KeyError:
                    continue
            if oficio_bytes is None:
                available = ", ".join(zf.namelist())
                return JsonResponse(
                    {
                        "ok": False,
                        "error": f"ZIP sem arquivo de Ofício esperado (solicitacao_oficio.docx/oficio.docx). Conteúdo: {available}",
                    },
                    status=502,
                )
    except KeyError as e:
        return JsonResponse({"ok": False, "error": f"ZIP sem arquivo esperado: {e}"}, status=502)
    except Exception as e:
        return JsonResponse({"ok": False, "error": f"ZIP inválido: {e}"}, status=502)

    _record_llm_usage_from_response(request, "gerar_tr_e_dfd", http_response=resp)

    tpl = Template.objects.filter(id=template_id).first() if template_id is not None else None

    def _maybe_merge_with_template(raw: bytes, name: str):
        """
        Retorna (bytes, applied, error_message).
        """
        if not tpl:
            return raw, False, "template_id não informado ou template não encontrado"
        try:
            with tempfile.NamedTemporaryFile(prefix=f"tr_dfd_{tpl.id}_", suffix=f"_{name}", delete=False) as src_tmp:
                src_tmp.write(raw)
                rag_docx_path = src_tmp.name
            with tempfile.NamedTemporaryFile(prefix=f"tr_dfd_tpl_{tpl.id}_", suffix=f"_{name}", delete=False) as out_tmp:
                out_docx_path = out_tmp.name
            merge_docx_with_template_body(
                source_docx_path=rag_docx_path,
                template_docx_path=tpl.file.path,
                out_docx_path=out_docx_path,
            )
            with open(out_docx_path, "rb") as fr:
                return fr.read(), True, ""
        except Exception as e:
            # Não quebrar geração: devolve original, mas registra para diagnóstico.
            err = f"{type(e).__name__}: {e}"
            print(f"[merge_docx_with_template_body] falha ao aplicar template_id={getattr(tpl, 'id', None)} arquivo={name}: {err}")
            return raw, False, err

    tr_bytes, tr_template_applied, tr_merge_error = _maybe_merge_with_template(tr_bytes, "termo_referencia.docx")
    dfd_bytes, dfd_template_applied, dfd_merge_error = _maybe_merge_with_template(dfd_bytes, "dfd.docx")
    oficio_bytes, oficio_template_applied, oficio_merge_error = _maybe_merge_with_template(oficio_bytes, "solicitacao_oficio.docx")

    # Opcional: salvar instância principal (TR) em "Meus Documentos"
    if tpl and request.user.is_authenticated:
        try:
            inst = DocumentInstance(
                template=tpl,
                owner=request.user,
                data={
                    "user_prompt": user_prompt,
                    "context": context,
                    "document_type_hint": "tr_dfd_modelo",
                },
                status="final",
            )
            inst.file_docx.save(
                f"{inst.id}.docx",
                ContentFile(tr_bytes),
                save=True,
            )
            record_document_instance_created(
                doc_type="tr_dfd",
                package=slot_package_key,
                prefeitura=prefeitura_label_from_request(request),
            )
        except Exception:
            pass

    # Monta ZIP TR+DFD+Ofício em memória
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(tr_filename, tr_bytes)
        zf.writestr(dfd_filename, dfd_bytes)
        zf.writestr(oficio_filename, oficio_bytes)
    zip_bytes = zip_buffer.getvalue()

    return JsonResponse(
        {
            "ok": True,
            "tr": {
                "filename": tr_filename,
                "docx_base64": base64.b64encode(tr_bytes).decode("ascii"),
                "template_applied": tr_template_applied,
                "merge_error": tr_merge_error or None,
            },
            "dfd": {
                "filename": dfd_filename,
                "docx_base64": base64.b64encode(dfd_bytes).decode("ascii"),
                "template_applied": dfd_template_applied,
                "merge_error": dfd_merge_error or None,
            },
            "oficio": {
                "filename": oficio_filename,
                "docx_base64": base64.b64encode(oficio_bytes).decode("ascii"),
                "template_applied": oficio_template_applied,
                "merge_error": oficio_merge_error or None,
            },
            "zip": {
                "filename": zip_filename,
                "zip_base64": base64.b64encode(zip_bytes).decode("ascii"),
            },
        }
    )


@csrf_exempt
@api_login_required
@track_docmaster_view("fill_tr_slots")
def fill_tr_slots_api(request):
    """
    Preenche slots do TR via rag_service (fill_tr_slots_with_llm) — mesmo pipeline da
    geração TR/DFD/Ofício, sem DOCX. Usado pelo botão «Gerar» objeto/justificativa antes do documento.
    """
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Use POST"}, status=405)

    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({"ok": False, "error": "Corpo JSON inválido"}, status=400)

    slot_package_key = _resolve_slot_package_key(payload, request)
    set_request_metrics(request, package=slot_package_key, output="json")

    user_prompt = (payload.get("user_prompt") or "").strip()
    slots_override = payload.get("slots_override")

    if not user_prompt:
        return JsonResponse({"ok": False, "error": "user_prompt é obrigatório"}, status=400)

    context = build_llm_context_from_request(request)
    if slot_package_key:
        context["slot_package_key"] = slot_package_key

    rag_url = getattr(django_settings, "RAG_SERVICE_URL", "http://127.0.0.1:8004").rstrip("/")
    url = f"{rag_url}/api/rag/fill-tr-slots"
    body = {
        "user_prompt": user_prompt,
        "slots_override": slots_override or None,
        "context": context if context else None,
        "skip_context_in_prompt": True,
    }

    try:
        resp = _rag_post_json(
            url,
            body,
            timeout=_rag_timeout_seconds_for_tr_dfd(body),
        )
    except requests.exceptions.ConnectionError:
        return JsonResponse(
            {"ok": False, "error": "Serviço de geração indisponível. Verifique se o rag_service está em execução."},
            status=503,
        )
    except requests.exceptions.Timeout:
        return JsonResponse(
            {
                "ok": False,
                "error": (
                    "Tempo limite na geração (fill-tr-slots). "
                    "Verifique RAG_HTTP_TIMEOUT no Django, RAG_TIMEOUT no rag_service e LLM_TIMEOUT no llm_api."
                ),
            },
            status=504,
        )
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=502)

    try:
        out = resp.json()
    except Exception:
        return JsonResponse(
            {"ok": False, "error": f"Resposta inválida do rag_service (status {resp.status_code})."},
            status=502,
        )

    if resp.status_code != 200:
        err = out.get("detail") if isinstance(out, dict) else None
        if err is None and isinstance(out, dict):
            err = out.get("error")
        if err is None:
            err = str(out)
        return JsonResponse({"ok": False, "error": err}, status=resp.status_code)

    if isinstance(out, dict):
        _record_llm_usage_from_response(request, "fill_tr_slots", usage=out.get("llm_token_usage"))

    return JsonResponse(out)


@csrf_exempt
@api_login_required
@track_platform("analise", "documento")
def analise_documentos_api(request):
    """
    Recebe um arquivo (PDF/DOCX) e delega a análise para o rag_service (/api/rag/analyze-document).
    Retorna o JSON de AnalyzeDocumentResponse diretamente para o frontend Vue.
    """
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Use POST"}, status=405)

    uploaded = request.FILES.get("file")
    if not uploaded:
        return JsonResponse({"ok": False, "error": "Envie um arquivo PDF ou DOCX no campo 'file'."}, status=400)

    name = uploaded.name or "documento.pdf"
    suffix = os.path.splitext(name)[1].lower()
    if suffix not in (".pdf", ".docx", ".doc"):
        return JsonResponse({"ok": False, "error": "Formato não suportado. Use PDF ou DOCX."}, status=400)

    rag_url = getattr(django_settings, "RAG_SERVICE_URL", "http://127.0.0.1:8004").rstrip("/")
    url = f"{rag_url}/api/rag/analyze-document"

    files = {
        "file": (name, uploaded.read(), uploaded.content_type or "application/octet-stream"),
    }
    data = {}  # top_k, collection podem ser adicionados futuramente

    try:
        # Sem timeout explícito: deixa a chamada ao rag_service rodar até responder
        resp = requests.post(url, files=files, data=data)
    except requests.exceptions.ConnectionError:
        return JsonResponse({"ok": False, "error": "Serviço de análise de documentos indisponível. Verifique se o rag_service está em execução."}, status=503)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=502)

    try:
        payload = resp.json()
    except Exception:
        return JsonResponse({"ok": False, "error": f"Resposta inválida do serviço de análise (status {resp.status_code})."}, status=502)

    if resp.status_code != 200:
        return JsonResponse({"ok": False, "error": payload.get("detail") or payload.get("error") or str(payload)}, status=resp.status_code)

    return JsonResponse(payload)


# API: retorna até 10 templates para autocomplete/busca.
@csrf_exempt
@require_GET
@api_login_required
def template_list_api(request):
    """
    Retorna até 10 templates em JSON.
    Se `q` vazio => retorna 10 templates mais recentes (do usuário ou todos, ajustar).
    """
    q = request.GET.get("q", "").strip()
    only_user_prefeitura = str(request.GET.get("only_user_prefeitura", "")).strip().lower() in ("1", "true", "yes")
    # Se quiser limitar a templates do usuário: use owner=request.user
    base_qs = _templates_queryset_for_user(request.user).order_by("-created_at")

    if only_user_prefeitura:
        user_pref_id = getattr(request.user, "prefeitura_id", None)
        if user_pref_id is None:
            base_qs = base_qs.none()
        else:
            base_qs = base_qs.filter(prefeitura_id=user_pref_id)

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
@csrf_exempt
@api_login_required
def template_preview_pdf_api(request, template_id):
    tpl = get_object_or_404(Template, id=template_id)
    if not _can_user_access_template(request.user, tpl):
        return JsonResponse({"ok": False, "error": "Acesso negado ao template desta prefeitura."}, status=403)
    if tpl.preview_pdf and tpl.preview_pdf.name:
        # Se o arquivo sumiu do MEDIA (ex.: container recriado sem volume),
        # regenerar em vez de retornar URL quebrada.
        try:
            exists = tpl.preview_pdf.storage.exists(tpl.preview_pdf.name)
        except Exception:
            exists = False
        if exists:
            url = tpl.preview_pdf.url
            return JsonResponse({"ok": True, "pdf_url": url})
        try:
            tpl.preview_pdf.delete(save=False)
        except Exception:
            pass
        tpl.preview_pdf = None
        try:
            tpl.save(update_fields=["preview_pdf"])
        except Exception:
            pass

    # se não existir, gera (requer LibreOffice no servidor)
    url = generate_docx_preview_pdf(tpl)
    if url:
        return JsonResponse({"ok": True, "pdf_url": url})
    return JsonResponse({
        "ok": False,
        "error": "Preview PDF não disponível. O servidor pode não ter LibreOffice instalado ou o arquivo do template não pôde ser convertido.",
    })


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
        record_auth_login(result="failure", prefeitura="Não identificado")
        return JsonResponse({"ok": False, "error": "E-mail/usuário e senha são obrigatórios."}, status=400)

    if request.user.is_authenticated:
        return JsonResponse({"ok": True, "message": "Já autenticado."})

    prefeitura = None
    enforce_prefeitura_match = False
    if prefeitura_url:
        try:
            prefeitura = Prefeitura.objects.get(url=prefeitura_url)
            enforce_prefeitura_match = True
        except Prefeitura.DoesNotExist:
            record_auth_login(result="failure", prefeitura="Não identificado")
            return JsonResponse({"ok": False, "error": "Prefeitura inválida."}, status=400)
    else:
        # Login por SPA/API sem contexto explícito de prefeitura:
        # não deve bloquear usuário válido por fallback arbitrário de tenant.
        prefeitura = None

    ip_key = f"ip:{get_client_ip(request)}"
    if is_locked(ip_key):
        record_auth_login(result="locked", prefeitura="Não identificado")
        return JsonResponse({"ok": False, "error": "Muitas tentativas deste IP. Tente novamente mais tarde."}, status=429)

    form = LoginForm(request=request, data={"email_or_username": email_or_username, "password": password, "remember": remember})
    if not form.is_valid():
        record_failed_attempt(ip_key)
        if email_or_username:
            record_failed_attempt(f"user:{email_or_username}")
        record_auth_login(result="failure", prefeitura="Não identificado")
        err = form.non_field_errors()
        if err:
            return JsonResponse({"ok": False, "error": err[0]}, status=401)
        return JsonResponse({"ok": False, "error": "E-mail/usuário ou senha inválidos."}, status=401)

    user = form.get_user()
    if enforce_prefeitura_match and not user.is_staff and not user.is_superuser:
        if user.prefeitura_id != prefeitura.id:
            record_auth_login(result="forbidden_prefeitura", user=user)
            return JsonResponse({"ok": False, "error": "Usuário não pertence a esta prefeitura."}, status=403)
    user_key = f"user:{user.get_username()}"
    if is_locked(user_key):
        record_auth_login(result="locked", user=user)
        return JsonResponse({"ok": False, "error": "Conta bloqueada temporariamente. Tente novamente mais tarde."}, status=429)
    clear_failed_attempts(ip_key)
    clear_failed_attempts(user_key)
    auth_login(request, user)
    if remember:
        request.session.set_expiry(60 * 60 * 24 * 30)
    else:
        request.session.set_expiry(0)
    resolved_prefeitura_url = prefeitura.url if prefeitura else getattr(getattr(user, "prefeitura", None), "url", "")
    pref_metric = prefeitura or getattr(user, "prefeitura", None)
    record_auth_login(
        result="success",
        prefeitura=prefeitura_label_from_instance(pref_metric) if pref_metric else None,
        user=user,
    )
    return JsonResponse({"ok": True, "message": "Login realizado com sucesso.", "prefeitura_url": resolved_prefeitura_url})


# API: logout (encerra sessão e retorna OK para o front redirecionar ao login).
@csrf_exempt
def api_auth_logout(request):
    if request.method not in ("GET", "POST"):
        return JsonResponse({"ok": False, "error": "Use GET ou POST"}, status=405)
    auth_logout(request)
    # user_logged_out (metrics.connect_auth_signals) incrementa docmaster_auth_logout_total.
    return JsonResponse({"ok": True, "message": "Logout realizado."})


# API: perfil do usuário logado (GET) e atualização (POST).
@csrf_exempt
@api_login_required
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
            "date_joined": (
                timezone.localtime(user.date_joined).strftime("%d/%m/%Y %H:%M")
                if user.date_joined
                else ""
            ),
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
            "allowed_modules": user.get_allowed_modules() if hasattr(user, "get_allowed_modules") else [],
        }
        if user.profile_photo and user.profile_photo.name:
            data["profile_photo"] = user.profile_photo.url
        else:
            data["profile_photo"] = None
        if getattr(user, "secretaria", None):
            data["secretaria"] = str(user.secretaria)
        else:
            data["secretaria"] = None
        pref = getattr(user, "prefeitura", None)
        if pref:
            data["prefeitura"] = str(pref)
            data["prefeitura_id"] = str(pref.id)
            data["prefeitura_uf"] = pref.estado or ""
            data["prefeitura_nome"] = pref.nome_municipio
        else:
            data["prefeitura"] = None
            data["prefeitura_id"] = None
            data["prefeitura_uf"] = ""
            data["prefeitura_nome"] = ""
        return JsonResponse(data)
    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return JsonResponse({"ok": True, "message": "Dados atualizados com sucesso!"})
        return JsonResponse({"ok": False, "errors": form.errors}, status=400)
    return JsonResponse({"error": "Method not allowed"}, status=405)


# API: alteração de senha do usuário logado (requer senha atual).
@csrf_exempt
@api_login_required
def api_me_change_password(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Use POST"}, status=405)
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({"ok": False, "error": "Corpo inválido"}, status=400)

    form = ChangePasswordForm(
        request.user,
        data={
            "current_password": data.get("current_password") or "",
            "new_password1": data.get("new_password") or data.get("new_password1") or "",
            "new_password2": data.get("confirm_password") or data.get("new_password2") or "",
        },
    )
    if form.is_valid():
        form.save()
        update_session_auth_hash(request, request.user)
        return JsonResponse({"ok": True, "message": "Senha alterada com sucesso."})
    return JsonResponse({"ok": False, "errors": form.errors}, status=400)


# API: lista de documentos do usuário (paginação e busca).
@csrf_exempt
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
            "updated_at": (
                timezone.localtime(doc.updated_at).strftime("%d/%m/%Y %H:%M")
                if doc.updated_at
                else ""
            ),
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


@api_login_required
@require_GET
def slot_catalog_batch_api(request):
    raw_fields = (request.GET.get("fields") or "").strip()
    if not raw_fields:
        return JsonResponse({"ok": True, "items": {}})

    fields = [f.strip() for f in raw_fields.split(",") if f.strip()][:80]
    try:
        limit = int(request.GET.get("limit", 20) or 20)
    except Exception:
        limit = 20
    limit = min(max(limit, 1), 100)

    items = {}
    for field_key in fields:
        values = (
            SlotValueCatalog.objects.filter(
                owner=request.user,
                field_key=field_key,
                is_active=True,
            )
            .order_by("-usage_count", "-last_used_at")
            .values_list("value", flat=True)[:limit]
        )
        items[field_key] = list(values)

    return JsonResponse({"ok": True, "items": items})


@api_login_required
@csrf_exempt
def slot_catalog_upsert_api(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Use POST"}, status=405)

    try:
        payload = json.loads(request.body or "{}")
    except Exception:
        return JsonResponse({"ok": False, "error": "Corpo JSON inválido"}, status=400)

    entries = payload.get("entries") or []
    if not isinstance(entries, list):
        return JsonResponse({"ok": False, "error": "entries deve ser uma lista"}, status=400)

    created = 0
    updated = 0
    for item in entries[:300]:
        if not isinstance(item, dict):
            continue
        field_key = str(item.get("field_key") or "").strip()
        value = str(item.get("value") or "").strip()
        if not field_key or not value:
            continue
        normalized = _normalize_slot_value(value)
        if not normalized:
            continue

        obj, was_created = SlotValueCatalog.objects.get_or_create(
            owner=request.user,
            field_key=field_key,
            normalized_value=normalized,
            defaults={"value": value, "usage_count": 1, "is_active": True},
        )
        if was_created:
            created += 1
            continue

        obj.value = value
        obj.usage_count = (obj.usage_count or 0) + 1
        obj.is_active = True
        obj.save(update_fields=["value", "usage_count", "is_active", "last_used_at", "updated_at"])
        updated += 1

    return JsonResponse({"ok": True, "created": created, "updated": updated})


@api_login_required
@csrf_exempt
def slot_catalog_delete_api(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Use POST"}, status=405)

    try:
        payload = json.loads(request.body or "{}")
    except Exception:
        return JsonResponse({"ok": False, "error": "Corpo JSON inválido"}, status=400)

    field_key = str(payload.get("field_key") or "").strip()
    value = str(payload.get("value") or "").strip()
    if not field_key or not value:
        return JsonResponse({"ok": False, "error": "field_key e value são obrigatórios"}, status=400)

    normalized = _normalize_slot_value(value)
    rows = SlotValueCatalog.objects.filter(
        owner=request.user,
        field_key=field_key,
        normalized_value=normalized,
        is_active=True,
    ).update(is_active=False)
    return JsonResponse({"ok": True, "deleted": rows})


@api_login_required
@require_GET
def slot_form_state_get_api(request):
    slot_package_key = str(request.GET.get("slot_package_key") or "").strip() or "tr_dfd_generico"
    obj = SlotFormState.objects.filter(owner=request.user, slot_package_key=slot_package_key).first()
    return JsonResponse({"ok": True, "slot_package_key": slot_package_key, "data": (obj.data if obj else {})})


@api_login_required
@csrf_exempt
def slot_form_state_save_api(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Use POST"}, status=405)

    try:
        payload = json.loads(request.body or "{}")
    except Exception:
        return JsonResponse({"ok": False, "error": "Corpo JSON inválido"}, status=400)

    slot_package_key = str(payload.get("slot_package_key") or "").strip() or "tr_dfd_generico"
    data = payload.get("data")
    if not isinstance(data, dict):
        return JsonResponse({"ok": False, "error": "data deve ser um objeto JSON"}, status=400)

    merged = {}
    existing = SlotFormState.objects.filter(owner=request.user, slot_package_key=slot_package_key).first()
    if existing and isinstance(existing.data, dict):
        merged = dict(existing.data)
    merged.update(data)

    # Limite simples defensivo de volume.
    if len(json.dumps(merged, ensure_ascii=False)) > 100_000:
        return JsonResponse({"ok": False, "error": "data excede tamanho máximo permitido"}, status=400)

    obj, _ = SlotFormState.objects.update_or_create(
        owner=request.user,
        slot_package_key=slot_package_key,
        defaults={"data": merged},
    )
    return JsonResponse({"ok": True, "id": str(obj.id), "slot_package_key": slot_package_key})
