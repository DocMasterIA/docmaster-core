from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse

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

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Template, DocumentInstance
from .services import save_file_to_field, generate_docx_and_pdf_from_template_model
from django.core.files import File
import os

@login_required
def DocumentGeneratorView(request, template_slug):
    template = get_object_or_404(Template, slug=template_slug)

    if request.method == "POST":
        # coleta dados do form; aqui capturamos tudo menos csrf
        data = {k: v for k, v in request.POST.items() if k != "csrfmiddlewaretoken"}

        # (opcional) construir HTML preview com render_to_string:
        # preview_html = render_to_string('documents/preview_base.html', {'context': data, 'template': template})
        preview_html = data.get("_preview_html", "")  # ou gere na view

        # Salvar rascunho no banco (sem arquivos)
        inst = DocumentInstance.objects.create(
            template=template, owner=request.user, data=data, content_html=preview_html, status='draft'
        )

        # Se o usuário pediu para finalizar, gerar arquivos
        if "finalize" in request.POST:
            try:
                # gera arquivos temporários
                docx_path, pdf_path = generate_docx_and_pdf_from_template_model(template, {**data, "_preview_html": preview_html})
                # salva nos FileFields do DocumentInstance
                save_file_to_field(inst, "file_docx", docx_path, save_instance=False)
                save_file_to_field(inst, "file_pdf", pdf_path, save_instance=False)
                inst.status = "final"
                inst.save()
                messages.success(request, "Documento gerado com sucesso.")
                return redirect("document_detail", pk=inst.pk)
            except Exception as e:
                messages.error(request, f"Erro gerando arquivos: {e}")
                # keep inst as draft for user to retry

        # caso seja apenas preview, redireciona para a página de edição/preview
        return render(request, "document_generator.html", {"template": template, "instance": inst, "preview_html": preview_html, "form_data": data})

    # GET -> mostra form com campos
    fields = template.required_fields or []
    return render(request, "document_generator.html", {"template": template, "fields": fields})
