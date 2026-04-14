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
from typing import Any, Dict, List, Optional, Tuple

from django.utils import timezone

# Mínimo de cotações (fontes) por item para marcar situação como válida (IN 65 / prática comum).
MIN_FONTES_SITUACAO_VALIDA = 3

_CNPJ_LOOSE = re.compile(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}")


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


def _formatar_moeda_br(v: Any) -> str:
    if v is None:
        return "—"
    try:
        n = float(v)
    except (TypeError, ValueError):
        return "—"
    if math.isnan(n) or math.isinf(n):
        return "—"
    s = f"{n:.2f}"
    inteiro, frac = s.split(".")
    return f"{inteiro},{frac}"


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


def _valor_numerico_item(it: Any) -> Optional[float]:
    for attr in ("valor_total", "valor_unitario"):
        v = getattr(it, attr, None)
        if v is None:
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if math.isnan(f) or math.isinf(f):
            continue
        return f
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


def fonte_dict_de_item(it: Any, *, tz) -> Dict[str, str]:
    """Uma linha ORM → uma linha da tabela «fontes» do detalhamento."""
    src: Dict[str, Any] = getattr(it, "source", None) or {}
    if not isinstance(src, dict):
        src = {}

    tipo = _pick_source(src, "tipo_fonte", "fonte", "origem", "tipoFonte", "tipo")
    if tipo == "—":
        np = (getattr(it, "numero_pncp", None) or "").strip()
        tipo = "PNCP" if np else "Registro importado"

    fornecedor = _pick_source(
        src,
        "fornecedor",
        "nomeRazaoSocialFornecedor",
        "razaoSocialFornecedor",
        "razao_social",
        "nome_fornecedor",
        "fornecedor_nome",
    )
    if fornecedor == "—":
        fornecedor = (getattr(it, "orgao", None) or "—")[:400]

    cnpj = _pick_source(
        src,
        "cnpj",
        "cnpj_fornecedor",
        "cnpjCpfFornecedor",
        "niFornecedor",
        "cnpjFornecedor",
    )
    if cnpj == "—":
        cnpj = _primeiro_cnpj_no_json(src)
    if cnpj == "—":
        cnpj = _primeiro_cnpj_no_json(getattr(it, "__dict__", {}))

    created = getattr(it, "created_at", None)
    data_str = "—"
    if created is not None:
        data_str = timezone.localtime(created, tz).strftime("%d/%m/%Y")

    vn = _valor_numerico_item(it)
    valor = f"R$ {_formatar_moeda_br(vn)}" if vn is not None else "—"

    orgao = (getattr(it, "orgao", None) or "—")[:200]
    mun = (getattr(it, "municipio", None) or "").strip()
    uf = (getattr(it, "uf", None) or "").strip()
    if mun and uf:
        municipio_uf = f"{mun}/{uf}"
    elif mun:
        municipio_uf = mun
    elif uf:
        municipio_uf = uf
    else:
        municipio_uf = "—"

    processo = _pick_source(src, "processo", "numeroControlePNCP")
    if processo == "—":
        processo = (getattr(it, "numero_pncp", None) or "").strip() or "—"

    ajuste = _pick_source(src, "ajuste", "observacao_frete", "frete", default="Sem frete")

    return {
        "tipo": tipo[:120],
        "fornecedor": fornecedor[:400],
        "cnpj": cnpj[:32],
        "data": data_str,
        "valor": valor[:32],
        "orgao": orgao,
        "municipio_uf": municipio_uf[:120],
        "processo": str(processo)[:120],
        "ajuste": ajuste[:120],
    }


def agrupar_itens_relatorio_pesquisa_precos(itens: List[Any]) -> Tuple[List[Dict[str, Any]], int]:
    """
    Retorna lista de grupos (ordenada por menor id no grupo) e total de linhas importadas.

    Cada grupo vira um «Item N» no PDF com N cotações (fontes) na sub-tabela.
    """
    if not itens:
        return [], 0

    tz = timezone.get_current_timezone()
    total_linhas = len(itens)

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

        first = members[0]
        nome = (getattr(first, "descricao_item", None) or "—")[:500]
        q_fmt = _fmt_quantidade(getattr(first, "quantidade", None))
        und = (getattr(first, "unidade_medida", None) or "—")[:64]

        vals = [v for v in (_valor_numerico_item(x) for x in members) if v is not None]
        media_valor: Optional[float] = None
        if vals:
            media_valor = sum(vals) / len(vals)
            media_fmt = f"R$ {_formatar_moeda_br(media_valor)}"
        else:
            media_fmt = "—"

        n_cot = len(members)
        if n_cot >= MIN_FONTES_SITUACAO_VALIDA:
            situacao = "Válido"
        else:
            situacao = f"Insuficiente ({n_cot} de {MIN_FONTES_SITUACAO_VALIDA} fontes)"

        fontes = [fonte_dict_de_item(m, tz=tz) for m in members]

        grupos.append(
            {
                "ordem": ordem,
                "nome": nome,
                "quantidade_fmt": q_fmt,
                "unidade": und,
                "n_cotacoes": n_cot,
                "media_valor": media_valor,
                "media_fmt": media_fmt,
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
