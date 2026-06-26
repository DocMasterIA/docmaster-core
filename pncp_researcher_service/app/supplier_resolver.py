"""
Resolução de fornecedor vencedor a partir de payloads PNCP (offline / testável).

Fase A do módulo de cobertura de fornecedor — usado por ingestão, cache e pncp_client.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .config import PNCP_SUPPLIER_ELIGIBLE_SITUATIONS, PNCP_SUPPLIER_SKIP_SITUATIONS

_CNPJ_RE = re.compile(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}")

GENERIC_SUPPLIER_NAMES = frozenset(
    {
        "demais",
        "nao informado",
        "não informado",
        "nao informada",
        "não informada",
        "epp",
        "me",
        "mei",
        "outros",
        "n/a",
        "na",
        "n.a",
        "n.a.",
        "nao se aplica",
        "não se aplica",
        "nao aplicavel",
        "não aplicavel",
        "não aplicável",
        "sem fornecedor",
        "nao consta",
        "não consta",
        "inexistente",
        "-",
        "—",
    }
)

SUPPLIER_NAME_KEYS = (
    "fornecedor",
    "razaosocial",
    "razao_social",
    "nomerazaosocialfornecedor",
    "nomeRazaoSocialFornecedor",
    "razaoSocialFornecedor",
    "nome_fornecedor",
    "fornecedor_nome",
    "vencedor",
)

CNPJ_KEYS = (
    "cnpj",
    "cnpjfornecedor",
    "cnpjcpffornecedor",
    "nifornecedor",
    "ni_fornecedor",
    "cnpjFornecedor",
    "niFornecedor",
)


@dataclass
class SupplierResolution:
    cnpj_fornecedor: str = ""
    fornecedor: str = ""
    fornecedor_fonte: str = ""
    fornecedor_elegivel: bool = False
    situacao_item: str = ""
    situacao_compra: str = ""
    fornecedor_cadastro: Dict[str, Any] = field(default_factory=dict)
    valor_unitario_homologado: Optional[float] = None
    valor_total_homologado: Optional[float] = None
    quantidade_homologada: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def cnpj_digits(raw: Any) -> str:
    return re.sub(r"\D", "", str(raw or ""))


def normalize_cnpj(raw: Any) -> str:
    d = cnpj_digits(raw)
    if len(d) != 14:
        return ""
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:14]}"


def nome_fornecedor_e_util(nome: str) -> bool:
    s = re.sub(r"\s+", " ", str(nome or "").strip()).lower()
    if not s or len(s) < 3:
        return False
    if s in GENERIC_SUPPLIER_NAMES:
        return False
    if s.startswith("pncp_"):
        return False
    if _CNPJ_RE.fullmatch(s.replace(" ", "")) or len(cnpj_digits(s)) == 14:
        return False
    return True


def _fornecedor_nomes_no_item(it: Dict[str, Any]) -> List[str]:
    names: List[str] = []
    if not isinstance(it, dict):
        return names
    for key in (*SUPPLIER_NAME_KEYS, "fornecedor_nome", "nome_fornecedor"):
        v = str(it.get(key) or "").strip()
        if v:
            names.append(v)
    cad = it.get("fornecedor_cadastro")
    if isinstance(cad, dict):
        for k in ("razao_social", "nome_fantasia", "razaoSocial", "nomeFantasia"):
            v = str(cad.get(k) or "").strip()
            if v:
                names.append(v)
    return names


def item_fornecedor_tem_cnpj_para_salvar(it: Dict[str, Any]) -> bool:
    """Cotação no backend exige CNPJ de fornecedor (14 dígitos)."""
    if not isinstance(it, dict):
        return False
    cnpj = cnpj_digits(
        it.get("cnpj_fornecedor")
        or it.get("cnpjFornecedor")
        or it.get("niFornecedor")
        or it.get("cnpj")
        or ""
    )
    return len(cnpj) == 14


def item_fornecedor_valido_para_busca(it: Dict[str, Any]) -> bool:
    """
    Resultado exibível na pesquisa de preços: CNPJ de fornecedor (14 dígitos)
    ou razão social útil — rejeita placeholders como «Não se aplica».
    """
    if not isinstance(it, dict):
        return False
    cnpj = cnpj_digits(
        it.get("cnpj_fornecedor")
        or it.get("cnpjFornecedor")
        or it.get("niFornecedor")
        or it.get("cnpj")
        or ""
    )
    if len(cnpj) == 14:
        return True
    names = _fornecedor_nomes_no_item(it)
    if not names:
        return False
    return any(nome_fornecedor_e_util(n) for n in names)


def _fonte_sufixada(prefix: str, sufixo: str) -> str:
    """Evita sufixo duplicado quando o prefixo já termina com _item / _compra."""
    p = str(prefix or "").strip().rstrip("_")
    s = str(sufixo or "").strip().lstrip("_")
    if not p:
        return s
    if p.endswith(f"_{s}"):
        return p
    return f"{p}_{s}"


def _situacao_lower(value: Any) -> str:
    return str(value or "").strip().lower()


def situacao_contem_any(situacao: str, tokens: Iterable[str]) -> bool:
    sit = _situacao_lower(situacao)
    if not sit:
        return False
    return any(tok.strip().lower() in sit for tok in tokens if tok.strip())


def compra_elegivel(situacao_compra: Any) -> bool:
    sit = str(situacao_compra or "").strip()
    if not sit:
        return False
    if situacao_contem_any(sit, PNCP_SUPPLIER_SKIP_SITUATIONS):
        return False
    return situacao_contem_any(sit, PNCP_SUPPLIER_ELIGIBLE_SITUATIONS)


def item_homologado_para_busca(
    item_row: Optional[Dict[str, Any]],
    *,
    situacao_compra: Any = "",
) -> bool:
    """
    Critério de exibição na busca de preços: somente homologado/adjudicado (não «Em andamento»).
    `temResultado` sozinho não basta — no PNCP costuma vir 204 em /resultados mesmo assim.
    """
    if not isinstance(item_row, dict):
        return False
    sit_item = str(
        item_row.get("situacaoCompraItemNome")
        or item_row.get("situacaoCompraItem")
        or item_row.get("situacaoItemNome")
        or ""
    ).strip().lower()
    if situacao_contem_any(sit_item, PNCP_SUPPLIER_SKIP_SITUATIONS):
        return False
    if situacao_contem_any(sit_item, ("homolog", "adjudic")):
        return True
    sit_compra = str(
        situacao_compra
        or item_row.get("situacao_compra")
        or item_row.get("situacao")
        or item_row.get("situacaoCompraNome")
        or ""
    ).strip().lower()
    if situacao_contem_any(sit_compra, PNCP_SUPPLIER_SKIP_SITUATIONS):
        return False
    return situacao_contem_any(sit_compra, PNCP_SUPPLIER_ELIGIBLE_SITUATIONS)


def item_elegivel(item_row: Optional[Dict[str, Any]], *, situacao_compra: Any = "") -> bool:
    if not isinstance(item_row, dict):
        return compra_elegivel(situacao_compra)
    if bool(item_row.get("temResultado")):
        return True
    sit_item = str(
        item_row.get("situacaoCompraItemNome")
        or item_row.get("situacaoCompraItem")
        or item_row.get("situacaoItemNome")
        or ""
    ).strip()
    if situacao_contem_any(sit_item, PNCP_SUPPLIER_SKIP_SITUATIONS):
        return False
    if situacao_contem_any(sit_item, PNCP_SUPPLIER_ELIGIBLE_SITUATIONS):
        return True
    if "result" in _situacao_lower(sit_item):
        return True
    return compra_elegivel(situacao_compra)


def is_orgao_path(path: str) -> bool:
    p = (path or "").lower()
    if not p:
        return False
    blocked_tokens = ("orgaoentidade", "orgao_entidade", "unidadeorgao", "unidade_orgao")
    if any(tok in p for tok in blocked_tokens):
        return True
    parts = [x for x in re.split(r"[.\[\]]+", p) if x]
    return any(part in {"orgao", "unidadeorgao", "orgaoentidade"} for part in parts)


def walk_supplier_candidates(
    obj: Any, *, path: str = "", acc: Optional[List[Dict[str, str]]] = None
) -> List[Dict[str, str]]:
    if acc is None:
        acc = []
    if isinstance(obj, dict):
        nome = ""
        cnpj = ""
        for k, v in obj.items():
            kk = str(k or "").strip().lower()
            vv = str(v or "").strip()
            if not vv:
                continue
            if any(x in kk for x in SUPPLIER_NAME_KEYS) and len(vv) > 2:
                nome = vv
            if any(x in kk for x in CNPJ_KEYS):
                m = _CNPJ_RE.search(vv)
                if m:
                    cnpj = m.group()
                else:
                    d = cnpj_digits(vv)
                    if len(d) == 14:
                        cnpj = d
        if nome or cnpj:
            acc.append({"path": path, "fornecedor": nome, "cnpj": cnpj})
        for k, v in obj.items():
            nxt = f"{path}.{k}" if path else str(k)
            walk_supplier_candidates(v, path=nxt, acc=acc)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk_supplier_candidates(v, path=f"{path}[{i}]", acc=acc)
    return acc


def extract_supplier_cnpj_only(payload: Any) -> str:
    for cand in walk_supplier_candidates(payload):
        if is_orgao_path(cand.get("path", "")):
            continue
        cj = normalize_cnpj(cand.get("cnpj", ""))
        if cj:
            return cj
    return ""


def extract_best_supplier_from_payload(payload: Any) -> Dict[str, str]:
    """Melhor par CNPJ + nome no JSON (exclui contexto de órgão comprador)."""
    cands = walk_supplier_candidates(payload)
    best: Optional[Dict[str, str]] = None
    for cand in cands:
        if is_orgao_path(cand.get("path", "")):
            continue
        cnpj = normalize_cnpj(cand.get("cnpj", ""))
        nome = str(cand.get("fornecedor") or "").strip()
        nome_ok = nome_fornecedor_e_util(nome)
        if cnpj and nome_ok:
            return {"cnpj_fornecedor": cnpj, "fornecedor": nome}
        if cnpj and not best:
            best = {"cnpj_fornecedor": cnpj, "fornecedor": nome if nome_ok else ""}
        elif nome_ok and not best:
            best = {"cnpj_fornecedor": "", "fornecedor": nome}
    return best or {"cnpj_fornecedor": "", "fornecedor": ""}


def iter_resultado_entries(payload: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        rows = payload["data"]
    elif isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = [payload]
    else:
        return
    for row in rows:
        if isinstance(row, dict):
            yield row


_ITEM_NUMERO_KEYS = (
    "numeroItem",
    "ordemItem",
    "sequencialItem",
    "numeroItemCompra",
    "numeroItemContratacao",
    "itemNumero",
)


def _numero_item_match(row: Dict[str, Any], numero_item: str) -> bool:
    want = str(numero_item or "").strip()
    if not want:
        return False
    for key in _ITEM_NUMERO_KEYS:
        got = str(row.get(key) or "").strip()
        if got == want:
            return True
    return False


def resolve_from_resultados_payload(
    payload: Any,
    *,
    numero_item: Optional[str] = None,
    situacao_compra: Any = "",
    fonte_prefix: str = "pncp_resultado",
) -> SupplierResolution:
    """Extrai vencedor de /resultados ou /itens/{n}/resultados."""
    entries = list(iter_resultado_entries(payload))
    situacao_item = ""
    if numero_item and entries:
        for row in entries:
            if _numero_item_match(row, numero_item):
                snap = extract_best_supplier_from_payload(row)
                situacao_item = str(
                    row.get("situacaoCompraItemNome") or row.get("situacaoItemNome") or ""
                ).strip()
                if snap.get("cnpj_fornecedor") or snap.get("fornecedor") or _row_has_homolog_pricing(row):
                    return _build_resolution(
                        snap,
                        fonte=_fonte_sufixada(fonte_prefix, "item"),
                        situacao_item=situacao_item,
                        situacao_compra=situacao_compra,
                        item_row=row,
                    )
    for row in entries:
        snap = extract_best_supplier_from_payload(row)
        if snap.get("cnpj_fornecedor") or snap.get("fornecedor") or _row_has_homolog_pricing(row):
            situacao_item = str(
                row.get("situacaoCompraItemNome") or row.get("situacaoItemNome") or ""
            ).strip()
            fonte = _fonte_sufixada(fonte_prefix, "compra")
            if numero_item and _numero_item_match(row, numero_item):
                fonte = _fonte_sufixada(fonte_prefix, "item")
            return _build_resolution(
                snap,
                fonte=fonte,
                situacao_item=situacao_item,
                situacao_compra=situacao_compra,
                item_row=row,
            )
    if not entries and payload is not None and isinstance(payload, dict):
        snap = extract_best_supplier_from_payload(payload)
        if snap.get("cnpj_fornecedor") or snap.get("fornecedor") or _row_has_homolog_pricing(payload):
            return _build_resolution(
                snap,
                fonte=fonte_prefix,
                situacao_compra=situacao_compra,
                item_row=payload,
            )
    return SupplierResolution(situacao_compra=str(situacao_compra or "").strip())


def resolve_from_contratos_payload(
    payload: Any,
    *,
    numero_item: Optional[str] = None,
    situacao_compra: Any = "",
) -> SupplierResolution:
    """Extrai fornecedor de GET /contratos/contratacao/{ano}/{seq}."""
    return resolve_from_resultados_payload(
        payload,
        numero_item=numero_item,
        situacao_compra=situacao_compra,
        fonte_prefix="pncp_contrato",
    )


def resolve_from_item_catalog_row(
    item_row: Dict[str, Any],
    *,
    situacao_compra: Any = "",
) -> SupplierResolution:
    """Campos inline no GET /itens (sem /resultados)."""
    snap = extract_best_supplier_from_payload(item_row)
    if not snap.get("cnpj_fornecedor"):
        for key in ("niFornecedor", "cnpjFornecedor", "cnpjCpfFornecedor", "ni_fornecedor"):
            cj = normalize_cnpj(item_row.get(key))
            if cj:
                snap["cnpj_fornecedor"] = cj
                break
    if not snap.get("fornecedor"):
        for key in ("nomeRazaoSocialFornecedor", "razaoSocialFornecedor", "nomeFornecedor"):
            nome = str(item_row.get(key) or "").strip()
            if nome_fornecedor_e_util(nome):
                snap["fornecedor"] = nome
                break
    if not snap.get("cnpj_fornecedor") and not snap.get("fornecedor"):
        return SupplierResolution(
            situacao_item=str(
                item_row.get("situacaoCompraItemNome") or item_row.get("situacaoCompraItem") or ""
            ).strip(),
            situacao_compra=str(situacao_compra or "").strip(),
        )
    return _build_resolution(
        snap,
        fonte="pncp_item_inline",
        situacao_item=str(
            item_row.get("situacaoCompraItemNome") or item_row.get("situacaoCompraItem") or ""
        ).strip(),
        situacao_compra=situacao_compra,
        item_row=item_row,
    )


def merge_with_cadastro(
    resolution: SupplierResolution,
    *,
    nome: str,
    cadastro: Optional[Dict[str, Any]] = None,
    fonte_nome: str = "brasilapi",
) -> SupplierResolution:
    """Preenche razão social a partir de cache/BrasilAPI quando só há CNPJ."""
    out = SupplierResolution(
        cnpj_fornecedor=resolution.cnpj_fornecedor,
        fornecedor=resolution.fornecedor,
        fornecedor_fonte=resolution.fornecedor_fonte,
        fornecedor_elegivel=resolution.fornecedor_elegivel,
        situacao_item=resolution.situacao_item,
        situacao_compra=resolution.situacao_compra,
        fornecedor_cadastro=dict(resolution.fornecedor_cadastro or {}),
    )
    nome_s = str(nome or "").strip()
    if nome_s and nome_fornecedor_e_util(nome_s) and not nome_fornecedor_e_util(out.fornecedor):
        out.fornecedor = nome_s
        if out.fornecedor_fonte and "brasilapi" not in out.fornecedor_fonte:
            out.fornecedor_fonte = f"{out.fornecedor_fonte}+{fonte_nome}"
        else:
            out.fornecedor_fonte = fonte_nome
    if cadastro:
        out.fornecedor_cadastro = {k: v for k, v in cadastro.items() if v}
    return out


def _apply_homolog_pricing_to_resolution(
    res: SupplierResolution,
    item_row: Optional[Dict[str, Any]],
) -> SupplierResolution:
    if not isinstance(item_row, dict):
        return res
    pricing = extract_homologated_pricing(item_row)
    vu = pricing.get("valor_unitario_homologado")
    vt = pricing.get("valor_total_homologado")
    qh = pricing.get("quantidade_homologada")
    if vu is not None:
        res.valor_unitario_homologado = vu
    if vt is not None:
        res.valor_total_homologado = vt
    if qh is not None:
        res.quantidade_homologada = qh
    return res


def _row_has_homolog_pricing(row: Dict[str, Any]) -> bool:
    p = extract_homologated_pricing(row)
    return p.get("valor_unitario_homologado") is not None or p.get("valor_total_homologado") is not None


def _build_resolution(
    snap: Dict[str, str],
    *,
    fonte: str,
    situacao_item: str = "",
    situacao_compra: Any = "",
    item_row: Optional[Dict[str, Any]] = None,
) -> SupplierResolution:
    elegivel = item_elegivel(item_row, situacao_compra=situacao_compra)
    res = SupplierResolution(
        cnpj_fornecedor=str(snap.get("cnpj_fornecedor") or "").strip(),
        fornecedor=str(snap.get("fornecedor") or "").strip(),
        fornecedor_fonte=fonte,
        fornecedor_elegivel=elegivel,
        situacao_item=situacao_item,
        situacao_compra=str(situacao_compra or "").strip(),
    )
    return _apply_homolog_pricing_to_resolution(res, item_row)


def extract_item_numbers_prioritized(items_payload: Any, *, max_items: int = 8) -> List[str]:
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
        score = score_item_for_supplier_fetch(it)
        scored.append((score, n))
    scored.sort(key=lambda x: (-x[0], int(cnpj_digits(x[1]) or 0)))
    out: List[str] = []
    for _, n in scored:
        if n not in out:
            out.append(n)
        if len(out) >= max_items:
            break
    return out


def score_item_for_supplier_fetch(item_row: Dict[str, Any]) -> int:
    score = 0
    if bool(item_row.get("temResultado")):
        score += 5
    sit = str(item_row.get("situacaoCompraItemNome") or item_row.get("situacaoCompraItem") or "").lower()
    if "homolog" in sit:
        score += 3
    if "result" in sit:
        score += 1
    if "adjudic" in sit:
        score += 2
    return score


def parse_brasilapi_to_fornecedor(payload: Dict[str, Any], *, cnpj_digits_val: str) -> Tuple[str, Dict[str, Any]]:
    razao = str(payload.get("razao_social") or "").strip()
    fantasia = str(payload.get("nome_fantasia") or "").strip()
    nome = razao or fantasia
    porte_raw = payload.get("porte")
    if isinstance(porte_raw, dict):
        porte_txt = str(porte_raw.get("descricao") or porte_raw.get("descricaoPorte") or "").strip()
    else:
        porte_txt = str(porte_raw or "").strip()
    cadastro: Dict[str, Any] = {
        "cnpj": normalize_cnpj(cnpj_digits_val),
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


def item_numero_from_row(row: Dict[str, Any]) -> str:
    """Número do item no catálogo ou resultado PNCP."""
    for key in _ITEM_NUMERO_KEYS:
        got = str(row.get(key) or "").strip()
        if got:
            return got
    return ""


def _optional_float(val: Any) -> Optional[float]:
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def extract_homologated_pricing(row: Optional[Dict[str, Any]]) -> Dict[str, Optional[float]]:
    """Preço homologado a partir de GET /resultados ou campos inline no /itens."""
    if not isinstance(row, dict):
        return {
            "valor_unitario_homologado": None,
            "valor_total_homologado": None,
            "quantidade_homologada": None,
        }
    return {
        "valor_unitario_homologado": _optional_float(row.get("valorUnitarioHomologado")),
        "valor_total_homologado": _optional_float(row.get("valorTotalHomologado")),
        "quantidade_homologada": _optional_float(row.get("quantidadeHomologada")),
    }


def item_row_needs_resultado_fetch(item_row: Dict[str, Any]) -> bool:
    """True se o item provavelmente tem preço homologado fora do GET /itens."""
    if extract_homologated_pricing(item_row)["valor_unitario_homologado"] is not None:
        return False
    if extract_homologated_pricing(item_row)["valor_total_homologado"] is not None:
        return False
    if bool(item_row.get("temResultado")):
        return True
    return item_homologado_para_busca(item_row)


def index_resultados_by_numero_item(payload: Any) -> Dict[str, Dict[str, Any]]:
    """Agrupa linhas de /resultados por numeroItem (preferência ordemClassificacaoSrp=1)."""
    out: Dict[str, Dict[str, Any]] = {}
    for row in iter_resultado_entries(payload):
        ni = item_numero_from_row(row)
        if not ni:
            continue
        prev = out.get(ni)
        if prev is None:
            out[ni] = row
            continue
        prev_rank = int(prev.get("ordemClassificacaoSrp") or 99)
        row_rank = int(row.get("ordemClassificacaoSrp") or 99)
        if row_rank < prev_rank:
            out[ni] = row
    return out


def find_catalog_item_row(items_payload: Any, numero_item: str) -> Optional[Dict[str, Any]]:
    """Localiza a linha do GET /itens pelo numero_item."""
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


def resolution_to_api_dict(res: SupplierResolution) -> Dict[str, Any]:
    """Formato consumido por busca/cotação (`cnpj_fornecedor`, `fornecedor`, preço homologado, …)."""
    out: Dict[str, Any] = {
        "cnpj_fornecedor": res.cnpj_fornecedor,
        "fornecedor": res.fornecedor,
        "fornecedor_cadastro": dict(res.fornecedor_cadastro or {}),
    }
    if res.valor_unitario_homologado is not None:
        out["valor_unitario_homologado"] = res.valor_unitario_homologado
        out["valor_unitario"] = res.valor_unitario_homologado
    if res.valor_total_homologado is not None:
        out["valor_total_homologado"] = res.valor_total_homologado
        if res.valor_unitario_homologado is None:
            out["valor_total"] = res.valor_total_homologado
    if res.quantidade_homologada is not None:
        out["quantidade_homologada"] = res.quantidade_homologada
    if res.fornecedor_fonte:
        out["fornecedor_fonte"] = res.fornecedor_fonte
        if res.fornecedor and "brasilapi" not in res.fornecedor_fonte:
            out["fornecedor_fonte_nome"] = res.fornecedor_fonte
        elif res.fornecedor:
            out["fornecedor_fonte_nome"] = res.fornecedor_fonte
    if res.fornecedor_elegivel:
        out["fornecedor_elegivel"] = True
    return out


def resolve_item_supplier_offline(
    *,
    item_row: Optional[Dict[str, Any]] = None,
    resultados_item_payload: Any = None,
    resultados_compra_payload: Any = None,
    contratos_payload: Any = None,
    situacao_compra: Any = "",
    numero_item: Optional[str] = None,
    cadastro_nome: str = "",
    cadastro: Optional[Dict[str, Any]] = None,
) -> SupplierResolution:
    """
    Ordem: resultados item → resultados compra → contratos da contratação → inline catálogo.
    Opcionalmente merge com nome/cadastro já resolvido (cache BrasilAPI).
    """
    sit_compra = str(situacao_compra or "").strip()
    n_item = str(numero_item or "").strip()
    if not n_item and isinstance(item_row, dict):
        n_item = str(
            item_row.get("numeroItem") or item_row.get("ordemItem") or item_row.get("sequencialItem") or ""
        ).strip()

    if resultados_item_payload is not None:
        res = resolve_from_resultados_payload(
            resultados_item_payload,
            numero_item=n_item or None,
            situacao_compra=sit_compra,
            fonte_prefix="pncp_resultado_item",
        )
        if res.cnpj_fornecedor or res.fornecedor:
            return merge_with_cadastro(res, nome=cadastro_nome, cadastro=cadastro)

    if resultados_compra_payload is not None:
        res = resolve_from_resultados_payload(
            resultados_compra_payload,
            numero_item=n_item or None,
            situacao_compra=sit_compra,
            fonte_prefix="pncp_resultado_compra",
        )
        if res.cnpj_fornecedor or res.fornecedor:
            return merge_with_cadastro(res, nome=cadastro_nome, cadastro=cadastro)

    if contratos_payload is not None:
        res = resolve_from_contratos_payload(
            contratos_payload,
            numero_item=n_item or None,
            situacao_compra=sit_compra,
        )
        if res.cnpj_fornecedor or res.fornecedor:
            return merge_with_cadastro(res, nome=cadastro_nome, cadastro=cadastro)

    if isinstance(item_row, dict):
        res = resolve_from_item_catalog_row(item_row, situacao_compra=sit_compra)
        if res.cnpj_fornecedor or res.fornecedor:
            return merge_with_cadastro(res, nome=cadastro_nome, cadastro=cadastro)

    empty = SupplierResolution(situacao_compra=sit_compra)
    if isinstance(item_row, dict):
        empty.situacao_item = str(
            item_row.get("situacaoCompraItemNome") or item_row.get("situacaoCompraItem") or ""
        ).strip()
        empty.fornecedor_elegivel = item_elegivel(item_row, situacao_compra=sit_compra)
    return merge_with_cadastro(empty, nome=cadastro_nome, cadastro=cadastro)
