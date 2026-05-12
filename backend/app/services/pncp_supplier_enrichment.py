from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

import requests

from backend.app.models import PncpCotacaoItemCotacao

PNCP_API_BASE = "https://pncp.gov.br/api/pncp"
BRASILAPI_CNPJ_URL = "https://brasilapi.com.br/api/cnpj/v1/{cnpj_digits}"
_CNPJ_RE = re.compile(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}")

# GET curto: evita travar geração de PDF (o browser cancela com "Failed to fetch").
_DEFAULT_TIMEOUT = (1.2, 2.4)
# BrasilAPI costuma responder rápido; timeout um pouco maior que PNCP interno.
_BRASILAPI_TIMEOUT = (1.2, 3.5)


def _normalize_cnpj(raw: Any) -> str:
    d = re.sub(r"\D", "", str(raw or ""))
    if len(d) != 14:
        return ""
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:14]}"


def _extract_cnpj_orgao(numero_pncp: str) -> str:
    s = str(numero_pncp or "").strip()
    if "-" in s:
        s = s.split("-", 1)[0]
    d = re.sub(r"\D", "", s)
    return d if len(d) == 14 else ""


def _is_orgao_path(path: str) -> bool:
    p = (path or "").lower()
    if not p:
        return False
    if any(x in p for x in ("orgaoentidade", "orgao_entidade", "unidadeorgao", "unidade_orgao")):
        return True
    parts = [x for x in re.split(r"[.\[\]]+", p) if x]
    return any(part in {"orgao", "orgaoentidade", "unidadeorgao"} for part in parts)


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


def _extract_supplier_snapshot(payload: Any) -> Dict[str, str]:
    cands = _walk_supplier_candidates(payload)
    generic_names = {"demais", "nao informado", "não informado", "epp", "me", "mei", "outros"}
    best: Dict[str, str] | None = None
    for cand in cands:
        if _is_orgao_path(cand.get("path", "")):
            continue
        cnpj = _normalize_cnpj(cand.get("cnpj", ""))
        nome = str(cand.get("fornecedor") or "").strip()
        nome_norm = re.sub(r"\s+", " ", nome).strip().lower()
        nome_ok = bool(nome and nome_norm not in generic_names)
        if cnpj and nome_ok:
            return {"cnpj_fornecedor": cnpj, "fornecedor": nome}
        if cnpj and not best:
            best = {"cnpj_fornecedor": cnpj, "fornecedor": nome if nome_ok else ""}
        elif nome_ok and not best:
            best = {"cnpj_fornecedor": "", "fornecedor": nome}
    return best or {"cnpj_fornecedor": "", "fornecedor": ""}


def _cnpj_digits(raw: Any) -> str:
    return re.sub(r"\D", "", str(raw or ""))


def _fornecedor_display_name_from_source(src: Dict[str, Any]) -> str:
    """Primeiro nome legível no topo do source (ignora CNPJ colado em «fornecedor»)."""
    keys = (
        "fornecedor",
        "fornecedor_nome",
        "nome_fornecedor",
        "nomeRazaoSocialFornecedor",
        "razaoSocialFornecedor",
        "razao_social",
    )
    generic = {"demais", "nao informado", "não informado", "epp", "me", "mei", "outros"}
    for k in keys:
        v = str(src.get(k) or "").strip()
        if not v:
            continue
        low = re.sub(r"\s+", " ", v).strip().lower()
        if low in generic:
            continue
        if _nome_e_somente_cnpj_formatado(v):
            continue
        return v
    return ""


def _nome_e_somente_cnpj_formatado(nome: str) -> bool:
    """
    PNCP (ou importações) às vezes repetem o CNPJ no campo de razão social.
    Qualquer texto sem letras e com exatamente 14 dígitos conta como placeholder.
    """
    nome = str(nome or "").strip()
    if not nome or any(ch.isalpha() for ch in nome):
        return False
    return len(_cnpj_digits(nome)) == 14


def _fornecedor_tem_nome_util(src: Dict[str, Any]) -> bool:
    """Nome legível para exibição (não genérico PNCP nem o próprio CNPJ)."""
    nome = _fornecedor_display_name_from_source(src)
    if not nome:
        return False
    generic_names = {"demais", "nao informado", "não informado", "epp", "me", "mei", "outros"}
    nome_norm = re.sub(r"\s+", " ", nome).strip().lower()
    if nome_norm in generic_names:
        return False
    if _nome_e_somente_cnpj_formatado(nome):
        return False
    cnpj_raw = src.get("cnpj_fornecedor") or ""
    d_cnpj = _cnpj_digits(cnpj_raw)
    d_nome = _cnpj_digits(nome)
    if len(d_cnpj) == 14 and len(d_nome) == 14 and d_nome == d_cnpj:
        return False
    return True


