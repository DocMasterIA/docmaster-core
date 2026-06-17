"""
API de relatório PDF de cotação PNCP (esquema inicial).

POST …/relatorio/pdf — gera PDF de forma síncrona (legado).

POST …/relatorio/pdf/start — enfileira geração e devolve 202 + job_id (evita timeout de proxy).

GET  …/relatorio/pdf/jobs/<uuid> — enquanto pendente devolve 202 JSON; quando pronto devolve 200 JSON com file_url.

GET  …/relatorio/pdf/jobs/<uuid>/file — devolve o PDF (evita misturar JSON e binário no mesmo URL, o que confunde proxies).

O QR codifica URL pública de download da cópia de verificação do PDF gerado
(GET …/relatorio/verificacao/<token>/download). Base: DOCMASTER_QR_PUBLIC_BASE_URL.

GET  …/relatorio/verificar — metadados JSON (sessão autenticada; o QR não aponta aqui).
"""
from __future__ import annotations

import io
import json
import logging
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union
from uuid import UUID

from django.conf import settings
from django.db import close_old_connections
from django.http import FileResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods
from weasyprint import HTML

from backend.app.api import api_login_required
from backend.app.metrics import track_platform
from backend.app.models import PncpCotacao, PncpCotacaoAnexo, PncpCotacaoAnexoArquivo
from backend.app.qr import build_public_absolute_url, resolve_public_api_base_url
from backend.app.services.pncp_relatorio_pdf import gerar_pdf_relatorio_cotacao, nome_arquivo_relatorio, nome_sistema_relatorio
from backend.app.services.pncp_relatorio_verification_store import (
    issue_verification_token,
    load_verification_pdf,
    save_verification_pdf,
    verification_download_path,
)
from backend.app.services.pncp_supplier_enrichment import enrich_missing_supplier_fields_for_cotacao

logger = logging.getLogger(__name__)

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


def _url_qr_download_pdf_verificacao(api_base_url: str, sessao_id: int, token: str) -> str:
    """URL absoluta no QR: baixa a mesma cópia do PDF gravada na geração."""
    return build_public_absolute_url(api_base_url, verification_download_path(sessao_id, token))


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


def _collect_anexos_merge_files_only(cotacao_id: int) -> List[Tuple[str, bytes]]:
    anexos_merge: List[Tuple[str, bytes]] = []
    anexos = list(PncpCotacaoAnexoArquivo.objects.filter(cotacao_id=cotacao_id).order_by("id"))
    for an in anexos:
        if not an.arquivo_pdf:
            continue
        nome = (an.nome_original or "").strip() or "cotacao-fornecedor.pdf"
        try:
            an.arquivo_pdf.open("rb")
            raw = an.arquivo_pdf.read()
            if raw:
                anexos_merge.append((nome, raw))
        finally:
            try:
                an.arquivo_pdf.close()
            except Exception:
                pass
    anexo_legacy = PncpCotacaoAnexo.objects.filter(cotacao_id=cotacao_id).first()
    if anexo_legacy and anexo_legacy.arquivo_pdf:
        nome = (anexo_legacy.nome_original or "").strip() or "cotacao-fornecedor.pdf"
        try:
            anexo_legacy.arquivo_pdf.open("rb")
            raw = anexo_legacy.arquivo_pdf.read()
            if raw:
                anexos_merge.append((nome, raw))
        finally:
            try:
                anexo_legacy.arquivo_pdf.close()
            except Exception:
                pass
    return anexos_merge


def _legacy_anexo_public_url(request, sessao_id: int, cotacao_id: int) -> str:
    anexo_legacy = PncpCotacaoAnexo.objects.filter(cotacao_id=cotacao_id).first()
    if anexo_legacy and anexo_legacy.arquivo_pdf:
        return _url_download_anexo_fornecedor(request, sessao_id)
    return ""


