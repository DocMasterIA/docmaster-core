from django.urls import path
from .views import LoginView, RegisterView, DashboardView, AreaDoUsuarioView, LogoutView, DocumentGeneratorView, GetTemplatesView
from .api import upload_template_and_request_mapping_api, get_template_list_api, generate_document_with_values_api, template_list_api, template_preview_pdf_api
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('login', LoginView, name="login_panel"),
    path('logout', LogoutView, name="logout"),
    path('registro', RegisterView, name="registro_panel"),
    path('',DashboardView, name="dashboard"),
    path('area_do_usuario', AreaDoUsuarioView, name="area_do_usuario"),
    path('gerador_de_documentos/', DocumentGeneratorView, name="gerador_de_documentos"),
    path('biblioteca_documentos/',GetTemplatesView, name="biblioteca_documentos"),
    ### API
    path('api/documentos_modelos/enviar', upload_template_and_request_mapping_api, name="documentos_modelos-enviar_api"),
    path("api/documentos_modelos/", get_template_list_api, name="documentos_modelos-get_api"),
    path("api/documentos_modelos/gerar", generate_document_with_values_api, name="documentos_modelos-gerar_api"),
    path("api/documentos_modelos/lista_10", template_list_api, name="documentos_modelos-lista_10_api"),
    path('api/documentos_modelos/<uuid:template_id>/pdf/', template_preview_pdf_api, name='documentos_modelos-previsualizar'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

