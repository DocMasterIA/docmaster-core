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
    PNCP_INGEST_JSON_INVALID_RETRIES,
    PNCP_INGEST_JSON_INVALID_RETRY_SECONDS,
)
from .supplier_resolver import (
    SupplierResolution,
    cnpj_digits as _cnpj_digits,
    extract_item_numbers_prioritized as _extract_item_numbers_prioritized,
    find_catalog_item_row,
    merge_with_cadastro,
    nome_fornecedor_e_util,
    parse_brasilapi_to_fornecedor as _parse_brasilapi_to_fornecedor,
    resolution_to_api_dict,
    resolve_from_contratos_payload,
    resolve_from_item_catalog_row,
    resolve_from_resultados_payload,
)


class PNCPClientError(Exception):
    pass



# 429/5xx: limite/instabilidade PNCP ou gateway/proxy (transitório).
_PNCP_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})


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
    GET com pacing + retries em 429/500/502/503/504.
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
    tolerate_rate_limit: bool = True,
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

    json_attempts = max(1, int(PNCP_INGEST_JSON_INVALID_RETRIES) + 1)
    last_json_error: Optional[ValueError] = None
    try:
        for json_try in range(json_attempts):
            resp = await _get_pncp(
                client,
                endpoint,
                params=req_params,
                tolerate_rate_limit=tolerate_rate_limit,
            )
            if resp is None:
                return []
            if resp.status_code == 204:
                return []
            if resp.status_code >= 400:
                raise PNCPClientError(
                    f"PNCP retornou {resp.status_code}: {_http_error_snippet(resp)}"
                )
            try:
                data = resp.json()
            except ValueError as e:
                last_json_error = e
                if json_try < json_attempts - 1:
                    wait = float(PNCP_INGEST_JSON_INVALID_RETRY_SECONDS) * (2 ** json_try)
                    await asyncio.sleep(min(wait, 30.0))
                    continue
                raise PNCPClientError("PNCP retornou JSON inválido.") from e

            if isinstance(data, dict) and isinstance(data.get("data"), list):
                return data["data"]
            if isinstance(data, list):
                return data
            return []
    finally:
        if close_client:
            await client.aclose()

    if last_json_error is not None:
        raise PNCPClientError("PNCP retornou JSON inválido.") from last_json_error
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


async def fetch_resultados_map_for_items(
    cnpj_orgao: str,
    ano_compra: Any,
    sequencial_compra: Any,
    item_rows: List[Dict[str, Any]],
    *,
    client: httpx.AsyncClient,
) -> Dict[str, Dict[str, Any]]:
    """
    Busca preços/fornecedor homologados: 1× GET /resultados da compra + GET por item faltante.
    """
    from .config import PNCP_INGEST_FETCH_ITEM_RESULTADOS
    from .supplier_resolver import (
        index_resultados_by_numero_item,
        item_numero_from_row,
        item_row_needs_resultado_fetch,
    )

    if not PNCP_INGEST_FETCH_ITEM_RESULTADOS or not item_rows:
        return {}

    cnpj = str(cnpj_orgao or "").strip()
    ano = str(ano_compra or "").strip()
    seq = str(sequencial_compra or "").strip()
    if not cnpj or not ano or not seq:
        return {}

    need: Dict[str, Dict[str, Any]] = {}
    for row in item_rows:
        if not isinstance(row, dict):
            continue
        ni = item_numero_from_row(row)
        if not ni or not item_row_needs_resultado_fetch(row):
            continue
        need[ni] = row

    if not need:
        return {}

    base = f"{PNCP_PNCP_API_BASE_URL}/v1/orgaos/{cnpj}/compras/{ano}/{seq}"
    out: Dict[str, Dict[str, Any]] = {}

    compra_payload = await _fetch_json_pncp(client, f"{base}/resultados")
    if compra_payload is not None:
        out.update(index_resultados_by_numero_item(compra_payload))

    for ni in list(need.keys()):
        if ni in out:
            continue
        item_payload = await _fetch_json_pncp(client, f"{base}/itens/{ni}/resultados")
        if item_payload is None:
            continue
        mapped = index_resultados_by_numero_item(item_payload)
        if ni in mapped:
            out[ni] = mapped[ni]
        elif mapped:
            out.update(mapped)

    return {k: v for k, v in out.items() if k in need}


async def fetch_contract_items_with_resultados(
    cnpj_orgao: str,
    ano_compra: Any,
    sequencial_compra: Any,
    *,
    client: Optional[httpx.AsyncClient] = None,
) -> tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """GET /itens + mapa de /resultados para itens homologados."""
    close_client = False
    if client is None:
        client = create_pncp_http_client()
        close_client = True
    try:
        rows = await get_contract_items(cnpj_orgao, ano_compra, sequencial_compra, client=client)
        if not rows:
            return [], {}
        resultados = await fetch_resultados_map_for_items(
            cnpj_orgao,
            ano_compra,
            sequencial_compra,
            rows,
            client=client,
        )
        return rows, resultados
    finally:
        if close_client:
            await client.aclose()


