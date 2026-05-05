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
from typing import Any, Dict, List, Tuple

from django.conf import settings
from django.http import FileResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods
from weasyprint import HTML

from backend.app.api import api_login_required
from backend.app.models import PncpCotacao, PncpCotacaoAnexo, PncpCotacaoAnexoArquivo
from backend.app.services.pncp_relatorio_pdf import gerar_pdf_relatorio_cotacao, nome_arquivo_relatorio, nome_sistema_relatorio
from backend.app.services.pncp_supplier_enrichment import enrich_missing_supplier_fields_for_cotacao

DEFAULT_FORMULA_CALCULO = "media_aritmetica_precos_obtidos"
FORMULA_LABELS = {
    "media_aritmetica_precos_obtidos": "Média aritmética dos preços obtidos",
    "mediana_precos_obtidos": "Mediana dos preços obtidos",
    "menor_preco": "Menor preço",
    "media_saneada": "Média saneada",
    "media_ponderada": "Média ponderada",
    "media_relativa_25_50": "Média relativa 25% - 50%",
}
FORMULA_LABELS_TO_ID = {v.lower(): k for k, v in FORMULA_LABELS.items()}


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


def _url_download_anexo_fornecedor(request, sessao_id: int) -> str:
    return request.build_absolute_uri(
        f"/api/pncp/cotacoes/research/sessions/{int(sessao_id)}/attachments/supplier-pdf/download"
    )


def _resolve_formula_calculo_id(filtros: Any) -> str:
    if not isinstance(filtros, dict):
        return DEFAULT_FORMULA_CALCULO
    fid = str(filtros.get("formula_calculo") or "").strip()
    if not fid:
        return DEFAULT_FORMULA_CALCULO
    by_label = FORMULA_LABELS_TO_ID.get(fid.lower())
    if by_label:
        return by_label
    if fid in FORMULA_LABELS:
        return fid
    return DEFAULT_FORMULA_CALCULO


