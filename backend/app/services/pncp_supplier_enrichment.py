from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests
from django.conf import settings

from backend.app.services.pncp_cnpj_email_cache import (
    get_cached_cnpj_email,
    set_cached_cnpj_email,
)
from backend.app.models import PncpCotacaoItemCotacao
from backend.app.services.pncp_source_normalize import normalize_pncp_geo_in_payload

logger = logging.getLogger(__name__)

PNCP_API_BASE = "https://pncp.gov.br/api/pncp"
BRASILAPI_CNPJ_URL = "https://brasilapi.com.br/api/cnpj/v1/{cnpj_digits}"
RECEITAWS_CNPJ_URL = "https://www.receitaws.com.br/v1/cnpj/{cnpj_digits}"
CNPJ_WS_URL = "https://publica.cnpj.ws/cnpj/{cnpj_digits}"
_HTTP_UA = "DocMaster-PNCP/1.0"
_CNPJ_RE = re.compile(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}")

# Timeout PNCP na geração de PDF / adicionar fonte (evita cancelar cedo demais).
_DEFAULT_TIMEOUT = (2.5, 5.0)
# BrasilAPI costuma responder rápido; timeout um pouco maior que PNCP interno.
_BRASILAPI_TIMEOUT = (2.0, 5.0)
_RECEITAWS_TIMEOUT = 10


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


