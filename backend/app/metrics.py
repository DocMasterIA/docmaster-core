"""
Métricas Prometheus de negócio do DocMaster (exportadas em GET /metrics).

Labels com cardinalidade controlada: pacotes de slots conhecidos; tenant truncado em 16 chars.
Logins usam label `prefeitura` com nome do município + UF (até 56 chars).
"""
from __future__ import annotations

import time
from functools import wraps

import json

from prometheus_client import Counter, Gauge, Histogram

# Pacotes de geração (mesmo conjunto do route_map em api._resolve_slot_package_key).
KNOWN_SLOT_PACKAGES = frozenset(
    {
        # Dispensa normal (formulário completo)
        "dispensa_75_i_manutencao_veiculos",
        "dispensa_75_i_obras_engenharia",
        "dispensa_75_ii_compras",
        "dispensa_75_ii_servicos",
        "dispensa_75_ii_compras_servicos_inclusos",
        # Dispensa rápida (fluxo simplificado)
        "dispensa_rapida_75_i_manutencao_veiculos",
        "dispensa_rapida_75_i_obras_engenharia",
        "dispensa_rapida_75_ii_compras",
        "dispensa_rapida_75_ii_servicos",
        "dispensa_rapida_75_ii_compras_servicos_inclusos",
        "inexigibilidade_74_i_manutencao_veiculos",
        "inexigibilidade_74_i_fornecedor_exclusivo",
    }
)

# Com PROMETHEUS_MULTIPROC_DIR (Gunicorn), prometheus_client usa mmap automaticamente.
docmaster_auth_login_total = Counter(
    "docmaster_auth_login_total",
    "Tentativas de login na API DocMaster",
    ["result", "prefeitura"],
)

docmaster_auth_logout_total = Counter(
    "docmaster_auth_logout_total",
    "Logouts na API DocMaster",
    ["prefeitura"],
)

docmaster_document_operations_total = Counter(
    "docmaster_document_operations_total",
    "Operações de geração / pipeline de documentos",
    ["operation", "result", "package", "tipo_geracao", "output", "prefeitura"],
)

docmaster_document_operation_duration_seconds = Histogram(
    "docmaster_document_operation_duration_seconds",
    "Duração das operações de documento (segundos)",
    ["operation", "result", "package", "tipo_geracao", "prefeitura"],
    buckets=(0.5, 1, 2.5, 5, 10, 30, 60, 120, 300, 600, 900, 1200),
)

docmaster_document_instances_created_total = Counter(
    "docmaster_document_instances_created_total",
    "Documentos persistidos em Meus Documentos",
    ["doc_type", "package", "prefeitura"],
)

docmaster_platform_events_total = Counter(
    "docmaster_platform_events_total",
    "Eventos de uso por módulo (LLM, PNCP, análise, etc.)",
    ["module", "action", "result", "prefeitura"],
)

docmaster_llm_tokens_total = Counter(
    "docmaster_llm_tokens_total",
    "Tokens LLM na geração de documentos (entrada e saída)",
    ["prefeitura", "direction", "fluxo", "tipo_geracao", "package"],
)

# Sempre visível em /metrics após o worker subir (confirma deploy do módulo de métricas).
docmaster_metrics_active = Gauge(
    "docmaster_metrics_active",
    "1 quando as métricas docmaster_* estão registradas neste worker",
    multiprocess_mode="livesum",
)

KNOWN_LLM_ACTIONS = frozenset(
    {"health", "planner", "section", "analysis", "generate", "test-audit"}
)

KNOWN_PNCp_RESEARCH_ACTIONS = frozenset(
    {
        "health",
        "market-search",
        "market-search-stream",
        "local-index-stats",
        "local-index-search",
        "local-index-search-items",
        "research-sessions",
        "research-cotacoes",
        "other",
    }
)


def normalize_package_key(key: str | None) -> str:
    k = (key or "").strip().lower()
    if not k:
        return "unknown"
    if k in KNOWN_SLOT_PACKAGES:
        return k
    if k in ("etp", "tr_dfd_generico"):
        return k
    if len(k) > 64:
        return "other"
    return "other"