BRASILAPI_CNPJ_URL = "https://brasilapi.com.br/api/cnpj/v1/{cnpj_digits}"


async def fetch_brasilapi_fornecedor_por_cnpj(
    client: httpx.AsyncClient, cnpj_formatted_or_digits: str
) -> tuple[str, Dict[str, Any]]:
    d = _cnpj_digits(cnpj_formatted_or_digits)
    if len(d) != 14:
        return "", {}
    url = BRASILAPI_CNPJ_URL.format(cnpj_digits=d)
    try:
        resp = await client.get(url, timeout=httpx.Timeout(12.0, connect=5.0))
    except httpx.RequestError:
        return "", {}
    if resp.status_code in (204, 404) or resp.status_code >= 400:
        return "", {}
    try:
        body = resp.json()
    except ValueError:
        return "", {}
    if not isinstance(body, dict):
        return "", {}
    return _parse_brasilapi_to_fornecedor(body, cnpj_digits_val=d)


async def _finalize_supplier_resolution(
    client: httpx.AsyncClient,
    res: SupplierResolution,
) -> Dict[str, Any]:
    """PNCP primeiro; BrasilAPI se faltar nome útil ou contato (tel/e-mail)."""
    merged = res
    cad = dict(res.fornecedor_cadastro or {})
    tel = str(cad.get("telefone") or cad.get("ddd_telefone_1") or "").strip()
    email = str(cad.get("email") or "").strip()
    precisa_brasil = bool(res.cnpj_fornecedor) and (
        not nome_fornecedor_e_util(res.fornecedor) or not tel or not email
    )
    if precisa_brasil:
        nome, cad_br = await fetch_brasilapi_fornecedor_por_cnpj(client, res.cnpj_fornecedor)
        merged = merge_with_cadastro(res, nome=nome, cadastro=cad_br, fonte_nome="brasilapi_cnpj")
    elif res.cnpj_fornecedor and res.fornecedor and not merged.fornecedor_fonte:
        merged.fornecedor_fonte = "pncp"
    out = resolution_to_api_dict(merged)
    cad_out = out.get("fornecedor_cadastro") if isinstance(out.get("fornecedor_cadastro"), dict) else {}
    if cad_out and not str(out.get("email") or "").strip():
        em = str(cad_out.get("email") or "").strip()
        if em:
            out["email"] = em
    if cad_out and not str(out.get("telefone") or "").strip():
        tel_out = str(cad_out.get("telefone") or cad_out.get("ddd_telefone_1") or "").strip()
        if tel_out:
            out["telefone"] = tel_out
    if merged.fornecedor and "brasilapi" in (merged.fornecedor_fonte or ""):
        out["fornecedor_fonte_nome"] = "brasilapi_cnpj"
        if cad_out:
            out["fornecedor_contato_fonte"] = "brasilapi_cnpj"
    elif merged.fornecedor and merged.fornecedor_fonte:
        out["fornecedor_fonte_nome"] = merged.fornecedor_fonte
    return out


async def _fetch_json_pncp(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
) -> Any:
    resp = await _get_pncp(client, url, params=params, tolerate_rate_limit=True)
    if resp is None or resp.status_code in (204, 404) or resp.status_code >= 400:
        return None
    try:
        return resp.json()
    except ValueError:
        return None


async def _fetch_contratos_contratacao(
    client: httpx.AsyncClient,
    cnpj: str,
    ano: str,
    seq: str,
) -> Any:
    url = f"{PNCP_PNCP_API_BASE_URL}/v1/orgaos/{cnpj}/contratos/contratacao/{ano}/{seq}"
    return await _fetch_json_pncp(
        client,
        url,
        params={"pagina": 1, "tamanhoPagina": 50},
    )


async def _try_contratos_supplier(
    client: httpx.AsyncClient,
    *,
    cnpj: str,
    ano: str,
    seq: str,
    numero_item: str,
    situacao_compra: str,
) -> Optional[Dict[str, Any]]:
    data = await _fetch_contratos_contratacao(client, cnpj, ano, seq)
    if data is None:
        return None
    res = resolve_from_contratos_payload(
        data,
        numero_item=numero_item or None,
        situacao_compra=situacao_compra,
    )
    if res.cnpj_fornecedor or res.fornecedor:
        return await _finalize_supplier_resolution(client, res)
    return None


