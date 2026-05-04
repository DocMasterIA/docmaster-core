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
    gerar_tr_e_dfd_api,
    template_filters_api,
    analise_documentos_api,
    slot_catalog_batch_api,
    slot_catalog_upsert_api,
    slot_catalog_delete_api,
    slot_form_state_get_api,
    slot_form_state_save_api,
)
from .llm_proxy import llm_proxy
from .pncp_research_proxy import pncp_research_proxy
from .pncp_cotacao_api import (
    pncp_fornecedores_cadastrados,
    pncp_research_sessions_add_items,
    pncp_research_sessions_download_supplier_pdf,
    pncp_research_sessions_delete_items,
    pncp_research_sessions_detail,
    pncp_research_sessions_item_cotacoes,
    pncp_research_sessions_item_cotacoes_update,
    pncp_research_sessions_item_update,
    pncp_research_sessions_import_items,
    pncp_research_sessions_list_create,
    pncp_research_sessions_upload_supplier_pdf,
    pncp_research_sessions_update,
)
from .pncp_relatorio_api import pncp_cotacao_relatorio_pdf, pncp_cotacao_relatorio_verificar
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
    path("api/documentos_modelos/filtros", template_filters_api, name="documentos_modelos-filtros_api"),
    path("api/documentos/gerar-tr-e-dfd", gerar_tr_e_dfd_api, name="documentos_gerar_tr_e_dfd_api"),
    path("api/analise-documentos/", analise_documentos_api, name="analise_documentos_api"),
    path("api/documentos_modelos/lista_10", template_list_api, name="documentos_modelos-lista_10_api"),
    path('api/documentos_modelos/<uuid:template_id>/pdf/', template_preview_pdf_api, name='documentos_modelos-previsualizar'),
    path('api/me/', api_me, name='api_me'),
    path('api/me/documents/', api_me_documents, name='api_me_documents'),
    path('api/auth/login/', api_auth_login, name='api_auth_login'),
    path('api/auth/logout/', api_auth_logout, name='api_auth_logout'),
    path("api/slots/catalog/batch", slot_catalog_batch_api, name="slots_catalog_batch_api"),
    path("api/slots/catalog/upsert", slot_catalog_upsert_api, name="slots_catalog_upsert_api"),
    path("api/slots/catalog/delete", slot_catalog_delete_api, name="slots_catalog_delete_api"),
    path("api/slots/form-state", slot_form_state_get_api, name="slots_form_state_get_api"),
    path("api/slots/form-state/save", slot_form_state_save_api, name="slots_form_state_save_api"),
    # Proxy LLM: sessão Django obrigatória; repassa para FastAPI (LLM_API_BASE_URL)
    path('api/llm/<path:path>', llm_proxy, name='api_llm_proxy'),
    # Cotações PNCP persistidas no Django (ORM)
    path(
        'api/pncp/cotacoes/fornecedores',
        pncp_fornecedores_cadastrados,
        name='api_pncp_cotacoes_fornecedores',
    ),
    path(
        'api/pncp/cotacoes/research/sessions',
        pncp_research_sessions_list_create,
        name='api_pncp_cotacoes_sessions',
    ),
    path(
        'api/pncp/cotacoes/research/sessions/<int:sessao_id>',
        pncp_research_sessions_detail,
        name='api_pncp_cotacoes_session_detail',
    ),
    path(
        'api/pncp/cotacoes/research/sessions/<int:sessao_id>/update',
        pncp_research_sessions_update,
        name='api_pncp_cotacoes_session_update',
    ),
    path(
        'api/pncp/cotacoes/research/sessions/<int:sessao_id>/items',
        pncp_research_sessions_add_items,
        name='api_pncp_cotacoes_session_items',
    ),
    path(
        'api/pncp/cotacoes/research/sessions/<int:sessao_id>/items/import',
        pncp_research_sessions_import_items,
        name='api_pncp_cotacoes_session_items_import',
    ),
    path(
        'api/pncp/cotacoes/research/sessions/<int:sessao_id>/attachments/supplier-pdf',
        pncp_research_sessions_upload_supplier_pdf,
        name='api_pncp_cotacoes_session_supplier_pdf_upload',
    ),
    path(
        'api/pncp/cotacoes/research/sessions/<int:sessao_id>/attachments/supplier-pdf/download',
        pncp_research_sessions_download_supplier_pdf,
        name='api_pncp_cotacoes_session_supplier_pdf_download',
    ),
    path(
        'api/pncp/cotacoes/research/sessions/<int:sessao_id>/items/delete',
        pncp_research_sessions_delete_items,
        name='api_pncp_cotacoes_session_items_delete',
    ),
    path(
        'api/pncp/cotacoes/research/sessions/<int:sessao_id>/items/<int:item_id>/update',
        pncp_research_sessions_item_update,
        name='api_pncp_cotacoes_session_item_update',
    ),
    path(
        'api/pncp/cotacoes/research/sessions/<int:sessao_id>/items/<int:item_id>/cotacoes',
        pncp_research_sessions_item_cotacoes,
        name='api_pncp_cotacoes_session_item_cotacoes',
    ),
    path(
        'api/pncp/cotacoes/research/sessions/<int:sessao_id>/items/<int:item_id>/cotacoes/<int:cotacao_id>/update',
        pncp_research_sessions_item_cotacoes_update,
        name='api_pncp_cotacoes_session_item_cotacao_update',
    ),
    path(
        'api/pncp/cotacoes/research/sessions/<int:sessao_id>/relatorio/pdf',
        pncp_cotacao_relatorio_pdf,
        name='api_pncp_cotacao_relatorio_pdf',
    ),
    path(
        'api/pncp/cotacoes/research/sessions/<int:sessao_id>/relatorio/verificar',
        pncp_cotacao_relatorio_verificar,
        name='api_pncp_cotacao_relatorio_verificar',
    ),
    # Proxy pesquisador PNCP (sessão Django → pncp_researcher_service)
    path('api/pncp-research/<path:path>', pncp_research_proxy, name='api_pncp_research_proxy'),
    path('secretaria-autocomplete/ajax/', SecretariaAutocomplete.as_view(), name='secretaria-autocomplete'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

