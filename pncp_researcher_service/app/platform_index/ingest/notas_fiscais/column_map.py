"""
Mapeamento CSV Portal da Transparência (Notas Fiscais) → platform_index.

Views mensais:
  NotaFiscal      — cabeçalho + EVENTO MAIS RECENTE (join)
  NotaFiscalItem  — item + VALOR UNITÁRIO (tabela-mãe da busca)
  NotaFiscalEvento — opcional / frequentemente vazio
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

REQUIRED_NOTA_HEADER_GROUPS: Tuple[Tuple[str, ...], ...] = (
    ("chave_de_acesso",),
    ("evento_mais_recente",),
    ("data_emissao",),
)

REQUIRED_ITEM_HEADER_GROUPS: Tuple[Tuple[str, ...], ...] = (
    ("chave_de_acesso",),
    ("numero_produto",),
    ("descricao_do_produto_servico",),
    ("valor_unitario",),
    ("quantidade",),
    ("unidade",),
)

REQUIRED_NOTA_HEADERS: Tuple[str, ...] = tuple(g[0] for g in REQUIRED_NOTA_HEADER_GROUPS)
REQUIRED_ITEM_HEADERS: Tuple[str, ...] = tuple(g[0] for g in REQUIRED_ITEM_HEADER_GROUPS)

# Eventos da Nota que autorizam entrada no índice.
AUTHORIZED_EVENT_MARKERS: Tuple[str, ...] = (
    "autorizacao de uso",
    "autorizacao",
)

# Eventos / valores que excluem a nota.
REJECT_EVENT_MARKERS: Tuple[str, ...] = (
    "sem informacao",
    "cancelamento",
    "cancelada",
    "deneg",
)


def normalize_header(name: str) -> str:
    s = unicodedata.normalize("NFKD", str(name or ""))
    s = s.encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()
    return s


def normalize_row_keys(row: Dict[str, Any]) -> Dict[str, Any]:
    return {normalize_header(k): v for k, v in (row or {}).items()}


def _pick(row: Dict[str, Any], aliases: Iterable[str]) -> Optional[str]:
    for alias in aliases:
        key = normalize_header(alias)
        val = row.get(key)
        if val is None:
            continue
        s = str(val).strip()
        if s and s.lower() not in {"null", "none", "nan", "-1"}:
            if s.lower() in {"sem informacao", "sem informação"}:
                continue
            return s
    return None


def _pick_float(row: Dict[str, Any], aliases: Iterable[str]) -> Optional[float]:
    raw = _pick(row, aliases)
    if raw is None:
        return None
    cleaned = raw.replace("R$", "").replace(" ", "").strip()
    if not cleaned:
        return None
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        n = float(cleaned)
        return n if n >= 0 else None
    except ValueError:
        return None


def _cnpj_digits(v: Optional[str]) -> Optional[str]:
    if not v:
        return None
    digits = "".join(ch for ch in str(v) if ch.isdigit())
    if len(digits) == 14:
        return digits
    # CPF (11) — não usar como CNPJ de fornecedor na cotação.
    return None


def _norm_text(s: Optional[str]) -> str:
    if not s:
        return ""
    t = unicodedata.normalize("NFKD", str(s))
    t = t.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", t).strip().lower()


def normalize_unidade(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    s = str(raw).strip()
    key = _norm_text(s)
    aliases = {
        "unidad": "UN",
        "un": "UN",
        "unid": "UN",
        "unidade": "UN",
        "pc": "PC",
        "peca": "PC",
        "pecas": "PC",
        "kg": "KG",
        "l": "L",
        "lt": "L",
        "litro": "L",
        "cx": "CX",
        "caixa": "CX",
    }
    return aliases.get(key, s.upper()[:20])


def parse_data_emissao(raw: Optional[str]) -> Optional[str]:
    """DD/MM/YYYY[ HH:MM:SS] → YYYY-MM-DD (ISO date)."""
    if not raw:
        return None
    s = str(raw).strip()
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})", s)
    if not m:
        return s[:10] if s else None
    d, mo, y = m.group(1), m.group(2), m.group(3)
    return f"{y}-{mo}-{d}"


def missing_required_header_groups(
    headers: Sequence[str],
    groups: Sequence[Sequence[str]],
) -> List[str]:
    have: Set[str] = {normalize_header(h) for h in headers}
    missing: List[str] = []
    for group in groups:
        aliases = [normalize_header(a) for a in group]
        if not any(a in have for a in aliases):
            missing.append(group[0])
    return missing


def validate_nota_headers(headers: Sequence[str]) -> Dict[str, Any]:
    missing = missing_required_header_groups(headers, REQUIRED_NOTA_HEADER_GROUPS)
    return {
        "ok": not missing,
        "view": "NotaFiscal",
        "missing_required": missing,
        "headers_normalized": sorted({normalize_header(h) for h in headers}),
    }


def validate_item_headers(headers: Sequence[str]) -> Dict[str, Any]:
    missing = missing_required_header_groups(headers, REQUIRED_ITEM_HEADER_GROUPS)
    return {
        "ok": not missing,
        "view": "NotaFiscalItem",
        "missing_required": missing,
        "headers_normalized": sorted({normalize_header(h) for h in headers}),
    }


def build_processo_id(chave: str) -> str:
    return f"notas_fiscais:{chave}"


def build_plataforma_item_id(chave: str, numero_produto: str) -> str:
    return f"notas_fiscais:{chave}:{numero_produto}"


def build_url_origem(chave: str) -> str:
    """Deep-link provisório pela chave (portal / consulta pública)."""
    return f"https://portaldatransparencia.gov.br/notas-fiscais?chave={chave}"


def evento_autoriza_ingest(evento: Optional[str]) -> bool:
    """True se a nota pode alimentar o índice."""
    n = _norm_text(evento)
    if not n:
        return False
    if any(m in n for m in REJECT_EVENT_MARKERS):
        return False
    return any(m in n for m in AUTHORIZED_EVENT_MARKERS)


def map_nota_row(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    r = normalize_row_keys(row)
    chave = _pick(r, ("chave_de_acesso",))
    if not chave:
        return None
    evento = _pick(r, ("evento_mais_recente",))
    orgao = _pick(r, ("orgao_destinatario", "nome_destinatario"))
    return {
        "chave": chave,
        "processo_id": build_processo_id(chave),
        "numero_processo": _pick(r, ("numero",)) or chave,
        "serie": _pick(r, ("serie",)),
        "modelo": _pick(r, ("modelo",)),
        "evento": evento,
        "evento_ok": evento_autoriza_ingest(evento),
        "data_emissao": parse_data_emissao(_pick(r, ("data_emissao",))),
        "orgao": orgao,
        "orgao_superior": _pick(r, ("orgao_superior_destinatario",)),
        "uf": (_pick(r, ("uf_destinatario",)) or "").upper() or None,
        "cnpj_destinatario": _cnpj_digits(_pick(r, ("cnpj_destinatario",))),
        "nome_destinatario": _pick(r, ("nome_destinatario",)),
        "fornecedor_nome": _pick(r, ("razao_social_emitente",)),
        "cnpj_fornecedor": _cnpj_digits(_pick(r, ("cpf_cnpj_emitente",))),
        "valor_nota": _pick_float(r, ("valor_nota_fiscal",)),
        "natureza": _pick(r, ("natureza_da_operacao",)),
        "url_origem": build_url_origem(chave),
        "inciso_classificacao": "inciso_v",
        "esfera": "federal",
    }


def map_item_row(
    row: Dict[str, Any],
    *,
    nota: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Linha Item (+ Nota opcional) → dict para materialize.

    Preço efetivo = VALOR UNITÁRIO → valor_unitario e valor_unitario_homologado.
    """
    r = normalize_row_keys(row)
    chave = _pick(r, ("chave_de_acesso",))
    numero = _pick(r, ("numero_produto",))
    if not chave or not numero:
        return None

    descricao = _pick(r, ("descricao_do_produto_servico",)) or ""
    if not descricao.strip():
        return None

    vu = _pick_float(r, ("valor_unitario",))
    if vu is None or vu <= 0:
        return None

    nota = nota or {}
    # Sem Nota no join: ainda indexa se houver VU (evento filtrado quando Nota existe).
    if nota and nota.get("evento_ok") is False:
        return None

    orgao = (
        (nota.get("orgao") if nota else None)
        or _pick(r, ("orgao_destinatario", "nome_destinatario"))
    )
    uf = (
        (nota.get("uf") if nota else None)
        or (_pick(r, ("uf_destinatario",)) or "").upper()
        or None
    )
    data_ref = (nota.get("data_emissao") if nota else None) or parse_data_emissao(
        _pick(r, ("data_emissao",))
    )
    forn_nome = (nota.get("fornecedor_nome") if nota else None) or _pick(
        r, ("razao_social_emitente",)
    )
    forn_cnpj = (nota.get("cnpj_fornecedor") if nota else None) or _cnpj_digits(
        _pick(r, ("cpf_cnpj_emitente",))
    )

    return {
        "chave": chave,
        "processo_id": build_processo_id(chave),
        "plataforma_item_id": build_plataforma_item_id(chave, numero),
        "numero_item": numero,
        "numero_processo": (nota.get("numero_processo") if nota else None)
        or _pick(r, ("numero",))
        or chave,
        "numero_pncp": None,
        "descricao": descricao.strip(),
        "material_servico": _pick(r, ("ncm_sh_tipo_de_produto",)),
        "ncm": _pick(r, ("codigo_ncm_sh",)),
        "cfop": _pick(r, ("cfop",)),
        "unidade_medida": normalize_unidade(_pick(r, ("unidade",))),
        "quantidade": _pick_float(r, ("quantidade",)),
        "valor_unitario": float(vu),
        # Preço efetivo da NF = “fechado” no pipeline (equiv. funcional ao homologado).
        "valor_unitario_homologado": float(vu),
        "valor_total_linha": _pick_float(r, ("valor_total",)),
        "fornecedor_nome": forn_nome,
        "cnpj_fornecedor": forn_cnpj,
        "orgao": orgao,
        "municipio": None,
        "uf": uf,
        "data_referencia": data_ref,
        "url_origem": (nota.get("url_origem") if nota else None) or build_url_origem(chave),
        "inciso_classificacao": "inciso_v",
        "esfera": "federal",
        "plataforma": "notas_fiscais",
        "evento": nota.get("evento") if nota else None,
    }


def column_map_spec() -> Dict[str, Any]:
    return {
        "platform_id": "notas_fiscais",
        "views": {
            "nota": "NotaFiscal",
            "item": "NotaFiscalItem",
            "evento": "NotaFiscalEvento",
        },
        "join_keys": ["CHAVE DE ACESSO"],
        "required_nota_headers": list(REQUIRED_NOTA_HEADERS),
        "required_item_headers": list(REQUIRED_ITEM_HEADERS),
        "price_field": "VALOR UNITÁRIO",
        "price_as_homologado": True,
        "inciso_default": "inciso_v",
        "esfera_default": "federal",
        "item_materialize_enabled": True,
        "encoding": "cp1252",
        "delimiter": ";",
    }
