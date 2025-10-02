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
from .services import render_docx_from_template, render_preview_html, convert_html_to_pdf
from django.core.files import File
import os

@login_required
def DocumentGeneratorView(request, template_slug):
    template = get_object_or_404(Template, slug=template_slug)

    if request.method == 'POST':
        # coletar campos dinamicamente do POST
        data = {k: v for k, v in request.POST.items() if k not in ['csrfmiddlewaretoken']}
        # gerar preview html
        preview = render_preview_html(template, data)
        # se for ação "Gerar PDF/DOCX"
        if 'finalize' in request.POST:
            docx_path = render_docx_from_template(template, data)
            # converter preview HTML para PDF
            pdf_path = os.path.splitext(docx_path)[0] + '.pdf'
            convert_html_to_pdf(preview, pdf_path)
            # salvar DocumentInstance
            inst = DocumentInstance.objects.create(
                template=template, owner=request.user, data=data, content_html=preview, status='final'
            )
            # anexar arquivos gerados
            with open(docx_path, 'rb') as f:
                inst.file_docx.save(os.path.basename(docx_path), File(f), save=False)
            with open(pdf_path, 'rb') as f:
                inst.file_pdf.save(os.path.basename(pdf_path), File(f), save=False)
            inst.save()
            return redirect('document_detail', pk=inst.pk)
        # se for apenas preview
        return render(request, 'documents/create.html', {'template': template, 'preview': preview, 'form_data': data})

    # GET: render form com campos esperados
    fields = template.required_fields or []
    return render(request, 'documents/create.html', {'template': template, 'fields': fields})