def _collect_anexos_for_pdf(request, sessao_id: int, cotacao_id: int, incluir_anexos: bool) -> Tuple[List[Tuple[str, bytes]], str]:
    if not incluir_anexos:
        return [], ""
    return _collect_anexos_merge_files_only(cotacao_id), _legacy_anexo_public_url(request, sessao_id, cotacao_id)


def _generate_relatorio_pdf_bytes(
    *,
    cotacao: PncpCotacao,
    itens_qs,
    titulo_rel: str,
    sessao_id: int,
    anexos_merge: List[Tuple[str, bytes]],
    anexo_fornecedor_url: str,
    api_base_url: str,
    verification_filename: str,
) -> bytes:
    formula_id = _resolve_formula_calculo_id(cotacao.filtros or {})
    verification_token = issue_verification_token()
    url_qr = _url_qr_download_pdf_verificacao(api_base_url, sessao_id, verification_token)
    # Enriquecimento PNCP/BrasilAPI: ligado por omissão; desligar com PNCP_RELATORIO_PDF_SKIP_ENRICH.
    enriched_emails = False
    if not settings.PNCP_RELATORIO_PDF_SKIP_ENRICH:
        try:
            enrich_missing_supplier_fields_for_cotacao(
                cotacao.id,
                max_lookups=settings.PNCP_RELATORIO_PDF_MAX_PNCP_LOOKUPS,
                max_brasilapi_lookups=settings.PNCP_RELATORIO_PDF_MAX_BRASILAPI_LOOKUPS,
                receitaws_allow_wait=True,
                receitaws_unlimited=False,
            )
            enriched_emails = True
        except Exception:
            logger.exception(
                "enrich_missing_supplier_fields_for_cotacao falhou cotacao_id=%s",
                cotacao.id,
            )

    pdf_bytes = gerar_pdf_relatorio_cotacao(
        cotacao=cotacao,
        itens_qs=itens_qs,
        titulo_relatorio=titulo_rel,
        url_verificacao=url_qr,
        anexo_fornecedor_url=anexo_fornecedor_url,
        formula_id=formula_id,
        skip_email_http_prefetch=enriched_emails,
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
            pass
    save_verification_pdf(
        sessao_id=sessao_id,
        token=verification_token,
        pdf_bytes=pdf_bytes,
        filename=verification_filename,
    )
    return pdf_bytes


def _relatorio_pdf_jobs_dir() -> Path:
    p = Path(settings.MEDIA_ROOT) / "pncp_relatorio_pdf_jobs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _prune_stale_relatorio_pdf_jobs(jobs_dir: Path) -> None:
    max_age = int(getattr(settings, "PNCP_RELATORIO_PDF_JOB_MAX_AGE_SEC", 3600) or 0)
    if max_age <= 0:
        return
    now = timezone.now().timestamp()
    for path in jobs_dir.glob("*.meta.json"):
        try:
            if now - path.stat().st_mtime <= max_age:
                continue
            stem = path.name[: -len(".meta.json")]
            path.unlink(missing_ok=True)
            (jobs_dir / f"{stem}.pdf").unlink(missing_ok=True)
        except OSError:
            pass


def _write_job_meta_error(meta_path: Path, message: str) -> None:
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        meta = {}
    meta["status"] = "error"
    meta["error"] = message
    try:
        meta_path.write_text(json.dumps(meta), encoding="utf-8")
    except OSError:
        pass


def _meta_sessao_id_int(meta: Dict[str, Any]) -> int:
    try:
        return int(meta.get("sessao_id", -1))
    except (TypeError, ValueError):
        return -1


def _load_relatorio_job_meta(job_key: str) -> Tuple[Dict[str, Any] | None, JsonResponse | None]:
    meta_path = _relatorio_pdf_jobs_dir() / f"{job_key}.meta.json"
    if not meta_path.is_file():
        return None, JsonResponse({"detail": "Job não encontrado."}, status=404)
    try:
        return json.loads(meta_path.read_text(encoding="utf-8")), None
    except json.JSONDecodeError:
        return None, JsonResponse({"detail": "Metadados do job inválidos."}, status=500)


def _forbidden_job_owner() -> JsonResponse:
    return JsonResponse({"detail": "Não autorizado."}, status=403)


def _assert_relatorio_job_owner(meta: Dict[str, Any], user, sessao_id: int) -> JsonResponse | None:
    # user.id é UUIDField — meta vem de JSON, user_id é sempre string no ficheiro.
    if _meta_sessao_id_int(meta) != sessao_id or str(meta.get("user_id", "")) != str(user.id):
        return _forbidden_job_owner()
    return None


def _run_relatorio_pdf_job(
    *,
    job_id: str,
    user_id: Union[int, str, UUID],
    is_superuser: bool,
    sessao_id: int,
    titulo_rel: str,
    incluir_anexos: bool,
    anexo_fornecedor_url: str,
    api_base_url: str,
) -> None:
    close_old_connections()
    jobs_dir = _relatorio_pdf_jobs_dir()
    meta_path = jobs_dir / f"{job_id}.meta.json"
    pdf_path = jobs_dir / f"{job_id}.pdf"
    try:
        qs = PncpCotacao.objects.all()
        if not is_superuser:
            qs = qs.filter(usuario_id=user_id)
        c = qs.select_related("usuario", "prefeitura", "usuario__prefeitura").filter(pk=sessao_id).first()
        if not c:
            _write_job_meta_error(meta_path, "Cotação não encontrada.")
            return
        itens_qs = c.itens.prefetch_related("cotacoes")
        if not itens_qs.exists():
            _write_job_meta_error(meta_path, "Esta cotação ainda não possui itens.")
            return
        anexos_merge: List[Tuple[str, bytes]] = []
        eff_anexo_url = ""
        if incluir_anexos:
            anexos_merge = _collect_anexos_merge_files_only(c.id)
            eff_anexo_url = anexo_fornecedor_url or ""
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
        pdf_bytes = _generate_relatorio_pdf_bytes(
            cotacao=c,
            itens_qs=itens_qs,
            titulo_rel=titulo_rel,
            sessao_id=sessao_id,
            anexos_merge=anexos_merge,
            anexo_fornecedor_url=eff_anexo_url,
            api_base_url=api_base_url,
            verification_filename=fname,
        )
        pdf_path.write_bytes(pdf_bytes)
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["status"] = "done"
        meta["filename"] = fname
        meta_path.write_text(json.dumps(meta), encoding="utf-8")
    except Exception as e:
        _write_job_meta_error(meta_path, f"Falha ao gerar PDF ({e}).")
    finally:
        close_old_connections()


def _relatorio_pdf_request_body_validation(request) -> Tuple[Dict[str, Any] | None, JsonResponse | None]:
    """Retorna (body, None) ou (None, JsonResponse erro)."""
    body = _parse_json(request)
    titulo_rel = str(body.get("titulo_relatorio") or "").strip()
    incluir_anexos = bool(body.get("incluir_anexos_fornecedor", False))
    if not titulo_rel:
        return None, JsonResponse({"detail": "titulo_relatorio é obrigatório."}, status=422)
    if len(titulo_rel) > 500:
        return None, JsonResponse({"detail": "titulo_relatorio excede 500 caracteres."}, status=422)
    return {"titulo_relatorio": titulo_rel, "incluir_anexos_fornecedor": incluir_anexos}, None


@api_login_required
@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
@track_platform("pncp_cotacao", "relatorio_pdf")
def pncp_cotacao_relatorio_pdf_start(request, sessao_id: int):
    if request.method == "OPTIONS":
        return JsonResponse({}, status=204)

    parsed, err = _relatorio_pdf_request_body_validation(request)
    if err:
        return err
    assert parsed is not None
    titulo_rel = parsed["titulo_relatorio"]
    incluir_anexos = parsed["incluir_anexos_fornecedor"]

    c = (
        _cotacao_qs_for_user(request.user)
        .select_related("usuario", "prefeitura", "usuario__prefeitura")
        .filter(pk=sessao_id)
        .first()
    )
    if not c:
        return JsonResponse({"ok": False, "error": "Cotação não encontrada."}, status=404)

    itens_qs = c.itens.prefetch_related("cotacoes")
    if not itens_qs.exists():
        return JsonResponse(
            {"detail": "Esta cotação ainda não possui itens. Adicione ao menos 1 item para gerar o PDF."},
            status=422,
        )

    anexo_url = ""
    if incluir_anexos:
        anexo_url = _legacy_anexo_public_url(request, sessao_id, c.id)

    jobs_dir = _relatorio_pdf_jobs_dir()
    _prune_stale_relatorio_pdf_jobs(jobs_dir)
    job_id = str(uuid.uuid4())
    meta = {
        "user_id": str(request.user.id),
        "sessao_id": sessao_id,
        "status": "pending",
        "created": timezone.now().isoformat(),
    }
    meta_path = jobs_dir / f"{job_id}.meta.json"
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    api_base = resolve_public_api_base_url(request)
    threading.Thread(
        target=_run_relatorio_pdf_job,
        kwargs={
            "job_id": job_id,
            "user_id": request.user.id,
            "is_superuser": request.user.is_superuser,
            "sessao_id": sessao_id,
            "titulo_rel": titulo_rel,
            "incluir_anexos": incluir_anexos,
            "anexo_fornecedor_url": anexo_url,
            "api_base_url": api_base,
        },
        daemon=True,
    ).start()

    return JsonResponse(
        {
            "job_id": job_id,
            "status": "pending",
            "poll_path": f"/api/pncp/cotacoes/research/sessions/{sessao_id}/relatorio/pdf/jobs/{job_id}",
        },
        status=202,
    )


@api_login_required
@csrf_exempt
@require_http_methods(["GET", "OPTIONS"])
def pncp_cotacao_relatorio_pdf_job_poll(request, sessao_id: int, job_id: UUID):
    if request.method == "OPTIONS":
        return JsonResponse({}, status=204)
    try:
        job_key = str(job_id)
        meta, err = _load_relatorio_job_meta(job_key)
        if err:
            return err
        assert meta is not None
        owner_err = _assert_relatorio_job_owner(meta, request.user, sessao_id)
        if owner_err:
            return owner_err

        status = meta.get("status")
        if status == "pending":
            return JsonResponse({"status": "pending"}, status=202)
        if status == "error":
            return JsonResponse(
                {
                    "status": "error",
                    "detail": meta.get("error", "Erro ao gerar PDF."),
                },
                status=422,
            )
        if status != "done":
            return JsonResponse({"detail": "Estado do job desconhecido.", "status": str(status)}, status=500)

        pdf_path = _relatorio_pdf_jobs_dir() / f"{job_key}.pdf"
        if not pdf_path.is_file():
            return JsonResponse({"detail": "Arquivo PDF não encontrado."}, status=500)

        fname = str(meta.get("filename") or "relatorio.pdf")
        file_url = (
            f"/api/pncp/cotacoes/research/sessions/{sessao_id}/relatorio/pdf/jobs/{job_key}/file"
        )
        return JsonResponse(
            {
                "status": "done",
                "filename": fname,
                "file_url": file_url,
            }
        )
    except Exception as e:
        return JsonResponse({"detail": f"Erro ao consultar o job ({e})."}, status=500)


@api_login_required
@csrf_exempt
@require_http_methods(["GET", "OPTIONS"])
def pncp_cotacao_relatorio_pdf_job_file(request, sessao_id: int, job_id: UUID):
    if request.method == "OPTIONS":
        return JsonResponse({}, status=204)
    try:
        job_key = str(job_id)
        meta, err = _load_relatorio_job_meta(job_key)
        if err:
            return err
        assert meta is not None
        owner_err = _assert_relatorio_job_owner(meta, request.user, sessao_id)
        if owner_err:
            return owner_err
        if meta.get("status") != "done":
            return JsonResponse({"detail": "O PDF ainda não está pronto."}, status=409)

        pdf_path = _relatorio_pdf_jobs_dir() / f"{job_key}.pdf"
        if not pdf_path.is_file():
            return JsonResponse({"detail": "Arquivo PDF não encontrado."}, status=500)

        fname = str(meta.get("filename") or "relatorio.pdf")
        fh = pdf_path.open("rb")
        resp = FileResponse(fh, as_attachment=True, filename=fname, content_type="application/pdf")
        resp["Access-Control-Expose-Headers"] = "Content-Disposition, X-Relatorio-Layout-Version"
        resp["X-Relatorio-Layout-Version"] = "fontes-cards-v1"
        resp["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp["Pragma"] = "no-cache"
        resp["Expires"] = "0"
        return resp
    except Exception as e:
        return JsonResponse({"detail": f"Erro ao transferir o PDF ({e})."}, status=500)


@api_login_required
@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def pncp_cotacao_relatorio_pdf(request, sessao_id: int):
    if request.method == "OPTIONS":
        return JsonResponse({}, status=204)

    parsed, err = _relatorio_pdf_request_body_validation(request)
    if err:
        return err
    assert parsed is not None
    titulo_rel = parsed["titulo_relatorio"]
    incluir_anexos = parsed["incluir_anexos_fornecedor"]

    c = (
        _cotacao_qs_for_user(request.user)
        .select_related("usuario", "prefeitura", "usuario__prefeitura")
        .filter(pk=sessao_id)
        .first()
    )
    if not c:
        return JsonResponse({"ok": False, "error": "Cotação não encontrada."}, status=404)

    itens_qs = c.itens.prefetch_related("cotacoes")
    if not itens_qs.exists():
        return JsonResponse(
            {"detail": "Esta cotação ainda não possui itens. Adicione ao menos 1 item para gerar o PDF."},
            status=422,
        )

    anexos_merge, anexo_url = _collect_anexos_for_pdf(request, sessao_id, c.id, incluir_anexos)

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
    api_base = resolve_public_api_base_url(request)

    try:
        pdf_bytes = _generate_relatorio_pdf_bytes(
            cotacao=c,
            itens_qs=itens_qs,
            titulo_rel=titulo_rel,
            sessao_id=sessao_id,
            anexos_merge=anexos_merge,
            anexo_fornecedor_url=anexo_url,
            api_base_url=api_base,
            verification_filename=fname,
        )
    except Exception as e:
        return JsonResponse(
            {"detail": f"Falha ao gerar PDF ({e}). Verifique se WeasyPrint e dependências estão instaladas."},
            status=500,
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


@csrf_exempt
@require_GET
def pncp_cotacao_relatorio_verificacao_download(request, sessao_id: int, token: UUID):
    """
    Download público da cópia de verificação (URL codificada no QR do PDF).

    Não exige login: o token UUID na URL é o segredo de acesso.
    """
    loaded = load_verification_pdf(sessao_id, str(token))
    if not loaded:
        return JsonResponse({"detail": "Cópia de verificação não encontrada ou expirada."}, status=404)
    pdf_bytes, fname = loaded
    buf = io.BytesIO(pdf_bytes)
    resp = FileResponse(buf, as_attachment=True, filename=fname, content_type="application/pdf")
    resp["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp["Pragma"] = "no-cache"
    resp["Expires"] = "0"
    resp["X-Relatorio-Verificacao"] = "1"
    return resp


@api_login_required
@require_GET
def pncp_cotacao_relatorio_verificar(request, sessao_id: int):
    """Metadados da cotação (sessão autenticada); o QR aponta para o download de verificação."""
    c = (
        _cotacao_qs_for_user(request.user)
        .select_related("usuario", "prefeitura", "usuario__prefeitura")
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
            "url_verificacao_padrao": build_public_absolute_url(
                resolve_public_api_base_url(request),
                verification_download_path(sessao_id, "<token-da-geracao>"),
            ),
            "mensagem": (
                "O QR do PDF aponta para …/relatorio/verificacao/<token>/download e entrega a mesma "
                "cópia do relatório gerada naquele momento. Este endpoint só devolve metadados em JSON."
            ),
        }
    )
