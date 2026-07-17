from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from ..config import (
    PNCP_FEDERATED_PNCP_TIMEOUT_SECONDS,
    PNCP_FEDERATED_SEARCH_ENABLED,
    PNCP_FEDERATED_SOURCE_TIMEOUT_SECONDS,
)
from .contracts import FederatedSearchQuery, MarketPriceHit
from .crosslink import assign_canonical_keys
from .dedup import dedupe_hits
from .mapping import hit_to_pncp_row, platform_row_to_hit
from .orchestrator import orchestrate_federated_hits
from .pncp_adapter import PncpAdapter
from .registry import get_adapter, get_adapters


def _timeout_for_source(source_id: str) -> float:
    """PNCP (pipeline inteligente) precisa de bem mais tempo que FTS de plataformas."""
    sid = str(source_id or "").strip().lower()
    if sid == "pncp":
        return max(30.0, float(PNCP_FEDERATED_PNCP_TIMEOUT_SECONDS or 100.0))
    return max(5.0, float(PNCP_FEDERATED_SOURCE_TIMEOUT_SECONDS or 20.0))


async def _search_adapter_with_timeout(
    adapter_id: str,
    query: FederatedSearchQuery,
    *,
    timeout_s: float,
) -> tuple[str, List[MarketPriceHit], Optional[str]]:
    adapters = get_adapters([adapter_id])
    if not adapters:
        return adapter_id, [], f"fonte desconhecida: {adapter_id}"
    adapter = adapters[0]
    try:
        hits = await asyncio.wait_for(adapter.search(query), timeout=timeout_s)
        return adapter_id, hits, None
    except asyncio.TimeoutError:
        return adapter_id, [], "timeout"
    except Exception as exc:
        return adapter_id, [], str(exc)[:240]


def _row_unit_price(row: Dict[str, Any]) -> float:
    for key in (
        "valor_unitario_homologado",
        "valorUnitarioHomologado",
        "valor_unitario",
        "valorUnitario",
    ):
        try:
            n = float(row.get(key) or 0)
            if n > 0:
                return n
        except (TypeError, ValueError):
            continue
    return 0.0


def _keep_homolog_row(row: Dict[str, Any], *, somente_homologados: Optional[bool]) -> bool:
    if not somente_homologados:
        return True
    try:
        hom = float(row.get("valor_unitario_homologado") or 0)
        if hom > 0:
            return True
    except (TypeError, ValueError):
        pass
    if row.get("item_homologado") is True:
        return _row_unit_price(row) > 0
    # TCE / platform: se não há coluna homologado, aceita preço positivo.
    plat = str(row.get("plataforma") or "").lower()
    if plat and plat != "pncp":
        return _row_unit_price(row) > 0
    return False


