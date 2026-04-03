from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional

import httpx

from .config import (
    PNCP_BASE_URL,
    PNCP_PNCP_API_BASE_URL,
    PNCP_TIMEOUT,
    PNCP_MAX_RETRIES,
    PNCP_RETRY_BACKOFF_SECONDS,
    PNCP_MIN_REQUEST_INTERVAL_SECONDS,
    PNCP_THROTTLE_MODE,
    PNCP_BUCKET_CAPACITY,
    PNCP_BUCKET_REFILL_PER_SEC,
    PNCP_RATE_LIMIT_EXTRA_ATTEMPTS,
    PNCP_RATE_LIMIT_BACKOFF_CAP_SECONDS,
)


class PNCPClientError(Exception):
    pass


# 429/503: limite ou indisponibilidade PNCP. 502/504: gateway/proxy (gera HTML; costuma ser transitório).
_PNCP_RETRY_STATUS = frozenset({429, 502, 503, 504})


def _http_error_snippet(resp: httpx.Response, max_len: int = 240) -> str:
    """Extrai trecho legível; evita vazar HTML de Bad Gateway no detalhe para o usuário."""
    ctype = (resp.headers.get("content-type") or "").lower()
    text = (resp.text or "").strip()
    head = (text[:400] or "").lower()
    if "html" in ctype or text.startswith("<") or "<html" in head or "<body" in head:
        return (
            "serviço do PNCP ou gateway retornou página de erro (indisponível ou sobrecarga). "
            "Tente novamente em alguns minutos."
        )
    snippet = " ".join(text.split())
    if len(snippet) > max_len:
        snippet = snippet[: max_len - 1].rstrip() + "…"
    return snippet or "sem detalhe no corpo da resposta"


_pace_lock = asyncio.Lock()
_last_request_monotonic: float = 0.0

_bucket_lock = asyncio.Lock()
_bucket_tokens: float = 0.0
_bucket_last: Optional[float] = None


async def _throttle_interval() -> None:
    global _last_request_monotonic
    interval = max(0.0, float(PNCP_MIN_REQUEST_INTERVAL_SECONDS or 0))
    if interval <= 0:
        return
    async with _pace_lock:
        now = time.monotonic()
        delta = now - _last_request_monotonic
        if delta < interval:
            await asyncio.sleep(interval - delta)
        _last_request_monotonic = time.monotonic()


async def _throttle_bucket() -> None:
    """Token bucket: permite vários GETs em paralelo com teto médio (menos lento que interval global)."""
    global _bucket_tokens, _bucket_last
    cap = max(1.0, float(PNCP_BUCKET_CAPACITY))
    rate = max(0.05, float(PNCP_BUCKET_REFILL_PER_SEC))
    while True:
        wait = 0.0
        async with _bucket_lock:
            now = time.monotonic()
            if _bucket_last is None:
                _bucket_last = now
                _bucket_tokens = cap
            else:
                _bucket_tokens = min(cap, _bucket_tokens + (now - _bucket_last) * rate)
                _bucket_last = now
            if _bucket_tokens >= 1.0:
                _bucket_tokens -= 1.0
                return
            need = 1.0 - _bucket_tokens
            wait = need / rate
        await asyncio.sleep(wait)


async def _throttle_pace() -> None:
    """Controle de taxa configurável (ver PNCP_THROTTLE_MODE)."""
    mode = (PNCP_THROTTLE_MODE or "bucket").strip().lower()
    if mode in ("off", "none", "0", "false"):
        return
    if mode == "interval":
        await _throttle_interval()
        return
    # default: bucket
    await _throttle_bucket()


def _pncp_client_limits() -> httpx.Limits:
    return httpx.Limits(max_connections=40, max_keepalive_connections=20)


def create_pncp_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=PNCP_TIMEOUT, limits=_pncp_client_limits())


def _retry_after_seconds(resp: httpx.Response) -> float:
    raw = (resp.headers.get("Retry-After") or "").strip()
    if not raw:
        return 0.0
    try:
        return float(raw)
    except ValueError:
        return 0.0