def _parse_ano_seq_from_numero_pncp(numero_pncp: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Extrai ano/sequencial do numeroControlePNCP.

    Formatos:
    - ``CNPJ-1-2024-42`` (4 segmentos)
    - ``CNPJ-1-000261/2025`` (sequencial/ano no último segmento)
    """
    s = str(numero_pncp or "").strip()
    m = re.search(r"-(\d+)/(\d{4})\s*$", s)
    if m:
        try:
            seq = int(m.group(1))
            ano = int(m.group(2))
        except (TypeError, ValueError):
            return None, None
        if 1990 <= ano <= 2100 and 1 <= seq <= 2_147_483_647:
            return ano, seq
        return None, None

    parts = [p.strip() for p in s.split("-") if p.strip()]
    if len(parts) < 4:
        return None, None
    try:
        ano = int(parts[-2])
        seq = int(parts[-1])
    except (TypeError, ValueError):
        return None, None
    if ano < 1990 or ano > 2100 or seq < 1 or seq > 2_147_483_647:
        return None, None
    return ano, seq


def _ano_seq_for_enrichment(
    *,
    numero_pncp: str = "",
    ano_compra: Any = None,
    sequencial_compra: Any = None,
    source: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[int], Optional[int]]:
    """Colunas ORM → source JSON → parse do numeroControlePNCP."""
    ano = _safe_int_field(ano_compra, min_v=1990, max_v=2100)
    seq = _safe_int_field(sequencial_compra, min_v=1, max_v=2_147_483_647)
    if ano is not None and seq is not None:
        return ano, seq
    src = source if isinstance(source, dict) else {}
    if ano is None:
        ano = _safe_int_field(src.get("ano_compra"), min_v=1990, max_v=2100)
    if seq is None:
        seq = _safe_int_field(src.get("sequencial_compra"), min_v=1, max_v=2_147_483_647)
    if ano is not None and seq is not None:
        return ano, seq
    np = str(
        numero_pncp
        or src.get("numero_pncp")
        or src.get("numeroControlePNCP")
        or ""
    ).strip()
    return _parse_ano_seq_from_numero_pncp(np)


_HOMOLOG_TOKENS = ("homolog", "adjudic")
_SKIP_SIT_TOKENS = ("revog", "anul", "cancel")


def _situacao_lower(value: Any) -> str:
    return str(value or "").strip().lower()


def _situacao_has_any(sit: str, tokens: tuple[str, ...]) -> bool:
    if not sit:
        return False
    return any(tok in sit for tok in tokens)


def item_homologado_para_busca_dict(it: Dict[str, Any]) -> bool:
    """Alinhado ao researcher: só homologado/adjudicado na montagem de cotação."""
    if not isinstance(it, dict):
        return False
    sit_item = _situacao_lower(
        it.get("situacaoCompraItemNome")
        or it.get("situacaoCompraItem")
        or it.get("situacao_item_exibicao")
        or ""
    )
    if _situacao_has_any(sit_item, _SKIP_SIT_TOKENS):
        return False
    if _situacao_has_any(sit_item, _HOMOLOG_TOKENS):
        return True
    sit_compra = _situacao_lower(
        it.get("situacao_compra") or it.get("situacao") or it.get("situacaoCompraNome") or ""
    )
    if _situacao_has_any(sit_compra, _SKIP_SIT_TOKENS):
        return False
    if _situacao_has_any(sit_compra, ("homolog", "adjudic", "encerr")):
        return True
    if it.get("item_homologado") is True:
        return True
    return False


def _pncp_compra_keys_present(it: Dict[str, Any]) -> bool:
    """True se há dados mínimos para lookup PNCP de fornecedor (compra + item)."""
    np = str(it.get("numero_pncp") or it.get("numeroControlePNCP") or "").strip()
    if not np or len(_extract_cnpj_orgao(np)) != 14:
        return False
    ano, seq = _ano_seq_for_enrichment(
        numero_pncp=np,
        ano_compra=it.get("ano_compra"),
        sequencial_compra=it.get("sequencial_compra"),
        source=it,
    )
    return ano is not None and seq is not None


def _should_attempt_pncp_supplier_lookup(it: Dict[str, Any], *, only_homolog: bool) -> bool:
    """
    Decide se consulta PNCP por fornecedor.
    Com chaves PNCP válidas, tenta sempre (mesmo não homologado / busca em lote).
    """
    if _payload_supplier_complete(it):
        return False
    if _pncp_compra_keys_present(it):
        return True
    if item_homologado_para_busca_dict(it):
        return True
    return not only_homolog


def _ensure_pncp_compra_keys(it: Dict[str, Any]) -> None:
    """Preenche numero_pncp / ano / seq a partir do controle PNCP antes do enrich."""
    if not isinstance(it, dict):
        return
    np = str(it.get("numero_pncp") or it.get("numeroControlePNCP") or "").strip()
    if np:
        it.setdefault("numero_pncp", np)
    ano, seq = _ano_seq_for_enrichment(
        numero_pncp=np,
        ano_compra=it.get("ano_compra"),
        sequencial_compra=it.get("sequencial_compra"),
        source=it,
    )
    if ano is not None:
        it.setdefault("ano_compra", ano)
    if seq is not None:
        it.setdefault("sequencial_compra", seq)
    ni = str(it.get("numero_item") or it.get("numeroItem") or "").strip()
    if ni:
        it.setdefault("numero_item", ni)


def _promote_supplier_from_deep_walk(it: Dict[str, Any]) -> bool:
    """Varre JSON aninhado (sourceRaw) e promove CNPJ/nome para o topo."""
    if _payload_supplier_complete(it):
        return False
    snap = _extract_supplier_snapshot(it)
    if not snap.get("cnpj_fornecedor") and not snap.get("fornecedor"):
        return False
    return _merge_supplier_snap_into_payload(it, snap)


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
        nome_ok = bool(
            nome
            and nome_norm not in generic_names
            and not nome_norm.startswith("pncp_")
            and not _nome_e_somente_cnpj_formatado(nome)
        )
        if cnpj and nome_ok:
            return {"cnpj_fornecedor": cnpj, "fornecedor": nome}
        if cnpj and not best:
            best = {"cnpj_fornecedor": cnpj, "fornecedor": nome if nome_ok else ""}
        elif nome_ok and not best:
            best = {"cnpj_fornecedor": "", "fornecedor": nome}
    return best or {"cnpj_fornecedor": "", "fornecedor": ""}


def _cnpj_digits(raw: Any) -> str:
    return re.sub(r"\D", "", str(raw or ""))


def _supplier_payload_layers(it: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Camadas onde cotações PNCP guardam fornecedor (topo, source aninhado, cadastro)."""
    layers: List[Dict[str, Any]] = []
    if isinstance(it, dict):
        layers.append(it)
        inner = it.get("source")
        if isinstance(inner, dict):
            layers.append(inner)
            inner2 = inner.get("source")
            if isinstance(inner2, dict):
                layers.append(inner2)
        cad = it.get("fornecedor_cadastro")
        if isinstance(cad, dict):
            layers.append(cad)
    return layers


def _pick_supplier_field_from_layers(it: Dict[str, Any], *keys: str) -> str:
    for layer in _supplier_payload_layers(it):
        for k in keys:
            v = str(layer.get(k) or "").strip()
            if v:
                return v
    return ""


def _merge_fornecedor_cadastro_dict(it: Dict[str, Any], cad: Dict[str, Any]) -> None:
    if not isinstance(cad, dict) or not cad:
        return
    prev = it.get("fornecedor_cadastro")
    if not isinstance(prev, dict):
        prev = {}
    merged = {**prev, **{k: v for k, v in cad.items() if v}}
    if merged != prev:
        it["fornecedor_cadastro"] = merged


def _promote_supplier_contact_from_layers(it: Dict[str, Any]) -> None:
    """Promove telefone/e-mail/cadastro de source aninhado (sourceRaw) para o topo."""
    if not isinstance(it, dict):
        return
    email_keys = ("email", "emailFornecedor", "email_fornecedor")
    tel_keys = ("telefone", "ddd_telefone_1", "ddd_telefone_2", "telefone1", "telefone2")
    for layer in _supplier_payload_layers(it):
        cad = layer.get("fornecedor_cadastro")
        if isinstance(cad, dict) and cad:
            _merge_fornecedor_cadastro_dict(it, cad)
        if not str(it.get("email") or "").strip():
            for k in email_keys:
                em = str(layer.get(k) or "").strip()
                if em and em != "—":
                    it["email"] = em
                    break
        if not str(it.get("telefone") or "").strip():
            for k in tel_keys:
                tel = str(layer.get(k) or "").strip()
                if tel and tel != "—":
                    it["telefone"] = tel
                    break


def flatten_supplier_fields_in_payload(it: Dict[str, Any]) -> None:
    """
    Promove CNPJ/nome de source aninhado para o topo do payload.
    Cotações da busca inteligente gravam sourceRaw dentro de source.source.
    """
    if not isinstance(it, dict):
        return
    if not str(it.get("cnpj_fornecedor") or "").strip():
        raw_cnpj = _pick_supplier_field_from_layers(
            it,
            "cnpj_fornecedor",
            "cnpjFornecedor",
            "cnpjCpfFornecedor",
            "niFornecedor",
            "cnpj",
        )
        digits = _cnpj_digits(raw_cnpj)
        if len(digits) == 14:
            it["cnpj_fornecedor"] = _normalize_cnpj(digits)
    if not _fornecedor_tem_nome_util_topo(it):
        for layer in _supplier_payload_layers(it):
            cad = layer.get("fornecedor_cadastro")
            if isinstance(cad, dict):
                for k in ("razao_social", "nome_fantasia", "razaoSocial", "nomeFantasia"):
                    v = str(cad.get(k) or "").strip()
                    if v and not _nome_e_somente_cnpj_formatado(v):
                        it["fornecedor"] = v
                        _promote_supplier_contact_from_layers(it)
                        return
            for k in (
                "fornecedor",
                "fornecedor_nome",
                "nome_fornecedor",
                "nomeRazaoSocialFornecedor",
                "razaoSocialFornecedor",
                "razao_social",
            ):
                v = str(layer.get(k) or "").strip()
                if not v or _nome_e_somente_cnpj_formatado(v):
                    continue
                low = re.sub(r"\s+", " ", v).strip().lower()
                if low in {"demais", "nao informado", "não informado", "epp", "me", "mei", "outros"}:
                    continue
                if low.startswith("pncp_"):
                    continue
                it["fornecedor"] = v
                _promote_supplier_contact_from_layers(it)
                return
    _promote_supplier_contact_from_layers(it)


def _fornecedor_display_name_from_source(src: Dict[str, Any]) -> str:
    """Nome legível em qualquer camada do payload (topo, source aninhado, cadastro)."""
    # Não chamar flatten_supplier_fields_in_payload aqui: flatten usa _fornecedor_tem_nome_util,
    # que delega a esta função — recursão infinita (500 ao carregar sessão / PDF).
    generic = {"demais", "nao informado", "não informado", "epp", "me", "mei", "outros"}
    for layer in _supplier_payload_layers(src):
        cad = layer.get("fornecedor_cadastro")
        if isinstance(cad, dict):
            for k in ("razao_social", "nome_fantasia", "razaoSocial", "nomeFantasia"):
                v = str(cad.get(k) or "").strip()
                if not v or _nome_e_somente_cnpj_formatado(v):
                    continue
                low = re.sub(r"\s+", " ", v).strip().lower()
                if low in generic or low.startswith("pncp_"):
                    continue
                return v
        for k in (
            "fornecedor",
            "fornecedor_nome",
            "nome_fornecedor",
            "nomeRazaoSocialFornecedor",
            "razaoSocialFornecedor",
            "razao_social",
        ):
            v = str(layer.get(k) or "").strip()
            if not v:
                continue
            low = re.sub(r"\s+", " ", v).strip().lower()
            if low in generic or low.startswith("pncp_"):
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


def _nome_fornecedor_util_para_flatten(nome: str, *, cnpj_raw: str = "") -> bool:
    if not nome:
        return False
    generic = {"demais", "nao informado", "não informado", "epp", "me", "mei", "outros"}
    nome_norm = re.sub(r"\s+", " ", nome).strip().lower()
    if nome_norm in generic:
        return False
    if nome_norm.startswith("pncp_"):
        return False
    if _nome_e_somente_cnpj_formatado(nome):
        return False
    d_cnpj = _cnpj_digits(cnpj_raw)
    d_nome = _cnpj_digits(nome)
    if len(d_cnpj) == 14 and len(d_nome) == 14 and d_nome == d_cnpj:
        return False
    return True


def _fornecedor_tem_nome_util_topo(src: Dict[str, Any]) -> bool:
    """Nome legível só no topo do payload (flatten promove camadas aninhadas se faltar aqui)."""
    if not isinstance(src, dict):
        return False
    cnpj_raw = str(src.get("cnpj_fornecedor") or "")
    cad = src.get("fornecedor_cadastro")
    if isinstance(cad, dict):
        for k in ("razao_social", "nome_fantasia", "razaoSocial", "nomeFantasia"):
            v = str(cad.get(k) or "").strip()
            if _nome_fornecedor_util_para_flatten(v, cnpj_raw=cnpj_raw):
                return True
    for k in (
        "fornecedor",
        "fornecedor_nome",
        "nome_fornecedor",
        "nomeRazaoSocialFornecedor",
        "razaoSocialFornecedor",
        "razao_social",
    ):
        v = str(src.get(k) or "").strip()
        if _nome_fornecedor_util_para_flatten(v, cnpj_raw=cnpj_raw):
            return True
    return False


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


def fornecedor_tem_cnpj_para_cotacao(it: Dict[str, Any]) -> bool:
    """
    Exige CNPJ de fornecedor (14 dígitos) para gravar fonte PNCP na cotação.
    Chamar após flatten/enrich no payload.
    """
    if not isinstance(it, dict):
        return False
    flatten_supplier_fields_in_payload(it)
    _promote_supplier_from_deep_walk(it)
    raw = str(it.get("cnpj_fornecedor") or "").strip()
    if len(_cnpj_digits(raw)) != 14:
        raw = _pick_supplier_field_from_layers(
            it,
            "cnpj_fornecedor",
            "cnpjFornecedor",
            "cnpjCpfFornecedor",
            "niFornecedor",
            "cnpj",
        )
    return len(_cnpj_digits(raw)) == 14


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
    t1 = str(payload.get("ddd_telefone_1") or "").strip()
    t2 = str(payload.get("ddd_telefone_2") or "").strip()
    telefone = t1
    if t2 and t2 != t1:
        telefone = f"{t1} / {t2}" if t1 else t2
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
        "telefone": telefone,
        "ddd_telefone_1": t1,
        "ddd_telefone_2": t2,
        "situacao": str(payload.get("descricao_situacao_cadastral") or "").strip(),
        "data_situacao": str(payload.get("data_situacao_cadastral") or "").strip(),
        "motivo_situacao": str(payload.get("motivo_situacao_cadastral") or "").strip(),
        "situacao_especial": str(payload.get("situacao_especial") or "").strip(),
        "data_situacao_especial": str(payload.get("data_situacao_especial") or "").strip(),
    }
    return nome, {k: v for k, v in cadastro.items() if v}


