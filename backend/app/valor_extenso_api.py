from __future__ import annotations

import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from backend.app.api import api_login_required
from backend.app.utils.valor_extenso_pt import valor_monetario_extenso_payload


def _parse_valor_request(request):
    valor = request.GET.get("valor")
    if request.method == "POST" and request.body:
        try:
            body = json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return None, JsonResponse({"ok": False, "error": "JSON inválido."}, status=400)
        if isinstance(body, dict):
            valor = body.get("valor", valor)
    if valor is None or str(valor).strip() == "":
        return None, JsonResponse({"ok": False, "error": "Informe o parâmetro «valor»."}, status=400)
    return valor, None


@api_login_required
@csrf_exempt
@require_http_methods(["GET", "POST", "OPTIONS"])
def api_valor_monetario_extenso(request):
    if request.method == "OPTIONS":
        return JsonResponse({}, status=204)

    valor, err = _parse_valor_request(request)
    if err is not None:
        return err

    try:
        payload = valor_monetario_extenso_payload(valor)
    except ValueError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

    return JsonResponse({"ok": True, **payload})
