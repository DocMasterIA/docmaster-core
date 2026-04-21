"""
CRUD de cotações PNCP no Django (ORM). O proxy `/api/pncp-research/` continua
servindo busca no índice local, market-search e streams no FastAPI.

Validação, limites de payload e transações com select_for_update ao gravar itens.
"""
from __future__ import annotations

import json
import math
import re
import csv
import io
import unicodedata
from datetime import timezone as dt_timezone
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
from django.db import DatabaseError, transaction
from django.db.models import Count
from django.core.files.base import ContentFile
from django.http import JsonResponse, HttpRequest, FileResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from backend.app.api import api_login_required
from backend.app.models import (
    PncpCotacao,
    PncpCotacaoAnexo,
    PncpCotacaoItem,
    PncpCotacaoItemCotacao,
    Prefeitura,
)
from backend.app.services.pncp_relatorio_itens import (
    agrupar_itens_relatorio_pesquisa_precos,
    resumo_calculo_precos,
)
from backend.app.services.pncp_relatorio_pdf import extrair_cnpjs_dos_itens


def _cfg_int(name: str, default: int) -> int:
    v = getattr(settings, name, default)
    try:
        return max(1, int(v))
    except (TypeError, ValueError):
        return default


MAX_JSON_BODY_BYTES = _cfg_int("PNCP_COTACAO_MAX_JSON_BYTES", 8 * 1024 * 1024)
MAX_ITEMS_PER_REQUEST = _cfg_int("PNCP_COTACAO_MAX_ITEMS_PER_REQUEST", 2000)
BULK_CREATE_BATCH = _cfg_int("PNCP_COTACAO_BULK_CREATE_BATCH", 250)
MAX_FILTROS_JSON_BYTES = _cfg_int("PNCP_COTACAO_MAX_FILTROS_JSON_BYTES", 32 * 1024)
MAX_SOURCE_JSON_BYTES = _cfg_int("PNCP_COTACAO_MAX_SOURCE_JSON_BYTES", 120 * 1024)
MAX_ANEXO_PDF_BYTES = _cfg_int("PNCP_COTACAO_MAX_ANEXO_PDF_BYTES", 30 * 1024 * 1024)

ALLOWED_MODELOS = frozenset({"pesquisa_precos_padrao", "referencia_mercado"})
ALLOWED_STATUS = frozenset({"aberta", "finalizada", "cancelada"})
CLOSED_FOR_ITEMS = frozenset({"finalizada", "cancelada"})
ALLOWED_FORMULA_CALCULO = frozenset(
    {
        "media_aritmetica_precos_obtidos",
        "mediana_precos_obtidos",
        "menor_preco",
        "media_saneada",
        "media_ponderada",
        "media_relativa_25_50",
    }
)
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


def _nome_padrao_anexo_fornecedor(sessao_id: int) -> str:
    return f"cotacao-fornecedor-sessao-{int(sessao_id)}.pdf"

_UF_RE = re.compile(r"^[A-Z]{2}$")

# Chaves típicas PNCP / front para preservar se o payload bruto for grande
_SOURCE_KEEP_KEYS = frozenset(
    {
        "numero_pncp",
        "numeroControlePNCP",
        "ano_compra",
        "sequencial_compra",
        "numero_item",
        "numeroItem",
        "descricao_item",
        "descricao",
        "objeto_resumido",
        "objetoCompra",
        "unidade_medida",
        "unidadeMedida",
        "quantidade",
        "valor_unitario",
        "valor_total",
        "valor_global",
        "valorUnitario",
        "valorTotal",
        "orgao",
        "municipio",
        "uf",
        "modalidade",
        "data_publicacao",
        "valor_base",
        "valorBase",
        "preco_base",
        "precoBase",
        "variacao",
        "variacao_percentual",
        "variacaoPercentual",
        "faixa_regional",
        "faixaRegional",
    }
)

IMPORT_REQUIRED_COLUMN_IDS = ("descricao_item", "quantidade", "unidade_medida", "valor_unitario")
IMPORT_OPTIONAL_COLUMN_IDS = (
    "numero_item",
    "numero_pncp",
    "ano_compra",
    "sequencial_compra",
    "orgao",
    "municipio",
    "uf",
    "modalidade",
    "valor_base",
    "variacao_percentual",
)
_IMPORT_ALLOWED_IDS = frozenset(IMPORT_REQUIRED_COLUMN_IDS + IMPORT_OPTIONAL_COLUMN_IDS)
_IMPORT_ALIASES = {
    "id_item": "numero_item",
    "item_id": "numero_item",
    "item": "numero_item",
    "descricao": "descricao_item",
    "descricaoitem": "descricao_item",
    "qtd": "quantidade",
    "unidade": "unidade_medida",
    "unidade_medida": "unidade_medida",
    "valor": "valor_unitario",
    "valor_unitario": "valor_unitario",
    "valorunitario": "valor_unitario",
    "numeropncp": "numero_pncp",
    "ano": "ano_compra",
    "sequencial": "sequencial_compra",
    "variacao": "variacao_percentual",
    "variacao_percentual": "variacao_percentual",
    "valor_base": "valor_base",
}