def receitaws_email_fallback_enabled() -> bool:
    return bool(getattr(settings, "PNCP_RELATORIO_PDF_RECEITAWS_EMAIL", True))


def receitaws_email_max_lookups() -> int:
    """Máximo de chamadas HTTP externas por requisição (cada API limita ~3/min)."""
    return int(getattr(settings, "PNCP_RELATORIO_PDF_MAX_RECEITAWS_LOOKUPS", 3) or 0)


def _email_externo_valido(em: Any) -> bool:
    s = str(em or "").strip()
    return "@" in s and len(s) >= 5


def _fetch_cnpj_ws_email_http(cnpj_digits: str) -> Tuple[str, bool]:
    """Retorna (email, rate_limited)."""
    url = CNPJ_WS_URL.format(cnpj_digits=cnpj_digits)
    try:
        r = requests.get(url, timeout=_RECEITAWS_TIMEOUT, headers={"User-Agent": _HTTP_UA})
    except Exception:
        return "", False
    if r.status_code == 429:
        return "", True
    if r.status_code >= 400:
        return "", False
    try:
        payload = r.json()
    except Exception:
        return "", False
    if not isinstance(payload, dict):
        return "", False
    est = payload.get("estabelecimento")
    if not isinstance(est, dict):
        return "", False
    em = str(est.get("email") or "").strip()
    return (em, False) if _email_externo_valido(em) else ("", False)


def _fetch_receitaws_email_http(cnpj_digits: str) -> Tuple[str, bool]:
    """Retorna (email, rate_limited)."""
    url = RECEITAWS_CNPJ_URL.format(cnpj_digits=cnpj_digits)
    try:
        r = requests.get(url, timeout=_RECEITAWS_TIMEOUT, headers={"User-Agent": _HTTP_UA})
    except Exception:
        return "", False
    if r.status_code == 429:
        return "", True
    if r.status_code >= 400:
        return "", False
    try:
        payload = r.json()
    except Exception:
        return "", False
    if not isinstance(payload, dict):
        return "", False
    if str(payload.get("status") or "").strip().upper() == "ERROR":
        msg = str(payload.get("message") or "").lower()
        if any(x in msg for x in ("rate", "many", "limite", "too many")):
            return "", True
        return "", False
    em = str(payload.get("email") or "").strip()
    return (em, False) if _email_externo_valido(em) else ("", False)


