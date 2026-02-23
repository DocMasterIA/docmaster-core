from django.urls import path
from .views import favicon_view
from .api import (
    upload_template_and_request_mapping_api,
    get_template_list_api,
    generate_document_with_values_api,
    template_list_api,
    template_preview_pdf_api,
    api_me,
    api_me_documents,
    api_auth_login,
    api_auth_logout,
    gerar_via_llm_api,
    gerar_tr_modelo_api,
    analise_documentos_api,
)
from .llm_proxy import llm_proxy
from .ajax import area_do_usuario_ajax
from django.conf import settings
from django.conf.urls.static import static
from .admin import SecretariaAutocomplete

# Rotas globais do app (APIs e auxiliares como autocomplete)
urlpatterns = [
    path('favicon.ico', favicon_view),
    # API
    path('api/documentos_modelos/enviar', upload_template_and_request_mapping_api, name="documentos_modelos-enviar_api"),
    path("api/documentos_modelos/", get_template_list_api, name="documentos_modelos-get_api"),
    path("api/documentos_modelos/gerar", generate_document_with_values_api, name="documentos_modelos-gerar_api"),
    path("api/documentos/gerar-via-llm", gerar_via_llm_api, name="documentos_gerar_via_llm_api"),
    path("api/documentos/gerar-tr-modelo", gerar_tr_modelo_api, name="documentos_gerar_tr_modelo_api"),
    path("api/analise-documentos/", analise_documentos_api, name="analise_documentos_api"),
    path("api/documentos_modelos/lista_10", template_list_api, name="documentos_modelos-lista_10_api"),
    path('api/documentos_modelos/<uuid:template_id>/pdf/', template_preview_pdf_api, name='documentos_modelos-previsualizar'),
    path('api/me/', api_me, name='api_me'),
    path('api/me/documents/', api_me_documents, name='api_me_documents'),
    path('api/auth/login/', api_auth_login, name='api_auth_login'),
    path('api/auth/logout/', api_auth_logout, name='api_auth_logout'),
    # Proxy LLM: sessão Django obrigatória; repassa para FastAPI (LLM_API_BASE_URL)
    path('api/llm/<path:path>', llm_proxy, name='api_llm_proxy'),
    path('secretaria-autocomplete/ajax/', SecretariaAutocomplete.as_view(), name='secretaria-autocomplete'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

