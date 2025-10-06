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
from backend.app.forms import LoginForm
from backend.app.utils.utils import get_client_ip, is_locked, clear_failed_attempts, record_failed_attempt

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
    return render(request,"register_portal.html")

@login_required
def LogoutView(request):
    logout(request)
    messages.info(request, "Você saiu da sua conta.")
    return redirect(reverse("login_panel"))

@login_required
def DashboardView(request):
    return render(request, "dashboard.html")

@login_required
def AreaDoUsuarioView(request):
    return render(request,"area_do_usuario.html")


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

@login_required
def GetTemplatesView(request):
    templates = Template.objects.all()
    return render(request, "template_list.html", {"templates": templates})

@login_required
def DocumentGeneratorView(request):
    from django.core.files import File
    import json, tempfile, os, traceback
    from django.contrib import messages
    from django.shortcuts import render, redirect, get_object_or_404

    # --- lista de templates disponíveis ---
    templates = Template.objects.all()

    print(request.GET)
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

        template = get_object_or_404(Template, pk=template_id)

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