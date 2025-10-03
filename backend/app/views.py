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

def LoginView(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, "Login realizado com sucesso!")
            return redirect(reverse("dashboard"))
        else:
            messages.error(request, "E-mail ou senha inválidos.")

    return render(request, "login_portal.html")

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

    if request.method == "POST":
        template_id = request.POST.get("template_id")
        template = get_object_or_404(Template, pk=template_id)

        prompt = request.POST.get("prompt_ia", "").strip()
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
        "form_data": {}
    })