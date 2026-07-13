from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional

from ..platform_index.crosslink_db import resolve_canonical_key, upsert_cross_ref
from .contracts import MarketPriceHit


def _norm_text(v: str) -> str:
    s = unicodedata.normalize("NFKD", str(v or ""))
    s = s.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", s).strip()


def _cnpj_digits(v: Any) -> str:
    return re.sub(r"\D", "", str(v or ""))


def _price_bucket(price: Optional[float], *, epsilon: float = 0.01) -> int:
    return int(round(float(price or 0) / epsilon))


def extract_cross_identifiers(hit: MarketPriceHit) -> Dict[str, Optional[str]]:
    """Extrai identificadores usados para cruzar a mesma compra entre plataformas."""
    raw = dict(hit.raw or {})
    np = str(
        raw.get("numero_pncp")
        or raw.get("numeroControlePNCP")
        or raw.get("numero_pncp_cross")
        or ""
    ).strip() or None
    ni = str(raw.get("numero_item") or raw.get("numeroItem") or "").strip() or None
    if not ni and hit.plataforma_item_id and ":" in hit.plataforma_item_id:
        ni = hit.plataforma_item_id.split(":", 1)[1] or None

    proc = str(
        raw.get("numero_processo")
        or raw.get("numeroProcesso")
        or raw.get("identificacao")
        or ""
    ).strip() or None

    cnpj = _cnpj_digits(hit.fornecedor_cnpj or raw.get("cnpj_fornecedor") or raw.get("cnpj"))
    cnpj = cnpj or None

    price = hit.valor_unitario_homologado if hit.valor_unitario_homologado is not None else hit.valor_unitario
    desc = _norm_text(hit.descricao_item)[:120] or None

    return {
        "numero_pncp": np,
        "numero_item": ni,
        "numero_processo": proc,
        "cnpj_fornecedor": cnpj,
        "valor_bucket": str(_price_bucket(price)),
        "desc_norm": desc,
    }


def build_canonical_key(hit: MarketPriceHit, ids: Optional[Dict[str, Optional[str]]] = None) -> str:
    """
    Chave unificada para dedup cross-platform.
    Prioridade: numero_pncp+item > processo+item+plataforma > orgao+cnpj+preço+desc.
    """
    meta = ids or extract_cross_identifiers(hit)
    plat = str(hit.plataforma or "").strip().lower()
    ext_id = str(hit.plataforma_item_id or "").strip()

    np = meta.get("numero_pncp")
    ni = meta.get("numero_item")
    if np:
        return f"pncp|{np}|{ni or ext_id.split(':')[-1] if ext_id else ''}"

    proc = meta.get("numero_processo")
    if proc:
        item_part = ni or (ext_id.split(":")[-1] if ":" in ext_id else ext_id)
        return f"proc|{proc}|{item_part or ''}|{plat}"

    orgao = _norm_text(hit.orgao or "")
    cnpj = meta.get("cnpj_fornecedor") or ""
    bucket = meta.get("valor_bucket") or "0"
    desc = meta.get("desc_norm") or ""
    if orgao and (cnpj or desc):
        return f"soft|{orgao}|{cnpj}|{bucket}|{desc}"

    return f"plat|{plat}|{ext_id or desc or 'unknown'}"


def assign_canonical_keys(
    hits: Iterable[MarketPriceHit],
    *,
    persist: bool = True,
    db_path: Optional[str] = None,
) -> List[MarketPriceHit]:
    """
    Atribui canonical_key e cross_refs a cada hit.
    Consulta/persiste no banco central de cruzamento quando possível.
    """
    out: List[MarketPriceHit] = []
    for hit in hits:
        ids = extract_cross_identifiers(hit)
        stored = resolve_canonical_key(
            plataforma=hit.plataforma,
            plataforma_item_id=hit.plataforma_item_id,
            numero_pncp=ids.get("numero_pncp"),
            numero_item=ids.get("numero_item"),
            numero_processo=ids.get("numero_processo"),
            db_path=db_path,
        )
        canonical = stored or build_canonical_key(hit, ids)
        cross_refs = dict(hit.cross_refs or {})
        cross_refs[hit.plataforma] = hit.plataforma_item_id
        if ids.get("numero_pncp"):
            cross_refs["numero_pncp"] = ids["numero_pncp"]  # type: ignore[assignment]

        enriched = MarketPriceHit(
            plataforma=hit.plataforma,
            plataforma_item_id=hit.plataforma_item_id,
            descricao_item=hit.descricao_item,
            valor_unitario=hit.valor_unitario,
            valor_unitario_homologado=hit.valor_unitario_homologado,
            unidade_medida=hit.unidade_medida,
            quantidade=hit.quantidade,
            orgao=hit.orgao,
            municipio=hit.municipio,
            uf=hit.uf,
            fornecedor_nome=hit.fornecedor_nome,
            fornecedor_cnpj=hit.fornecedor_cnpj,
            data_referencia=hit.data_referencia,
            inciso_classificacao=hit.inciso_classificacao,
            esfera=hit.esfera,
            url_origem=hit.url_origem,
            raw=hit.raw,
            canonical_key=canonical,
            cross_refs=cross_refs,
        )
        out.append(enriched)

        if persist and hit.plataforma_item_id:
            upsert_cross_ref(
                canonical_key=canonical,
                plataforma=hit.plataforma,
                plataforma_item_id=hit.plataforma_item_id,
                numero_pncp=ids.get("numero_pncp"),
                numero_item=ids.get("numero_item"),
                numero_processo=ids.get("numero_processo"),
                cnpj_fornecedor=ids.get("cnpj_fornecedor"),
                valor_bucket=int(ids.get("valor_bucket") or "0"),
                desc_norm=ids.get("desc_norm"),
                metodo="federated_search",
                db_path=db_path,
            )
    return out