def fetch_cnpj_email_externo(
    cnpj_formatted: str,
    *,
    state: Optional[Dict[str, Any]] = None,
) -> str:
    """
    E-mail via cache persistente + cnpj.ws / ReceitaWS (BrasilAPI omite).
    state opcional: cache de memória, contagem HTTP e rate limit na requisição.
    """
    d = _cnpj_digits(cnpj_formatted)
    if len(d) != 14:
        return ""

    mem: Optional[Dict[str, str]] = None
    if state is not None:
        mem = state.setdefault("cache", {})
        if d in mem:
            return str(mem[d] or "")

    cached = get_cached_cnpj_email(d)
    if cached:
        if mem is not None:
            mem[d] = cached
        return cached

    if state is not None and state.get("rate_limited"):
        return ""

    max_http = int((state or {}).get("max_http_fetches") or receitaws_email_max_lookups())
    http_n = int((state or {}).get("http_fetches") or 0)
    if state is not None and max_http > 0 and http_n >= max_http:
        return ""

    def _http_fetch(fetch_fn) -> Tuple[str, bool]:
        nonlocal http_n
        em, rl = fetch_fn(d)
        if state is not None:
            state["http_fetches"] = http_n + 1
            http_n += 1
            if rl:
                state["rate_limited"] = True
        return em, rl

    wait_sec = int(getattr(settings, "PNCP_CNPJ_EMAIL_RATE_LIMIT_WAIT_SEC", 0) or 0)
    if state is not None and state.get("allow_rate_limit_wait"):
        wait_sec = int(getattr(settings, "PNCP_CNPJ_EMAIL_RATE_LIMIT_WAIT_SEC", 22) or 0)

    em = ""
    fonte = ""
    for fetch_fn, nome_fonte in ((_fetch_cnpj_ws_email_http, "cnpj.ws"), (_fetch_receitaws_email_http, "receitaws")):
        if state is not None and state.get("rate_limited"):
            break
        if state is not None and max_http > 0 and http_n >= max_http:
            break
        got, rl = _http_fetch(fetch_fn)
        if got:
            em, fonte = got, nome_fonte
            break
        if rl and wait_sec > 0 and state is not None and not state.get("_rate_wait_done"):
            time.sleep(wait_sec)
            state["_rate_wait_done"] = True
            state["rate_limited"] = False
            got2, rl2 = _http_fetch(fetch_fn)
            if got2:
                em, fonte = got2, nome_fonte
                break
            if rl2 and state is not None:
                state["rate_limited"] = True
        if rl:
            break

    if em:
        set_cached_cnpj_email(d, em, fonte=fonte)
        if mem is not None:
            mem[d] = em
    return em


def fetch_receitaws_email_por_cnpj(cnpj_formatted: str) -> str:
    """Compat: consulta com cache persistente e cnpj.ws antes da ReceitaWS."""
    return fetch_cnpj_email_externo(cnpj_formatted)


def _apply_receitaws_email_enrichment(
    it: Dict[str, Any],
    *,
    rw_state: Optional[Dict[str, Any]],
) -> bool:
    if not rw_state or not receitaws_email_fallback_enabled():
        return False
    flatten_supplier_fields_in_payload(it)
    if _contact_email_from_payload(it):
        return False
    ck = _cnpj_digits(str(it.get("cnpj_fornecedor") or ""))
    if len(ck) != 14:
        return False
    em = fetch_cnpj_email_externo(ck, state=rw_state)
    if not em:
        return False
    prev = it.get("fornecedor_cadastro")
    cad = dict(prev) if isinstance(prev, dict) else {}
    cad["email"] = em
    snap: Dict[str, Any] = {
        "cnpj_fornecedor": it.get("cnpj_fornecedor"),
        "fornecedor_cadastro": cad,
        "fornecedor_contato_fonte": "receitaws_cnpj",
    }
    return _merge_supplier_snap_into_payload(it, snap)


def _get_json(url: str, timeout=_DEFAULT_TIMEOUT, *, params: Optional[Dict[str, Any]] = None) -> Any:
    try:
        r = requests.get(url, timeout=timeout, params=params or {})
    except Exception:
        return None
    if r.status_code in (204, 404) or r.status_code >= 400:
        return None
    try:
        return r.json()
    except Exception:
        return None


def _fetch_contratos_contratacao_sync(cnpj_org: str, ano: Any, seq: Any) -> Any:
    url = f"{PNCP_API_BASE}/v1/orgaos/{cnpj_org}/contratos/contratacao/{ano}/{seq}"
    return _get_json(url, params={"pagina": 1, "tamanhoPagina": 50})


def _supplier_snap_from_contratos_payload(
    data: Any,
    *,
    numero_item: str = "",
    situacao_compra: str = "",
) -> Dict[str, str]:
    return _supplier_snap_from_resultados_payload(
        data, numero_item=numero_item, situacao_compra=situacao_compra
    )


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


def _numero_item_from_row_or_source(row: PncpCotacaoItemCotacao, src: Dict[str, Any]) -> str:
    for raw in (
        getattr(row, "numero_item", None),
        src.get("numero_item"),
        src.get("numeroItem"),
    ):
        n = str(raw or "").strip()
        if n:
            return n
    return ""


def _cadastro_tem_contato_util(cad: Dict[str, Any]) -> bool:
    tel = str(
        cad.get("telefone")
        or cad.get("ddd_telefone_1")
        or cad.get("ddd_telefone_2")
        or ""
    ).strip()
    email = str(cad.get("email") or "").strip()
    return bool(tel or email)


