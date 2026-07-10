from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .contracts import MarketPriceHit


def _safe_float(v: Any) -> Optional[float]:
    try:
        if v is None or v == "":
            return None
        n = float(v)
        return n if n >= 0 else None
    except (TypeError, ValueError):
        return None


def _cnpj_digits(v: Any) -> str:
    return re.sub(r"\D", "", str(v or ""))


def pncp_row_to_hit(row: Dict[str, Any]) -> MarketPriceHit:
    """Converte linha PNCP (dict do researcher) em MarketPriceHit."""
    raw = dict(row) if isinstance(row, dict) else {}
    hom = _safe_float(
        raw.get("valor_unitario_homologado")
        or raw.get("valorUnitarioHomologado")
    )
    unit = hom
    if unit is None:
        unit = _safe_float(raw.get("valor_unitario") or raw.get("valorUnitario")) or 0.0
    np = str(raw.get("numero_pncp") or raw.get("numeroControlePNCP") or "").strip()
    ni = str(raw.get("numero_item") or raw.get("numeroItem") or "").strip()
    item_id = f"{np}:{ni}" if np else ni or str(raw.get("id") or "")
    esfera = str(
        raw.get("esfera")
        or raw.get("esfera_administrativa")
        or raw.get("esferaAdministrativa")
        or ""
    ).strip() or None
    return MarketPriceHit(
        plataforma="pncp",
        plataforma_item_id=item_id,
        descricao_item=str(
            raw.get("descricao_item")
            or raw.get("descricao")
            or raw.get("objeto_resumido")
            or ""
        ).strip(),
        valor_unitario=float(unit or 0.0),
        valor_unitario_homologado=hom,
        unidade_medida=str(raw.get("unidade_medida") or raw.get("unidadeMedida") or "").strip() or None,
        quantidade=_safe_float(raw.get("quantidade")),
        orgao=str(raw.get("orgao") or "").strip() or None,
        municipio=str(raw.get("municipio") or raw.get("municipioNome") or "").strip() or None,
        uf=str(raw.get("uf") or raw.get("ufSigla") or "").strip() or None,
        fornecedor_nome=str(
            raw.get("fornecedor")
            or raw.get("fornecedor_nome")
            or raw.get("nome_fornecedor")
            or ""
        ).strip() or None,
        fornecedor_cnpj=_cnpj_digits(
            raw.get("cnpj_fornecedor")
            or raw.get("cnpjFornecedor")
            or raw.get("cnpj")
        ) or None,
        data_referencia=str(raw.get("data_publicacao") or raw.get("dataPublicacao") or "").strip() or None,
        inciso_classificacao=str(raw.get("inciso_classificacao") or raw.get("incisoClassificacao") or "").strip() or None,
        esfera=esfera,
        url_origem=str(raw.get("url_origem") or raw.get("link_pncp") or "").strip() or None,
        raw=raw,
    )


def hit_to_pncp_row(hit: MarketPriceHit) -> Dict[str, Any]:
    """Reconstrói dict PNCP-compatível a partir de MarketPriceHit."""
    row = dict(hit.raw or {})
    row["plataforma"] = hit.plataforma
    row["plataforma_item_id"] = hit.plataforma_item_id
    if hit.descricao_item:
        row["descricao_item"] = hit.descricao_item
    if hit.valor_unitario_homologado is not None:
        row["valor_unitario_homologado"] = hit.valor_unitario_homologado
    if hit.valor_unitario:
        row["valor_unitario"] = hit.valor_unitario
    if hit.unidade_medida:
        row["unidade_medida"] = hit.unidade_medida
    if hit.quantidade is not None:
        row["quantidade"] = hit.quantidade
    if hit.orgao:
        row["orgao"] = hit.orgao
    if hit.municipio:
        row["municipio"] = hit.municipio
    if hit.uf:
        row["uf"] = hit.uf
    if hit.fornecedor_nome:
        row["fornecedor"] = hit.fornecedor_nome
    if hit.fornecedor_cnpj:
        row["cnpj_fornecedor"] = hit.fornecedor_cnpj
    if hit.data_referencia:
        row["data_publicacao"] = hit.data_referencia
    if hit.inciso_classificacao:
        row["inciso_classificacao"] = hit.inciso_classificacao
    if hit.esfera:
        row["esfera_administrativa"] = hit.esfera
    if hit.url_origem:
        row["url_origem"] = hit.url_origem
    return row


def hits_to_pncp_rows(hits: List[MarketPriceHit]) -> List[Dict[str, Any]]:
    return [hit_to_pncp_row(h) for h in hits]
