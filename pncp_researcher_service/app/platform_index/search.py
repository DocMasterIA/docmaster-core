from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .connection import platform_conn
from .registry import PlatformIndexSpec


def _first_token(term: str) -> str:
    parts = re.split(r"\s+", (term or "").strip())
    return parts[0] if parts else ""


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
