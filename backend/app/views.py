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
import os, traceback

@login_required
def DocumentGeneratorView(request, template_slug):
    template = get_object_or_404(Template, slug=template_slug)

    # campos mínimos esperados (ou pegue do template.required_fields)
    expected = template.required_fields or ['tipo_documento','modalidade','objeto','orgao','valor_estimado']

    if request.method == 'POST':
        # coleta dados do POST (inclui action)
        data = {k: v for k, v in request.POST.items() if k not in ['csrfmiddlewaretoken']}
        action = data.pop('action', None)

        # validação mínima
        missing = [f for f in expected if not data.get(f)]
        if missing:
            messages.error(request, f"Preencha os campos obrigatórios: {', '.join(missing)}")
            return render(request, 'document_generator.html', {'template': template, 'form_data': data})

        # Caso de edição: tente recuperar instance_id para atualizar rascunho
        instance_id = request.POST.get('instance_id') or request.GET.get('instance')
        inst = None
        if instance_id:
            try:
                inst = DocumentInstance.objects.get(pk=instance_id, owner=request.user)
            except DocumentInstance.DoesNotExist:
                inst = None

        if inst:
            inst.data = data
            inst.save()
        else:
            inst = DocumentInstance.objects.create(template=template, owner=request.user, data=data, status='draft')

        # Se o usuário clicou em "finalize" (ou 'generate'), geramos os arquivos
        if action in ('finalize', 'generate'):
            try:
                # Gere docx e pdf (caminhos temporários)
                docx_path, pdf_path = generate_docx_and_pdf_from_template_model(template, data)

                # Salva os arquivos no model (usa DEFAULT_FILE_STORAGE)
                save_file_to_field(inst, 'file_docx', docx_path, save_instance=False)
                save_file_to_field(inst, 'file_pdf', pdf_path, save_instance=False)

                inst.status = 'final'
                inst.save()

                messages.success(request, 'Documento gerado com sucesso.')
                return redirect('document_detail', pk=inst.pk)

            except Exception as e:
                traceback.print_exc()
                messages.error(request, f"Erro ao gerar arquivo: {e}")
                # mantem rascunho para o usuário tentar novamente

        # Se só salvou/next, redireciona para o passo seguinte de edição
        if action == 'next':
            return redirect('document_step2', pk=inst.pk)

        messages.success(request, 'Rascunho salvo.')
        return redirect('document_edit', pk=inst.pk)

    # GET
    return render(request, 'document_generator.html', {'template': template, 'form_data': {}, 'modalidades': None})
