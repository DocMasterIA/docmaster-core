from django.contrib import admin
from django.urls import path
from .views import LoginView, RegisterView, DashboardView, DocumentGeneratorView

urlpatterns = [
    path('login', LoginView, name="login_panel"),
    path('registro', RegisterView, name="registro_panel"),
    path('',DashboardView, name="dashboard"),
    path('gerador_documentos', DocumentGeneratorView, name="gerador_documentos"),
]
