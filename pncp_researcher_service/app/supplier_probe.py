"""
Sondagem em camadas PNCP para diagnóstico de cobertura de fornecedor.

Uso: auditoria operacional, relatórios de gap e testes antes de backfill.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import httpx

from .config import PNCP_PNCP_API_BASE_URL
from .supplier_resolver import (
    cnpj_digits,
    resolution_to_api_dict,
    resolve_from_contratos_payload,
    resolve_from_item_catalog_row,
    resolve_from_resultados_payload,
)

# Motivos padronizados (métricas / dashboard)
GAP_OK = "ok_fornecedor_resolvido"
GAP_MISSING_KEYS = "missing_pncp_keys"
GAP_RESULTADOS_204 = "pncp_resultados_204"
GAP_RESULTADOS_404 = "pncp_resultados_404"
GAP_RESULTADOS_EMPTY = "pncp_resultados_200_sem_cnpj"
GAP_CONTRATO_404 = "pncp_contrato_404"
GAP_CONTRATO_EMPTY = "pncp_contrato_200_sem_cnpj"
GAP_CATALOG_SEM_FORNECEDOR = "pncp_catalogo_sem_fornecedor"
GAP_HTTP_ERROR = "pncp_http_error"


@dataclass
class LayerProbe:
    name: str
    url: str
    status_code: Optional[int] = None
    error: str = ""
    found_supplier: bool = False


@dataclass
class SupplierProbeReport:
    cnpj_orgao: str = ""
    ano: Optional[int] = None
    sequencial: Optional[int] = None
    numero_item: str = ""
    situacao_item: str = ""
    tem_resultado: Optional[bool] = None
    gap_reason: str = ""
    cnpj_fornecedor: str = ""
    fornecedor: str = ""
    fornecedor_fonte: str = ""
    layers: List[LayerProbe] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["layers"] = [asdict(x) for x in self.layers]
        return d


def _parse_ano_seq(numero_pncp: str) -> Tuple[Optional[int], Optional[int]]:
    s = str(numero_pncp or "").strip()
    m = re.search(r"-(\d+)/(\d{4})\s*$", s)
    if m:
        try:
            return int(m.group(2)), int(m.group(1))
        except (TypeError, ValueError):
            return None, None
    parts = [p.strip() for p in s.split("-") if p.strip()]
    if len(parts) < 4:
        return None, None
    try:
        ano = int(parts[-2])
        seq = int(parts[-1])
    except (TypeError, ValueError):
        return None, None
    if ano < 1990 or ano > 2100 or seq < 1:
        return None, None
    return ano, seq


def _cnpj_from_numero_pncp(numero_pncp: str) -> str:
    s = str(numero_pncp or "").strip()
    if "-" in s:
        s = s.split("-", 1)[0]
    d = re.sub(r"\D", "", s)
    return d if len(d) == 14 else ""


def _keys_from_row(
    *,
    numero_pncp: str = "",
    ano_compra: Any = None,
    sequencial_compra: Any = None,
) -> Tuple[str, Optional[int], Optional[int]]:
    cnpj = _cnpj_from_numero_pncp(numero_pncp)
    ano = int(ano_compra) if ano_compra not in (None, "") else None
    seq = int(sequencial_compra) if sequencial_compra not in (None, "") else None
    if ano is None or seq is None:
        pa, ps = _parse_ano_seq(numero_pncp)
        ano = ano or pa
        seq = seq or ps
    return cnpj, ano, seq


async def probe_supplier_layers(
    *,
    numero_pncp: str = "",
    ano_compra: Any = None,
    sequencial_compra: Any = None,
    numero_item: str = "",
    situacao_compra: str = "",
    client: Optional[httpx.AsyncClient] = None,
    timeout: float = 8.0,
) -> SupplierProbeReport:
    """
    Consulta PNCP em camadas e classifica o motivo quando não há fornecedor.
    """
    cnpj, ano, seq = _keys_from_row(
        numero_pncp=numero_pncp,
        ano_compra=ano_compra,
        sequencial_compra=sequencial_compra,
    )
    n_item = str(numero_item or "").strip()
    report = SupplierProbeReport(
        cnpj_orgao=cnpj,
        ano=ano,
        sequencial=seq,
        numero_item=n_item,
    )

    if len(cnpj) != 14 or not ano or not seq:
        report.gap_reason = GAP_MISSING_KEYS
        return report

    base = f"{PNCP_PNCP_API_BASE_URL}/v1/orgaos/{cnpj}/compras/{ano}/{seq}"
    close = False
    if client is None:
        client = httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=3.0))
        close = True

    async def _hit(name: str, url: str, *, params: Optional[Dict[str, Any]] = None) -> Tuple[LayerProbe, Any]:
        layer = LayerProbe(name=name, url=url)
        try:
            resp = await client.get(url, params=params or {})
            layer.status_code = resp.status_code
            if resp.status_code in (204, 404):
                return layer, None
            if resp.status_code >= 400:
                layer.error = (resp.text or "")[:200]
                return layer, None
            return layer, resp.json()
        except Exception as exc:
            layer.error = str(exc)[:200]
            return layer, None

    try:
        cat_url = f"{base}/itens/{n_item}" if n_item else f"{base}/itens"
        layer_cat, cat_json = await _hit("catalogo_item" if n_item else "catalogo_lista", cat_url)
        report.layers.append(layer_cat)
        item_row: Optional[Dict[str, Any]] = None
        if n_item and isinstance(cat_json, dict):
            item_row = cat_json
            report.situacao_item = str(
                cat_json.get("situacaoCompraItemNome") or cat_json.get("situacaoCompraItem") or ""
            ).strip()
            tr = cat_json.get("temResultado")
            report.tem_resultado = bool(tr) if tr is not None else None
            res = resolve_from_item_catalog_row(cat_json, situacao_compra=situacao_compra)
            if res.cnpj_fornecedor or res.fornecedor:
                layer_cat.found_supplier = True
                _apply_resolution(report, res)
                report.gap_reason = GAP_OK
                return report

        if n_item:
            res_url = f"{base}/itens/{n_item}/resultados"
            layer_res, res_json = await _hit("resultados_item", res_url)
            report.layers.append(layer_res)
            if layer_res.status_code == 204:
                report.gap_reason = GAP_RESULTADOS_204
            elif layer_res.status_code == 404:
                report.gap_reason = GAP_RESULTADOS_404
            elif layer_res.error:
                report.gap_reason = GAP_HTTP_ERROR
            elif res_json is not None:
                res = resolve_from_resultados_payload(
                    res_json, numero_item=n_item, situacao_compra=situacao_compra
                )
                if res.cnpj_fornecedor or res.fornecedor:
                    layer_res.found_supplier = True
                    _apply_resolution(report, res)
                    report.gap_reason = GAP_OK
                    return report
                report.gap_reason = GAP_RESULTADOS_EMPTY

        ct_url = f"{PNCP_PNCP_API_BASE_URL}/v1/orgaos/{cnpj}/contratos/contratacao/{ano}/{seq}"
        layer_ct, ct_json = await _hit(
            "contratos_contratacao",
            ct_url,
            params={"pagina": 1, "tamanhoPagina": 50},
        )
        report.layers.append(layer_ct)
        if layer_ct.status_code == 404 and report.gap_reason in ("", GAP_RESULTADOS_204):
            report.gap_reason = GAP_CONTRATO_404
        elif ct_json is not None:
            res = resolve_from_contratos_payload(
                ct_json, numero_item=n_item or None, situacao_compra=situacao_compra
            )
            if res.cnpj_fornecedor or res.fornecedor:
                layer_ct.found_supplier = True
                _apply_resolution(report, res)
                report.gap_reason = GAP_OK
                return report
            if report.gap_reason in ("", GAP_RESULTADOS_204, GAP_CONTRATO_404):
                report.gap_reason = GAP_CONTRATO_EMPTY

        if report.gap_reason in ("", GAP_RESULTADOS_EMPTY):
            report.gap_reason = GAP_CATALOG_SEM_FORNECEDOR
    finally:
        if close:
            await client.aclose()

    return report


def _apply_resolution(report: SupplierProbeReport, res: Any) -> None:
    api = resolution_to_api_dict(res)
    report.cnpj_fornecedor = str(api.get("cnpj_fornecedor") or "")
    report.fornecedor = str(api.get("fornecedor") or "")
    report.fornecedor_fonte = str(api.get("fornecedor_fonte") or api.get("fornecedor_fonte_nome") or "")


def summarize_reports(reports: List[SupplierProbeReport]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for r in reports:
        key = r.gap_reason or "unknown"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: -x[1]))
