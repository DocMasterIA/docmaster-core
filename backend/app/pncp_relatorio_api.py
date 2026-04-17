"""
API de relatório PDF de cotação PNCP (esquema inicial).

POST …/relatorio/pdf — gera PDF (título personalizado no corpo JSON).
O QR codifica a URL do SPA para abrir a cotação com usuário autenticado
(/pesquisador-pncp/cotacoes/<id>). Base fixa: PNCP_RELATORIO_QR_FRONTEND_BASE_URL (default docmasteria.com.br).

GET  …/relatorio/verificar — metadados JSON (mesma sessão); o QR não aponta mais aqui.
"""
from __future__ import annotations

import io
import json
from typing import Any, Dict

from django.conf import settings
from django.http import FileResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from backend.app.api import api_login_required
from backend.app.models import PncpCotacao, PncpCotacaoAnexo
from backend.app.services.pncp_relatorio_pdf import (
    concatenar_relatorio_com_anexo_fornecedor,
    gerar_pdf_relatorio_cotacao,
    nome_arquivo_relatorio,
    nome_sistema_relatorio,
)


def _cotacao_qs_for_user(user):
    qs = PncpCotacao.objects.all()
    if user.is_superuser:
        return qs
    return qs.filter(usuario_id=user.id)


def _parse_json(request) -> Dict[str, Any]:
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return {}


def _url_qr_acesso_cotacao_no_sistema(sessao_id: int) -> str:
    """URL do Vue para abrir a cotação com sessão no domínio do app (PNCP_RELATORIO_QR_FRONTEND_BASE_URL)."""
    base = getattr(settings, "PNCP_RELATORIO_QR_FRONTEND_BASE_URL", "https://docmasteria.com.br")
    base = str(base).strip().rstrip("/") or "https://docmasteria.com.br"
    return f"{base}/pesquisador-pncp/cotacoes/{int(sessao_id)}"


@api_login_required
@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def pncp_cotacao_relatorio_pdf(request, sessao_id: int):
    if request.method == "OPTIONS":
        return JsonResponse({}, status=204)

    body = _parse_json(request)
    titulo_rel = str(body.get("titulo_relatorio") or "").strip()
    if not titulo_rel:
        return JsonResponse({"detail": "titulo_relatorio é obrigatório."}, status=422)
    if len(titulo_rel) > 500:
        return JsonResponse({"detail": "titulo_relatorio excede 500 caracteres."}, status=422)

    c = (
        _cotacao_qs_for_user(request.user)
        .select_related("usuario")
        .filter(pk=sessao_id)
        .first()
    )
    if not c:
        return JsonResponse({"ok": False, "error": "Cotação não encontrada."}, status=404)

    itens_qs = c.itens.all()
    if not itens_qs.exists():
        return JsonResponse(
            {"detail": "Esta cotação ainda não possui itens. Adicione ao menos 1 item para gerar o PDF."},
            status=422,
        )

    url_qr = _url_qr_acesso_cotacao_no_sistema(sessao_id)

    try:
        pdf_bytes = gerar_pdf_relatorio_cotacao(
            cotacao=c,
            itens_qs=itens_qs,
            titulo_relatorio=titulo_rel,
            url_verificacao=url_qr,
        )
        anexo = PncpCotacaoAnexo.objects.filter(cotacao_id=c.id).first()
        if anexo and anexo.arquivo_pdf:
            anexo.arquivo_pdf.open("rb")
            try:
                anexo_bytes = anexo.arquivo_pdf.read() or b""
            finally:
                anexo.arquivo_pdf.close()
            if anexo_bytes:
                pdf_bytes = concatenar_relatorio_com_anexo_fornecedor(
                    relatorio_pdf=pdf_bytes,
                    anexo_pdf=anexo_bytes,
                )
    except Exception as e:
        return JsonResponse(
            {"detail": f"Falha ao gerar PDF ({e}). Verifique se WeasyPrint e dependências estão instaladas."},
            status=500,
        )

    fname = nome_arquivo_relatorio(sessao_id, titulo_rel)
    buf = io.BytesIO(pdf_bytes)
    return FileResponse(buf, as_attachment=True, filename=fname, content_type="application/pdf")


@api_login_required
@require_GET
def pncp_cotacao_relatorio_verificar(request, sessao_id: int):
    """Resposta leve para validação digital (conteúdo apontado pelo QR)."""
    c = (
        _cotacao_qs_for_user(request.user)
        .select_related("usuario")
        .filter(pk=sessao_id)
        .first()
    )
    if not c:
        return JsonResponse({"ok": False, "error": "Cotação não encontrada."}, status=404)

    tz = timezone.get_current_timezone()
    criado = timezone.localtime(c.created_at, tz) if c.created_at else None
    return JsonResponse(
        {
            "ok": True,
            "sistema": nome_sistema_relatorio(),
            "cotacao_id": c.id,
            "titulo_cotacao": c.titulo,
            "registrado_em": criado.isoformat() if criado else None,
            "total_itens": c.itens.count(),
            "url_cotacao_spa": _url_qr_acesso_cotacao_no_sistema(sessao_id),
            "mensagem": (
                "O QR do PDF abre esta cotação no aplicativo (rota /pesquisador-pncp/cotacoes/) "
                "quando há sessão autenticada. Este endpoint só devolve metadados em JSON."
            ),
        }
    )
