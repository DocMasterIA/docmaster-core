from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .connection import platform_conn
from .registry import PlatformIndexSpec


def _escape_fts_token(token: str) -> str:
    return re.sub(r'["*]', " ", (token or "")).strip()


def resolve_platform_fts_anchor(termo: str) -> str:
    """
    Mesma âncora FTS do PNCP local: preprocess + cabeça do tier core/anchor
    (fallback: 1º token group do termo processado).
    """
    from ..local_index import (
        _build_search_tokens,
        _token_group_head,
        build_search_query_tiers,
    )
    from ..search_text_clean import preprocess_cotacao_search_term

    raw = (termo or "").strip()
    if not raw:
        return ""
    search_tiers = build_search_query_tiers(raw)
    for tier in search_tiers:
        if tier.label in ("anchor", "core") and tier.token_groups:
            head = _token_group_head(tier.token_groups[0])
            if head:
                return head
    pre = preprocess_cotacao_search_term(raw) or raw
    groups = _build_search_tokens(pre)
    if groups:
        head = _token_group_head(groups[0])
        if head:
            return head
    parts = re.split(r"\s+", pre.strip())
    return parts[0] if parts else ""


def _is_licitacon_process_url(url: str) -> bool:
    u = (url or "").strip()
    if not u.lower().startswith("http"):
        return False
    # Página de busca genérica (:19:) não serve como link de processo.
    if re.search(r"f\?p=50500:19:", u, flags=re.I):
        return False
    return "portal.tce.rs.gov.br" in u.lower() or "P10_ID_LICITACAO" in u.upper()