def _finalize_supplier_snapshot_sync(snap: Dict[str, str]) -> Dict[str, Any]:
    cnpj_fmt = str(snap.get("cnpj_fornecedor") or "").strip()
    nome = str(snap.get("fornecedor") or "").strip()
    if not cnpj_fmt and not nome:
        return {"cnpj_fornecedor": "", "fornecedor": "", "fornecedor_cadastro": {}}
    precisa_brasil = bool(cnpj_fmt) and (
        not _fornecedor_tem_nome_util({"fornecedor": nome, "cnpj_fornecedor": cnpj_fmt})
        or not _cadastro_tem_contato_util({})
    )
    if precisa_brasil:
        nome_br, cad = fetch_brasilapi_fornecedor_por_cnpj(cnpj_fmt)
        if nome_br and not _fornecedor_tem_nome_util({"fornecedor": nome, "cnpj_fornecedor": cnpj_fmt}):
            nome = nome_br
        out: Dict[str, Any] = {
            "cnpj_fornecedor": cnpj_fmt,
            "fornecedor": nome,
            "fornecedor_cadastro": cad or {},
        }
        if nome_br or cad:
            out["fornecedor_fonte_nome"] = "brasilapi_cnpj"
        if cad:
            out["fornecedor_contato_fonte"] = "brasilapi_cnpj"
            em = str(cad.get("email") or "").strip()
            tel = str(cad.get("telefone") or cad.get("ddd_telefone_1") or "").strip()
            if em:
                out["email"] = em
            if tel:
                out["telefone"] = tel
        return out
    out = {"cnpj_fornecedor": cnpj_fmt, "fornecedor": nome, "fornecedor_cadastro": {}}
    if nome:
        out["fornecedor_fonte_nome"] = "pncp"
    return out


def _supplier_snap_from_resultados_payload(
    data: Any,
    *,
    numero_item: str = "",
    situacao_compra: str = "",
) -> Dict[str, str]:
    """Extrai fornecedor do JSON /resultados com match opcional por numeroItem."""
    if numero_item and isinstance(data, dict) and isinstance(data.get("data"), list):
        want = str(numero_item).strip()
        for row in data["data"]:
            if not isinstance(row, dict):
                continue
            got = str(row.get("numeroItem") or row.get("ordemItem") or "").strip()
            if got == want:
                snap = _extract_supplier_snapshot(row)
                if snap.get("cnpj_fornecedor") or snap.get("fornecedor"):
                    return snap
    return _extract_supplier_snapshot(data)


def _find_catalog_row(items_payload: Any, numero_item: str) -> Optional[Dict[str, Any]]:
    want = str(numero_item or "").strip()
    if not want:
        return None
    if isinstance(items_payload, dict) and isinstance(items_payload.get("data"), list):
        rows = items_payload["data"]
    elif isinstance(items_payload, list):
        rows = items_payload
    else:
        return None
    for it in rows:
        if not isinstance(it, dict):
            continue
        got = str(it.get("numeroItem") or it.get("ordemItem") or it.get("sequencialItem") or "").strip()
        if got == want:
            return it
    return None


def _supplier_snapshot_compra_fallback(
    base: str,
    *,
    cnpj: str,
    ano: str,
    seq: str,
    situacao_compra: str = "",
) -> Dict[str, Any]:
    """Fallback quando resultados do item específico não trazem fornecedor."""
    empty: Dict[str, Any] = {"cnpj_fornecedor": "", "fornecedor": "", "fornecedor_cadastro": {}}
    itens_data = _get_json(f"{base}/itens")
    nums = _extract_item_numbers(itens_data, max_items=5)
    for num in nums:
        data = _get_json(f"{base}/itens/{num}/resultados")
        if data is not None:
            snap = _supplier_snap_from_resultados_payload(data, numero_item=num)
            if snap.get("cnpj_fornecedor") or snap.get("fornecedor"):
                return _finalize_supplier_snapshot_sync(snap)
        catalog = _find_catalog_row(itens_data, num)
        if catalog:
            snap = _extract_supplier_snapshot(catalog)
            if snap.get("cnpj_fornecedor") or snap.get("fornecedor"):
                return _finalize_supplier_snapshot_sync(snap)

    data = _get_json(f"{base}/resultados")
    if data is not None:
        snap = _supplier_snap_from_resultados_payload(data)
        if snap.get("cnpj_fornecedor") or snap.get("fornecedor"):
            return _finalize_supplier_snapshot_sync(snap)

    contratos = _fetch_contratos_contratacao_sync(cnpj, ano, seq)
    if contratos is not None:
        snap = _supplier_snap_from_contratos_payload(contratos, situacao_compra=situacao_compra)
        if snap.get("cnpj_fornecedor") or snap.get("fornecedor"):
            out = _finalize_supplier_snapshot_sync(snap)
            out["fornecedor_fonte"] = out.get("fornecedor_fonte") or "pncp_contrato"
            return out
    return empty


def get_contract_supplier_snapshot_sync(
    cnpj_orgao: str,
    ano_compra: Any,
    sequencial_compra: Any,
    *,
    numero_item: Optional[str] = None,
    situacao_compra: Any = None,
) -> Dict[str, Any]:
    """
    Fornecedor por `numero_item` quando informado; senão fallback por compra.
    """
    empty = {"cnpj_fornecedor": "", "fornecedor": "", "fornecedor_cadastro": {}}
    cnpj = re.sub(r"\D", "", str(cnpj_orgao or ""))
    ano = str(ano_compra or "").strip()
    seq = str(sequencial_compra or "").strip()
    if len(cnpj) != 14 or not ano or not seq:
        return empty

    base = f"{PNCP_API_BASE}/v1/orgaos/{cnpj}/compras/{ano}/{seq}"
    sit = str(situacao_compra or "").strip()
    n_item = str(numero_item or "").strip()

    if n_item:
        data = _get_json(f"{base}/itens/{n_item}/resultados")
        if data is not None:
            snap = _supplier_snap_from_resultados_payload(
                data, numero_item=n_item, situacao_compra=sit
            )
            if snap.get("cnpj_fornecedor") or snap.get("fornecedor"):
                return _finalize_supplier_snapshot_sync(snap)

        data = _get_json(f"{base}/resultados")
        if data is not None:
            snap = _supplier_snap_from_resultados_payload(
                data, numero_item=n_item, situacao_compra=sit
            )
            if snap.get("cnpj_fornecedor") or snap.get("fornecedor"):
                return _finalize_supplier_snapshot_sync(snap)

        itens_data = _get_json(f"{base}/itens")
        catalog = _find_catalog_row(itens_data, n_item)
        if catalog:
            snap = _extract_supplier_snapshot(catalog)
            if snap.get("cnpj_fornecedor") or snap.get("fornecedor"):
                return _finalize_supplier_snapshot_sync(snap)

        contratos = _fetch_contratos_contratacao_sync(cnpj, ano, seq)
        if contratos is not None:
            snap = _supplier_snap_from_contratos_payload(
                contratos, numero_item=n_item, situacao_compra=sit
            )
            if snap.get("cnpj_fornecedor") or snap.get("fornecedor"):
                out = _finalize_supplier_snapshot_sync(snap)
                out["fornecedor_fonte"] = out.get("fornecedor_fonte") or "pncp_contrato"
                return out
        return _supplier_snapshot_compra_fallback(
            base,
            cnpj=cnpj,
            ano=ano,
            seq=seq,
            situacao_compra=sit,
        )

    return _supplier_snapshot_compra_fallback(
        base,
        cnpj=cnpj,
        ano=ano,
        seq=seq,
        situacao_compra=sit,
    )