def _iso_z(dt) -> Optional[str]:
    if dt is None:
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_default_timezone())
    return dt.astimezone(dt_timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds") + "Z"


def _parse_json_body(request: HttpRequest) -> Tuple[Optional[Dict[str, Any]], Optional[JsonResponse]]:
    raw = request.body or b""
    if len(raw) > MAX_JSON_BODY_BYTES:
        return None, JsonResponse(
            {"detail": f"Corpo JSON excede {MAX_JSON_BODY_BYTES} bytes."},
            status=413,
        )
    if not raw.strip():
        return {}, None
    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return None, JsonResponse({"detail": "Corpo da requisição não é JSON válido."}, status=400)
    if not isinstance(data, dict):
        return None, JsonResponse({"detail": "JSON raiz deve ser um objeto."}, status=422)
    return data, None


def _normalize_column_id(v: Any) -> str:
    s = str(v or "").strip().lower()
    if not s:
        return ""
    s = "".join(ch for ch in unicodedata.normalize("NFD", s) if unicodedata.category(ch) != "Mn")
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    s = _IMPORT_ALIASES.get(s, s)
    return s


def _parse_column_map_raw(raw: str) -> Dict[str, str]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    out: Dict[str, str] = {}
    for key, value in data.items():
        k = _normalize_column_id(key)
        v = _normalize_column_id(value)
        if k in _IMPORT_ALLOWED_IDS and v:
            out[k] = v
    return out


def _read_rows_from_upload(upload) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    name = str(getattr(upload, "name", "")).lower()
    if name.endswith(".csv"):
        content = upload.read()
        text = content.decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        return [dict(r) for r in reader], None

    if name.endswith(".xlsx"):
        try:
            from openpyxl import load_workbook
        except Exception:
            return [], "Leitura XLSX indisponível. Instale 'openpyxl' no backend ou envie CSV do Google Sheets."
        wb = load_workbook(filename=upload, read_only=True, data_only=True)
        ws = wb.active
        rows_iter = ws.iter_rows(values_only=True)
        try:
            header = next(rows_iter)
        except StopIteration:
            return [], None
        header_vals = [str(c or "").strip() for c in header]
        out_rows: List[Dict[str, Any]] = []
        for row in rows_iter:
            d: Dict[str, Any] = {}
            for i, h in enumerate(header_vals):
                if not h:
                    continue
                d[h] = row[i] if i < len(row) else None
            out_rows.append(d)
        return out_rows, None

    return [], "Formato inválido. Envie arquivo .csv ou .xlsx."


def _build_items_from_import_rows(rows: List[Dict[str, Any]], column_map: Dict[str, str]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    items: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    for idx, row in enumerate(rows, start=2):
        src = row if isinstance(row, dict) else {}
        normalized_row = {_normalize_column_id(k): v for k, v in src.items()}
        it: Dict[str, Any] = {}
        for cid in IMPORT_REQUIRED_COLUMN_IDS + IMPORT_OPTIONAL_COLUMN_IDS:
            source_key = column_map.get(cid) or cid
            source_key = _normalize_column_id(source_key)
            val = normalized_row.get(source_key)
            if val is None and source_key != cid:
                val = normalized_row.get(cid)
            it[cid] = val

        desc = str(it.get("descricao_item") or "").strip()
        if not desc:
            errors.append({"row": idx, "error": "descricao_item obrigatório"})
            continue
        item_payload = {
            "numero_item": str(it.get("numero_item") or "").strip(),
            "descricao_item": desc,
            "quantidade": _safe_float(it.get("quantidade")),
            "unidade_medida": str(it.get("unidade_medida") or "").strip(),
            "valor_unitario": _safe_float(it.get("valor_unitario")),
            "numero_pncp": str(it.get("numero_pncp") or "").strip(),
            "ano_compra": _safe_int_field(it.get("ano_compra"), min_v=1990, max_v=2100),
            "sequencial_compra": _safe_int_field(it.get("sequencial_compra"), min_v=1, max_v=2_147_483_647),
            "orgao": str(it.get("orgao") or "").strip(),
            "municipio": str(it.get("municipio") or "").strip(),
            "uf": _normalize_uf(it.get("uf")),
            "modalidade": str(it.get("modalidade") or "").strip(),
            "valor_base": _safe_float(it.get("valor_base")),
            "variacao_percentual": _safe_float(it.get("variacao_percentual")),
            "faixa_regional": {
                "valor_base": _safe_float(it.get("valor_base")),
                "variacao_percentual": _safe_float(it.get("variacao_percentual")),
            },
            "origem": "planilha_manual",
        }
        items.append(item_payload)
    return items, errors


def _safe_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def _safe_int_field(v: Any, *, min_v: int, max_v: int) -> Optional[int]:
    if v is None or v == "":
        return None
    try:
        i = int(v)
    except (TypeError, ValueError):
        return None
    if i < min_v or i > max_v:
        return None
    return i


def _normalize_uf(uf: Any) -> str:
    if uf is None:
        return ""
    s = str(uf).strip().upper()[:8]
    if _UF_RE.match(s):
        return s
    return str(uf).strip()[:8]


def _sanitize_filtros(obj: Any) -> Dict[str, Any]:
    """JSON seguro e limitado para o campo filtros (sem estruturas arbitrárias profundas)."""

    def coerce(v: Any, depth: int) -> Any:
        if depth <= 0:
            return None
        if v is None or isinstance(v, bool):
            return v
        if isinstance(v, int):
            return v if -(2**31) <= v < 2**31 else None
        if isinstance(v, float):
            if math.isnan(v) or math.isinf(v):
                return None
            return v
        if isinstance(v, str):
            return v[:4000]
        if isinstance(v, list):
            return [coerce(x, depth - 1) for x in v[:100]]
        if isinstance(v, dict):
            out: Dict[str, Any] = {}
            for i, (k, val) in enumerate(v.items()):
                if i >= 80:
                    break
                if isinstance(k, str) and 0 < len(k) <= 120:
                    out[k] = coerce(val, depth - 1)
            return out
        return str(v)[:500]

    if not isinstance(obj, dict):
        return {}
    coerced = coerce(obj, depth=5)
    assert isinstance(coerced, dict)
    try:
        raw = json.dumps(coerced, ensure_ascii=False, default=str)
    except Exception:
        return {}
    if len(raw.encode("utf-8")) > MAX_FILTROS_JSON_BYTES:
        return {}
    return coerced


def _resolve_formula_calculo_id(filtros: Any) -> str:
    def _coerce_formula_id(raw_value: Any) -> str:
        if raw_value is None:
            return DEFAULT_FORMULA_CALCULO
        fid = str(raw_value).strip()
        if fid in ALLOWED_FORMULA_CALCULO:
            return fid
        by_label = FORMULA_LABELS_TO_ID.get(fid.lower())
        if by_label:
            return by_label
        return DEFAULT_FORMULA_CALCULO

    if not isinstance(filtros, dict):
        return DEFAULT_FORMULA_CALCULO
    raw = filtros.get("formula_calculo") or filtros.get("formula_calculo_id")
    if raw is None:
        return DEFAULT_FORMULA_CALCULO
    return _coerce_formula_id(raw)


def _compact_item_source(it: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(it, dict):
        return {}
    try:
        raw = json.dumps(it, ensure_ascii=False, default=str)
    except Exception:
        slim = {k: it[k] for k in _SOURCE_KEEP_KEYS if k in it}
        return slim
    if len(raw.encode("utf-8")) <= MAX_SOURCE_JSON_BYTES:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {k: it[k] for k in _SOURCE_KEEP_KEYS if k in it}
    slim = {k: it[k] for k in _SOURCE_KEEP_KEYS if k in it}
    try:
        raw2 = json.dumps(slim, ensure_ascii=False, default=str)
        if len(raw2.encode("utf-8")) > MAX_SOURCE_JSON_BYTES:
            return {"_truncado": True, "numero_pncp": str(it.get("numero_pncp") or it.get("numeroControlePNCP") or "")[:256]}
    except Exception:
        pass
    return slim


def _usuario_criacao_snapshot(user) -> tuple[str, str]:
    """Nome e e-mail exibidos na cotação (snapshot no create)."""
    nome = ""
    first = (getattr(user, "first_name", None) or "").strip()
    last = (getattr(user, "last_name", None) or "").strip()
    if first or last:
        nome = f"{first} {last}".strip()
    if not nome:
        get_full_name = getattr(user, "get_full_name", None)
        if callable(get_full_name):
            try:
                nome = (get_full_name() or "").strip()
            except Exception:
                nome = ""
    email = (getattr(user, "email", None) or "").strip()
    if not nome:
        nome = email or str(user.pk)
    return nome[:240], email[:254]


def _create_cotacao_with_snapshot_fallback(
    *,
    usuario,
    prefeitura_id,
    titulo: str,
    termo: str,
    modelo: str,
    filtros: Dict[str, Any],
    nome_snap: str,
    email_snap: str,
) -> PncpCotacao:
    """
    Evita 500 quando o banco ainda não possui colunas de snapshot do criador.
    """
    base_kwargs = {
        "usuario": usuario,
        "prefeitura_id": prefeitura_id,
        "titulo": titulo,
        "termo_busca": termo,
        "modelo_cotacao": modelo,
        "filtros": filtros,
        "status": "aberta",
    }
    try:
        return PncpCotacao.objects.create(
            **base_kwargs,
            criado_por_nome=nome_snap,
            criado_por_email=email_snap,
        )
    except DatabaseError as e:
        msg = str(e).lower()
        if ("criado_por_nome" not in msg) and ("criado_por_email" not in msg):
            raise
        return PncpCotacao.objects.create(**base_kwargs)


def _cotacao_qs_for_user(user):
    return PncpCotacao.objects.filter(usuario_id=user.id)


def _safe_prefeitura_id_for_user(user) -> Optional[int]:
    """
    Evita 500 em create quando user.prefeitura_id aponta para registro inexistente.
    """
    pref_id = getattr(user, "prefeitura_id", None)
    if not pref_id:
        return None
    try:
        pid = int(pref_id)
    except (TypeError, ValueError):
        return None
    return pid if Prefeitura.objects.filter(id=pid).exists() else None


def _sessao_dict(c: PncpCotacao, *, include_owner: bool = False) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "id": c.id,
        "titulo": c.titulo,
        "termo_busca": c.termo_busca,
        "modelo_cotacao": c.modelo_cotacao or "pesquisa_precos_padrao",
        "filtros": c.filtros or {},
        "status": c.status,
        "created_at": _iso_z(c.created_at),
        "updated_at": _iso_z(c.updated_at),
    }
    if include_owner:
        u = c.usuario
        snap_nome = (getattr(c, "criado_por_nome", None) or "").strip()
        snap_email = (getattr(c, "criado_por_email", None) or "").strip()
        full_name = ""
        first = (getattr(u, "first_name", None) or "").strip()
        last = (getattr(u, "last_name", None) or "").strip()
        if first or last:
            full_name = f"{first} {last}".strip()
        if not full_name:
            get_full_name = getattr(u, "get_full_name", None)
            if callable(get_full_name):
                try:
                    full_name = (get_full_name() or "").strip()
                except Exception:
                    full_name = ""
        out["criado_por"] = snap_nome or full_name or getattr(u, "email", "") or str(u.pk)
        out["criado_por_email"] = snap_email or (getattr(u, "email", None) or "").strip()
    return out


def _item_dict(row: PncpCotacaoItem) -> Dict[str, Any]:
    return {
        "id": row.id,
        "numero_pncp": row.numero_pncp or None,
        "ano_compra": row.ano_compra,
        "sequencial_compra": row.sequencial_compra,
        "numero_item": row.numero_item or None,
        "descricao_item": row.descricao_item or None,
        "quantidade": row.quantidade,
        "unidade_medida": row.unidade_medida or None,
        "valor_unitario": row.valor_unitario,
        "valor_total": row.valor_total,
        "orgao": row.orgao or None,
        "municipio": row.municipio or None,
        "uf": row.uf or None,
        "modalidade": row.modalidade or None,
        "source": row.source or {},
        "created_at": _iso_z(row.created_at),
    }


def _item_cotacao_dict(row: PncpCotacaoItemCotacao) -> Dict[str, Any]:
    return {
        "id": row.id,
        "item_id": row.item_id,
        "numero_pncp": row.numero_pncp or None,
        "ano_compra": row.ano_compra,
        "sequencial_compra": row.sequencial_compra,
        "numero_item": row.numero_item or None,
        "descricao_item": row.descricao_item or None,
        "quantidade": row.quantidade,
        "unidade_medida": row.unidade_medida or None,
        "valor_unitario": row.valor_unitario,
        "valor_total": row.valor_total,
        "orgao": row.orgao or None,
        "municipio": row.municipio or None,
        "uf": row.uf or None,
        "modalidade": row.modalidade or None,
        "data_publicacao": row.data_publicacao or None,
        "score_aprovacao": row.score_aprovacao,
        "confiabilidade": row.confiabilidade or None,
        "risco": row.risco or None,
        "status": row.status or None,
        "source": row.source or {},
        "created_at": _iso_z(row.created_at),
    }


def _item_identity_error(it: Dict[str, Any]) -> Optional[str]:
    """Exige âncora mínima para precisão: PNCP, par compra ou descrição não vazia."""
    np = str(it.get("numero_pncp") or it.get("numeroControlePNCP") or "").strip()
    if np:
        return None
    desc = (
        it.get("descricao_item")
        or it.get("descricao")
        or it.get("objeto_resumido")
        or it.get("objetoCompra")
        or ""
    )
    desc_s = str(desc).strip()
    if desc_s:
        return None
    ano = _safe_int_field(it.get("ano_compra"), min_v=1990, max_v=2100)
    seq = _safe_int_field(it.get("sequencial_compra"), min_v=1, max_v=2_147_483_647)
    if ano is not None and seq is not None:
        return None
    return (
        "cada item precisa de numero_pncp, ou (ano_compra + sequencial_compra), "
        "ou descrição/objeto não vazio"
    )


def _item_from_payload(it: Dict[str, Any], cotacao: PncpCotacao) -> PncpCotacaoItem:
    desc = (
        it.get("descricao_item")
        or it.get("descricao")
        or it.get("objeto_resumido")
        or it.get("objetoCompra")
        or ""
    )
    vt = _safe_float(it.get("valor_total")) or _safe_float(it.get("valor_global"))
    np = str(it.get("numero_pncp") or it.get("numeroControlePNCP") or "")[:256]
    return PncpCotacaoItem(
        cotacao=cotacao,
        numero_pncp=np,
        ano_compra=_safe_int_field(it.get("ano_compra"), min_v=1990, max_v=2100),
        sequencial_compra=_safe_int_field(it.get("sequencial_compra"), min_v=1, max_v=2_147_483_647),
        numero_item=str(it.get("numero_item") or it.get("numeroItem") or "")[:64],
        descricao_item=str(desc)[:10000] if desc else "",
        quantidade=_safe_float(it.get("quantidade")),
        unidade_medida=str(it.get("unidade_medida") or it.get("unidadeMedida") or "")[:64],
        valor_unitario=_safe_float(it.get("valor_unitario")) or _safe_float(it.get("valorUnitario")),
        valor_total=vt,
        orgao=str(it.get("orgao") or "")[:512],
        municipio=str(it.get("municipio") or "")[:256],
        uf=_normalize_uf(it.get("uf")),
        modalidade=str(it.get("modalidade") or "")[:256],
        source=_compact_item_source(it),
    )


@api_login_required
@csrf_exempt
@require_http_methods(["GET", "POST", "OPTIONS"])
def pncp_research_sessions_list_create(request):
    if request.method == "OPTIONS":
        return JsonResponse({}, status=204)

    if request.method == "GET":
        try:
            limit = int(request.GET.get("limit") or "100")
        except ValueError:
            limit = 100
        limit = max(1, min(limit, 1000))
        rows = (
            _cotacao_qs_for_user(request.user)
            .select_related("usuario")
            .annotate(total_itens=Count("itens"))
            .order_by("-id")[:limit]
        )
        sessoes: List[Dict[str, Any]] = []
        for r in rows:
            d = _sessao_dict(r, include_owner=True)
            d["total_itens"] = r.total_itens
            sessoes.append(d)
        return JsonResponse({"ok": True, "sessoes": sessoes})

    body, err = _parse_json_body(request)
    if err:
        return err

    titulo = str(body.get("titulo") or "").strip()
    if not titulo:
        return JsonResponse({"detail": "titulo é obrigatório."}, status=422)
    if len(titulo) > 500:
        return JsonResponse({"detail": "titulo excede 500 caracteres."}, status=422)

    modelo = str(body.get("modelo_cotacao") or "pesquisa_precos_padrao").strip()
    if modelo not in ALLOWED_MODELOS:
        return JsonResponse(
            {"detail": "modelo_cotacao inválido.", "allowed": sorted(ALLOWED_MODELOS)},
            status=422,
        )

    termo_raw = body.get("termo_busca")
    termo = str(termo_raw).strip() if termo_raw is not None else ""
    if not termo:
        termo = titulo
    if len(termo) > 2000:
        return JsonResponse({"detail": "termo_busca excede 2000 caracteres."}, status=422)

    filtros = _sanitize_filtros(body.get("filtros"))
    prefeitura_id = _safe_prefeitura_id_for_user(request.user)
    nome_snap, email_snap = _usuario_criacao_snapshot(request.user)

    with transaction.atomic():
        c = _create_cotacao_with_snapshot_fallback(
            usuario=request.user,
            prefeitura_id=prefeitura_id,
            titulo=titulo,
            termo=termo,
            modelo=modelo,
            filtros=filtros,
            nome_snap=nome_snap,
            email_snap=email_snap,
        )

    cotacao_payload = _sessao_dict(c, include_owner=True)
    cotacao_payload["total_itens"] = 0
    return JsonResponse(
        {
            "ok": True,
            "sessao_id": c.id,
            "cotacao_id": c.id,
            **cotacao_payload,
            "cotacao": cotacao_payload,
        },
        status=201,
    )


@api_login_required
@csrf_exempt
@require_http_methods(["GET", "DELETE", "OPTIONS"])
def pncp_research_sessions_detail(request, sessao_id: int):
    if request.method == "OPTIONS":
        return JsonResponse({}, status=204)

    if request.method == "DELETE":
        with transaction.atomic():
            c = _cotacao_qs_for_user(request.user).select_for_update().filter(pk=sessao_id).first()
            if not c:
                return JsonResponse({"ok": False, "error": "Sessão não encontrada.", "sessao_id": sessao_id}, status=404)
            c.delete()
        return JsonResponse({"ok": True, "sessao_id": sessao_id, "deleted": True})

    c = _cotacao_qs_for_user(request.user).select_related("usuario").filter(pk=sessao_id).first()
    if not c:
        return JsonResponse({"ok": False, "error": "Sessão não encontrada.", "sessao_id": sessao_id}, status=404)

    itens_asc = list(c.itens.all().order_by("id"))
    grupos_relatorio, total_linhas_cotacao = agrupar_itens_relatorio_pesquisa_precos(itens_asc)
    formula_id = _resolve_formula_calculo_id(c.filtros or {})
    formula_label = FORMULA_LABELS.get(formula_id, FORMULA_LABELS[DEFAULT_FORMULA_CALCULO])
    anexo = PncpCotacaoAnexo.objects.filter(cotacao_id=c.id).first()
    itens_desc = list(reversed(itens_asc))
    return JsonResponse(
        {
            "ok": True,
            "sessao": {
                **_sessao_dict(c, include_owner=True),
                "total_itens": len(itens_asc),
                "total_grupos_relatorio": len(grupos_relatorio),
                "formula_calculo": formula_label,
                "formula_calculo_id": formula_id,
                "anexo_fornecedor_pdf": bool(anexo and anexo.arquivo_pdf),
                "anexo_fornecedor_nome": (anexo.nome_original if anexo else "") or "",
            },
            "itens": [_item_dict(x) for x in itens_desc],
            "grupos_relatorio": grupos_relatorio,
            "calculo_precos": resumo_calculo_precos(grupos_relatorio, formula_id),
            "total_linhas_cotacao": total_linhas_cotacao,
            "cnpjs_fontes": extrair_cnpjs_dos_itens(itens_asc),
            "stats": {"total_itens": len(itens_asc), "total_grupos": len(grupos_relatorio)},
        }
    )


@api_login_required
@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def pncp_research_sessions_update(request, sessao_id: int):
    if request.method == "OPTIONS":
        return JsonResponse({}, status=204)

    body, err = _parse_json_body(request)
    if err:
        return err

    with transaction.atomic():
        c = _cotacao_qs_for_user(request.user).select_for_update().filter(pk=sessao_id).first()
        if not c:
            return JsonResponse({"ok": False, "error": "Sessão não encontrada.", "sessao_id": sessao_id}, status=404)

        if "titulo" in body and body["titulo"] is not None:
            t = str(body["titulo"]).strip()
            if not t:
                return JsonResponse({"detail": "titulo não pode ser vazio."}, status=422)
            if len(t) > 500:
                return JsonResponse({"detail": "titulo excede 500 caracteres."}, status=422)
            c.titulo = t

        if "status" in body and body["status"] is not None:
            st = str(body["status"]).strip()
            if st not in ALLOWED_STATUS:
                return JsonResponse(
                    {"detail": "status inválido.", "allowed": sorted(ALLOWED_STATUS)},
                    status=422,
                )
            c.status = st

        if "termo_busca" in body and body["termo_busca"] is not None:
            t = str(body["termo_busca"]).strip()
            if t:
                if len(t) > 2000:
                    return JsonResponse({"detail": "termo_busca excede 2000 caracteres."}, status=422)
                c.termo_busca = t

        if "modelo_cotacao" in body and body["modelo_cotacao"] is not None:
            m = str(body["modelo_cotacao"]).strip()
            if m and m not in ALLOWED_MODELOS:
                return JsonResponse(
                    {"detail": "modelo_cotacao inválido.", "allowed": sorted(ALLOWED_MODELOS)},
                    status=422,
                )
            if m:
                c.modelo_cotacao = m

        incoming_formula = body.get("formula_calculo_id")
        if incoming_formula is None and body.get("formula_calculo") is not None:
            incoming_formula = body.get("formula_calculo")
        if incoming_formula is not None:
            fid = str(incoming_formula).strip()
            fid = FORMULA_LABELS_TO_ID.get(fid.lower(), fid)
            if fid not in ALLOWED_FORMULA_CALCULO:
                return JsonResponse(
                    {"detail": "formula_calculo_id inválida.", "allowed": sorted(ALLOWED_FORMULA_CALCULO)},
                    status=422,
                )
            filtros = dict(c.filtros or {})
            filtros["formula_calculo"] = fid
            c.filtros = _sanitize_filtros(filtros)

        c.save()

    formula_id = _resolve_formula_calculo_id(c.filtros or {})
    return JsonResponse(
        {
            "ok": True,
            "sessao_id": c.id,
            "titulo": c.titulo,
            "status": c.status,
            "termo_busca": c.termo_busca,
            "modelo_cotacao": c.modelo_cotacao,
            "formula_calculo_id": formula_id,
            "formula_calculo": FORMULA_LABELS.get(formula_id, FORMULA_LABELS[DEFAULT_FORMULA_CALCULO]),
            "updated_at": _iso_z(c.updated_at),
        }
    )


@api_login_required
@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def pncp_research_sessions_add_items(request, sessao_id: int):
    if request.method == "OPTIONS":
        return JsonResponse({}, status=204)

    body, err = _parse_json_body(request)
    if err:
        return err

    raw_itens = body.get("itens")
    if not isinstance(raw_itens, list):
        return JsonResponse({"detail": "Campo itens deve ser uma lista."}, status=422)

    if len(raw_itens) > MAX_ITEMS_PER_REQUEST:
        return JsonResponse(
            {
                "detail": f"No máximo {MAX_ITEMS_PER_REQUEST} itens por requisição.",
                "received": len(raw_itens),
            },
            status=422,
        )

    if not raw_itens:
        c0 = _cotacao_qs_for_user(request.user).filter(pk=sessao_id).first()
        if not c0:
            return JsonResponse({"ok": False, "error": "Sessão não encontrada.", "sessao_id": sessao_id}, status=404)
        return JsonResponse({"ok": True, "sessao_id": c0.id, "itens_inseridos": 0})

    for idx, it in enumerate(raw_itens):
        if not isinstance(it, dict):
            return JsonResponse(
                {"detail": "Cada item deve ser um objeto JSON.", "index": idx},
                status=422,
            )
        id_err = _item_identity_error(it)
        if id_err:
            return JsonResponse({"detail": id_err, "index": idx}, status=422)

    inserted = 0
    with transaction.atomic():
        c = _cotacao_qs_for_user(request.user).select_for_update().filter(pk=sessao_id).first()
        if not c:
            return JsonResponse({"ok": False, "error": "Sessão não encontrada.", "sessao_id": sessao_id}, status=404)
        if c.status in CLOSED_FOR_ITEMS:
            return JsonResponse(
                {"detail": "Cotação encerrada; não é permitido adicionar itens."},
                status=409,
            )
        built = [_item_from_payload(it, c) for it in raw_itens]
        for i in range(0, len(built), BULK_CREATE_BATCH):
            chunk = built[i : i + BULK_CREATE_BATCH]
            PncpCotacaoItem.objects.bulk_create(chunk, batch_size=BULK_CREATE_BATCH)
        inserted = len(built)
        c.save(update_fields=["updated_at"])

    return JsonResponse({"ok": True, "sessao_id": c.id, "itens_inseridos": inserted})


@api_login_required
@csrf_exempt
@require_http_methods(["GET", "POST", "OPTIONS"])
def pncp_research_sessions_item_cotacoes(request, sessao_id: int, item_id: int):
    if request.method == "OPTIONS":
        return JsonResponse({}, status=204)

    c = _cotacao_qs_for_user(request.user).filter(pk=sessao_id).first()
    if not c:
        return JsonResponse({"ok": False, "error": "Sessão não encontrada.", "sessao_id": sessao_id}, status=404)

    item = c.itens.filter(pk=item_id).first()
    if not item:
        return JsonResponse({"ok": False, "error": "Item não encontrado na sessão.", "item_id": item_id}, status=404)

    if request.method == "GET":
        rows = list(item.cotacoes.all().order_by("-id"))
        return JsonResponse(
            {
                "ok": True,
                "sessao_id": c.id,
                "item_id": item.id,
                "cotacoes": [_item_cotacao_dict(x) for x in rows],
                "stats": {"total_cotacoes": len(rows)},
            }
        )

    body, err = _parse_json_body(request)
    if err:
        return err
    raw_cotacoes = body.get("cotacoes")
    if not isinstance(raw_cotacoes, list):
        return JsonResponse({"detail": "Campo cotacoes deve ser uma lista."}, status=422)
    if len(raw_cotacoes) > MAX_ITEMS_PER_REQUEST:
        return JsonResponse(
            {"detail": f"No máximo {MAX_ITEMS_PER_REQUEST} cotações por requisição.", "received": len(raw_cotacoes)},
            status=422,
        )
    if c.status in CLOSED_FOR_ITEMS:
        return JsonResponse({"detail": "Cotação encerrada; não é permitido adicionar cotações."}, status=409)

    built: List[PncpCotacaoItemCotacao] = []
    for row in raw_cotacoes:
        if not isinstance(row, dict):
            continue
        built.append(
            PncpCotacaoItemCotacao(
                cotacao=c,
                item=item,
                numero_pncp=str(row.get("numero_pncp") or row.get("numeroControlePNCP") or "")[:256],
                ano_compra=_safe_int_field(row.get("ano_compra"), min_v=1990, max_v=2100),
                sequencial_compra=_safe_int_field(row.get("sequencial_compra"), min_v=1, max_v=2_147_483_647),
                numero_item=str(row.get("numero_item") or row.get("numeroItem") or "")[:64],
                descricao_item=str(row.get("descricao_item") or row.get("descricao") or row.get("objeto_resumido") or "")[:10000],
                quantidade=_safe_float(row.get("quantidade")),
                unidade_medida=str(row.get("unidade_medida") or row.get("unidadeMedida") or "")[:64],
                valor_unitario=_safe_float(row.get("valor_unitario") or row.get("valorUnitario")),
                valor_total=_safe_float(row.get("valor_total") or row.get("valor_global") or row.get("valorTotal")),
                orgao=str(row.get("orgao") or "")[:512],
                municipio=str(row.get("municipio") or "")[:256],
                uf=_normalize_uf(row.get("uf")),
                modalidade=str(row.get("modalidade") or "")[:256],
                data_publicacao=str(row.get("data_publicacao") or row.get("dataPublicacao") or "")[:64],
                score_aprovacao=int(max(0, min(100, _safe_float(row.get("score_aprovacao"))))),
                confiabilidade=str(row.get("confiabilidade") or "")[:32],
                risco=str(row.get("risco") or "")[:32],
                status=str(row.get("status") or "")[:32],
                source=_compact_item_source(row),
            )
        )

    if not built:
        return JsonResponse({"detail": "Nenhuma cotação válida para inserir."}, status=422)

    with transaction.atomic():
        for i in range(0, len(built), BULK_CREATE_BATCH):
            chunk = built[i : i + BULK_CREATE_BATCH]
            PncpCotacaoItemCotacao.objects.bulk_create(chunk, batch_size=BULK_CREATE_BATCH)
        c.save(update_fields=["updated_at"])

    return JsonResponse(
        {
            "ok": True,
            "sessao_id": c.id,
            "item_id": item.id,
            "cotacoes_inseridas": len(built),
        }
    )


@api_login_required
@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def pncp_research_sessions_upload_supplier_pdf(request, sessao_id: int):
    if request.method == "OPTIONS":
        return JsonResponse({}, status=204)

    upload = request.FILES.get("arquivo")
    if not upload:
        return JsonResponse({"detail": "Envie o arquivo em 'arquivo'."}, status=422)

    name = str(getattr(upload, "name", "")).strip()
    ctype = str(getattr(upload, "content_type", "")).lower().strip()
    if not name.lower().endswith(".pdf"):
        return JsonResponse({"detail": "Apenas arquivo PDF é aceito."}, status=422)
    if ctype and ctype not in {"application/pdf", "application/x-pdf"}:
        return JsonResponse({"detail": "Tipo de arquivo inválido. Envie PDF."}, status=422)
    size = int(getattr(upload, "size", 0) or 0)
    if size <= 0:
        return JsonResponse({"detail": "Arquivo vazio."}, status=422)
    if size > MAX_ANEXO_PDF_BYTES:
        return JsonResponse(
            {"detail": f"Arquivo excede limite de {MAX_ANEXO_PDF_BYTES} bytes."},
            status=422,
        )

    with transaction.atomic():
        c = _cotacao_qs_for_user(request.user).select_for_update().filter(pk=sessao_id).first()
        if not c:
            return JsonResponse({"ok": False, "error": "Sessão não encontrada.", "sessao_id": sessao_id}, status=404)

        anexo = PncpCotacaoAnexo.objects.filter(cotacao_id=c.id).first()
        if anexo:
            if anexo.arquivo_pdf:
                anexo.arquivo_pdf.delete(save=False)
        else:
            anexo = PncpCotacaoAnexo(cotacao=c)
        std_name = _nome_padrao_anexo_fornecedor(c.id)
        file_bytes = upload.read()
        anexo.arquivo_pdf.save(std_name, ContentFile(file_bytes), save=False)
        anexo.nome_original = std_name[:255]
        anexo.tamanho_bytes = size
        anexo.content_type = ctype or "application/pdf"
        anexo.save()
        c.save(update_fields=["updated_at"])

    return JsonResponse(
        {
            "ok": True,
            "sessao_id": c.id,
            "anexo_fornecedor_pdf": True,
            "arquivo": {
                "nome": anexo.nome_original,
                "tamanho_bytes": anexo.tamanho_bytes,
                "content_type": anexo.content_type,
            },
        }
    )


@api_login_required
@require_http_methods(["GET", "OPTIONS"])
def pncp_research_sessions_download_supplier_pdf(request, sessao_id: int):
    if request.method == "OPTIONS":
        return JsonResponse({}, status=204)

    c = _cotacao_qs_for_user(request.user).filter(pk=sessao_id).first()
    if not c:
        return JsonResponse({"ok": False, "error": "Sessão não encontrada.", "sessao_id": sessao_id}, status=404)

    anexo = PncpCotacaoAnexo.objects.filter(cotacao_id=c.id).first()
    if not anexo or not anexo.arquivo_pdf:
        return JsonResponse({"ok": False, "error": "Anexo PDF do fornecedor não encontrado."}, status=404)

    anexo.arquivo_pdf.open("rb")
    filename = (anexo.nome_original or "").strip() or _nome_padrao_anexo_fornecedor(c.id)
    return FileResponse(
        anexo.arquivo_pdf,
        as_attachment=True,
        filename=filename,
        content_type=(anexo.content_type or "application/pdf"),
    )


@api_login_required
@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def pncp_research_sessions_import_items(request, sessao_id: int):
    if request.method == "OPTIONS":
        return JsonResponse({}, status=204)

    upload = request.FILES.get("arquivo")
    if not upload:
        return JsonResponse({"detail": "Envie o arquivo em 'arquivo'."}, status=422)

    column_map = _parse_column_map_raw(request.POST.get("column_map", ""))
    rows, read_err = _read_rows_from_upload(upload)
    if read_err:
        return JsonResponse({"detail": read_err}, status=422)
    if not rows:
        return JsonResponse({"detail": "Arquivo sem linhas de dados."}, status=422)

    items_payload, parse_errors = _build_items_from_import_rows(rows, column_map)
    if not items_payload:
        return JsonResponse(
            {"detail": "Nenhuma linha válida encontrada para importar.", "errors": parse_errors[:20]},
            status=422,
        )

    inserted = 0
    with transaction.atomic():
        c = _cotacao_qs_for_user(request.user).select_for_update().filter(pk=sessao_id).first()
        if not c:
            return JsonResponse({"ok": False, "error": "Sessão não encontrada.", "sessao_id": sessao_id}, status=404)
        if c.status in CLOSED_FOR_ITEMS:
            return JsonResponse(
                {"detail": "Cotação encerrada; não é permitido importar itens."},
                status=409,
            )

        built = [_item_from_payload(it, c) for it in items_payload]
        for i in range(0, len(built), BULK_CREATE_BATCH):
            chunk = built[i : i + BULK_CREATE_BATCH]
            PncpCotacaoItem.objects.bulk_create(chunk, batch_size=BULK_CREATE_BATCH)
        inserted = len(built)
        c.save(update_fields=["updated_at"])

    return JsonResponse(
        {
            "ok": True,
            "sessao_id": c.id,
            "itens_inseridos": inserted,
            "linhas_arquivo": len(rows),
            "linhas_invalidas": len(parse_errors),
            "errors": parse_errors[:20],
            "required_column_ids": list(IMPORT_REQUIRED_COLUMN_IDS),
        }
    )


@api_login_required
@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def pncp_research_sessions_delete_items(request, sessao_id: int):
    if request.method == "OPTIONS":
        return JsonResponse({}, status=204)

    body, err = _parse_json_body(request)
    if err:
        return err

    raw_ids = body.get("item_ids")
    if not isinstance(raw_ids, list) or not raw_ids:
        return JsonResponse({"detail": "Campo item_ids deve ser uma lista não vazia."}, status=422)

    ids: List[int] = []
    for v in raw_ids[:MAX_ITEMS_PER_REQUEST]:
        try:
            i = int(v)
        except (TypeError, ValueError):
            continue
        if i > 0:
            ids.append(i)
    if not ids:
        return JsonResponse({"detail": "Nenhum item_id válido informado."}, status=422)

    with transaction.atomic():
        c = _cotacao_qs_for_user(request.user).select_for_update().filter(pk=sessao_id).first()
        if not c:
            return JsonResponse({"ok": False, "error": "Sessão não encontrada.", "sessao_id": sessao_id}, status=404)
        if c.status in CLOSED_FOR_ITEMS:
            return JsonResponse(
                {"detail": "Cotação encerrada; não é permitido excluir itens."},
                status=409,
            )

        qs = c.itens.filter(id__in=ids)
        deleted_count, _ = qs.delete()
        c.save(update_fields=["updated_at"])

    return JsonResponse(
        {"ok": True, "sessao_id": c.id, "itens_excluidos": int(deleted_count), "item_ids": ids}
    )