def package_to_tipo_geracao(package: str | None, *, fluxo: str = "") -> str:
    """
    Agrupa pacotes de slots / rotas em famílias para dashboards (Grafana).
    Valores: dispensa_normal, dispensa_rapida, inexigibilidade, etp, other.
    """
    p = normalize_package_key(package)
    if p.startswith("dispensa_rapida_"):
        return "dispensa_rapida"
    if p.startswith("dispensa_75_") or p.startswith("dispensa_"):
        return "dispensa_normal"
    if p.startswith("inexigibilidade_"):
        return "inexigibilidade"
    if p == "etp" or p.startswith("etp_"):
        return "etp"
    if (fluxo or "").strip().lower() == "gerar_llm":
        return "etp"
    return "other"


def tenant_label(user) -> str:
    """Identificador curto (16 chars) para métricas de documento/IA — não usar em logins."""
    if user is None or not getattr(user, "is_authenticated", False):
        return "anonymous"
    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return "staff"
    pref = getattr(user, "prefeitura", None)
    if pref is None:
        return "sem_prefeitura"
    nome = (getattr(pref, "nome_municipio", None) or "").strip()
    uf = (getattr(pref, "estado", None) or "").strip().upper()
    if nome and len(uf) == 2 and uf.isalpha():
        return f"{nome} ({uf})"[:16]
    if nome:
        return nome[:16]
    url = (getattr(pref, "url", None) or "").strip().lower()[:16]
    return url or "sem_prefeitura"


def tenant_label_from_request(request) -> str:
    return tenant_label(getattr(request, "user", None))


def prefeitura_label_from_instance(pref) -> str:
    """Nome legível a partir do modelo Prefeitura (município + UF quando possível)."""
    if pref is None:
        return "Sem prefeitura"
    nome = (getattr(pref, "nome_municipio", None) or "").strip()
    uf = (getattr(pref, "estado", None) or "").strip().upper()
    if nome and uf:
        return f"{nome} ({uf})"[:56]
    if nome:
        return nome[:56]
    url = (getattr(pref, "url", None) or "").strip()
    return url[:56] if url else "Prefeitura sem nome"


def prefeitura_label(user) -> str:
    """Nome legível da prefeitura para dashboards de login (uma série por município)."""
    if user is None or not getattr(user, "is_authenticated", False):
        return "Não identificado"
    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return "Equipe DocMaster (staff)"
    return prefeitura_label_from_instance(getattr(user, "prefeitura", None))


def prefeitura_label_from_request(request) -> str:
    return prefeitura_label(getattr(request, "user", None))


def result_from_response(response) -> str:
    if response is None:
        return "error"
    status_code = getattr(response, "status_code", 200)
    if status_code >= 400:
        return "error"
    from django.http import JsonResponse

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


def record_auth_login(*, result: str, user=None, prefeitura: str | None = None) -> None:
    pref = prefeitura if prefeitura is not None else prefeitura_label(user)
    docmaster_auth_login_total.labels(result=result, prefeitura=pref).inc()


def record_auth_logout(*, user=None, prefeitura: str | None = None) -> None:
    pref = prefeitura if prefeitura is not None else prefeitura_label(user)
    docmaster_auth_logout_total.labels(prefeitura=pref).inc()


def record_llm_token_usage(
    *,
    fluxo: str,
    prefeitura: str,
    package: str = "unknown",
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
) -> None:
    """Registra tokens agregados de uma geração (valores vindos do rag_service ou llm_api)."""
    pref = (prefeitura or "Não identificado")[:56]
    fl = (fluxo or "unknown")[:24]
    pkg = normalize_package_key(package)
    tipo = package_to_tipo_geracao(pkg, fluxo=fl)
    if prompt_tokens > 0:
        docmaster_llm_tokens_total.labels(
            prefeitura=pref,
            direction="entrada",
            fluxo=fl,
            tipo_geracao=tipo,
            package=pkg,
        ).inc(prompt_tokens)
    if completion_tokens > 0:
        docmaster_llm_tokens_total.labels(
            prefeitura=pref,
            direction="saida",
            fluxo=fl,
            tipo_geracao=tipo,
            package=pkg,
        ).inc(completion_tokens)