async def _fetch_homolog_pricing_only(
    client: httpx.AsyncClient,
    base: str,
    *,
    numero_item: str,
    situacao_compra: str,
) -> Dict[str, Any]:
    """GET /resultados quando só falta preço homologado (sem fornecedor novo)."""
    n_item = str(numero_item or "").strip()
    if not n_item:
        return {}
    sit = str(situacao_compra or "").strip()
    res_data = await _fetch_json_pncp(client, f"{base}/itens/{n_item}/resultados")
    if res_data is not None:
        res = resolve_from_resultados_payload(
            res_data,
            numero_item=n_item,
            situacao_compra=sit,
            fonte_prefix="pncp_resultado_item",
        )
        if res.valor_unitario_homologado is not None or res.valor_total_homologado is not None:
            return resolution_to_api_dict(res)
    root_data = await _fetch_json_pncp(client, f"{base}/resultados")
    if root_data is not None:
        res = resolve_from_resultados_payload(
            root_data,
            numero_item=n_item,
            situacao_compra=sit,
            fonte_prefix="pncp_resultado_compra",
        )
        if res.valor_unitario_homologado is not None or res.valor_total_homologado is not None:
            return resolution_to_api_dict(res)
    return {}


async def get_contract_supplier_snapshot(
    cnpj_orgao: str,
    ano_compra: Any,
    sequencial_compra: Any,
    *,
    numero_item: Optional[str] = None,
    situacao_compra: Any = None,
    client: Optional[httpx.AsyncClient] = None,
) -> Dict[str, Any]:
    """
    Fornecedor vencedor por linha de item quando `numero_item` é informado;
    senão fallback na compra (itens priorizados + /resultados).
    """
    empty: Dict[str, Any] = {"cnpj_fornecedor": "", "fornecedor": "", "fornecedor_cadastro": {}}
    cnpj = _cnpj_digits(str(cnpj_orgao or ""))
    ano = str(ano_compra or "").strip()
    seq = str(sequencial_compra or "").strip()
    if len(cnpj) != 14 or not ano or not seq:
        return empty

    base = f"{PNCP_PNCP_API_BASE_URL}/v1/orgaos/{cnpj}/compras/{ano}/{seq}"
    sit_compra = str(situacao_compra or "").strip()
    n_item = str(numero_item or "").strip()

    close_client = False
    if client is None:
        client = create_pncp_http_client()
        close_client = True

    try:
        if n_item:
            res_data = await _fetch_json_pncp(client, f"{base}/itens/{n_item}/resultados")
            if res_data is not None:
                res = resolve_from_resultados_payload(
                    res_data,
                    numero_item=n_item,
                    situacao_compra=sit_compra,
                    fonte_prefix="pncp_resultado_item",
                )
                if res.cnpj_fornecedor or res.fornecedor:
                    return await _finalize_supplier_resolution(client, res)

            root_data = await _fetch_json_pncp(client, f"{base}/resultados")
            if root_data is not None:
                res = resolve_from_resultados_payload(
                    root_data,
                    numero_item=n_item,
                    situacao_compra=sit_compra,
                    fonte_prefix="pncp_resultado_compra",
                )
                if res.cnpj_fornecedor or res.fornecedor:
                    return await _finalize_supplier_resolution(client, res)

            itens_data = await _fetch_json_pncp(client, f"{base}/itens")
            catalog_row = find_catalog_item_row(itens_data, n_item) if itens_data is not None else None
            if catalog_row:
                res = resolve_from_item_catalog_row(catalog_row, situacao_compra=sit_compra)
                if res.cnpj_fornecedor or res.fornecedor:
                    return await _finalize_supplier_resolution(client, res)

            out = await _try_contratos_supplier(
                client,
                cnpj=cnpj,
                ano=ano,
                seq=seq,
                numero_item=n_item,
                situacao_compra=sit_compra,
            )
            if out:
                return out
            pricing_only = await _fetch_homolog_pricing_only(
                client, base, numero_item=n_item, situacao_compra=sit_compra
            )
            if pricing_only:
                return {**empty, **pricing_only}
            return empty

        nums: List[str] = []
        itens_data = await _fetch_json_pncp(client, f"{base}/itens")
        if itens_data is not None:
            try:
                nums = _extract_item_numbers_prioritized(itens_data, max_items=3)
            except Exception:
                nums = []
        for num in nums:
            res_data = await _fetch_json_pncp(client, f"{base}/itens/{num}/resultados")
            if res_data is None:
                continue
            res = resolve_from_resultados_payload(
                res_data,
                numero_item=num,
                situacao_compra=sit_compra,
                fonte_prefix="pncp_resultado_item",
            )
            if res.cnpj_fornecedor or res.fornecedor:
                return await _finalize_supplier_resolution(client, res)

        root_data = await _fetch_json_pncp(client, f"{base}/resultados")
        if root_data is not None:
            res = resolve_from_resultados_payload(
                root_data,
                situacao_compra=sit_compra,
                fonte_prefix="pncp_resultado_compra",
            )
            if res.cnpj_fornecedor or res.fornecedor:
                return await _finalize_supplier_resolution(client, res)

        out = await _try_contratos_supplier(
            client,
            cnpj=cnpj,
            ano=ano,
            seq=seq,
            numero_item=n_item,
            situacao_compra=sit_compra,
        )
        if out:
            return out
    finally:
        if close_client:
            await client.aclose()

    return empty
