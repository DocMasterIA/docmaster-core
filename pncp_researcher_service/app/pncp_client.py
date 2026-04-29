from __future__ import annotations

import asyncio
import time
import re
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


_CNPJ_RE = re.compile(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}")


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
        resp = await _get_pncp(client, endpoint, params=req_params, tolerate_rate_limit=True)
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


def _walk_supplier_candidates(obj: Any, *, path: str = "", acc: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, str]]:
    if acc is None:
        acc = []
    if isinstance(obj, dict):
        name_keys = (
            "fornecedor",
            "razaosocial",
            "razao_social",
            "nomerazaosocialfornecedor",
            "nome_fornecedor",
            "fornecedor_nome",
            "vencedor",
        )
        cnpj_keys = ("cnpj", "cnpjfornecedor", "cnpjcpffornecedor", "nifornecedor", "ni_fornecedor")
        nome = ""
        cnpj = ""
        for k, v in obj.items():
            kk = str(k or "").strip().lower()
            vv = str(v or "").strip()
            if vv:
                if any(x in kk for x in name_keys) and len(vv) > 2:
                    nome = vv
                if any(x in kk for x in cnpj_keys):
                    m = _CNPJ_RE.search(vv)
                    if m:
                        cnpj = m.group()
                    else:
                        d = re.sub(r"\D", "", vv)
                        if len(d) == 14:
                            cnpj = d
        if nome or cnpj:
            acc.append({"path": path, "fornecedor": nome, "cnpj": cnpj})
        for k, v in obj.items():
            nxt = f"{path}.{k}" if path else str(k)
            _walk_supplier_candidates(v, path=nxt, acc=acc)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _walk_supplier_candidates(v, path=f"{path}[{i}]", acc=acc)
    return acc


def _is_orgao_path(path: str) -> bool:
    p = (path or "").lower()
    if not p:
        return False
    # Evita falso positivo por conter "orgao" em qualquer trecho;
    # só bloqueia quando o caminho aponta de forma explícita para entidade compradora.
    blocked_tokens = ("orgaoentidade", "orgao_entidade", "unidadeorgao", "unidade_orgao")
    if any(tok in p for tok in blocked_tokens):
        return True
    parts = [x for x in re.split(r"[.\[\]]+", p) if x]
    return any(part in {"orgao", "unidadeorgao", "orgaoentidade"} for part in parts)


def _normalize_cnpj(raw: str) -> str:
    d = re.sub(r"\D", "", str(raw or ""))
    if len(d) != 14:
        return ""
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:14]}"


def _cnpj_digits(raw: Any) -> str:
    return re.sub(r"\D", "", str(raw or ""))


BRASILAPI_CNPJ_URL = "https://brasilapi.com.br/api/cnpj/v1/{cnpj_digits}"


def _extract_supplier_cnpj_only(payload: Any) -> str:
    """Apenas CNPJ a partir do JSON PNCP; razão social / nome vêm da BrasilAPI."""
    cands = _walk_supplier_candidates(payload)
    for cand in cands:
        if _is_orgao_path(cand.get("path", "")):
            continue
        cj = _normalize_cnpj(str(cand.get("cnpj") or "").strip())
        if cj:
            return cj
    return ""


def _parse_brasilapi_to_fornecedor(payload: Dict[str, Any], *, cnpj_digits: str) -> tuple[str, Dict[str, Any]]:
    """Alinha campos ao fluxo de cotação direta (BrasilAPI CNPJ)."""
    razao = str(payload.get("razao_social") or "").strip()
    fantasia = str(payload.get("nome_fantasia") or "").strip()
    nome = razao or fantasia
    porte_raw = payload.get("porte")
    if isinstance(porte_raw, dict):
        porte_txt = str(porte_raw.get("descricao") or porte_raw.get("descricaoPorte") or "").strip()
    else:
        porte_txt = str(porte_raw or "").strip()
    cadastro: Dict[str, Any] = {
        "cnpj": _normalize_cnpj(cnpj_digits),
        "razao_social": razao,
        "nome_fantasia": fantasia,
        "tipo_pessoa": "Pessoa Jurídica",
        "tipo": str(payload.get("descricao_identificador_matriz_filial") or "").strip(),
        "porte": porte_txt,
        "logradouro": str(payload.get("logradouro") or "").strip(),
        "numero": str(payload.get("numero") or "").strip(),
        "complemento": str(payload.get("complemento") or "").strip(),
        "cep": str(payload.get("cep") or "").strip(),
        "bairro": str(payload.get("bairro") or "").strip(),
        "municipio": str(payload.get("municipio") or "").strip(),
        "uf": str(payload.get("uf") or "").strip(),
        "email": str(payload.get("email") or "").strip(),
        "telefone": str(payload.get("ddd_telefone_1") or payload.get("ddd_telefone_2") or "").strip(),
        "situacao": str(payload.get("descricao_situacao_cadastral") or "").strip(),
        "data_situacao": str(payload.get("data_situacao_cadastral") or "").strip(),
        "motivo_situacao": str(payload.get("motivo_situacao_cadastral") or "").strip(),
        "situacao_especial": str(payload.get("situacao_especial") or "").strip(),
        "data_situacao_especial": str(payload.get("data_situacao_especial") or "").strip(),
    }
    return nome, {k: v for k, v in cadastro.items() if v}


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
    return _parse_brasilapi_to_fornecedor(body, cnpj_digits=d)