def _safe_int_field(v: Any, *, min_v: int, max_v: int) -> Optional[int]:
    try:
        n = int(v)
    except (TypeError, ValueError):
        return None
    if n < min_v or n > max_v:
        return None
    return n


def _numero_item_from_payload(it: Dict[str, Any]) -> str:
    for key in ("numero_item", "numeroItem"):
        n = str(it.get(key) or "").strip()
        if n:
            return n
    return ""


def _supplier_cadastro_dict(it: Dict[str, Any]) -> Dict[str, Any]:
    cad = it.get("fornecedor_cadastro")
    return cad if isinstance(cad, dict) else {}


def _contact_telefone_from_payload(it: Dict[str, Any]) -> str:
    for layer in _supplier_payload_layers(it):
        cad = layer.get("fornecedor_cadastro")
        blobs = [layer]
        if isinstance(cad, dict):
            blobs.append(cad)
        for blob in blobs:
            v = str(
                blob.get("telefone")
                or blob.get("ddd_telefone_1")
                or blob.get("ddd_telefone_2")
                or blob.get("telefone1")
                or blob.get("telefone2")
                or ""
            ).strip()
            if v:
                return v
    return ""


def _contact_email_from_payload(it: Dict[str, Any]) -> str:
    for layer in _supplier_payload_layers(it):
        cad = layer.get("fornecedor_cadastro")
        if isinstance(cad, dict):
            v = str(cad.get("email") or "").strip()
            if v:
                return v
        for k in ("email", "emailFornecedor", "email_fornecedor"):
            v = str(layer.get(k) or "").strip()
            if v:
                return v
    return ""


def _enrich_payload_sort_key(it: Dict[str, Any]) -> Tuple[int, int]:
    """Prioriza itens com resultado/homologação e contato faltante (limite de lookups)."""
    score = 0
    if bool(it.get("temResultado")):
        score += 10
    sit = str(
        it.get("situacaoCompraItemNome")
        or it.get("situacao_compra")
        or it.get("situacao")
        or it.get("situacaoCompraNome")
        or ""
    ).lower()
    if "homolog" in sit:
        score += 5
    if "result" in sit:
        score += 2
    if str(it.get("cnpj_fornecedor") or "").strip():
        score += 1
    if not _payload_supplier_complete(it):
        score += 25
    if not _contact_telefone_from_payload(it):
        score += 4
    if not _contact_email_from_payload(it):
        score += 4
    return (-score, int(re.sub(r"\D", "", str(it.get("numero_item") or it.get("numeroItem") or "0")) or "0"))


def _needs_brasilapi_enrichment(it: Dict[str, Any]) -> bool:
    """Consulta Receita (BrasilAPI) se falta razão social ou contato no cadastro."""
    flatten_supplier_fields_in_payload(it)
    has_cnpj = bool(str(it.get("cnpj_fornecedor") or "").strip())
    if not has_cnpj:
        return False
    if not _fornecedor_tem_nome_util(it):
        return True
    tel = _contact_telefone_from_payload(it)
    email = _contact_email_from_payload(it)
    if tel and email:
        return False
    if str(it.get("fornecedor_contato_fonte") or "").strip() == "brasilapi_cnpj":
        return False
    return not tel or not email


def _payload_supplier_complete(it: Dict[str, Any]) -> bool:
    has_cnpj = bool(str(it.get("cnpj_fornecedor") or "").strip())
    return has_cnpj and _fornecedor_tem_nome_util(it)


def _merge_supplier_snap_into_payload(it: Dict[str, Any], snap: Dict[str, Any]) -> bool:
    """Mescla snapshot PNCP/BrasilAPI no dict do front; retorna True se alterou."""
    if not isinstance(snap, dict):
        return False
    changed = False
    cnpj_f = str(snap.get("cnpj_fornecedor") or "").strip()
    nome_f = str(snap.get("fornecedor") or "").strip()
    if cnpj_f and not str(it.get("cnpj_fornecedor") or "").strip():
        it["cnpj_fornecedor"] = cnpj_f
        changed = True
    if nome_f and not _fornecedor_tem_nome_util(it):
        it["fornecedor"] = nome_f
        changed = True
    cad = snap.get("fornecedor_cadastro")
    if isinstance(cad, dict) and cad:
        prev = it.get("fornecedor_cadastro")
        if not isinstance(prev, dict):
            prev = {}
        merged_cad = {**prev, **cad}
        if merged_cad != prev:
            it["fornecedor_cadastro"] = merged_cad
            changed = True
        if not _contact_telefone_from_payload(it):
            tel = str(
                merged_cad.get("telefone")
                or merged_cad.get("ddd_telefone_1")
                or merged_cad.get("ddd_telefone_2")
                or ""
            ).strip()
            if tel:
                it["telefone"] = tel
                changed = True
        if not _contact_email_from_payload(it):
            em = str(merged_cad.get("email") or "").strip()
            if em:
                it["email"] = em
                changed = True
    if snap.get("fornecedor_fonte_nome") and not str(it.get("fornecedor_fonte_nome") or "").strip():
        it["fornecedor_fonte_nome"] = snap["fornecedor_fonte_nome"]
        changed = True
    if snap.get("fornecedor_fonte") and not str(it.get("fornecedor_fonte") or "").strip():
        it["fornecedor_fonte"] = snap["fornecedor_fonte"]
        changed = True
    contato_fonte = str(snap.get("fornecedor_contato_fonte") or "").strip()
    if contato_fonte and not str(it.get("fornecedor_contato_fonte") or "").strip():
        it["fornecedor_contato_fonte"] = contato_fonte
        changed = True
    if changed:
        it["fornecedor_enriquecido_ao_adicionar"] = True
    return changed


