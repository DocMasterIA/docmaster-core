from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect, get_object_or_404
from django.core.files import File
from django.contrib import messages
from django.urls import reverse
from backend.app.models import Template, DocumentInstance
from backend.app.forms import TemplateUploadForm
from backend.app.services.services import assemble_document_context, generate_pdf_from_docx
from backend.app.services.render import render_docx_from_template
from django.contrib.auth.decorators import login_required
import os, traceback, tempfile
from django.contrib.auth import login as auth_login
from django.views.decorators.http import require_http_methods
from backend.app.forms import LoginForm, RegisterForm, UserProfileForm
from backend.app.utils.utils import get_client_ip, is_locked, clear_failed_attempts, record_failed_attempt
from django.core.paginator import Paginator
from django.views.decorators.cache import never_cache
from django.db.models import Q

from backend.app.models.usuario import User
@require_http_methods(["GET","POST"])
def LoginView(request):
    # se já autenticated, redireciona
    if request.user.is_authenticated:
        return redirect(reverse("dashboard"))

    form = LoginForm(request=request, data=request.POST or None)

    ip = get_client_ip(request)
    ip_key = f"ip:{ip}"

    # bloqueio por IP rápido
    if is_locked(ip_key):
        messages.error(request, "Muitas tentativas deste IP. Tente novamente mais tarde.")
        return render(request, "login_portal.html", {"form": form})

    if request.method == "POST" and form.is_valid():
        user = form.get_user()

        # bloqueio por usuário também
        user_key = f"user:{user.get_username()}"
        if is_locked(user_key):
            messages.error(request, "Conta bloqueada temporariamente por tentativas inválidas.")
            return render(request, "login_portal.html", {"form": form})

        # sucesso: limpa tentativas
        clear_failed_attempts(ip_key)
        clear_failed_attempts(user_key)

        # login
        auth_login(request, user)

        # session: lembrar (persistente) ou sessão expira com o browser
        if form.cleaned_data.get("remember"):
            # 30 dias por exemplo
            request.session.set_expiry(60 * 60 * 24 * 30)
        else:
            # expira quando fecha o browser (ou defina SESSION_COOKIE_AGE)
            request.session.set_expiry(0)

        messages.success(request, "Login realizado com sucesso!")
        return redirect(reverse("dashboard"))

    # se form inválido (POST) -> contabiliza falha
    if request.method == "POST" and not form.is_valid():
        # incrementa falhas por ip e por username se houver
        record_failed_attempt(ip_key)
        username_field = request.POST.get("email_or_username")
        if username_field:
            record_failed_attempt(f"user:{username_field}")

    return render(request, "login_portal.html", {"form": form})

def RegisterView(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Cadastro realizado com sucesso! Faça login para continuar.")
            return redirect('login_panel')
        else:
            # envia todos os erros do form para messages
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = RegisterForm()

    return render(request, "register_portal.html", {"form": form})

@login_required
def LogoutView(request):
    logout(request)
    messages.info(request, "Você saiu da sua conta.")
    return redirect(reverse("login_panel"))

@never_cache
@login_required
def DashboardView(request):
    return render(request, "dashboard.html")

@never_cache
@login_required
def AreaDoUsuarioView(request):
    user = request.user
    query = request.GET.get("q", "")  # busca por título/template

    docs = DocumentInstance.objects.filter(owner=user)
    if query:
        docs = docs.filter(template__name__icontains=query)

    docs = docs.order_by("-updated_at")  # mais recentes primeiro

        # Paginação (10 documentos por página)
    paginator = Paginator(docs, 2)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)


    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Dados atualizados com sucesso!")
            return redirect("area_do_usuario")  # ou use o nome da URL
        else:
            messages.error(request, "Erro ao atualizar os dados. Verifique os campos.")

    else:
        form = UserProfileForm(instance=user)

    return render(request, "area_do_usuario.html", {"form": form, "page_obj": page_obj, "query": query,})

@never_cache
@login_required
def UploadTemplateView(request):
    if request.method == "POST":
        form = TemplateUploadForm(request.POST, request.FILES)
        if form.is_valid():
            template = form.save(commit=False)
            template.owner = request.user
            template.save()
            messages.success(request, "Template enviado com sucesso!")
            # redirecionar para a página de mapeamento via IA depois
            # return redirect("map_template_fields", template_id=template.id)
        else:
            messages.error(request, "Erro ao enviar template. Verifique os campos.")
    else:
        form = TemplateUploadForm()

    return render(request, "upload_template.html", {"form": form})

from django.contrib.auth.decorators import login_required

@never_cache
@login_required
def GetTemplatesView(request):
    user = request.user

    if user.is_superuser or user.is_staff:
        templates = Template.objects.all().order_by("-created_at")
    else:
        user_role = getattr(user, "role", "") or ""
        user_role = str(user_role).upper().strip()
        print(user_role)
    
        templates = Template.objects.filter(
                Q(role_can_access="TODOS") | Q(role_can_access=user_role)
            ).order_by("-created_at")


    return render(request, "template_list.html", {"templates": templates})