def _url_from_processo_raw_blob(raw_blob: Any) -> Optional[str]:
    if not raw_blob:
        return None
    try:
        import zlib
        import json

        data = json.loads(zlib.decompress(raw_blob).decode("utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    for key in (
        "link_licitacon_cidadao",
        "LINK_LICITACON_CIDADAO",
        "url_origem",
        "link",
    ):
        cand = str(data.get(key) or "").strip()
        if _is_licitacon_process_url(cand):
            return cand
    return None


def lookup_portal_urls(
    spec: PlatformIndexSpec,
    *,
    keys: List[str],
) -> Dict[str, str]:
    """
    Resolve deep-links LicitaCon por processo_id / plataforma_item_id / numero_processo.
    Usado para cotações antigas salvas sem url_origem no JSON.
    """
    if not spec.db_path or not spec.db_exists():
        return {}
    cleaned: List[str] = []
    seen: set[str] = set()
    for raw in keys or []:
        k = str(raw or "").strip()
        if not k or k in seen:
            continue
        seen.add(k)
        cleaned.append(k)
        # Aceita chave sem prefixo da plataforma.
        if ":" in k and not k.startswith(f"{spec.id}:"):
            alt = f"{spec.id}:{k}"
            if alt not in seen:
                seen.add(alt)
                cleaned.append(alt)
        if k.startswith(f"{spec.id}:"):
            alt = k[len(spec.id) + 1 :]
            if alt and alt not in seen:
                seen.add(alt)
                cleaned.append(alt)
    if not cleaned:
        return {}

    out: Dict[str, str] = {}
    placeholders = ",".join("?" for _ in cleaned)
    sql = f"""
        SELECT processo_id, plataforma_item_id, numero_processo, url_origem
        FROM platform_itens_leitura
        WHERE url_origem IS NOT NULL AND trim(url_origem) != ''
          AND (
            processo_id IN ({placeholders})
            OR plataforma_item_id IN ({placeholders})
            OR numero_processo IN ({placeholders})
          )
        LIMIT 500
    """
    params = cleaned * 3
    try:
        with platform_conn(spec.db_path) as c:
            rows = c.execute(sql, params).fetchall()
            missing_proc: List[str] = []
            for row in rows:
                url = str(row["url_origem"] or "").strip()
                if not _is_licitacon_process_url(url):
                    continue
                for key in (
                    row["processo_id"],
                    row["plataforma_item_id"],
                    row["numero_processo"],
                ):
                    k = str(key or "").strip()
                    if k:
                        out[k] = url
            # Fallback: raw da licitação (bases ingeridas sem url na leitura).
            for key in cleaned:
                if key in out:
                    continue
                missing_proc.append(key)
            if missing_proc:
                ph2 = ",".join("?" for _ in missing_proc)
                prow = c.execute(
                    f"""
                    SELECT id, raw_json_zlib FROM platform_processos
                    WHERE id IN ({ph2})
                    LIMIT 200
                    """,
                    missing_proc,
                ).fetchall()
                for row in prow:
                    url = _url_from_processo_raw_blob(row["raw_json_zlib"])
                    if url:
                        out[str(row["id"])] = url
    except Exception:
        return out
    return out


def platform_item_search(
    spec: PlatformIndexSpec,
    *,
    termo: str,
    uf: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Busca FTS5 na camada platform_itens_leitura — mesma âncora do PNCP local.
    Retorna dicts compatíveis com mapeamento para MarketPriceHit.
    """
    if not spec.db_path or not spec.db_exists():
        return []

    anchor = resolve_platform_fts_anchor(termo)
    anchor = _escape_fts_token(anchor)
    if not anchor or len(anchor) < 2:
        return []

    fts_query = f'"{anchor}"*'
    params: List[Any] = [fts_query]
    where_geo = ""
    if uf:
        where_geo = (
            " AND COALESCE(NULLIF(trim(i.uf), ''), NULLIF(trim(p.uf), '')) = ?"
        )
        params.append(uf.strip().upper()[:2])

    params.append(max(1, min(int(limit), 5000)))

    sql = f"""
        SELECT
            i.plataforma,
            i.plataforma_item_id,
            i.processo_id,
            i.numero_item,
            i.descricao,
            i.material_servico,
            i.valor_unitario,
            i.valor_unitario_homologado,
            i.unidade_medida,
            i.quantidade,
            COALESCE(NULLIF(trim(i.orgao), ''), NULLIF(trim(p.orgao), '')) AS orgao,
            COALESCE(NULLIF(trim(i.municipio), ''), NULLIF(trim(p.municipio), '')) AS municipio,
            COALESCE(NULLIF(trim(i.uf), ''), NULLIF(trim(p.uf), '')) AS uf,
            COALESCE(NULLIF(trim(i.modalidade), ''), NULLIF(trim(p.modalidade), '')) AS modalidade,
            i.fornecedor_nome,
            i.cnpj_fornecedor,
            i.data_referencia,
            i.inciso_classificacao,
            i.esfera,
            i.url_origem,
            i.numero_pncp,
            i.numero_processo,
            bm25(platform_itens_fts) AS fts_rank
        FROM platform_itens_fts
        JOIN platform_itens_leitura i ON i.id = platform_itens_fts.rowid
        LEFT JOIN platform_processos p ON p.id = i.processo_id
        WHERE platform_itens_fts MATCH ?
        {where_geo}
        ORDER BY fts_rank
        LIMIT ?
    """

    try:
        with platform_conn(spec.db_path) as c:
            rows = c.execute(sql, params).fetchall()
    except Exception:
        # Fallback LIKE (desc + material_servico), mesma âncora PNCP.
        like = f"%{anchor}%"
        like_params: List[Any] = [like, like]
        if uf:
            like_params.append(uf.strip().upper()[:2])
        like_params.append(max(1, min(int(limit), 5000)))
        like_sql = f"""
            SELECT
              i.*,
              COALESCE(NULLIF(trim(i.orgao), ''), NULLIF(trim(p.orgao), '')) AS orgao,
              COALESCE(NULLIF(trim(i.municipio), ''), NULLIF(trim(p.municipio), '')) AS municipio,
              COALESCE(NULLIF(trim(i.uf), ''), NULLIF(trim(p.uf), '')) AS uf
            FROM platform_itens_leitura i
            LEFT JOIN platform_processos p ON p.id = i.processo_id
            WHERE (i.descricao LIKE ? OR COALESCE(i.material_servico, '') LIKE ?)
            {" AND COALESCE(NULLIF(trim(i.uf), ''), NULLIF(trim(p.uf), '')) = ?" if uf else ""}
            LIMIT ?
        """
        with platform_conn(spec.db_path) as c:
            rows = c.execute(like_sql, like_params).fetchall()

    out: List[Dict[str, Any]] = []
    for row in rows:
        d = dict(row)
        d["descricao_item"] = d.get("descricao") or ""
        d["fornecedor"] = d.get("fornecedor_nome")
        d["data_publicacao"] = d.get("data_referencia")
        out.append(d)
    return out