def _apply_brasilapi_enrichment_to_payload(
    it: Dict[str, Any],
    *,
    brasil_cache: Dict[str, tuple[str, Dict[str, Any]]],
    brasil_fetches: int,
    lim_br: int,
) -> tuple[bool, int]:
    """
    Consulta Receita (BrasilAPI) por CNPJ e mescla telefone/e-mail/razão social.
    Retorna (alterou_payload, brasil_fetches_atualizado).
    """
    if not _needs_brasilapi_enrichment(it):
        return False, brasil_fetches
    ck = _cnpj_digits(str(it.get("cnpj_fornecedor") or ""))
    if len(ck) != 14:
        return False, brasil_fetches
    if ck in brasil_cache:
        nome_br, cad_br = brasil_cache[ck]
    elif brasil_fetches < lim_br:
        nome_br, cad_br = fetch_brasilapi_fornecedor_por_cnpj(str(it.get("cnpj_fornecedor") or ""))
        brasil_cache[ck] = (nome_br, cad_br)
        brasil_fetches += 1
    else:
        return False, brasil_fetches
    if not nome_br and not cad_br:
        return False, brasil_fetches
    snap_br: Dict[str, Any] = {
        "cnpj_fornecedor": it.get("cnpj_fornecedor"),
        "fornecedor_cadastro": cad_br,
    }
    if nome_br and not _fornecedor_tem_nome_util(it):
        snap_br["fornecedor"] = nome_br
    if nome_br and not str(it.get("fornecedor_fonte_nome") or "").strip():
        snap_br["fornecedor_fonte_nome"] = "brasilapi_cnpj"
    elif cad_br and not str(it.get("fornecedor_contato_fonte") or "").strip():
        snap_br["fornecedor_contato_fonte"] = "brasilapi_cnpj"
    changed = _merge_supplier_snap_into_payload(it, snap_br)
    return changed, brasil_fetches


def enrich_supplier_fields_in_payloads(
    payloads: Iterable[Dict[str, Any]],
    *,
    max_pncp_lookups: Optional[int] = None,
    max_brasilapi_lookups: Optional[int] = None,
    ignore_add_source_setting: bool = False,
    only_homologated: Optional[bool] = None,
    receitaws_allow_wait: bool = False,
) -> int:
    """
    Passo 3: ao adicionar fonte da busca, consulta PNCP por numero_item se faltar CNPJ/nome.
    Retorna quantidade de lookups PNCP realizados.
    """
    if not ignore_add_source_setting and not getattr(settings, "PNCP_ADD_SOURCE_ENRICH_SUPPLIER", True):
        return 0
    lim_pncp = max_pncp_lookups
    if lim_pncp is None:
        lim_pncp = int(getattr(settings, "PNCP_ADD_SOURCE_MAX_PNCP_LOOKUPS", "48"))
    lim_br = max_brasilapi_lookups
    if lim_br is None:
        lim_br = int(getattr(settings, "PNCP_ADD_SOURCE_MAX_BRASILAPI_LOOKUPS", "96"))

    only_homolog = bool(getattr(settings, "PNCP_ADD_SOURCE_ONLY_HOMOLOGATED", True))
    if only_homologated is not None:
        only_homolog = bool(only_homologated)
    elif ignore_add_source_setting:
        only_homolog = False

    cache: Dict[Tuple[str, int, int, str], Dict[str, Any]] = {}
    brasil_cache: Dict[str, tuple[str, Dict[str, Any]]] = {}
    lookups = 0
    brasil_fetches = 0
    enriched_count = 0

    ordered = [it for it in payloads if isinstance(it, dict)]
    ordered.sort(key=_enrich_payload_sort_key)

    for it in ordered:
        if not isinstance(it, dict):
            continue
        _ensure_pncp_compra_keys(it)
        normalize_pncp_geo_in_payload(it)
        flatten_supplier_fields_in_payload(it)
        if _promote_supplier_from_deep_walk(it):
            enriched_count += 1

        has_cnpj = bool(str(it.get("cnpj_fornecedor") or "").strip())
        if not has_cnpj:
            display = _fornecedor_display_name_from_source(it)
            if _nome_e_somente_cnpj_formatado(display):
                fmt = _normalize_cnpj(_cnpj_digits(display))
                if fmt:
                    it["cnpj_fornecedor"] = fmt
                    has_cnpj = True

        # BrasilAPI (1ª passagem): itens que já têm CNPJ antes do lookup PNCP.
        changed, brasil_fetches = _apply_brasilapi_enrichment_to_payload(
            it,
            brasil_cache=brasil_cache,
            brasil_fetches=brasil_fetches,
            lim_br=lim_br,
        )
        if changed:
            enriched_count += 1

    for it in ordered:
        if not isinstance(it, dict):
            continue
        flatten_supplier_fields_in_payload(it)
        if not _should_attempt_pncp_supplier_lookup(it, only_homolog=only_homolog):
            if not _payload_supplier_complete(it):
                if _promote_supplier_from_deep_walk(it):
                    enriched_count += 1
            continue

        _ensure_pncp_compra_keys(it)
        has_cnpj = bool(str(it.get("cnpj_fornecedor") or "").strip())
        if not has_cnpj:
            display = _fornecedor_display_name_from_source(it)
            if _nome_e_somente_cnpj_formatado(display):
                fmt = _normalize_cnpj(_cnpj_digits(display))
                if fmt:
                    it["cnpj_fornecedor"] = fmt

        np = str(it.get("numero_pncp") or it.get("numeroControlePNCP") or "").strip()
        cnpj_org = _extract_cnpj_orgao(np)
        ano, seq = _ano_seq_for_enrichment(
            numero_pncp=np,
            ano_compra=it.get("ano_compra"),
            sequencial_compra=it.get("sequencial_compra"),
            source=it,
        )
        if ano is not None and it.get("ano_compra") is None:
            it["ano_compra"] = ano
        if seq is not None and it.get("sequencial_compra") is None:
            it["sequencial_compra"] = seq
        if len(cnpj_org) != 14 or ano is None or seq is None:
            if _promote_supplier_from_deep_walk(it):
                enriched_count += 1
            continue

        numero_item = _numero_item_from_payload(it)
        situacao = str(
            it.get("situacao_compra") or it.get("situacao") or it.get("situacaoCompraNome") or ""
        ).strip()
        key = (cnpj_org, int(ano), int(seq), numero_item)
        if key not in cache:
            if lookups >= lim_pncp:
                if _promote_supplier_from_deep_walk(it):
                    enriched_count += 1
                _, brasil_fetches = _apply_brasilapi_enrichment_to_payload(
                    it,
                    brasil_cache=brasil_cache,
                    brasil_fetches=brasil_fetches,
                    lim_br=lim_br,
                )
                continue
            cache[key] = get_contract_supplier_snapshot_sync(
                cnpj_org,
                int(ano),
                int(seq),
                numero_item=numero_item or None,
                situacao_compra=situacao,
            )
            lookups += 1
        snap = cache.get(key) or {}
        if _merge_supplier_snap_into_payload(it, snap):
            enriched_count += 1
        elif not _payload_supplier_complete(it) and _promote_supplier_from_deep_walk(it):
            enriched_count += 1

    # BrasilAPI + varredura final após PNCP.
    for it in ordered:
        if not isinstance(it, dict):
            continue
        flatten_supplier_fields_in_payload(it)
        if _promote_supplier_from_deep_walk(it):
            enriched_count += 1
        changed, brasil_fetches = _apply_brasilapi_enrichment_to_payload(
            it,
            brasil_cache=brasil_cache,
            brasil_fetches=brasil_fetches,
            lim_br=lim_br,
        )
        if changed:
            enriched_count += 1

    lim_rw = receitaws_email_max_lookups()
    rw_state: Dict[str, Any] = {
        "cache": {},
        "http_fetches": 0,
        "max_http_fetches": lim_rw,
        "rate_limited": False,
    }
    if receitaws_allow_wait:
        rw_state["allow_rate_limit_wait"] = True
    for it in ordered:
        if not isinstance(it, dict):
            continue
        if _apply_receitaws_email_enrichment(it, rw_state=rw_state):
            enriched_count += 1

    return enriched_count