async def _get_pncp(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    tolerate_rate_limit: bool,
) -> Optional[httpx.Response]:
    """
    GET com pacing + retries em 429/502/503/504.
    Se tolerate_rate_limit=True e ainda assim esgotar tentativas, retorna None (tratar como vazio).
    """
    total_attempts = max(1, PNCP_MAX_RETRIES + max(0, PNCP_RATE_LIMIT_EXTRA_ATTEMPTS))
    resp: Optional[httpx.Response] = None
    for attempt in range(total_attempts):
        await _throttle_pace()
        try:
            resp = await client.get(url, params=params)
        except httpx.RequestError:
            if attempt < total_attempts - 1:
                await asyncio.sleep(PNCP_RETRY_BACKOFF_SECONDS * (2 ** min(attempt, 6)))
                continue
            return None

        if resp.status_code in _PNCP_RETRY_STATUS:
            ra = _retry_after_seconds(resp)
            backoff = PNCP_RETRY_BACKOFF_SECONDS * (2 ** min(attempt, 10))
            wait = min(PNCP_RATE_LIMIT_BACKOFF_CAP_SECONDS, max(ra, backoff, 1.0))
            if attempt < total_attempts - 1:
                await asyncio.sleep(wait)
                continue
            return None if tolerate_rate_limit else resp

        return resp

    return None


async def search_contracts(
    data_inicial: str,
    data_final: str,
    codigo_modalidade: Optional[int] = None,
    uf: Optional[str] = None,
    codigo_municipio_ibge: Optional[str] = None,
    pagina: int = 1,
    tamanho_pagina: int = 50,
    *,
    client: Optional[httpx.AsyncClient] = None,
) -> List[Dict[str, Any]]:
    endpoint = f"{PNCP_BASE_URL}/v1/contratacoes/publicacao"
    req_params: Dict[str, Any] = {
        "dataInicial": data_inicial,
        "dataFinal": data_final,
        "pagina": max(1, int(pagina)),
        "tamanhoPagina": max(10, min(int(tamanho_pagina), 50)),
    }
    if codigo_modalidade is not None:
        req_params["codigoModalidadeContratacao"] = int(codigo_modalidade)
    if uf:
        req_params["uf"] = uf
    if codigo_municipio_ibge:
        req_params["codigoMunicipioIbge"] = codigo_municipio_ibge

    close_client = False
    if client is None:
        client = create_pncp_http_client()
        close_client = True
    try:
        # false: após esgotar retries (429/502/503/504) ainda há resposta → erro claro; não confundir com “zero resultados”.
        resp = await _get_pncp(client, endpoint, params=req_params, tolerate_rate_limit=False)
    finally:
        if close_client:
            await client.aclose()

    if resp is None:
        return []
    if resp.status_code == 204:
        return []
    if resp.status_code >= 400:
        # 422 período inválido, etc.; códigos retryáveis esgotados também chegam aqui (detalhe sem HTML cru).
        raise PNCPClientError(f"PNCP retornou {resp.status_code}: {_http_error_snippet(resp)}")

    try:
        data = resp.json()
    except ValueError as e:
        raise PNCPClientError("PNCP retornou JSON inválido.") from e

    if isinstance(data, dict) and isinstance(data.get("data"), list):
        return data["data"]
    if isinstance(data, list):
        return data
    return []


async def get_contract_items(
    cnpj_orgao: str,
    ano_compra: Any,
    sequencial_compra: Any,
    *,
    client: Optional[httpx.AsyncClient] = None,
) -> List[Dict[str, Any]]:
    """
    Busca tabela de itens de uma contratação no PNCP.

    A API de **consulta** (`/api/consulta`) não expõe este recurso; os itens ficam na
    base **pncp-api** (mesma árvore usada em arquivos), por exemplo:
    `{PNCP_PNCP_API}/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens`
    """
    cnpj = str(cnpj_orgao or "").strip()
    ano = str(ano_compra or "").strip()
    seq = str(sequencial_compra or "").strip()
    if not cnpj or not ano or not seq:
        return []

    endpoint = f"{PNCP_PNCP_API_BASE_URL}/v1/orgaos/{cnpj}/compras/{ano}/{seq}/itens"

    close_client = False
    if client is None:
        client = create_pncp_http_client()
        close_client = True
    try:
        resp = await _get_pncp(client, endpoint, params=None, tolerate_rate_limit=True)
    finally:
        if close_client:
            await client.aclose()

    if resp is None:
        return []
    if resp.status_code in (204, 404):
        return []
    if resp.status_code >= 400:
        # Erro pontual em itens: não derruba busca principal
        return []

    try:
        data = resp.json()
    except ValueError:
        return []

    if isinstance(data, dict) and isinstance(data.get("data"), list):
        return data["data"]
    # pncp-api devolve o array de itens direto no corpo.
    if isinstance(data, list):
        return data
    return []