def _extract_item_numbers_prioritized(items_payload: Any, *, max_items: int = 8) -> List[str]:
    if isinstance(items_payload, dict) and isinstance(items_payload.get("data"), list):
        rows = items_payload["data"]
    elif isinstance(items_payload, list):
        rows = items_payload
    else:
        rows = []
    scored: List[tuple[int, str]] = []
    for it in rows:
        if not isinstance(it, dict):
            continue
        n = str(it.get("numeroItem") or it.get("ordemItem") or it.get("sequencialItem") or "").strip()
        if not n:
            continue
        score = 0
        if bool(it.get("temResultado")):
            score += 5
        sit = str(it.get("situacaoCompraItemNome") or it.get("situacaoCompraItem") or "").lower()
        if "homolog" in sit:
            score += 3
        if "result" in sit:
            score += 1
        scored.append((score, n))
    scored.sort(key=lambda x: (-x[0], int(re.sub(r"\D", "", x[1]) or 0)))
    out: List[str] = []
    for _, n in scored:
        if n not in out:
            out.append(n)
        if len(out) >= max_items:
            break
    return out


async def get_contract_supplier_snapshot(
    cnpj_orgao: str,
    ano_compra: Any,
    sequencial_compra: Any,
    *,
    client: Optional[httpx.AsyncClient] = None,
) -> Dict[str, Any]:
    """
    Obtém CNPJ do fornecedor vencedor via PNCP (/itens/.../resultados ou /resultados)
    e resolve nome + cadastro na BrasilAPI (mesma fonte da cotação direta).
    """
    cnpj = _cnpj_digits(str(cnpj_orgao or ""))
    ano = str(ano_compra or "").strip()
    seq = str(sequencial_compra or "").strip()
    if len(cnpj) != 14 or not ano or not seq:
        return {"cnpj_fornecedor": "", "fornecedor": "", "fornecedor_cadastro": {}}

    base = f"{PNCP_PNCP_API_BASE_URL}/v1/orgaos/{cnpj}/compras/{ano}/{seq}"

    close_client = False
    if client is None:
        client = create_pncp_http_client()
        close_client = True

    async def _finalize(cnpj_fmt: str) -> Dict[str, Any]:
        if not cnpj_fmt:
            return {"cnpj_fornecedor": "", "fornecedor": "", "fornecedor_cadastro": {}}
        nome, cad = await fetch_brasilapi_fornecedor_por_cnpj(client, cnpj_fmt)
        out: Dict[str, Any] = {"cnpj_fornecedor": cnpj_fmt, "fornecedor": nome, "fornecedor_cadastro": cad or {}}
        if nome or cad:
            out["fornecedor_fonte_nome"] = "brasilapi_cnpj"
        return out

    try:
        itens_resp = await _get_pncp(client, f"{base}/itens", params=None, tolerate_rate_limit=True)
        nums: List[str] = []
        if itens_resp is not None and itens_resp.status_code < 400:
            try:
                nums = _extract_item_numbers_prioritized(itens_resp.json(), max_items=3)
            except Exception:
                nums = []
        for n_item in nums:
            res_resp = await _get_pncp(
                client, f"{base}/itens/{n_item}/resultados", params=None, tolerate_rate_limit=True
            )
            if res_resp is None or res_resp.status_code in (204, 404) or res_resp.status_code >= 400:
                continue
            try:
                res_data = res_resp.json()
            except ValueError:
                continue
            cj = _extract_supplier_cnpj_only(res_data)
            if cj:
                return await _finalize(cj)

        res_root = await _get_pncp(client, f"{base}/resultados", params=None, tolerate_rate_limit=True)
        if res_root is not None and res_root.status_code < 400:
            try:
                root_data = res_root.json()
            except ValueError:
                root_data = None
            if root_data is not None:
                cj = _extract_supplier_cnpj_only(root_data)
                if cj:
                    return await _finalize(cj)
    finally:
        if close_client:
            await client.aclose()

    return {"cnpj_fornecedor": "", "fornecedor": "", "fornecedor_cadastro": {}}
