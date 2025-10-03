from django.urls import path
from .views import LoginView, RegisterView, DashboardView, AreaDoUsuarioView, LogoutView, upload_template_and_request_mapping, get_template_list

urlpatterns = [
    path('login', LoginView, name="login_panel"),
    path('logout', LogoutView, name="logout"),
    path('registro', RegisterView, name="registro_panel"),
    path('',DashboardView, name="dashboard"),
    path('area_do_usuario', AreaDoUsuarioView, name="area_do_usuario"),
    path('documentos_modelos/enviar', upload_template_and_request_mapping, name="documentos_modelos-enviar"),
    path("documentos_modelos/", get_template_list, name="documentos_modelos"),

]