def record_document_operation(
    *,
    operation: str,
    result: str,
    package: str,
    output: str,
    prefeitura: str,
    duration_seconds: float,
) -> None:
    op = (operation or "unknown")[:32]
    pkg = normalize_package_key(package)
    tipo = package_to_tipo_geracao(pkg, fluxo=op)
    out = (output or "n/a")[:16]
    res = "success" if result == "success" else "error"
    pref = (prefeitura or "Não identificado")[:56]
    docmaster_document_operations_total.labels(
        operation=op,
        result=res,
        package=pkg,
        tipo_geracao=tipo,
        output=out,
        prefeitura=pref,
    ).inc()
    docmaster_document_operation_duration_seconds.labels(
        operation=op,
        result=res,
        package=pkg,
        tipo_geracao=tipo,
        prefeitura=pref,
    ).observe(max(0.0, duration_seconds))


def normalize_llm_action(path: str | None) -> str:
    seg = (path or "").strip("/").split("/")[0].lower()
    return seg if seg in KNOWN_LLM_ACTIONS else "other"


def normalize_pncp_research_action(path: str | None) -> str:
    parts = [p for p in (path or "").strip("/").split("/") if p]
    if not parts:
        return "health"
    head = parts[0].lower()
    if head == "market-search":
        if len(parts) > 1 and parts[1].lower() == "stream":
            return "market-search-stream"
        if len(parts) > 2 and parts[2].lower() == "stream":
            return "market-search-stream"
        return "market-search"
    if head == "local-index" and len(parts) > 1:
        sub = parts[1].lower()
        if sub in ("stats", "search", "search-items", "backfill"):
            return f"local-index-{sub}"
        return "local-index-search"
    if head == "research" and len(parts) > 1:
        return f"research-{parts[1].lower()[:24]}"
    if head in KNOWN_PNCp_RESEARCH_ACTIONS:
        return head
    return "other"


def record_platform_event(
    *,
    module: str,
    action: str,
    result: str,
    prefeitura: str,
) -> None:
    mod = (module or "unknown")[:24]
    act = (action or "unknown")[:32]
    res = "success" if result == "success" else "error"
    pref = (prefeitura or "Não identificado")[:56]
    docmaster_platform_events_total.labels(
        module=mod,
        action=act,
        result=res,
        prefeitura=pref,
    ).inc()


def record_document_instance_created(
    *,
    doc_type: str,
    package: str,
    prefeitura: str,
) -> None:
    docmaster_document_instances_created_total.labels(
        doc_type=(doc_type or "unknown")[:24],
        package=normalize_package_key(package),
        prefeitura=(prefeitura or "Não identificado")[:56],
    ).inc()


def track_platform(module: str, action: str | None = None):
    """Decorator para módulos além do pipeline de documentos (PNCP, análise, etc.)."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            act = action or (getattr(request, "method", "GET") or "GET").lower()[:16]
            result = "success"
            try:
                response = view_func(request, *args, **kwargs)
                result = result_from_response(response)
                return response
            except Exception:
                result = "error"
                raise
            finally:
                record_platform_event(
                    module=module,
                    action=act,
                    result=result,
                    prefeitura=prefeitura_label_from_request(request),
                )

        return wrapped

    return decorator


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
                    prefeitura=prefeitura_label_from_request(request),
                    duration_seconds=time.perf_counter() - start,
                )

        return wrapped

    return decorator


_auth_signals_connected = False


def mark_metrics_worker_ready() -> None:
    """Chamado no AppConfig.ready de cada worker (após post_fork configurar mmap)."""
    try:
        docmaster_metrics_active.set(1)
    except Exception:
        pass


def connect_auth_signals() -> None:
    """Login/logout via Django auth (funciona mesmo se api.py ainda não foi importado no worker)."""
    global _auth_signals_connected
    if _auth_signals_connected:
        return
    from django.contrib.auth.signals import user_logged_out

    def _on_logout(sender, request, user, **kwargs):
        record_auth_logout(user=user)

    # Login API: record_auth_login em api_auth_login (evita duplicar com sinal).
    user_logged_out.connect(_on_logout, dispatch_uid="docmaster_metrics_logout")
    _auth_signals_connected = True
