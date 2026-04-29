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

# Mínimo de cotações (fontes) por item para marcar situação como válida (IN 65 / prática comum).
MIN_FONTES_SITUACAO_VALIDA = 3

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


def _pick_supplier_name_from_source(src: Dict[str, Any]) -> str:
    nome = _pick_source(
        src,
        "fornecedor",
        "nomeRazaoSocialFornecedor",
        "razaoSocialFornecedor",
        "razao_social",
        "nome_fornecedor",
        "fornecedor_nome",
        default="",
    ).strip()
    if nome:
        return nome
    # Busca aninhada por chaves de fornecedor, sem cair em contexto de órgão.
    for path, key, value in _iter_source_pairs(src):
        if _looks_orgao_context(path):
            continue
        k = key.lower()
        if any(t in k for t in ("fornecedor", "razaosocial", "razao_social", "nomefornecedor", "nome_fornecedor")):
            s = str(value or "").strip()
            if s and len(s) > 2:
                return s
    return nome


def _pick_supplier_cnpj_from_source(src: Dict[str, Any]) -> str:
    raw = _pick_source(
        src,
        "cnpj_fornecedor",
        "cnpjCpfFornecedor",
        "niFornecedor",
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
        src = getattr(r, "source", None) or {}
        if not isinstance(src, dict):
            continue
        cnpj = _pick_supplier_cnpj_from_source(src)
        nome = _pick_supplier_name_from_source(src)
        if cnpj and nome:
            idx[cnpj] = nome
    return idx


def fonte_dict_de_item(it: Any, *, tz, supplier_name_by_cnpj: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Uma linha ORM → uma linha da tabela «fontes» do detalhamento."""
    src: Dict[str, Any] = getattr(it, "source", None) or {}
    if not isinstance(src, dict):
        src = {}

    # Regra de negócio: no relatório final, a fonte deve ser exibida como PNCP.
    tipo = "PNCP"

    cnpj_fornecedor = _pick_supplier_cnpj_from_source(src)
    fornecedor = _pick_supplier_name_from_source(src)
    if not fornecedor and cnpj_fornecedor and supplier_name_by_cnpj:
        fornecedor = str(supplier_name_by_cnpj.get(cnpj_fornecedor) or "").strip()
    if not fornecedor:
        fornecedor = "Não informado"
    cnpj = cnpj_fornecedor or "Não informado"

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
        "quantidade": _fmt_quantidade(getattr(it, "quantidade", None)),
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
        supplier_name_idx = _build_supplier_name_index(members)

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

        fontes = [fonte_dict_de_item(m, tz=tz, supplier_name_by_cnpj=supplier_name_idx) for m in members]

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
    formula_id: str,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Novo fluxo: item manual + múltiplas cotações vinculadas.

    - `itens`: linhas de PncpCotacaoItem (ordem/base visual do relatório).
    - `cotacoes`: linhas de PncpCotacaoItemCotacao vinculadas aos itens.
    """
    if not itens:
        return [], 0

    tz = timezone.get_current_timezone()
    total_linhas = len(cotacoes or [])
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

        vals = [v for v in (_valor_numerico_item(x, quantidade_base=qtd_item_f) for x in members) if v is not None]
        valor_calc = _valor_formula_em_lista(vals, formula_id)
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

        fontes = [fonte_dict_de_item(m, tz=tz, supplier_name_by_cnpj=supplier_name_idx) for m in members]
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
    medias: List[float] = []
    pesos: List[float] = []
    for g in grupos or []:
        valores_fontes: List[float] = []
        raw_vals = g.get("valores_fontes")
        if isinstance(raw_vals, list):
            for rv in raw_vals:
                try:
                    fv = float(rv)
                except (TypeError, ValueError):
                    continue
                if math.isnan(fv) or math.isinf(fv):
                    continue
                valores_fontes.append(fv)
        if not valores_fontes:
            mv = g.get("media_valor")
            try:
                f = float(mv)
            except (TypeError, ValueError):
                continue
            if math.isnan(f) or math.isinf(f):
                continue
            valores_fontes = [f]
        valor_item = _valor_formula_em_lista(valores_fontes, formula_id)
        if valor_item is None:
            continue
        medias.append(valor_item)
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

    if formula_id == "mediana_precos_obtidos":
        s = sorted(medias)
        n = len(s)
        if n % 2 == 1:
            val = s[n // 2]
        else:
            val = (s[n // 2 - 1] + s[n // 2]) / 2
        return _resumo_from_values(medias, formula_id=formula_id, valor_calculado=val)

    if formula_id == "menor_preco":
        val = min(medias)
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

    if formula_id == "media_ponderada":
        total_peso = sum(pesos) or 1.0
        val = sum(v * w for v, w in zip(medias, pesos)) / total_peso
        return _resumo_from_values(medias, formula_id=formula_id, valor_calculado=val)

    if formula_id == "media_relativa_25_50":
        s = sorted(medias)
        p25 = _percentile(s, 0.25)
        p50 = _percentile(s, 0.50)
        if p25 is None or p50 is None:
            val = None
            faixa = []
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

    val = sum(medias) / len(medias)
    return _resumo_from_values(medias, formula_id="media_aritmetica_precos_obtidos", valor_calculado=val)
