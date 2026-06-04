"""
Auditoria síncrona (requests) — classifica por que falta fornecedor em uma fonte PNCP.
Espelha as camadas de pncp_researcher_service/app/supplier_probe.py para o container backend.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import requests

from backend.app.services.pncp_supplier_enrichment import (
    PNCP_API_BASE,
    _ano_seq_for_enrichment,
    _extract_cnpj_orgao,
    _extract_supplier_snapshot,
    _fetch_contratos_contratacao_sync,
    _find_catalog_row,
    _get_json,
    _supplier_snap_from_resultados_payload,
)

GAP_OK = "ok_fornecedor_resolvido"
GAP_MISSING_KEYS = "missing_pncp_keys"
GAP_RESULTADOS_204 = "pncp_resultados_204"
GAP_RESULTADOS_404 = "pncp_resultados_404"
GAP_RESULTADOS_EMPTY = "pncp_resultados_200_sem_cnpj"
GAP_CONTRATO_404 = "pncp_contrato_404"
GAP_CONTRATO_EMPTY = "pncp_contrato_200_sem_cnpj"
GAP_CATALOG_SEM_FORNECEDOR = "pncp_catalogo_sem_fornecedor"
GAP_HTTP_ERROR = "pncp_http_error"
GAP_ALREADY_IN_SOURCE = "ok_ja_no_source"

_DEFAULT_TIMEOUT = (2.5, 6.0)


@dataclass
class LayerProbe:
    name: str
    url: str
    status_code: Optional[int] = None
    error: str = ""
    found_supplier: bool = False


@dataclass
class SupplierGapReport:
    row_id: Optional[int] = None
    numero_pncp: str = ""
    ano: Optional[int] = None
    sequencial: Optional[int] = None
    numero_item: str = ""
    situacao_item: str = ""
    tem_resultado: Optional[bool] = None
    gap_reason: str = ""
    cnpj_fornecedor: str = ""
    fornecedor: str = ""
    layers: List[LayerProbe] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["layers"] = [asdict(x) for x in self.layers]
        return d


def _http_status(url: str, *, params: Optional[Dict[str, Any]] = None) -> Tuple[int, Any, str]:
    try:
        r = requests.get(url, timeout=_DEFAULT_TIMEOUT, params=params or {})
    except Exception as exc:
        return 0, None, str(exc)[:200]
    if r.status_code in (204, 404):
        return r.status_code, None, ""
    if r.status_code >= 400:
        return r.status_code, None, (r.text or "")[:200]
    try:
        return r.status_code, r.json(), ""
    except Exception as exc:
        return r.status_code, None, str(exc)[:200]


def probe_fonte_pncp(
    *,
    numero_pncp: str = "",
    ano_compra: Any = None,
    sequencial_compra: Any = None,
    numero_item: str = "",
    situacao_compra: str = "",
    row_id: Optional[int] = None,
    source: Optional[Dict[str, Any]] = None,
) -> SupplierGapReport:
    src = source if isinstance(source, dict) else {}
    if str(src.get("cnpj_fornecedor") or "").strip():
        return SupplierGapReport(
            row_id=row_id,
            numero_pncp=numero_pncp,
            gap_reason=GAP_ALREADY_IN_SOURCE,
            cnpj_fornecedor=str(src.get("cnpj_fornecedor") or ""),
            fornecedor=str(src.get("fornecedor") or ""),
        )

    np = str(numero_pncp or src.get("numero_pncp") or src.get("numeroControlePNCP") or "").strip()
    ano, seq = _ano_seq_for_enrichment(
        numero_pncp=np,
        ano_compra=ano_compra,
        sequencial_compra=sequencial_compra,
        source=src,
    )
    n_item = str(numero_item or src.get("numero_item") or src.get("numeroItem") or "").strip()
    cnpj = _extract_cnpj_orgao(np)
    report = SupplierGapReport(
        row_id=row_id,
        numero_pncp=np,
        ano=ano,
        sequencial=seq,
        numero_item=n_item,
    )

    if len(cnpj) != 14 or ano is None or seq is None:
        report.gap_reason = GAP_MISSING_KEYS
        return report

    base = f"{PNCP_API_BASE}/v1/orgaos/{cnpj}/compras/{ano}/{seq}"
    sit = str(situacao_compra or src.get("situacao") or src.get("situacao_compra") or "").strip()

    if n_item:
        cat_url = f"{base}/itens/{n_item}"
        st, body, err = _http_status(cat_url)
        layer = LayerProbe("catalogo_item", cat_url, status_code=st or None, error=err)
        if isinstance(body, dict):
            report.situacao_item = str(
                body.get("situacaoCompraItemNome") or body.get("situacaoCompraItem") or ""
            ).strip()
            tr = body.get("temResultado")
            report.tem_resultado = bool(tr) if tr is not None else None
            snap = _extract_supplier_snapshot(body)
            if snap.get("cnpj_fornecedor") or snap.get("fornecedor"):
                layer.found_supplier = True
                report.gap_reason = GAP_OK
                report.cnpj_fornecedor = snap.get("cnpj_fornecedor", "")
                report.fornecedor = snap.get("fornecedor", "")
                report.layers.append(layer)
                return report
        report.layers.append(layer)

        res_url = f"{base}/itens/{n_item}/resultados"
        st, body, err = _http_status(res_url)
        layer_r = LayerProbe("resultados_item", res_url, status_code=st or None, error=err)
        report.layers.append(layer_r)
        if st == 204:
            report.gap_reason = GAP_RESULTADOS_204
        elif st == 404:
            report.gap_reason = GAP_RESULTADOS_404
        elif st == 0:
            report.gap_reason = GAP_HTTP_ERROR
        elif body is not None:
            snap = _supplier_snap_from_resultados_payload(body, numero_item=n_item, situacao_compra=sit)
            if snap.get("cnpj_fornecedor") or snap.get("fornecedor"):
                layer_r.found_supplier = True
                report.gap_reason = GAP_OK
                report.cnpj_fornecedor = snap.get("cnpj_fornecedor", "")
                report.fornecedor = snap.get("fornecedor", "")
                return report
            report.gap_reason = GAP_RESULTADOS_EMPTY

    ct_url = f"{PNCP_API_BASE}/v1/orgaos/{cnpj}/contratos/contratacao/{ano}/{seq}"
    st, body, err = _http_status(ct_url, params={"pagina": 1, "tamanhoPagina": 50})
    layer_c = LayerProbe("contratos_contratacao", ct_url, status_code=st or None, error=err)
    report.layers.append(layer_c)
    if st == 404 and report.gap_reason in ("", GAP_RESULTADOS_204):
        report.gap_reason = GAP_CONTRATO_404
    elif body is not None:
        snap = _supplier_snap_from_resultados_payload(body, numero_item=n_item, situacao_compra=sit)
        if snap.get("cnpj_fornecedor") or snap.get("fornecedor"):
            layer_c.found_supplier = True
            report.gap_reason = GAP_OK
            report.cnpj_fornecedor = snap.get("cnpj_fornecedor", "")
            report.fornecedor = snap.get("fornecedor", "")
            return report
        if report.gap_reason in ("", GAP_RESULTADOS_204, GAP_CONTRATO_404):
            report.gap_reason = GAP_CONTRATO_EMPTY

    if not report.gap_reason:
        report.gap_reason = GAP_CATALOG_SEM_FORNECEDOR
    return report


def summarize_gap_reports(reports: List[SupplierGapReport]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for r in reports:
        k = r.gap_reason or "unknown"
        counts[k] = counts.get(k, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: -x[1]))
