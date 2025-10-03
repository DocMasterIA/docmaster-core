from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from backend.app.models import Template
from django.contrib.auth.decorators import login_required

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
    templates = Template.objects.filter(owner=request.user).order_by("created_at")
    return render(request, "template_list.html", {"templates": templates})
