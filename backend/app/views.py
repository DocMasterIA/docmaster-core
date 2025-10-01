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

def DashboardView(request):
    return render(request, "dashboard.html")

def AreaDoUsuarioView(request):
    return render(request,"area_do_usuario.html")

def DocumentGeneratorView(request):
    return render(request, "document_generator.html")

def RegisterView(request):
    return render(request,"register_portal.html")