"""Métricas Prometheus do llm_api (tokens Ollama)."""
from __future__ import annotations

from prometheus_client import Counter

from app.token_usage import extract_token_usage

docmaster_llm_tokens_total = Counter(
    "docmaster_llm_tokens_total",
    "Tokens consumidos nas chamadas ao modelo (Ollama)",
    ["call_type", "direction", "prefeitura", "model"],
)

docmaster_llm_requests_total = Counter(
    "docmaster_llm_requests_total",
    "Chamadas ao modelo de linguagem",
    ["call_type", "result", "prefeitura"],
)


def normalize_prefeitura(value: str | None) -> str:
    pref = (value or "").strip()
    return pref[:56] if pref else "Não identificado"


def record_llm_tokens(
    *,
    call_type: str,
    prefeitura: str | None,
    body: object,
    result: str = "success",
) -> tuple[int, int]:
    """Incrementa contadores a partir da resposta; retorna (entrada, saída)."""
    pref = normalize_prefeitura(prefeitura)
    ct = (call_type or "unknown")[:24]
    prompt_t, completion_t, model = extract_token_usage(body)
    model_label = model or "unknown"

    docmaster_llm_requests_total.labels(call_type=ct, result=result, prefeitura=pref).inc()
    if prompt_t:
        docmaster_llm_tokens_total.labels(
            call_type=ct,
            direction="entrada",
            prefeitura=pref,
            model=model_label,
        ).inc(prompt_t)
    if completion_t:
        docmaster_llm_tokens_total.labels(
            call_type=ct,
            direction="saida",
            prefeitura=pref,
            model=model_label,
        ).inc(completion_t)
    return prompt_t, completion_t
