"""
Agrupamento de linhas `PncpCotacaoItem` em itens de pesquisa de preços (relatório).

Cada item do relatório corresponde a um conjunto de cotações (fontes) sobre o mesmo
produto — alinhado ao layout «relatorio-pesquisa-precos» (Resultado consolidado +
Detalhamento com tabela Fonte / Fornecedor / CNPJ / …). A composição do preço
esperada segue a lógica de múltiplas fontes por item (ex.: mínimo 3 cotações para
situação «Válido»).
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple

from django.utils import timezone

from backend.app.services.pncp_supplier_enrichment import (
    _nome_e_somente_cnpj_formatado,
    _promote_supplier_from_deep_walk,
    _supplier_payload_layers,
    fetch_brasilapi_fornecedor_por_cnpj,
    fetch_receitaws_email_por_cnpj,
    flatten_supplier_fields_in_payload,
    receitaws_email_fallback_enabled,
    receitaws_email_max_lookups,
)

# Mínimo de cotações (fontes) por item para marcar situação como válida (IN 65 / prática comum).
MIN_FONTES_SITUACAO_VALIDA = 3

# BrasilAPI/minha-receita não expõe e-mail corporativo (privacidade anti-spam).
EMAIL_INDISPONIVEL_RF = "Não divulgado pela Receita Federal"

_CNPJ_LOOSE = re.compile(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}")

FORMULA_LABELS: Dict[str, str] = {
    "media_aritmetica_precos_obtidos": "Média aritmética dos preços obtidos",
    "mediana_precos_obtidos": "Mediana dos preços obtidos",
    "menor_preco": "Menor preço",
    "media_saneada": "Média saneada",
    "media_ponderada": "Média ponderada",
    "media_relativa_25_50": "Média relativa 25% - 50%",
}


def _normalize_cnpj(raw: str) -> str:
    d = re.sub(r"\D", "", raw)
    if len(d) != 14:
        return raw.strip()
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:14]}"


def _walk_cnpjs(obj: Any, acc: set) -> None:
    if isinstance(obj, dict):
        for v in obj.values():
            _walk_cnpjs(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            _walk_cnpjs(v, acc)
    elif isinstance(obj, str):
        for m in _CNPJ_LOOSE.finditer(obj):
            acc.add(_normalize_cnpj(m.group()))


def _primeiro_cnpj_no_json(obj: Any) -> str:
    acc: set = set()
    _walk_cnpjs(obj, acc)
    return sorted(acc)[0] if acc else "—"


def _inteiro_milhar_br(inteiro_sem_frac: str) -> str:
    """Formata parte inteira com pontos de milhar (ex.: 85082 -> 85.082)."""
    s = str(inteiro_sem_frac or "").strip()
    if not s:
        return "0"
    neg = s.startswith("-")
    if neg:
        s = s[1:]
    if not s.isdigit():
        return inteiro_sem_frac
    parts: List[str] = []
    while len(s) > 3:
        parts.append(s[-3:])
        s = s[:-3]
    parts.append(s)
    body = ".".join(reversed(parts))
    return f"-{body}" if neg else body


def _formatar_moeda_br(v: Any) -> str:
    """Valor em pt-BR: milhar com ponto, decimais com vírgula (ex.: R$ 85.082,26)."""
    if v is None:
        return "—"
    try:
        n = float(v)
    except (TypeError, ValueError):
        return "—"
    if math.isnan(n) or math.isinf(n):
        return "—"
    neg = n < 0
    n_abs = abs(n)
    s = f"{n_abs:.2f}"
    inteiro, frac = s.split(".")
    inteiro_fmt = _inteiro_milhar_br(inteiro)
    body = f"{inteiro_fmt},{frac}"
    return f"-{body}" if neg else body


def _fmt_quantidade(q: Any) -> str:
    if q is None:
        return "—"
    try:
        f = float(q)
    except (TypeError, ValueError):
        return str(q)[:32]
    if math.isnan(f) or math.isinf(f):
        return "—"
    if abs(f - round(f)) < 1e-9:
        return str(int(round(f)))
    return f"{f:.2f}".replace(".", ",")


def preco_unitario_cotacao_fonte(it: Any, *, quantidade_item: Optional[float] = None) -> Optional[float]:
    """
    Preço unitário na fonte/inciso para um registro de cotação (ORM ou dict).
    Prioriza valor_unitario; senão valor_total / quantidade (item da sessão, depois quantidade da linha).
    Retorna None quando não há como inferir (na agregação por item, tratar como 0 na média).
    """

    def _get(key: str) -> Any:
        if isinstance(it, dict):
            return it.get(key)
        return getattr(it, key, None)

    vu = _get("valor_unitario")
    try:
        fvu = float(vu) if vu is not None else None
    except (TypeError, ValueError):
        fvu = None
    if fvu is not None and fvu > 0 and not (math.isnan(fvu) or math.isinf(fvu)):
        return fvu

    vt = _get("valor_total")
    try:
        fvt = float(vt) if vt is not None else None
    except (TypeError, ValueError):
        fvt = None
    if fvt is None or fvt <= 0 or math.isnan(fvt) or math.isinf(fvt):
        return None

    if quantidade_item is not None:
        try:
            fq = float(quantidade_item)
            if fq > 0 and not math.isnan(fq) and not math.isinf(fq):
                return fvt / fq
        except (TypeError, ValueError):
            pass

    q_line = _get("quantidade")
    if q_line is not None:
        try:
            fq = float(q_line)
            if fq > 0 and not math.isnan(fq) and not math.isinf(fq):
                return fvt / fq
        except (TypeError, ValueError):
            pass

    return None


def _valor_numerico_item(it: Any, *, quantidade_base: Optional[float] = None) -> Optional[float]:
    vt = getattr(it, "valor_total", None)
    if vt is not None:
        try:
            fvt = float(vt)
        except (TypeError, ValueError):
            fvt = None
        if fvt is not None and not (math.isnan(fvt) or math.isinf(fvt)):
            return fvt

    vu = getattr(it, "valor_unitario", None)
    try:
        fvu = float(vu)
    except (TypeError, ValueError):
        return None
    if math.isnan(fvu) or math.isinf(fvu):
        return None

    q_candidates: List[Any] = [quantidade_base, getattr(it, "quantidade", None)]
    for q in q_candidates:
        if q is None:
            continue
        try:
            fq = float(q)
        except (TypeError, ValueError):
            continue
        if math.isnan(fq) or math.isinf(fq) or fq <= 0:
            continue
        return fvu * fq
    return None


def _chave_grupo_item(it: Any) -> Tuple[str, str, str, str]:
    """Identifica o mesmo produto na cotação (várias fontes aglutinadas)."""
    ni = (getattr(it, "numero_item", None) or "").strip()
    if ni:
        return ("num", ni, "", "")
    desc = (getattr(it, "descricao_item", None) or "").strip()[:4000]
    und = (getattr(it, "unidade_medida", None) or "").strip()[:64]
    q = getattr(it, "quantidade", None)
    qk = ""
    if q is not None:
        try:
            qk = f"{float(q):.6g}"
        except (TypeError, ValueError):
            qk = str(q)[:32]
    return ("desc", desc, und, qk)


def _pick_source(src: Dict[str, Any], *keys: str, default: str = "—") -> str:
    for k in keys:
        v = src.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return default


def _pick_descricao_fonte_pncp(it: Any, src: Dict[str, Any]) -> str:
    """
    Descrição/título do item na fonte PNCP (não confundir com descricao_item do item manual da cotação).
    Prioriza campos do payload PNCP em ``source``; usa coluna ORM só como fallback.
    """
    if not isinstance(src, dict):
        src = {}
    for key in (
        "descricao",
        "descricaoItem",
        "descricao_item",
        "objeto_resumido",
        "objetoResumido",
        "objetoCompra",
        "material_servico",
        "materialOuServicoNome",
        "titulo",
    ):
        v = _pick_source(src, key, default="")
        if v and v != "—":
            return v[:500]
    row_desc = str(getattr(it, "descricao_item", None) or "").strip()
    return row_desc[:500] if row_desc else "—"


def _iter_source_pairs(obj: Any, prefix: str = ""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = str(k or "")
            path = f"{prefix}.{key}" if prefix else key
            yield path, key, v
            yield from _iter_source_pairs(v, path)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            path = f"{prefix}[{i}]"
            yield from _iter_source_pairs(v, path)


def _looks_orgao_context(path: str) -> bool:
    p = (path or "").lower()
    if not p:
        return False
    blocked_tokens = ("orgaoentidade", "orgao_entidade", "unidadeorgao", "unidade_orgao")
    if any(x in p for x in blocked_tokens):
        return True
    parts = [x for x in re.split(r"[.\[\]]+", p) if x]
    return any(part in {"orgao", "orgaoentidade", "unidadeorgao"} for part in parts)


_SUPPLIER_NAME_TOP_KEYS = (
    "fornecedor",
    "nomeRazaoSocialFornecedor",
    "razaoSocialFornecedor",
    "razao_social",
    "nome_fornecedor",
    "fornecedor_nome",
)

_SUPPLIER_NAME_META_KEYS = frozenset(
    {
        "fornecedor_fonte",
        "fornecedor_fonte_nome",
        "fornecedor_elegivel",
        "fornecedor_origem_indice",
        "fornecedor_enriquecido_ao_adicionar",
        "fornecedor_cadastro",
        "fornecedor_hibrido_live",
        "fornecedor_busca_pncp",
    }
)


def _supplier_name_key_is_metadata(key: str) -> bool:
    k = str(key or "").strip().lower()
    if k in _SUPPLIER_NAME_META_KEYS:
        return True
    return k.startswith("fornecedor_fonte")


def nome_fornecedor_e_util_para_exibicao(nome: str) -> bool:
    """Nome legível (não placeholder PNCP nem o próprio CNPJ no campo de razão social)."""
    n = str(nome or "").strip()
    if len(n) <= 2:
        return False
    low = re.sub(r"\s+", " ", n).strip().lower()
    if low in {"demais", "nao informado", "não informado", "epp", "me", "mei", "outros"}:
        return False
    if low.startswith("pncp_"):
        return False
    if _nome_e_somente_cnpj_formatado(n):
        return False
    return True


def _coerce_positive_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def _item_parece_homologado_mesmo_sem_fornecedor_no_json(src: Dict[str, Any]) -> bool:
    """Evita rotular homologado como «compra em andamento» quando só faltou snapshot de fornecedor."""
    if src.get("temResultado") is True or src.get("item_homologado") is True:
        return True
    for k in (
        "valor_unitario_homologado",
        "valorUnitarioHomologado",
        "valor_total_homologado",
        "valorTotalHomologado",
    ):
        if _coerce_positive_float(src.get(k)) is not None:
            return True
    sit_item = str(
        _pick_source(
            src,
            "situacaoCompraItemNome",
            "situacao_item",
            "situacaoCompraItem",
            default="",
        )
        or ""
    ).strip().lower()
    return bool(sit_item and any(tok in sit_item for tok in ("homolog", "adjudic", "result")))


def _fonte_pncp_em_andamento_sem_fornecedor(src: Dict[str, Any]) -> bool:
    """Compra/item ainda sem vencedor publicado no PNCP (ex.: «Em andamento», temResultado=false)."""
    if _pick_supplier_cnpj_from_source(src) or _pick_supplier_name_from_source(src):
        return False
    if _item_parece_homologado_mesmo_sem_fornecedor_no_json(src):
        return False
    tem = src.get("temResultado")
    if tem is False:
        return True
    if src.get("item_homologado") is False:
        return True
    sit_item = str(
        _pick_source(
            src,
            "situacaoCompraItemNome",
            "situacao_item",
            "situacaoCompraItem",
            default="",
        )
        or ""
    ).strip().lower()
    if sit_item:
        if any(tok in sit_item for tok in ("homolog", "adjudic", "result")):
            return False
        if any(tok in sit_item for tok in ("andamento", "abert", "publicad", "receb", "julg", "disputa")):
            return True
    sit_compra = str(
        _pick_source(
            src,
            "situacao",
            "situacao_compra",
            "situacaoCompraNome",
            default="",
        )
        or ""
    ).strip().lower()
    if sit_compra and not sit_item:
        if any(tok in sit_compra for tok in ("andamento", "abert", "publicad", "receb", "julg", "disputa")):
            return True
        if any(tok in sit_compra for tok in ("homolog", "adjudic", "result")):
            return False
    return False


def _fornecedor_exibicao_relatorio(
    src: Dict[str, Any],
    *,
    fornecedor: str,
    cnpj_fornecedor: str,
    supplier_name_by_cnpj: Optional[Dict[str, str]] = None,
) -> str:
    if fornecedor:
        return fornecedor
    if cnpj_fornecedor and supplier_name_by_cnpj:
        nome = str(supplier_name_by_cnpj.get(cnpj_fornecedor) or "").strip()
        if nome_fornecedor_e_util_para_exibicao(nome):
            return nome
    if _fonte_pncp_em_andamento_sem_fornecedor(src):
        return "Sem fornecedor homologado (compra em andamento)"
    return "Não informado"


def _cnpj_exibicao_relatorio(src: Dict[str, Any], cnpj_fornecedor: str) -> str:
    if cnpj_fornecedor:
        return cnpj_fornecedor
    if _fonte_pncp_em_andamento_sem_fornecedor(src):
        return "—"
    return "Não informado"


def _pick_supplier_name_from_source(src: Dict[str, Any]) -> str:
    cad = src.get("fornecedor_cadastro")
    if isinstance(cad, dict):
        for k in ("razao_social", "nome_fantasia", "razaoSocial", "nomeFantasia"):
            v = str(cad.get(k) or "").strip()
            if nome_fornecedor_e_util_para_exibicao(v):
                return v
    # Não parar no primeiro campo preenchido: «fornecedor» costuma repetir o CNPJ
    # enquanto nomeRazaoSocialFornecedor / razaoSocial trazem a razão social.
    for k in _SUPPLIER_NAME_TOP_KEYS:
        v = src.get(k)
        if v is None:
            continue
        s = str(v).strip()
        if nome_fornecedor_e_util_para_exibicao(s):
            return s
    # Busca aninhada por chaves de fornecedor, sem cair em contexto de órgão.
    for path, key, value in _iter_source_pairs(src):
        if _looks_orgao_context(path):
            continue
        if _supplier_name_key_is_metadata(key):
            continue
        k = key.lower()
        if any(t in k for t in ("fornecedor", "razaosocial", "razao_social", "nomefornecedor", "nome_fornecedor")):
            s = str(value or "").strip()
            if nome_fornecedor_e_util_para_exibicao(s):
                return s
    return ""


def _pick_supplier_cnpj_from_source(src: Dict[str, Any]) -> str:
    raw = _pick_source(
        src,
        "cnpj_fornecedor",
        "cnpjCpfFornecedor",
        "niFornecedor",
        "ni_fornecedor",
        "niFornecedorSubContratado",
        "ni_fornecedor_subcontratado",
        "cnpjFornecedor",
        "cnpj",
        default="",
    ).strip()
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 14:
        return _normalize_cnpj(digits)
    # Busca aninhada por CNPJ/NI de fornecedor, excluindo contexto de órgão.
    for path, key, value in _iter_source_pairs(src):
        if _looks_orgao_context(path):
            continue
        k = key.lower()
        if not any(t in k for t in ("cnpj", "nifornecedor", "ni_fornecedor", "cnpjcpf", "fornecedor")):
            continue
        d = re.sub(r"\D", "", str(value or ""))
        if len(d) == 14:
            return _normalize_cnpj(d)
    return ""


def _build_supplier_name_index(rows: List[Any]) -> Dict[str, str]:
    """
    Índice local CNPJ fornecedor -> nome fornecedor, sem usar órgão comprador.
    """
    idx: Dict[str, str] = {}
    for r in rows or []:
        src = _source_efetivo_linha_cotacao(r)
        flatten_supplier_fields_in_payload(src)
        _promote_supplier_from_deep_walk(src)
        cnpj = _pick_supplier_cnpj_from_source(src)
        nome = _pick_supplier_name_from_source(src)
        if cnpj and nome and nome_fornecedor_e_util_para_exibicao(nome):
            idx[cnpj] = nome
    return idx


def _supplier_cadastro_dict(src: Dict[str, Any]) -> Dict[str, Any]:
    cad = src.get("fornecedor_cadastro")
    return cad if isinstance(cad, dict) else {}


def formatar_telefone_br(raw: Any) -> str:
    """Formata DDD+número (10 ou 11 dígitos) para exibição no relatório."""
    d = re.sub(r"\D", "", str(raw or ""))
    if len(d) == 10:
        return f"({d[:2]}) {d[2:6]}-{d[6:]}"
    if len(d) == 11:
        return f"({d[:2]}) {d[2:7]}-{d[7:]}"
    return str(raw or "").strip()


def formatar_email_exibicao_relatorio(email: Any) -> str:
    em = str(email or "").strip()
    return em if em and em != "—" else EMAIL_INDISPONIVEL_RF


def _email_contato_ausente(email: Any) -> bool:
    em = str(email or "").strip()
    return not em or em == "—" or em == EMAIL_INDISPONIVEL_RF


def _completar_email_receitaws_pdf(
    *,
    cnpj_fornecedor: str,
    email: str,
    state: Optional[Dict[str, Any]],
) -> str:
    """Cache por CNPJ na requisição; respeita max_lookups em state."""
    em = str(email or "").strip()
    if not _email_contato_ausente(em) or not state:
        return em if not _email_contato_ausente(em) else ""
    d = re.sub(r"\D", "", str(cnpj_fornecedor or ""))
    if len(d) != 14:
        return em
    cache: Dict[str, str] = state.setdefault("cache", {})
    if d in cache:
        return cache[d] or em
    max_l = int(state.get("max_lookups") or 0)
    n = int(state.get("fetches") or 0)
    if max_l <= 0 or n >= max_l:
        cache[d] = ""
        return em
    fetched = fetch_receitaws_email_por_cnpj(d)
    state["fetches"] = n + 1
    cache[d] = fetched
    return fetched or em


def _pick_supplier_telefone_from_source(src: Dict[str, Any]) -> str:
    tel_keys = ("telefone", "ddd_telefone_1", "ddd_telefone_2", "telefone1", "telefone2")
    for layer in _supplier_payload_layers(src):
        cad = layer.get("fornecedor_cadastro")
        blobs: List[Any] = [layer]
        if isinstance(cad, dict):
            blobs.append(cad)
        for blob in blobs:
            if not isinstance(blob, dict):
                continue
            for k in tel_keys:
                v = str(blob.get(k) or "").strip()
                if v and v != "—":
                    return formatar_telefone_br(v)
    return ""


def _pick_supplier_email_from_source(src: Dict[str, Any]) -> str:
    email_keys = ("email", "emailFornecedor", "email_fornecedor")
    for layer in _supplier_payload_layers(src):
        cad = layer.get("fornecedor_cadastro")
        if isinstance(cad, dict):
            v = str(cad.get("email") or "").strip()
            if v and v != "—":
                return v
        for k in email_keys:
            v = str(layer.get(k) or "").strip()
            if v and v != "—":
                return v
    return ""


def _endereco_de_source(src: Dict[str, Any]) -> str:
    for blob in (_supplier_cadastro_dict(src), src):
        partes: List[str] = []
        for k in ("logradouro", "numero", "complemento", "bairro", "municipio", "uf", "cep"):
            v = str(blob.get(k) or "").strip()
            if v:
                partes.append(v)
        if partes:
            return ", ".join(partes)[:400]
    v = _pick_source(src, "endereco", "enderecoCompleto", "endereco_completo", default="")
    return (v or "")[:400]


def _format_municipio_uf(municipio: Any, uf: Any) -> str:
    mun = str(municipio or "").strip()
    sigla = str(uf or "").strip()
    if mun and sigla:
        return f"{mun}/{sigla}"
    return mun or sigla or ""


_MUNICIPIO_NOME_KEYS = frozenset(
    {"municipio", "municipionome", "municipio_nome", "nomemunicipio", "cidade", "localidade"}
)
_UF_SIGLA_KEYS = frozenset({"uf", "ufsigla", "uf_sigla", "siglauf", "sigla_uf"})


def _pick_localidade_from_source(src: Dict[str, Any]) -> tuple[str, str]:
    """Município/UF em source PNCP (inclui unidadeOrgao aninhado)."""
    mun = ""
    uf = ""
    if not isinstance(src, dict):
        return mun, uf
    for k in ("municipio", "municipioNome", "municipio_nome", "cidade"):
        v = src.get(k)
        if v is not None and str(v).strip():
            mun = str(v).strip()
            break
    for k in ("uf", "ufSigla", "uf_sigla", "siglaUf"):
        v = src.get(k)
        if v is not None and str(v).strip():
            uf = str(v).strip().upper()[:2]
            break
    for _path, key, value in _iter_source_pairs(src):
        kl = str(key or "").lower()
        if not mun and kl in _MUNICIPIO_NOME_KEYS:
            s = str(value or "").strip()
            if len(s) >= 2 and not s.isdigit():
                mun = s
        if not uf and kl in _UF_SIGLA_KEYS:
            s = str(value or "").strip().upper()
            if len(s) == 2 and s.isalpha():
                uf = s
        if mun and uf:
            break
    return mun, uf


def _resolve_municipio_uf_para_fonte(
    municipio: Any,
    uf: Any,
    src: Dict[str, Any],
) -> tuple[str, str]:
    """ORM + source PNCP (topo e unidadeOrgao aninhado)."""
    mun = str(municipio or "").strip()
    sigla = str(uf or "").strip().upper()[:2] if str(uf or "").strip() else ""
    if not mun or not sigla:
        sm, su = _pick_localidade_from_source(src)
        mun = mun or sm
        sigla = sigla or su
    return mun, sigla


def _format_orgao_com_local(orgao: Any, municipio: Any, uf: Any) -> str:
    """Ex.: «Porto Alegre/RS - Secretaria da Saúde»."""
    org = str(orgao or "").strip()
    if org in {"—", "-"}:
        org = ""
    local = _format_municipio_uf(municipio, uf)
    if local and org:
        return f"{local} - {org}"
    if local:
        return local
    return org or "—"


def _completar_contato_brasilapi_se_faltar(
    *,
    cnpj_fornecedor: str,
    telefone: str,
    email: str,
    cache: Dict[str, Dict[str, Any]],
) -> tuple[str, str]:
    """Consulta BrasilAPI (cache por CNPJ na requisição) quando falta tel/e-mail no source."""
    tel = str(telefone or "").strip()
    em = str(email or "").strip()
    if tel and em:
        return tel, em
    d = re.sub(r"\D", "", str(cnpj_fornecedor or ""))
    if len(d) != 14:
        return tel, em
    if d not in cache:
        _, cad = fetch_brasilapi_fornecedor_por_cnpj(d)
        cache[d] = cad if isinstance(cad, dict) else {}
    cad = cache.get(d) or {}
    if not tel:
        tel = str(
            cad.get("telefone")
            or cad.get("ddd_telefone_1")
            or cad.get("ddd_telefone_2")
            or ""
        ).strip()
    if not em:
        em = str(cad.get("email") or "").strip()
    return tel, em


def _source_efetivo_linha_cotacao(it: Any) -> Dict[str, Any]:
    """Mescla colunas ORM com JSON `source` antes de extrair fornecedor."""
    src: Dict[str, Any] = dict(getattr(it, "source", None) or {})
    if not isinstance(src, dict):
        src = {}
    np = str(getattr(it, "numero_pncp", None) or "").strip()
    if np:
        src.setdefault("numero_pncp", np)
    ni = str(getattr(it, "numero_item", None) or "").strip()
    if ni:
        src.setdefault("numero_item", ni)
    ano = getattr(it, "ano_compra", None)
    if ano is not None:
        src.setdefault("ano_compra", ano)
    seq = getattr(it, "sequencial_compra", None)
    if seq is not None:
        src.setdefault("sequencial_compra", seq)
    return src


def fonte_dict_de_item(
    it: Any,
    *,
    tz,
    supplier_name_by_cnpj: Optional[Dict[str, str]] = None,
    quantidade_item_base: Optional[float] = None,
    brasilapi_cache: Optional[Dict[str, Dict[str, Any]]] = None,
    receitaws_pdf_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """Uma linha ORM → uma linha da tabela «fontes» do detalhamento."""
    src = _source_efetivo_linha_cotacao(it)
    flatten_supplier_fields_in_payload(src)
    _promote_supplier_from_deep_walk(src)

    tipo = (getattr(it, "modalidade", None) or "").strip()
    if not tipo:
        tipo = _pick_source(src, "tipo", "fonte", "origem", "tipoFonte", default="")
    tipo = (tipo or "PNCP")[:120]

    cnpj_fornecedor = _pick_supplier_cnpj_from_source(src)
    fornecedor = _pick_supplier_name_from_source(src)
    fornecedor = _fornecedor_exibicao_relatorio(
        src,
        fornecedor=fornecedor,
        cnpj_fornecedor=cnpj_fornecedor,
        supplier_name_by_cnpj=supplier_name_by_cnpj,
    )
    cnpj = _cnpj_exibicao_relatorio(src, cnpj_fornecedor)

    created = getattr(it, "created_at", None)
    data_str = "—"
    if created is not None:
        data_str = timezone.localtime(created, tz).strftime("%d/%m/%Y")

    pu = preco_unitario_cotacao_fonte(it, quantidade_item=quantidade_item_base)
    if pu is not None:
        valor = f"R$ {_formatar_moeda_br(pu)}"
        if _fonte_pncp_em_andamento_sem_fornecedor(src):
            valor = f"{valor} (estimado)"
    else:
        valor = "—"

    mun, uf = _resolve_municipio_uf_para_fonte(
        getattr(it, "municipio", None),
        getattr(it, "uf", None),
        src,
    )
    municipio_uf = _format_municipio_uf(mun, uf) or "—"
    orgao = _format_orgao_com_local(getattr(it, "orgao", None), mun, uf)[:200]

    processo = _pick_source(src, "processo", "numeroControlePNCP")
    if processo == "—":
        processo = (getattr(it, "numero_pncp", None) or "").strip() or "—"

    ajuste = _pick_source(src, "ajuste", "observacao_frete", "frete", default="Sem frete")

    telefone = _pick_supplier_telefone_from_source(src)
    email = _pick_supplier_email_from_source(src)
    if brasilapi_cache is not None and cnpj_fornecedor and (not telefone or _email_contato_ausente(email)):
        telefone, email = _completar_contato_brasilapi_se_faltar(
            cnpj_fornecedor=cnpj_fornecedor,
            telefone=telefone,
            email=email if not _email_contato_ausente(email) else "",
            cache=brasilapi_cache,
        )
    if receitaws_pdf_state is not None and cnpj_fornecedor and _email_contato_ausente(email):
        email = _completar_email_receitaws_pdf(
            cnpj_fornecedor=cnpj_fornecedor,
            email=email,
            state=receitaws_pdf_state,
        )
    if telefone:
        telefone = formatar_telefone_br(telefone)
    email = formatar_email_exibicao_relatorio(email)
    endereco = _endereco_de_source(src)
    descricao_fonte = _pick_descricao_fonte_pncp(it, src)

    return {
        "tipo": tipo[:120],
        "descricao_fonte": descricao_fonte,
        "fornecedor": fornecedor[:400],
        "cnpj": cnpj[:32],
        "data": data_str,
        "valor": valor[:32],
        "quantidade": _fmt_quantidade(getattr(it, "quantidade", None)),
        "orgao": orgao,
        "municipio_uf": municipio_uf[:120],
        "processo": str(processo)[:120],
        "ajuste": ajuste[:120],
        "telefone": telefone[:64],
        "email": email[:255],
        "endereco": endereco,
    }


def _receitaws_state_if_enabled(*, receitaws_email_fallback: bool) -> Optional[Dict[str, Any]]:
    if not receitaws_email_fallback or not receitaws_email_fallback_enabled():
        return None
    max_l = receitaws_email_max_lookups()
    if max_l <= 0:
        return None
    return {"cache": {}, "fetches": 0, "max_lookups": max_l}


def agrupar_itens_relatorio_pesquisa_precos(
    itens: List[Any],
    *,
    receitaws_email_fallback: bool = False,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Retorna lista de grupos (ordenada por menor id no grupo) e total de linhas importadas.

    Cada grupo vira um «Item N» no PDF com N cotações (fontes) na sub-tabela.
    """
    if not itens:
        return [], 0

    tz = timezone.get_current_timezone()
    total_linhas = len(itens)
    brasilapi_cache: Dict[str, Dict[str, Any]] = {}
    receitaws_pdf_state = _receitaws_state_if_enabled(receitaws_email_fallback=receitaws_email_fallback)

    buckets: Dict[Tuple[str, str, str, str], List[Any]] = {}
    order_keys: List[Tuple[str, str, str, str]] = []

    for it in itens:
        key = _chave_grupo_item(it)
        if key not in buckets:
            buckets[key] = []
            order_keys.append(key)
        buckets[key].append(it)

    grupos: List[Dict[str, Any]] = []
    for ordem, key in enumerate(order_keys, start=1):
        members = buckets[key]
        members.sort(key=lambda x: int(getattr(x, "pk", 0) or 0))
        supplier_name_idx = _build_supplier_name_index(members)

        first = members[0]
        nome = (getattr(first, "descricao_item", None) or "—")[:500]
        q_fmt = _fmt_quantidade(getattr(first, "quantidade", None))
        und = (getattr(first, "unidade_medida", None) or "—")[:64]

        try:
            q_first = float(getattr(first, "quantidade", None)) if getattr(first, "quantidade", None) is not None else None
            if q_first is not None and (math.isnan(q_first) or math.isinf(q_first) or q_first <= 0):
                q_first = None
        except (TypeError, ValueError):
            q_first = None

        n_fontes = len(members)
        unit_slots: List[float] = []
        for x in members:
            pu = preco_unitario_cotacao_fonte(x, quantidade_item=q_first)
            unit_slots.append(0.0 if pu is None else float(pu))
        vals = unit_slots
        media_valor: Optional[float] = (sum(unit_slots) / n_fontes) if n_fontes else None
        media_fmt = f"R$ {_formatar_moeda_br(media_valor)}" if media_valor is not None else "—"

        n_cot = len(members)
        if n_cot >= MIN_FONTES_SITUACAO_VALIDA:
            situacao = "Válido"
        else:
            situacao = f"Insuficiente ({n_cot} de {MIN_FONTES_SITUACAO_VALIDA} fontes)"

        fontes = [
            fonte_dict_de_item(
                m,
                tz=tz,
                supplier_name_by_cnpj=supplier_name_idx,
                quantidade_item_base=q_first,
                brasilapi_cache=brasilapi_cache,
                receitaws_pdf_state=receitaws_pdf_state,
            )
            for m in members
        ]

        grupos.append(
            {
                "ordem": ordem,
                "nome": nome,
                "quantidade_fmt": q_fmt,
                "unidade": und,
                "n_cotacoes": n_cot,
                "valores_fontes": vals,
                "media_valor": media_valor,
                "media_fmt": media_fmt,
                "situacao": situacao,
                "fontes": fontes,
            }
        )

    return grupos, total_linhas


