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
from .services import save_file_to_field, assemble_document_context, render_docx_from_template, generate_pdf_from_docx
from django.core.files import File
import os, traceback
from django.template.loader import render_to_string
import tempfile

@login_required
def DocumentGeneratorView(request, template_slug):
    template = get_object_or_404(Template, slug=template_slug)

    if request.method == "POST":
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

        action = request.POST.get("action", "finalize")  # "save" ou "finalize"

        # Cria a DocumentInstance como rascunho
        inst = DocumentInstance.objects.create(
            template=template,
            owner=request.user,
            data=data,
            status="draft"
        )

        # Se clicou em "finalize", gera DOCX e PDF
        if action == "finalize":
            tmpdir = tempfile.gettempdir()
            try:
                # Monta contexto completo
                context = assemble_document_context(data)

                # Gera DOCX
                docx_path = render_docx_from_template(template.file.path, context, dest_dir=tmpdir)

                # Gera PDF
                pdf_path = generate_pdf_from_docx(docx_path)

                # Salva nos campos FileField
                with open(docx_path, "rb") as f:
                    inst.file_docx.save(os.path.basename(docx_path), File(f), save=False)
                with open(pdf_path, "rb") as f:
                    inst.file_pdf.save(os.path.basename(pdf_path), File(f), save=False)

                inst.status = "final"
                inst.save()

                messages.success(request, "Documento finalizado e arquivos gerados com sucesso.")
                # return redirect("document_detail", pk=inst.pk)

            except Exception as e:
                traceback.print_exc()
                messages.error(request, f"Erro ao gerar arquivos: {e}")

        else:
            messages.success(request, "Rascunho salvo com sucesso.")
            # return redirect("document_edit", pk=inst.pk)

    # GET: renderiza form vazio ou com dados se houver
    return render(request, "document_generator.html", {"template": template})
