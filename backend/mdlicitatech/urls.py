"""
URL configuration for mdlicitatech project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from backend.app.admin import dashboard_view

# Roteamento principal do projeto:
# - /admin e /admin/painel (dashboard custom)
# - rotas globais do app
# - rotas multi-tenant com primeiro segmento como slug da prefeitura
urlpatterns = [
    path('admin/painel/', dashboard_view, name='admin-painel'),
    path('admin/', admin.site.urls),
    path("", include("backend.app.urls")), 
    re_path(r'^(?P<prefeitura_slug>[-\w]+)/', include('backend.app.prefeitura_urls')),

]