def enrich_missing_supplier_fields_for_cotacao(
    cotacao_id: int,
    *,
    max_lookups: int = 12,
    max_brasilapi_lookups: int = 48,
    receitaws_allow_wait: bool = False,
) -> int:
    rows = list(
        PncpCotacaoItemCotacao.objects.filter(cotacao_id=cotacao_id).only(
            "id",
            "numero_pncp",
            "ano_compra",
            "sequencial_compra",
            "numero_item",
            "municipio",
            "uf",
            "source",
        )
    )
    if not rows:
        return 0

    work: List[Tuple[PncpCotacaoItemCotacao, Dict[str, Any]]] = []
    for row in rows:
        src = dict(row.source) if isinstance(row.source, dict) else {}
        merged = {**src}
        np = str(
            row.numero_pncp
            or merged.get("numero_pncp")
            or merged.get("numeroControlePNCP")
            or ""
        ).strip()
        if np:
            merged.setdefault("numero_pncp", np)
        ni = _numero_item_from_row_or_source(row, merged)
        if ni:
            merged.setdefault("numero_item", ni)
        ano, seq = _ano_seq_for_enrichment(
            numero_pncp=np,
            ano_compra=row.ano_compra,
            sequencial_compra=row.sequencial_compra,
            source=merged,
        )
        if ano is not None:
            merged.setdefault("ano_compra", ano)
        if seq is not None:
            merged.setdefault("sequencial_compra", seq)
        flatten_supplier_fields_in_payload(merged)
        work.append((row, merged))

    payloads = [m for _, m in work]
    enrich_supplier_fields_in_payloads(
        payloads,
        max_pncp_lookups=max_lookups,
        max_brasilapi_lookups=max_brasilapi_lookups,
        ignore_add_source_setting=True,
        only_homologated=False,
        receitaws_allow_wait=receitaws_allow_wait,
    )

    updated: List[PncpCotacaoItemCotacao] = []
    for row, merged in work:
        orig = row.source if isinstance(row.source, dict) else {}
        changed = merged != orig
        if changed:
            row.source = merged
        np = str(merged.get("numero_pncp") or merged.get("numeroControlePNCP") or "").strip()
        if np and np != str(row.numero_pncp or "").strip():
            row.numero_pncp = np[:256]
            changed = True
        ano = _safe_int_field(merged.get("ano_compra"), min_v=1990, max_v=2100)
        if ano is not None and row.ano_compra != ano:
            row.ano_compra = ano
            changed = True
        seq = _safe_int_field(merged.get("sequencial_compra"), min_v=1, max_v=2_147_483_647)
        if seq is not None and row.sequencial_compra != seq:
            row.sequencial_compra = seq
            changed = True
        ni = _numero_item_from_row_or_source(row, merged)
        if ni and ni != str(row.numero_item or "").strip():
            row.numero_item = ni[:64]
            changed = True
        mun = str(merged.get("municipio") or "").strip()
        uf = str(merged.get("uf") or "").strip().upper()[:2]
        if mun and not str(row.municipio or "").strip():
            row.municipio = mun[:256]
            changed = True
        if uf and not str(row.uf or "").strip():
            row.uf = uf[:8]
            changed = True
        if changed:
            updated.append(row)

    if updated:
        PncpCotacaoItemCotacao.objects.bulk_update(
            updated,
            ["source", "municipio", "uf", "numero_pncp", "ano_compra", "sequencial_compra", "numero_item"],
            batch_size=500,
        )
        logger.info(
            "fornecedor enriquecido antes do PDF: cotacao_id=%s linhas=%s",
            cotacao_id,
            len(updated),
        )
    return len(updated)
