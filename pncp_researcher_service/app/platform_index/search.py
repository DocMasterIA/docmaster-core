from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .connection import platform_conn
from .registry import PlatformIndexSpec


def _first_token(term: str) -> str:
    parts = re.split(r"\s+", (term or "").strip())
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
    Busca FTS5 na camada platform_itens_leitura.
    Retorna dicts compatíveis com mapeamento para MarketPriceHit.
    """
    if not spec.db_path or not spec.db_exists():
        return []

    anchor = _first_token(termo)
    if not anchor or len(anchor) < 2:
        return []

    fts_query = f'"{anchor}"*'
    params: List[Any] = [fts_query]
    where_geo = ""
    if uf:
        where_geo = " AND i.uf = ?"
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
            i.orgao,
            i.municipio,
            i.uf,
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
        WHERE platform_itens_fts MATCH ?
        {where_geo}
        ORDER BY fts_rank
        LIMIT ?
    """

    try:
        with platform_conn(spec.db_path) as c:
            rows = c.execute(sql, params).fetchall()
    except Exception:
        # Fallback LIKE se FTS vazio ou erro de sintaxe
        like = f"%{anchor}%"
        like_params: List[Any] = [like]
        if uf:
            like_params.append(uf.strip().upper()[:2])
        like_params.append(max(1, min(int(limit), 5000)))
        like_sql = f"""
            SELECT * FROM platform_itens_leitura i
            WHERE i.descricao LIKE ?
            {" AND i.uf = ?" if uf else ""}
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