def _render_anexo_fornecedor_capa_pdf(*, titulo_relatorio: str, nome_arquivo: str) -> bytes:
    html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <style>
    @page {{ size: A4; margin: 22mm 18mm; }}
    body {{
      margin: 0;
      font-family: system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
      color: #0f172a;
      min-height: 100vh;
    }}
    .page-center {{
      min-height: 240mm;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .box {{
      border: 1px solid #d6dde8;
      border-radius: 12px;
      padding: 24px 28px;
      background: #fff;
      text-align: center;
      min-width: 360px;
    }}
    h1 {{
      margin: 0;
      font-size: 32px;
      line-height: 1.2;
      color: #1f4e79;
    }}
  </style>
</head>
<body>
  <div class="page-center">
    <section class="box">
      <h1>Anexo da Cotação</h1>
    </section>
  </div>
</body>
</html>
"""
    return HTML(string=html).write_pdf()


def _merge_pdf_bytes(parts: list[bytes]) -> bytes:
    PdfReader = None
    PdfWriter = None
    try:
        from pypdf import PdfReader as _PdfReader, PdfWriter as _PdfWriter

        PdfReader = _PdfReader
        PdfWriter = _PdfWriter
    except Exception:
        try:
            from PyPDF2 import PdfReader as _PdfReader, PdfWriter as _PdfWriter

            PdfReader = _PdfReader
            PdfWriter = _PdfWriter
        except Exception as e:
            raise RuntimeError("biblioteca de merge PDF não instalada (pypdf/PyPDF2)") from e

    writer = PdfWriter()
    for payload in parts:
        if not payload:
            continue
        reader = PdfReader(io.BytesIO(payload))
        for page in reader.pages:
            writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


@api_login_required
@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def pncp_cotacao_relatorio_pdf(request, sessao_id: int):
    if request.method == "OPTIONS":
        return JsonResponse({}, status=204)

    body = _parse_json(request)
    titulo_rel = str(body.get("titulo_relatorio") or "").strip()
    incluir_anexos = bool(body.get("incluir_anexos_fornecedor", False))
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
    formula_id = _resolve_formula_calculo_id(c.filtros or {})

    url_qr = _url_qr_acesso_cotacao_no_sistema(sessao_id)

    anexos_merge: List[Tuple[str, bytes]] = []
    anexo_url = ""
    if incluir_anexos:
        anexos = list(PncpCotacaoAnexoArquivo.objects.filter(cotacao_id=c.id).order_by("id"))
        for an in anexos:
            if not an.arquivo_pdf:
                continue
            nome = (an.nome_original or "").strip() or "cotacao-fornecedor.pdf"
            try:
                an.arquivo_pdf.open("rb")
                body = an.arquivo_pdf.read()
                if body:
                    anexos_merge.append((nome, body))
            finally:
                try:
                    an.arquivo_pdf.close()
                except Exception:
                    pass
        anexo_legacy = PncpCotacaoAnexo.objects.filter(cotacao_id=c.id).first()
        if anexo_legacy and anexo_legacy.arquivo_pdf:
            anexo_url = _url_download_anexo_fornecedor(request, sessao_id)
            nome = (anexo_legacy.nome_original or "").strip() or "cotacao-fornecedor.pdf"
            try:
                anexo_legacy.arquivo_pdf.open("rb")
                body = anexo_legacy.arquivo_pdf.read()
                if body:
                    anexos_merge.append((nome, body))
            finally:
                try:
                    anexo_legacy.arquivo_pdf.close()
                except Exception:
                    pass

    try:
        # Auto-enriquecimento para cotações legadas que ficaram sem fornecedor/CNPJ.
        try:
            enrich_missing_supplier_fields_for_cotacao(c.id, max_lookups=10)
        except Exception:
            pass

        pdf_bytes = gerar_pdf_relatorio_cotacao(
            cotacao=c,
            itens_qs=itens_qs,
            titulo_relatorio=titulo_rel,
            url_verificacao=url_qr,
            anexo_fornecedor_url=anexo_url,
            formula_id=formula_id,
        )
        if anexos_merge:
            try:
                merge_parts = [pdf_bytes]
                for nome, anexo_bytes in anexos_merge:
                    capa_anexo_pdf = _render_anexo_fornecedor_capa_pdf(
                        titulo_relatorio=titulo_rel,
                        nome_arquivo=nome,
                    )
                    merge_parts.extend([capa_anexo_pdf, anexo_bytes])
                pdf_bytes = _merge_pdf_bytes(merge_parts)
            except Exception:
                # Não bloqueia a geração do relatório principal quando faltar lib de merge.
                pass
    except Exception as e:
        return JsonResponse(
            {"detail": f"Falha ao gerar PDF ({e}). Verifique se WeasyPrint e dependências estão instaladas."},
            status=500,
        )

    u = c.usuario
    user_name = (
        (getattr(c, "criado_por_nome", None) or "").strip()
        or (u.get_full_name() or "").strip()
        or (getattr(u, "email", None) or "").strip()
        or str(u.pk)
    )
    fname = nome_arquivo_relatorio(
        sessao_id,
        titulo_rel,
        sistema_nome=nome_sistema_relatorio(),
        usuario_nome=user_name,
        dt=timezone.now(),
    )
    buf = io.BytesIO(pdf_bytes)
    resp = FileResponse(buf, as_attachment=True, filename=fname, content_type="application/pdf")
    # Permite ao frontend ler o nome do arquivo via Content-Disposition em cenários CORS.
    resp["Access-Control-Expose-Headers"] = "Content-Disposition"
    # Sinaliza explicitamente o layout aplicado no PDF para depuração de ambiente/versionamento.
    resp["X-Relatorio-Layout-Version"] = "fontes-cards-v1"
    resp["Access-Control-Expose-Headers"] = "Content-Disposition, X-Relatorio-Layout-Version"
    resp["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp["Pragma"] = "no-cache"
    resp["Expires"] = "0"
    return resp


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
