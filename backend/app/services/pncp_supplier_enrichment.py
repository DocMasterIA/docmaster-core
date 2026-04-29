from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

from backend.app.models import PncpCotacaoItemCotacao

PNCP_API_BASE = "https://pncp.gov.br/api/pncp"
_CNPJ_RE = re.compile(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}")


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


def _get_json(url: str, timeout_s: float = 5.0) -> Any:
    try:
        r = requests.get(url, timeout=timeout_s)
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
    out: List[str] = []
    for it in rows:
        if not isinstance(it, dict):
            continue
        n = str(it.get("numeroItem") or it.get("ordemItem") or it.get("sequencialItem") or "").strip()
        if n and n not in out:
            out.append(n)
        if len(out) >= max_items:
            break
    return out


def get_contract_supplier_snapshot_sync(cnpj_orgao: str, ano_compra: Any, sequencial_compra: Any) -> Dict[str, str]:
    cnpj = re.sub(r"\D", "", str(cnpj_orgao or ""))
    ano = str(ano_compra or "").strip()
    seq = str(sequencial_compra or "").strip()
    if len(cnpj) != 14 or not ano or not seq:
        return {"cnpj_fornecedor": "", "fornecedor": ""}

    base = f"{PNCP_API_BASE}/v1/orgaos/{cnpj}/compras/{ano}/{seq}"
    for suffix in ("resultado", "resultados", "fornecedor", "fornecedores", "vencedores", "atas", "contrato", "contratos", "empenhos", "partes-envolvidas"):
        data = _get_json(f"{base}/{suffix}")
        if data is None:
            continue
        snap = _extract_supplier_snapshot(data)
        if snap.get("cnpj_fornecedor") or snap.get("fornecedor"):
            return snap

    itens_data = _get_json(f"{base}/itens")
    for n_item in _extract_item_numbers(itens_data, max_items=8):
        data = _get_json(f"{base}/itens/{n_item}/resultados")
        if data is None:
            continue
        snap = _extract_supplier_snapshot(data)
        if snap.get("cnpj_fornecedor") or snap.get("fornecedor"):
            return snap
    return {"cnpj_fornecedor": "", "fornecedor": ""}


def enrich_missing_supplier_fields_for_cotacao(cotacao_id: int, *, max_lookups: int = 150) -> int:
    rows = list(
        PncpCotacaoItemCotacao.objects.filter(cotacao_id=cotacao_id).only(
            "id", "numero_pncp", "ano_compra", "sequencial_compra", "source"
        )
    )
    if not rows:
        return 0

    updated: List[PncpCotacaoItemCotacao] = []
    cache: Dict[Tuple[str, int, int], Dict[str, str]] = {}
    lookups = 0
    for row in rows:
        src = row.source if isinstance(row.source, dict) else {}
        has_cnpj = bool(str(src.get("cnpj_fornecedor") or "").strip())
        has_nome = bool(str(src.get("fornecedor") or src.get("fornecedor_nome") or src.get("nome_fornecedor") or "").strip())
        if has_cnpj and has_nome:
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
        if nome_f and not has_nome:
            new_src["fornecedor"] = nome_f
        if new_src != src:
            row.source = new_src
            updated.append(row)

    if updated:
        PncpCotacaoItemCotacao.objects.bulk_update(updated, ["source"], batch_size=500)
    return len(updated)
