# app/middleware.py
from django.shortcuts import get_object_or_404
from .models import Prefeitura

class PrefeituraMiddleware:
    """
    Middleware multi-tenant: resolve a prefeitura a partir do primeiro segmento do path
    e injeta em request.prefeitura. Deve estar após AuthenticationMiddleware.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # tenta extrair prefeitura_slug de kwargs (quando URLConf passou)
        prefeitura_slug = None
        if hasattr(request, "resolver_match") and request.resolver_match:
            prefeitura_slug = request.resolver_match.kwargs.get("prefeitura_slug")

        # fallback: pega do path (ex: /joinville/alguma/coisa)
        if not prefeitura_slug:
            parts = request.path_info.lstrip("/").split("/", 1)
            if parts and parts[0]:
                prefeitura_slug = parts[0]

        request.prefeitura = None
        if prefeitura_slug:
            try:
                request.prefeitura = Prefeitura.objects.get(url=prefeitura_slug)
            except Prefeitura.DoesNotExist:
                request.prefeitura = None

        return self.get_response(request)