async def _federated_lista_completa(query: FederatedSearchQuery) -> Dict[str, Any]:
    """
    Busca manual: índice local PNCP + FTS das plataformas, lista ampla (sem top-3 IA).
    Rápido — não chama market_search_intelligent.
    """
    from ..local_index import local_item_search
    from ..platform_index.registry import get_platform_spec
    from ..platform_index.search import platform_item_search
    from ..pricing_faixa import compute_faixa_regional

    sources = [s for s in (query.fontes_habilitadas or ["pncp"]) if s] or ["pncp"]
    # Paridade com /local-index/search-items: varrer o máximo viável dos filtros (sem top-3).
    requested = max(200, int(query.max_paginas or 1) * int(query.tamanho_pagina or 50))
    limit = max(200, min(5000, requested))
    per_source = max(200, min(3000, limit))

    source_stats: Dict[str, Any] = {}
    merged_rows: List[Dict[str, Any]] = []

    if "pncp" in sources:
        try:
            raw = local_item_search(
                query.termo_busca,
                uf=query.uf,
                municipio=query.municipio,
                recortes_geograficos=query.recortes_geograficos,
                codigo_modalidade=query.codigo_modalidade,
                limit=per_source,
                somente_homologados=query.somente_homologados,
            )
            itens = list((raw or {}).get("itens") or [])
            for row in itens:
                if not isinstance(row, dict):
                    continue
                row = dict(row)
                row.setdefault("plataforma", "pncp")
                merged_rows.append(row)
            source_stats["pncp"] = {"hits": len(itens), "erro": None, "modo": "local_item_search"}
        except Exception as exc:
            source_stats["pncp"] = {"hits": 0, "erro": str(exc)[:240], "modo": "local_item_search"}

    for source_id in sources:
        if source_id == "pncp":
            continue
        adapter = get_adapter(source_id)
        spec = get_platform_spec(source_id)
        if adapter is None or spec is None or spec.schema_kind != "platform_index":
            source_stats[source_id] = {"hits": 0, "erro": "fonte indisponível"}
            continue
        try:
            scope = getattr(spec, "uf_scope", None)
            if query.uf:
                uf = query.uf
                if scope and str(scope).strip().upper() != str(uf).strip().upper():
                    source_stats[source_id] = {
                        "hits": 0,
                        "erro": None,
                        "skipped": "uf_fora_escopo",
                    }
                    continue
            else:
                uf = scope
            rows = platform_item_search(
                spec,
                termo=query.termo_busca,
                uf=uf,
                limit=per_source,
            )
            n = 0
            defaults = {
                "inciso_default": getattr(spec, "inciso_default", None),
                "esfera_default": getattr(spec, "esfera_default", None),
            }
            for r in rows:
                hit = platform_row_to_hit(r, plataforma=source_id, spec_defaults=defaults)
                row = hit_to_pncp_row(hit)
                if not _keep_homolog_row(row, somente_homologados=query.somente_homologados):
                    continue
                if _row_unit_price(row) <= 0:
                    continue
                merged_rows.append(row)
                n += 1
            source_stats[source_id] = {"hits": n, "erro": None, "modo": "platform_fts"}
        except Exception as exc:
            source_stats[source_id] = {"hits": 0, "erro": str(exc)[:240], "modo": "platform_fts"}

    # Dedup leve por plataforma_item_id / numero_pncp+item
    seen: set[str] = set()
    deduped: List[Dict[str, Any]] = []
    for row in merged_rows:
        key = str(
            row.get("plataforma_item_id")
            or f"{row.get('plataforma')}:{row.get('numero_pncp')}:{row.get('numero_item')}"
            or row.get("descricao_item")
            or ""
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)

    faixa_min = None
    faixa_max = None
    if (
        query.valor_base_referencia
        and float(query.valor_base_referencia) > 0
        and query.variacao_percentual_referencia is not None
        and float(query.variacao_percentual_referencia) >= 0
    ):
        try:
            faixa_min, faixa_max = compute_faixa_regional(
                float(query.valor_base_referencia),
                float(query.variacao_percentual_referencia),
                sentido=query.variacao_sentido_referencia or "ambos",
            )
        except Exception:
            faixa_min = faixa_max = None

    if faixa_min is not None and faixa_max is not None:
        filtered = []
        for row in deduped:
            p = _row_unit_price(row)
            if p > 0 and faixa_min <= p <= faixa_max:
                filtered.append(row)
        deduped = filtered

    itens = deduped[:limit]
    return {
        "ok": True,
        "filtros": {
            "termo_busca": query.termo_busca,
            "uf": query.uf,
            "municipio": query.municipio,
            "recortes_geograficos": (
                [r.model_dump() for r in query.recortes_geograficos]
                if query.recortes_geograficos
                else None
            ),
            "codigo_modalidade": query.codigo_modalidade,
            "fontes_habilitadas": sources,
            "lista_completa": True,
            "faixa_regional_min": faixa_min,
            "faixa_regional_max": faixa_max,
            "variacao_sentido_referencia": query.variacao_sentido_referencia,
        },
        "stats": {
            "federated": True,
            "lista_completa": True,
            "fontes": source_stats,
            "fontes_habilitadas": sources,
            "total_hits": len(merged_rows),
            "total_apos_dedup": len(deduped),
            "total_retornados": len(itens),
            "regra_selecao": "lista_completa_indices_locais",
        },
        "itens": itens,
    }


async def federated_search(query: FederatedSearchQuery) -> Dict[str, Any]:
    """
    Orquestra busca em múltiplas fontes.
    Fast-path: sources=["pncp"] retorna resposta idêntica ao market_search_intelligent.
    lista_completa: busca manual — FTS local multi-fonte sem top-3.
    """
    if not PNCP_FEDERATED_SEARCH_ENABLED:
        return {
            "ok": False,
            "filtros": {"fontes_habilitadas": query.fontes_habilitadas},
            "stats": {"erro": "federated_disabled"},
            "itens": [],
        }

    sources = [s for s in (query.fontes_habilitadas or ["pncp"]) if s]
    if not sources:
        sources = ["pncp"]

    if query.lista_completa and not query.busca_lote:
        return await _federated_lista_completa(query)

    # Paridade: uma fonte PNCP = pipeline atual sem round-trip.
    if sources == ["pncp"]:
        adapter = PncpAdapter()
        raw = await adapter.search_raw(query)
        stats = dict(raw.get("stats") or {})
        stats["fontes_consultadas"] = ["pncp"]
        stats["fontes_habilitadas"] = sources
        raw["stats"] = stats
        filtros = dict(raw.get("filtros") or {})
        filtros["fontes_habilitadas"] = sources
        raw["filtros"] = filtros
        itens = raw.get("itens") or []
        for row in itens:
            if isinstance(row, dict) and not row.get("plataforma"):
                row["plataforma"] = "pncp"
        return raw

    tasks = [
        _search_adapter_with_timeout(
            source_id,
            query,
            timeout_s=_timeout_for_source(source_id),
        )
        for source_id in sources
    ]
    results = await asyncio.gather(*tasks)

    merged: List[MarketPriceHit] = []
    source_stats: Dict[str, Any] = {}
    for source_id, hits, err in results:
        source_stats[source_id] = {
            "hits": len(hits),
            "erro": err,
            "timeout_s": _timeout_for_source(source_id),
        }
        merged.extend(hits)

    linked = assign_canonical_keys(merged, persist=True)
    deduped = dedupe_hits(linked)

    return await orchestrate_federated_hits(
        query,
        deduped,
        source_stats=source_stats,
        total_hits=len(merged),
        total_after_dedup=len(deduped),
    )