def agrupar_cotacoes_por_item_relatorio_pesquisa_precos(
    itens: List[Any],
    cotacoes: List[Any],
    *,
    receitaws_email_fallback: bool = False,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Novo fluxo: item manual + múltiplas cotações vinculadas.

    - `itens`: linhas de PncpCotacaoItem (ordem/base visual do relatório).
    - `cotacoes`: linhas de PncpCotacaoItemCotacao vinculadas aos itens.

    Por item: valor médio = média aritmética dos preços unitários por fonte (fonte sem preço conta 0).
    A «Fórmula de Cálculo» da sessão aplica-se no resumo entre itens (resumo_calculo_precos), não dentro da linha.
    """
    if not itens:
        return [], 0

    tz = timezone.get_current_timezone()
    total_linhas = len(cotacoes or [])
    brasilapi_cache: Dict[str, Dict[str, Any]] = {}
    receitaws_pdf_state = _receitaws_state_if_enabled(receitaws_email_fallback=receitaws_email_fallback)
    cotacoes_por_item: Dict[int, List[Any]] = defaultdict(list)
    for c in cotacoes or []:
        item_id = getattr(c, "item_id", None)
        if item_id is None:
            continue
        cotacoes_por_item[int(item_id)].append(c)

    grupos: List[Dict[str, Any]] = []
    for ordem, it in enumerate(itens, start=1):
        item_id = int(getattr(it, "id", 0) or 0)
        members = sorted(cotacoes_por_item.get(item_id, []), key=lambda x: int(getattr(x, "pk", 0) or 0))
        supplier_name_idx = _build_supplier_name_index(members)

        nome = (getattr(it, "descricao_item", None) or "—")[:500]
        und = (getattr(it, "unidade_medida", None) or "").strip()[:64]

        qtd_item = getattr(it, "quantidade", None)
        try:
            qtd_item_f = float(qtd_item) if qtd_item is not None else None
            if qtd_item_f is not None and (math.isnan(qtd_item_f) or math.isinf(qtd_item_f) or qtd_item_f <= 0):
                qtd_item_f = None
        except (TypeError, ValueError):
            qtd_item_f = None

        n_fontes = len(members)
        unit_slots: List[float] = []
        for x in members:
            pu = preco_unitario_cotacao_fonte(x, quantidade_item=qtd_item_f)
            unit_slots.append(0.0 if pu is None else float(pu))
        vals = unit_slots
        valor_calc = (sum(unit_slots) / n_fontes) if n_fontes else None
        valor_fmt = f"R$ {_formatar_moeda_br(valor_calc)}" if valor_calc is not None else "—"

        quantidades: List[float] = []
        for m in members:
            q = getattr(m, "quantidade", None)
            if q is None:
                continue
            try:
                fq = float(q)
            except (TypeError, ValueError):
                continue
            if math.isnan(fq) or math.isinf(fq):
                continue
            quantidades.append(fq)

        if qtd_item_f is not None and qtd_item_f > 0:
            qtd_refletida: Any = qtd_item_f
        elif quantidades:
            qtd_refletida = Counter(quantidades).most_common(1)[0][0]
        else:
            qtd_refletida = getattr(it, "quantidade", None)
        q_fmt = _fmt_quantidade(qtd_refletida)
        if not und:
            und = ((getattr(members[0], "unidade_medida", None) if members else None) or "—")[:64]

        n_cot = len(members)
        if n_cot >= MIN_FONTES_SITUACAO_VALIDA:
            situacao = "Válido"
        else:
            situacao = f"Insuficiente ({n_cot} de {MIN_FONTES_SITUACAO_VALIDA} fontes)"

        fontes = [
            fonte_dict_de_item(
                m,
                tz=tz,
                supplier_name_by_cnpj=supplier_name_idx,
                quantidade_item_base=qtd_item_f,
                brasilapi_cache=brasilapi_cache,
                receitaws_pdf_state=receitaws_pdf_state,
            )
            for m in members
        ]
        grupos.append(
            {
                "ordem": ordem,
                "nome": nome,
                "quantidade_fmt": q_fmt,
                "unidade": und or "—",
                "n_cotacoes": n_cot,
                "valores_fontes": vals,
                "media_valor": valor_calc,
                "media_fmt": valor_fmt,
                "situacao": situacao,
                "fontes": fontes,
            }
        )

    return grupos, total_linhas


def resumo_calculo_media_aritmetica(grupos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Resumo do cálculo institucional:
    - fórmula aplicada;
    - média das médias por item;
    - faixa (mín/max) das médias por item.
    """
    medias = []
    for g in grupos or []:
        mv = g.get("media_valor")
        try:
            f = float(mv)
        except (TypeError, ValueError):
            continue
        if math.isnan(f) or math.isinf(f):
            continue
        medias.append(f)

    media_geral = (sum(medias) / len(medias)) if medias else None
    return {
        "formula_id": "media_aritmetica_precos_obtidos",
        "formula_label": "Média aritmética dos preços obtidos",
        "itens_com_media": len(medias),
        "media_das_medias": media_geral,
        "media_das_medias_fmt": f"R$ {_formatar_moeda_br(media_geral)}" if media_geral is not None else "—",
        "menor_media_item": min(medias) if medias else None,
        "menor_media_item_fmt": f"R$ {_formatar_moeda_br(min(medias))}" if medias else "—",
        "maior_media_item": max(medias) if medias else None,
        "maior_media_item_fmt": f"R$ {_formatar_moeda_br(max(medias))}" if medias else "—",
    }


def _percentile(sorted_vals: List[float], p: float) -> Optional[float]:
    if not sorted_vals:
        return None
    if p <= 0:
        return sorted_vals[0]
    if p >= 1:
        return sorted_vals[-1]
    idx = (len(sorted_vals) - 1) * p
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    if lo == hi:
        return sorted_vals[lo]
    frac = idx - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def _resumo_from_values(
    values: List[float],
    *,
    formula_id: str,
    valor_calculado: Optional[float],
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    extra = extra or {}
    return {
        "formula_id": formula_id,
        "formula_label": FORMULA_LABELS.get(formula_id, FORMULA_LABELS["media_aritmetica_precos_obtidos"]),
        "itens_com_media": len(values),
        "media_das_medias": valor_calculado,
        "media_das_medias_fmt": f"R$ {_formatar_moeda_br(valor_calculado)}" if valor_calculado is not None else "—",
        "menor_media_item": min(values) if values else None,
        "menor_media_item_fmt": f"R$ {_formatar_moeda_br(min(values))}" if values else "—",
        "maior_media_item": max(values) if values else None,
        "maior_media_item_fmt": f"R$ {_formatar_moeda_br(max(values))}" if values else "—",
        **extra,
    }


def _valor_formula_em_lista(values: List[float], formula_id: str) -> Optional[float]:
    if not values:
        return None
    s = sorted(values)
    if formula_id == "mediana_precos_obtidos":
        n = len(s)
        if n % 2 == 1:
            return s[n // 2]
        return (s[n // 2 - 1] + s[n // 2]) / 2
    if formula_id == "menor_preco":
        return min(s)
    if formula_id == "media_saneada":
        cut = int(len(s) * 0.2)
        saneados = s[cut : len(s) - cut] if len(s) - (2 * cut) >= 1 else s
        return sum(saneados) / len(saneados)
    if formula_id == "media_relativa_25_50":
        p25 = _percentile(s, 0.25)
        p50 = _percentile(s, 0.50)
        if p25 is None or p50 is None:
            return None
        faixa = [x for x in s if p25 <= x <= p50]
        if not faixa:
            faixa = [p25, p50]
        return sum(faixa) / len(faixa)
    # media_aritmetica_precos_obtidos e media_ponderada (peso uniforme por fonte)
    return sum(s) / len(s)


def resumo_calculo_precos(grupos: List[Dict[str, Any]], formula_id: str) -> Dict[str, Any]:
    """
    Agrega com a fórmula selecionada a lista de **médias de preço unitário por item**
    (cada `media_valor` já é média aritmética dos unitários por fonte, com ausência=0).
    """
    medias: List[float] = []
    pesos: List[float] = []
    for g in grupos or []:
        mv = g.get("media_valor")
        try:
            f = float(mv)
        except (TypeError, ValueError):
            continue
        if math.isnan(f) or math.isinf(f):
            continue
        medias.append(f)
        nc = g.get("n_cotacoes")
        try:
            p = float(nc)
        except (TypeError, ValueError):
            p = 1.0
        if math.isnan(p) or math.isinf(p) or p <= 0:
            p = 1.0
        pesos.append(p)

    if not medias:
        return _resumo_from_values([], formula_id=formula_id, valor_calculado=None)

    if formula_id == "media_ponderada":
        total_peso = sum(pesos) or 1.0
        val = sum(v * w for v, w in zip(medias, pesos)) / total_peso
        return _resumo_from_values(medias, formula_id=formula_id, valor_calculado=val)

    if formula_id == "media_saneada":
        s = sorted(medias)
        cut = int(len(s) * 0.2)
        saneados = s[cut : len(s) - cut] if len(s) - (2 * cut) >= 1 else s
        val = sum(saneados) / len(saneados)
        return _resumo_from_values(
            medias,
            formula_id=formula_id,
            valor_calculado=val,
            extra={"itens_saneados_utilizados": len(saneados)},
        )

    if formula_id == "media_relativa_25_50":
        s = sorted(medias)
        p25 = _percentile(s, 0.25)
        p50 = _percentile(s, 0.50)
        if p25 is None or p50 is None:
            val = None
            faixa: List[float] = []
        else:
            faixa = [x for x in s if p25 <= x <= p50]
            if not faixa:
                faixa = [p25, p50]
            val = sum(faixa) / len(faixa)
        return _resumo_from_values(
            medias,
            formula_id=formula_id,
            valor_calculado=val,
            extra={
                "p25_fmt": f"R$ {_formatar_moeda_br(p25)}" if p25 is not None else "—",
                "p50_fmt": f"R$ {_formatar_moeda_br(p50)}" if p50 is not None else "—",
                "itens_faixa_25_50": len(faixa),
            },
        )

    val = _valor_formula_em_lista(medias, formula_id)
    return _resumo_from_values(medias, formula_id=formula_id, valor_calculado=val)


def texto_orgao_capa_prefeitura_cotacao(cotacao: Any, usuario: Any) -> str:
    """
    Texto institucional para o campo «Órgão» na capa do relatório:
    prefeitura vinculada à cotação (snapshot multi-tenant) ou, se ausente, a do usuário.
    """
    from backend.app.models.prefeitura import Prefeitura

    pref = getattr(cotacao, "prefeitura", None)
    if pref is None:
        pid = getattr(cotacao, "prefeitura_id", None)
        if pid:
            pref = Prefeitura.objects.filter(pk=pid).only("nome_municipio", "estado").first()
    if pref is None:
        pref = getattr(usuario, "prefeitura", None)
    if pref is None:
        uid = getattr(usuario, "prefeitura_id", None)
        if uid:
            pref = Prefeitura.objects.filter(pk=uid).only("nome_municipio", "estado").first()
    if pref is None:
        return ""
    nome = str(getattr(pref, "nome_municipio", "") or "").strip()
    if not nome:
        return ""
    uf = str(getattr(pref, "estado", "") or "").strip()
    base = f"Prefeitura Municipal de {nome}"
    return f"{base} ({uf})" if uf else base


def texto_orgao_exibicao_relatorio_pesquisa_precos(
    cotacao: Any, usuario: Any, grupos: List[Dict[str, Any]]
) -> str:
    """Órgão na capa: prefeitura cadastrada; se não houver, primeira fonte com órgão preenchido."""
    capa = texto_orgao_capa_prefeitura_cotacao(cotacao, usuario)
    if capa:
        return capa
    for g in grupos:
        fontes = g.get("fontes") or []
        if fontes:
            org = str((fontes[0] or {}).get("orgao") or "").strip()
            if org:
                return org
    return "—"