@never_cache
@login_required
def DocumentGeneratorView(request):
    from django.core.files import File
    import json, tempfile, os, traceback
    from django.contrib import messages
    from django.shortcuts import render, redirect, get_object_or_404

    user = request.user

    if user.is_superuser or user.is_staff:
        templates = Template.objects.all().order_by("-created_at")
    else:
        user_role = getattr(user, "role", "") or ""
        user_role = str(user_role).upper().strip()
        print(user_role)
    
        templates = Template.objects.filter(
                Q(role_can_access="TODOS") | Q(role_can_access=user_role)
            ).order_by("-created_at")

    selected_template_id = request.GET.get("template_id")
    selected_template = None
    if selected_template_id:
        try:
            selected_template = Template.objects.get(pk=selected_template_id)
            print(f"Tem TemplateID {selected_template_id}")

        except Template.DoesNotExist:
            selected_template = None

    if request.method == "POST":
        template_id = request.POST.get("template_id")

        if not template_id:
            messages.error(request, "É necessário selecionar um documento base antes de gerar o documento.")
            return render(request, "document_generator.html", {"templates": templates})

        template = get_object_or_404(Template, pk=template_id, role_can_access__in=[user.role, "TODOS"])

        prompt = request.POST.get("ia_prompt", "").strip()
        if not prompt:
            messages.error(request, "É necessário fornecer o prompt da IA.")
            return render(request, "document_generator.html", {"templates": templates})

        # --- recebe dados da IA ---
        data_json = request.POST.get("data_json")
        if not data_json:
            messages.error(request, "Nenhum JSON recebido da IA.")
            return render(request, "document_generator.html", {"templates": templates})

        try:
            data = json.loads(data_json)
        except json.JSONDecodeError:
            messages.error(request, "JSON inválido enviado pela IA.")
            return render(request, "document_generator.html", {"templates": templates})

        # --- valida campos obrigatórios ---
        REQUIRED_FIELDS = ["tipo_documento", "modalidade", "objeto", "orgao", "valor_estimado"]
        missing = [f for f in REQUIRED_FIELDS if f not in data or not data[f]]
        if missing:
            messages.error(request, f"Campos obrigatórios faltando: {', '.join(missing)}")
            return render(request, "document_generator.html", {"templates": templates, "form_data": data})

        # --- monta contexto do template ---
        context = assemble_document_context(data)
        context['template'] = template

        # --- cria DocumentInstance como rascunho/final direto ---
        inst = DocumentInstance.objects.create(
            template=template,
            owner=request.user,
            data=data,
            status="draft"
        )

        tmpdir = tempfile.gettempdir()
        try:
            # --- gera DOCX ---
            docx_path = render_docx_from_template(template.file.path, context, dest_dir=tmpdir)

            # --- gera PDF ---
            pdf_path = generate_pdf_from_docx(docx_path)

            # --- salva arquivos ---
            with open(docx_path, "rb") as f:
                inst.file_docx.save(os.path.basename(docx_path), File(f), save=False)
            with open(pdf_path, "rb") as f:
                inst.file_pdf.save(os.path.basename(pdf_path), File(f), save=False)

            inst.status = "final"
            inst.save()
            messages.success(request, "Documento gerado com sucesso!")

            # aqui você pode redirecionar para download ou mostrar links
            return redirect("document_detail", pk=inst.pk)

        except Exception as e:
            traceback.print_exc()
            messages.error(request, f"Erro ao gerar arquivos: {e}")

    # GET: renderiza lista de templates e formulário de prompt
    return render(request, "document_generator.html", {
        "templates": templates,
        "form_data": {},
        "selected_template": selected_template
    })

import datetime

def dashboard_callback(request, context):
    # exemplo: contadores
    from django.db.models import Count
    from django.contrib.auth import get_user_model
    User = get_user_model()

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    templates = Template.objects.all()
    documents = DocumentInstance.objects.all()
    users = User.objects.all()

  

    if start_date:
        documents = documents.filter(created_at__date__gte=start_date)
    if end_date:
        documents = documents.filter(created_at__date__lte=end_date)


    top_users_qs = (
        User.objects
        .annotate(doc_count=Count('documentinstance', filter=Q(documentinstance__in=documents)))
        .order_by('-doc_count')[:5]
    )

    context.update({
        "total_users": users.count(),
        "active_users": users.filter(is_active=True).count(),
        "inactive_users": users.filter(is_active=False).count(),
        "total_templates": templates.count(),
        "template_names": [t.name for t in templates],
        "documents_per_template": [documents.filter(template=t).count() for t in templates],
        "total_documents": documents.count(),
        "documents_finalizados": documents.filter(status='final').count(),
        "latest_documents": documents.order_by('-created_at')[:5],
        "top_users": top_users_qs, 
        "top_users_names": [u.email for u in top_users_qs],
        "top_users_docs": [u.doc_count for u in top_users_qs],
    })

    context['cards'] = [
        {'title':'Usuários','value':users.count(),'chart':'chartUsers','bg':'oklch(62.7% .28 235)'},
        {'title':'Templates','value':templates.count(),'chart':'chartTemplates','bg':'oklch(55.8% .29 235)'},
        {'title':'Documentos','value':documents.count(),'chart':'chartDocuments','bg':'oklch(49.6% .27 235)'},
    ]

    return context