def _extract_supplier_cnpj_only(payload: Any) -> str:
    """Só CNPJ do fornecedor a partir do JSON PNCP; ignora nome (vem da BrasilAPI)."""
    cands = _walk_supplier_candidates(payload)
    for cand in cands:
        if _is_orgao_path(cand.get("path", "")):
            continue
        cj = _normalize_cnpj(str(cand.get("cnpj") or "").strip())
        if cj:
            return cj
    return ""


def fetch_brasilapi_fornecedor_por_cnpj(cnpj_formatted: str) -> tuple[str, Dict[str, Any]]:
    """
    Mesma fonte da cotação direta (BrasilAPI): razão social / nome fantasia estáveis.
    Retorna (nome_exibicao, dict opcional para source.fornecedor_cadastro).
    """
    d = _cnpj_digits(cnpj_formatted)
    if len(d) != 14:
        return "", {}
    url = BRASILAPI_CNPJ_URL.format(cnpj_digits=d)
    payload = _get_json(url, timeout=_BRASILAPI_TIMEOUT)
    if not isinstance(payload, dict):
        return "", {}
    razao = str(payload.get("razao_social") or "").strip()
    fantasia = str(payload.get("nome_fantasia") or "").strip()
    nome = razao or fantasia
    porte_raw = payload.get("porte")
    if isinstance(porte_raw, dict):
        porte_txt = str(porte_raw.get("descricao") or porte_raw.get("descricaoPorte") or "").strip()
    else:
        porte_txt = str(porte_raw or "").strip()
    cadastro: Dict[str, Any] = {
        "cnpj": _normalize_cnpj(d),
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


def _get_json(url: str, timeout=_DEFAULT_TIMEOUT) -> Any:
    try:
        r = requests.get(url, timeout=timeout)
    except Exception:
        return None
    if r.status_code in (204, 404) or r.status_code >= 400:
        return None
    try:
        return r.json()
    except Exception:
        return None


def _extract_item_numbers(items_payload: Any, max_items: int = 8) -> List[str]:
    if isinstance(items_payload, dict) and isinstance(items_payload.get("data"), list):
        rows = items_payload["data"]
    elif isinstance(items_payload, list):
        rows = items_payload
    else:
        rows = []
    scored: List[Tuple[int, str]] = []
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


def get_contract_supplier_snapshot_sync(cnpj_orgao: str, ano_compra: Any, sequencial_compra: Any) -> Dict[str, Any]:
    cnpj = re.sub(r"\D", "", str(cnpj_orgao or ""))
    ano = str(ano_compra or "").strip()
    seq = str(sequencial_compra or "").strip()
    if len(cnpj) != 14 or not ano or not seq:
        return {"cnpj_fornecedor": "", "fornecedor": "", "fornecedor_cadastro": {}}

    base = f"{PNCP_API_BASE}/v1/orgaos/{cnpj}/compras/{ano}/{seq}"

    def _finalize(cnpj_fmt: str) -> Dict[str, Any]:
        if not cnpj_fmt:
            return {"cnpj_fornecedor": "", "fornecedor": "", "fornecedor_cadastro": {}}
        nome, cad = fetch_brasilapi_fornecedor_por_cnpj(cnpj_fmt)
        out: Dict[str, Any] = {"cnpj_fornecedor": cnpj_fmt, "fornecedor": nome, "fornecedor_cadastro": cad or {}}
        if nome or cad:
            out["fornecedor_fonte_nome"] = "brasilapi_cnpj"
        return out

    # Caminho mais eficiente (documentado no manual PNCP): resultado por item — só CNPJ.
    itens_data = _get_json(f"{base}/itens")
    nums = _extract_item_numbers(itens_data, max_items=3)
    if nums:
        n_item = nums[0]
        data = _get_json(f"{base}/itens/{n_item}/resultados")
        if data is not None:
            cj = _extract_supplier_cnpj_only(data)
            if cj:
                return _finalize(cj)

    # Fallback mínimo (1 GET) quando o resultado por item não responde.
    data = _get_json(f"{base}/resultados")
    if data is not None:
        cj = _extract_supplier_cnpj_only(data)
        if cj:
            return _finalize(cj)
    return {"cnpj_fornecedor": "", "fornecedor": "", "fornecedor_cadastro": {}}


def enrich_missing_supplier_fields_for_cotacao(
    cotacao_id: int,
    *,
    max_lookups: int = 12,
    max_brasilapi_lookups: int = 48,
) -> int:
    rows = list(
        PncpCotacaoItemCotacao.objects.filter(cotacao_id=cotacao_id).only(
            "id", "numero_pncp", "ano_compra", "sequencial_compra", "source"
        )
    )
    if not rows:
        return 0

    updated: List[PncpCotacaoItemCotacao] = []
    cache: Dict[Tuple[str, int, int], Dict[str, Any]] = {}
    lookups = 0
    # Cache BrasilAPI por CNPJ (evita N requisições iguais em cotações com muitas linhas).
    brasil_cache: Dict[str, tuple[str, Dict[str, Any]]] = {}
    brasil_fetches = 0
    for row in rows:
        src = row.source if isinstance(row.source, dict) else {}
        has_cnpj = bool(str(src.get("cnpj_fornecedor") or "").strip())
        tem_nome_util = _fornecedor_tem_nome_util(src)
        if has_cnpj and tem_nome_util:
            continue

        cnpj_para_api = ""
        if has_cnpj:
            cnpj_para_api = str(src.get("cnpj_fornecedor") or "").strip()
        else:
            display = _fornecedor_display_name_from_source(src)
            if _nome_e_somente_cnpj_formatado(display):
                cnpj_para_api = _normalize_cnpj(_cnpj_digits(display))

        if cnpj_para_api and not tem_nome_util:
            ck_key = _cnpj_digits(cnpj_para_api)
            if len(ck_key) != 14:
                ck_key = ""
            if ck_key and ck_key in brasil_cache:
                nome_br, cad_br = brasil_cache[ck_key]
            elif ck_key and brasil_fetches >= max_brasilapi_lookups:
                nome_br, cad_br = "", {}
            elif ck_key:
                nome_br, cad_br = fetch_brasilapi_fornecedor_por_cnpj(cnpj_para_api)
                brasil_cache[ck_key] = (nome_br, cad_br)
                brasil_fetches += 1
            else:
                nome_br, cad_br = fetch_brasilapi_fornecedor_por_cnpj(cnpj_para_api)
            if nome_br or cad_br:
                new_src = dict(src)
                if not has_cnpj:
                    fmt = _normalize_cnpj(_cnpj_digits(cnpj_para_api))
                    if fmt:
                        new_src["cnpj_fornecedor"] = fmt
                if nome_br:
                    new_src["fornecedor"] = nome_br
                if cad_br:
                    new_src["fornecedor_cadastro"] = {**(new_src.get("fornecedor_cadastro") or {}), **cad_br}
                    new_src["fornecedor_fonte_nome"] = "brasilapi_cnpj"
                if new_src != src:
                    row.source = new_src
                    updated.append(row)
            continue

        cnpj_org = _extract_cnpj_orgao(row.numero_pncp or "")
        ano = int(row.ano_compra or 0)
        seq = int(row.sequencial_compra or 0)
        if len(cnpj_org) != 14 or ano <= 0 or seq <= 0:
            continue

        key = (cnpj_org, ano, seq)
        if key not in cache:
            if lookups >= max_lookups:
                break
            cache[key] = get_contract_supplier_snapshot_sync(cnpj_org, ano, seq)
            lookups += 1
        snap = cache.get(key) or {}
        cnpj_f = str(snap.get("cnpj_fornecedor") or "").strip()
        nome_f = str(snap.get("fornecedor") or "").strip()
        if not cnpj_f and not nome_f:
            continue

        new_src = dict(src)
        if cnpj_f and not has_cnpj:
            new_src["cnpj_fornecedor"] = cnpj_f
        if nome_f and not tem_nome_util:
            new_src["fornecedor"] = nome_f
        cad_snap = snap.get("fornecedor_cadastro")
        if isinstance(cad_snap, dict) and cad_snap:
            new_src["fornecedor_cadastro"] = {**(new_src.get("fornecedor_cadastro") or {}), **cad_snap}
        if snap.get("fornecedor_fonte_nome"):
            new_src["fornecedor_fonte_nome"] = snap["fornecedor_fonte_nome"]
        if new_src != src:
            row.source = new_src
            updated.append(row)

    if updated:
        PncpCotacaoItemCotacao.objects.bulk_update(updated, ["source"], batch_size=500)
    return len(updated)
