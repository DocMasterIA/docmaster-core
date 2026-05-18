"""
Métricas Prometheus de negócio do DocMaster (exportadas em GET /metrics).

Labels com cardinalidade controlada: pacotes de slots conhecidos, tenant por UF/staff.
"""
from __future__ import annotations

import time
from functools import wraps

import json

from django.http import JsonResponse
from prometheus_client import Counter, Histogram

# Pacotes de geração (mesmo conjunto do route_map em api._resolve_slot_package_key).
KNOWN_SLOT_PACKAGES = frozenset(
    {
        "dispensa_75_i_manutencao_veiculos",
        "dispensa_75_i_obras_engenharia",
        "dispensa_75_ii_compras",
        "dispensa_75_ii_servicos",
        "dispensa_75_ii_compras_servicos_inclusos",
        "inexigibilidade_74_i_manutencao_veiculos",
        "inexigibilidade_74_i_fornecedor_exclusivo",
    }
)

# Gunicorn + PROMETHEUS_MULTIPROC_DIR: sem multiprocess_mode as métricas não
# entram no /metrics (django_prometheus usa só MultiProcessCollector).
docmaster_auth_login_total = Counter(
    "docmaster_auth_login_total",
    "Tentativas de login na API DocMaster",
    ["result", "tenant"],
    multiprocess_mode="livesum",
)

docmaster_auth_logout_total = Counter(
    "docmaster_auth_logout_total",
    "Logouts na API DocMaster",
    ["tenant"],
    multiprocess_mode="livesum",
)

docmaster_document_operations_total = Counter(
    "docmaster_document_operations_total",
    "Operações de geração / pipeline de documentos",
    ["operation", "result", "package", "output", "tenant"],
    multiprocess_mode="livesum",
)

docmaster_document_operation_duration_seconds = Histogram(
    "docmaster_document_operation_duration_seconds",
    "Duração das operações de documento (segundos)",
    ["operation", "result", "package", "tenant"],
    buckets=(0.5, 1, 2.5, 5, 10, 30, 60, 120, 300, 600, 900, 1200),
    multiprocess_mode="liveall",
)

docmaster_document_instances_created_total = Counter(
    "docmaster_document_instances_created_total",
    "Documentos persistidos em Meus Documentos",
    ["doc_type", "package", "tenant"],
    multiprocess_mode="livesum",
)


def normalize_package_key(key: str | None) -> str:
    k = (key or "").strip().lower()
    if not k:
        return "unknown"
    if k in KNOWN_SLOT_PACKAGES:
        return k
    if len(k) > 64:
        return "other"
    return "other"


def tenant_label(user) -> str:
    if user is None or not getattr(user, "is_authenticated", False):
        return "anonymous"
    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return "staff"
    pref = getattr(user, "prefeitura", None)
    estado = (getattr(pref, "estado", None) or "").strip().upper()[:8]
    return estado or "sem_prefeitura"


def tenant_label_from_request(request) -> str:
    return tenant_label(getattr(request, "user", None))


def result_from_response(response) -> str:
    if response is None:
        return "error"
    status_code = getattr(response, "status_code", 200)
    if status_code >= 400:
        return "error"
    if isinstance(response, JsonResponse):
        try:
            data = json.loads(response.content.decode(response.charset or "utf-8"))
        except Exception:
            data = {}
        if isinstance(data, dict) and data.get("ok") is False:
            return "error"
    return "success"


def set_request_metrics(request, *, package: str = "", output: str = "") -> None:
    request.docmaster_metrics = {
        "package": normalize_package_key(package),
        "output": (output or "n/a").strip().lower()[:16],
    }


def record_auth_login(*, result: str, tenant: str) -> None:
    docmaster_auth_login_total.labels(result=result, tenant=tenant).inc()


def record_auth_logout(*, tenant: str) -> None:
    docmaster_auth_logout_total.labels(tenant=tenant).inc()


def record_document_operation(
    *,
    operation: str,
    result: str,
    package: str,
    output: str,
    tenant: str,
    duration_seconds: float,
) -> None:
    op = (operation or "unknown")[:32]
    pkg = normalize_package_key(package)
    out = (output or "n/a")[:16]
    res = "success" if result == "success" else "error"
    ten = (tenant or "anonymous")[:16]
    docmaster_document_operations_total.labels(
        operation=op,
        result=res,
        package=pkg,
        output=out,
        tenant=ten,
    ).inc()
    docmaster_document_operation_duration_seconds.labels(
        operation=op,
        result=res,
        package=pkg,
        tenant=ten,
    ).observe(max(0.0, duration_seconds))


def record_document_instance_created(
    *,
    doc_type: str,
    package: str,
    tenant: str,
) -> None:
    docmaster_document_instances_created_total.labels(
        doc_type=(doc_type or "unknown")[:24],
        package=normalize_package_key(package),
        tenant=(tenant or "anonymous")[:16],
    ).inc()


def track_docmaster_view(operation: str):
    """Decorator: contabiliza duração/resultado; use set_request_metrics no handler."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if getattr(request, "_docmaster_skip_metrics", False):
                return view_func(request, *args, **kwargs)
            start = time.perf_counter()
            result = "success"
            try:
                response = view_func(request, *args, **kwargs)
                result = result_from_response(response)
                return response
            except Exception:
                result = "error"
                raise
            finally:
                meta = getattr(request, "docmaster_metrics", None) or {}
                record_document_operation(
                    operation=operation,
                    result=result,
                    package=meta.get("package", "unknown"),
                    output=meta.get("output", "n/a"),
                    tenant=tenant_label_from_request(request),
                    duration_seconds=time.perf_counter() - start,
                )

        return wrapped

    return decorator
