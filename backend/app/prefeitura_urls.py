from django.urls import path
from .views import LoginView, RegisterView, DashboardView, AreaDoUsuarioView, LogoutView, DocumentGeneratorView, GetTemplatesView
from .api import upload_template_and_request_mapping_api, get_template_list_api, generate_document_with_values_api, template_list_api, template_preview_pdf_api
from .ajax import area_do_usuario_ajax
from django.conf import settings
from django.conf.urls.static import static

# Rotas específicas por prefeitura (multi-tenant)
urlpatterns = [
    path('login', LoginView, name="login_panel"),
    path('logout', LogoutView, name="logout"),
    path('registro', RegisterView, name="registro_panel"),
    path('',DashboardView, name="dashboard"),
    path('area_do_usuario', AreaDoUsuarioView, name="area_do_usuario"),
]