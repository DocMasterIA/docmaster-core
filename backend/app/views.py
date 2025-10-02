from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from .models import Rule

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

def LogoutView(request):
    logout(request)
    messages.info(request, "Você saiu da sua conta.")
    return redirect(reverse("login_panel"))

def DashboardView(request):
    return render(request, "dashboard.html")

def AreaDoUsuarioView(request):
    return render(request,"area_do_usuario.html")

from django.shortcuts import render, get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from .models import Template, DocumentInstance, Rule
from .services import render_docx_from_template, generate_pdf_from_docx, assemble_document_context, get_snippets_for_data
from django.core.files import File
import os, traceback
from django.template.loader import render_to_string
import tempfile
from django.contrib import messages

@login_required
def DocumentGeneratorView(request, template_slug):
    template = get_object_or_404(Template, slug=template_slug)

    if request.method == "POST":
        # --- coleta dados do form ---
        data = {
            "tipo_documento": request.POST.get("tipo_documento"),
            "modalidade": request.POST.get("modalidade"),
            "objeto": request.POST.get("objeto"),
            "orgao": request.POST.get("orgao"),
            "valor_estimado": request.POST.get("valor_estimado"),
            "prazo_execucao": request.POST.get("prazo_execucao"),
            "responsavel": request.POST.get("responsavel"),
            "observacoes": request.POST.get("observacoes"),
        }

        # --- seleciona snippets pela regra ---
        snippets = []
        rule = Rule.objects.filter(field_name="modalidade", match_value=data["modalidade"]).first()
        if rule:
            snippets.extend(rule.snippets.all())

        # --- monta contexto final para o template ---
        context = assemble_document_context(data)
        context['template'] = template  
        context.update(get_snippets_for_data(data))  
        action = request.POST.get("action", "finalize")  # "save" ou "finalize"

        # --- cria DocumentInstance como rascunho ---
        inst = DocumentInstance.objects.create(
            template=template,
            owner=request.user,
            data=data,
            status="draft"
        )

        if action == "finalize":
            tmpdir = tempfile.gettempdir()
            try:
                # --- gera DOCX ---
                docx_path = render_docx_from_template(template.file.path, context, dest_dir=tmpdir)

                # --- gera PDF ---
                pdf_path = generate_pdf_from_docx(docx_path)

                # --- salva nos FileFields ---
                with open(docx_path, "rb") as f:
                    inst.file_docx.save(os.path.basename(docx_path), File(f), save=False)
                with open(pdf_path, "rb") as f:
                    inst.file_pdf.save(os.path.basename(pdf_path), File(f), save=False)

                inst.status = "final"
                inst.save()

                messages.success(request, "Documento finalizado e arquivos gerados com sucesso.")

            except Exception as e:
                traceback.print_exc()
                messages.error(request, f"Erro ao gerar arquivos: {e}")

        else:
            messages.success(request, "Rascunho salvo com sucesso.")

    # GET: renderiza form
    return render(request, "document_generator.html", {
        "template": template,
        "form_data": data if request.method == "POST" else {}
    })
