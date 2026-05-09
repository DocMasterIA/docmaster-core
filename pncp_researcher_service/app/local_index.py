from __future__ import annotations

import json
import re
import sqlite3
import zlib
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

from .config import (
    PNCP_LOCAL_BACKFILL_MONTHS,
    PNCP_LOCAL_DB_PATH,
    PNCP_LOCAL_INCLUDE_ITEMS,
    PNCP_MODALIDADES_DEFAULT,
)
from .pncp_client import PNCPClientError, create_pncp_http_client, get_contract_items, search_contracts
from .search_text_clean import apply_item_display_cleanup, normalize_for_search


def _sqlite_pncp_search_norm(value: Any) -> str:
    """Função SQLite: mesmo pipeline de `normalize_for_search` para cruzar município PNCP × lista do usuário."""
    return normalize_for_search(str(value) if value is not None else "")


@contextmanager
def _conn():
    conn = sqlite3.connect(PNCP_LOCAL_DB_PATH)
    try:
        conn.row_factory = sqlite3.Row
        conn.create_function("pncp_search_norm", 1, _sqlite_pncp_search_norm)
        yield conn
        conn.commit()
    finally:
        conn.close()


def ensure_local_index() -> None:
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS pncp_contratos (
                numero_pncp TEXT PRIMARY KEY,
                ano_compra INTEGER,
                sequencial_compra INTEGER,
                objeto TEXT,
                orgao TEXT,
                municipio TEXT,
                uf TEXT,
                modalidade_codigo INTEGER,
                modalidade_nome TEXT,
                valor_global REAL,
                situacao TEXT,
                data_publicacao TEXT,
                updated_at TEXT NOT NULL,
                raw_json TEXT NOT NULL
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS pncp_itens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_pncp TEXT NOT NULL,
                ano_compra INTEGER,
                sequencial_compra INTEGER,
                numero_item TEXT,
                descricao TEXT,
                material_servico TEXT,
                quantidade REAL,
                unidade_medida TEXT,
                valor_unitario REAL,
                valor_total REAL,
                orgao TEXT,
                municipio TEXT,
                uf TEXT,
                modalidade_nome TEXT,
                data_publicacao TEXT,
                item_fingerprint TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                raw_json_zlib BLOB,
                UNIQUE(numero_pncp, item_fingerprint)
            )
            """
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_pncp_objeto ON pncp_contratos(objeto)"
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_pncp_uf_municipio ON pncp_contratos(uf, municipio)"
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_pncp_modalidade ON pncp_contratos(modalidade_codigo)"
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_pncp_data_pub ON pncp_contratos(data_publicacao)"
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_pncp_itens_desc ON pncp_itens(descricao)"
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_pncp_itens_pncp ON pncp_itens(numero_pncp)"
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_pncp_itens_uf_municipio ON pncp_itens(uf, municipio)"
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS pesquisador_sessoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT,
                termo_busca TEXT NOT NULL,
                filtros_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'aberta',
                modelo_cotacao TEXT NOT NULL DEFAULT 'pesquisa_precos_padrao',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        _migrate_pesquisador_sessoes_columns(c)
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS pesquisador_sessao_itens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sessao_id INTEGER NOT NULL,
                numero_pncp TEXT,
                ano_compra INTEGER,
                sequencial_compra INTEGER,
                numero_item TEXT,
                descricao_item TEXT,
                quantidade REAL,
                unidade_medida TEXT,
                valor_unitario REAL,
                valor_total REAL,
                orgao TEXT,
                municipio TEXT,
                uf TEXT,
                modalidade TEXT,
                source_json_zlib BLOB,
                created_at TEXT NOT NULL,
                FOREIGN KEY(sessao_id) REFERENCES pesquisador_sessoes(id)
            )
            """
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_pesq_sess_created ON pesquisador_sessoes(created_at DESC)"
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_pesq_sess_itens_sessao ON pesquisador_sessao_itens(sessao_id)"
        )


def _migrate_pesquisador_sessoes_columns(c: sqlite3.Cursor) -> None:
    """Compatibiliza bases antigas sem modelo_cotacao."""
    cols = {row[1] for row in c.execute("PRAGMA table_info(pesquisador_sessoes)")}
    if "modelo_cotacao" not in cols:
        c.execute(
            """
            ALTER TABLE pesquisador_sessoes
            ADD COLUMN modelo_cotacao TEXT DEFAULT 'pesquisa_precos_padrao'
            """
        )


def _objeto(raw: Dict[str, Any]) -> str:
    for k in ("objetoCompra", "objeto", "descricaoObjeto", "titulo"):
        v = raw.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def upsert_contracts(raw_items: Iterable[Dict[str, Any]]) -> int:
    ensure_local_index()
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    count = 0
    with _conn() as c:
        for raw in raw_items:
            if not isinstance(raw, dict):
                continue
            numero = str(raw.get("numeroControlePNCP") or "").strip()
            if not numero:
                continue
            org = raw.get("orgaoEntidade") or {}
            unid = raw.get("unidadeOrgao") or {}
            valor = raw.get("valorTotalEstimado")
            try:
                valor_f = float(valor) if valor is not None else None
            except Exception:
                valor_f = None
            c.execute(
                """
                INSERT INTO pncp_contratos (
                    numero_pncp, ano_compra, sequencial_compra, objeto, orgao, municipio, uf,
                    modalidade_codigo, modalidade_nome, valor_global, situacao, data_publicacao,
                    updated_at, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(numero_pncp) DO UPDATE SET
                    ano_compra=excluded.ano_compra,
                    sequencial_compra=excluded.sequencial_compra,
                    objeto=excluded.objeto,
                    orgao=excluded.orgao,
                    municipio=excluded.municipio,
                    uf=excluded.uf,
                    modalidade_codigo=excluded.modalidade_codigo,
                    modalidade_nome=excluded.modalidade_nome,
                    valor_global=excluded.valor_global,
                    situacao=excluded.situacao,
                    data_publicacao=excluded.data_publicacao,
                    updated_at=excluded.updated_at,
                    raw_json=excluded.raw_json
                """,
                (
                    numero,
                    raw.get("anoCompra"),
                    raw.get("sequencialCompra"),
                    _objeto(raw),
                    org.get("razaoSocial") or org.get("razaosocial"),
                    unid.get("municipioNome"),
                    unid.get("ufSigla"),
                    raw.get("modalidadeId"),
                    raw.get("modalidadeNome"),
                    valor_f,
                    raw.get("situacaoCompraNome"),
                    raw.get("dataPublicacaoPncp") or raw.get("dataPublicacao"),
                    now,
                    json.dumps(raw, ensure_ascii=False),
                ),
            )
            count += 1
    return count


def _safe_float(v: Any) -> Optional[float]:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except Exception:
        return None


def _item_desc(raw: Dict[str, Any]) -> str:
    for k in ("descricao", "descricaoItem", "descricaoResumida", "item", "nomeItem"):
        v = raw.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def upsert_contract_items(raw_contract: Dict[str, Any], item_rows: Iterable[Dict[str, Any]]) -> int:
    numero = str(raw_contract.get("numeroControlePNCP") or "").strip()
    if not numero:
        return 0
    org = raw_contract.get("orgaoEntidade") or {}
    unid = raw_contract.get("unidadeOrgao") or {}
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    ano = raw_contract.get("anoCompra")
    seq = raw_contract.get("sequencialCompra")
    modalidade_nome = raw_contract.get("modalidadeNome")
    data_pub = raw_contract.get("dataPublicacaoPncp") or raw_contract.get("dataPublicacao")
    count = 0
    with _conn() as c:
        for r in item_rows:
            if not isinstance(r, dict):
                continue
            desc = _item_desc(r)
            if not desc:
                continue
            numero_item = str(
                r.get("numeroItem") or r.get("ordemItem") or r.get("sequencialItem") or ""
            ).strip()
            qtd = _safe_float(r.get("quantidade"))
            valor_unit = _safe_float(
                r.get("valorUnitarioEstimado") or r.get("valorUnitarioHomologado")
            )
            valor_total = _safe_float(r.get("valorTotal") or r.get("valorTotalEstimado") or r.get("valorTotalHomologado"))
            material_servico = str(r.get("materialOuServicoNome") or r.get("tipoItemNome") or "").strip()
            unidade = str(r.get("unidadeMedida") or r.get("unidadeFornecimentoNome") or "").strip()
            fingerprint = f"{numero_item}|{desc}|{qtd}|{unidade}|{valor_unit}|{valor_total}"
            raw_blob = zlib.compress(json.dumps(r, ensure_ascii=False).encode("utf-8"), level=6)
            c.execute(
                """
                INSERT INTO pncp_itens (
                    numero_pncp, ano_compra, sequencial_compra, numero_item, descricao, material_servico,
                    quantidade, unidade_medida, valor_unitario, valor_total, orgao, municipio, uf,
                    modalidade_nome, data_publicacao, item_fingerprint, updated_at, raw_json_zlib
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(numero_pncp, item_fingerprint) DO UPDATE SET
                    ano_compra=excluded.ano_compra,
                    sequencial_compra=excluded.sequencial_compra,
                    numero_item=excluded.numero_item,
                    descricao=excluded.descricao,
                    material_servico=excluded.material_servico,
                    quantidade=excluded.quantidade,
                    unidade_medida=excluded.unidade_medida,
                    valor_unitario=excluded.valor_unitario,
                    valor_total=excluded.valor_total,
                    orgao=excluded.orgao,
                    municipio=excluded.municipio,
                    uf=excluded.uf,
                    modalidade_nome=excluded.modalidade_nome,
                    data_publicacao=excluded.data_publicacao,
                    updated_at=excluded.updated_at,
                    raw_json_zlib=excluded.raw_json_zlib
                """,
                (
                    numero,
                    ano,
                    seq,
                    numero_item,
                    desc,
                    material_servico,
                    qtd,
                    unidade,
                    valor_unit,
                    valor_total,
                    org.get("razaoSocial") or org.get("razaosocial"),
                    unid.get("municipioNome"),
                    unid.get("ufSigla"),
                    modalidade_nome,
                    data_pub,
                    fingerprint,
                    now,
                    raw_blob,
                ),
            )
            count += 1
    return count


def local_index_stats() -> Dict[str, Any]:
    ensure_local_index()
    with _conn() as c:
        total = c.execute("SELECT COUNT(*) AS n FROM pncp_contratos").fetchone()["n"]
        total_itens = c.execute("SELECT COUNT(*) AS n FROM pncp_itens").fetchone()["n"]
        by_uf_rows = c.execute(
            "SELECT COALESCE(uf,'') AS uf, COUNT(*) AS n FROM pncp_contratos GROUP BY uf ORDER BY n DESC LIMIT 27"
        ).fetchall()
        by_modal_rows = c.execute(
            "SELECT COALESCE(modalidade_nome,'') AS modalidade, COUNT(*) AS n FROM pncp_contratos GROUP BY modalidade_nome ORDER BY n DESC LIMIT 20"
        ).fetchall()
    return {
        "ok": True,
        "db_path": PNCP_LOCAL_DB_PATH,
        "total_contratos": int(total or 0),
        "total_itens": int(total_itens or 0),
        "por_uf": [{"uf": r["uf"], "total": r["n"]} for r in by_uf_rows],
        "por_modalidade": [{"modalidade": r["modalidade"], "total": r["n"]} for r in by_modal_rows],
    }


def local_search(
    termo_busca: str,
    *,
    uf: Optional[str] = None,
    codigo_modalidade: Optional[int] = None,
    limit: int = 200,
) -> Dict[str, Any]:
    ensure_local_index()
    term = (termo_busca or "").strip()
    if not term:
        return {"ok": True, "itens": [], "stats": {"total_registros": 0}}
    where = ["objeto LIKE ?"]
    params: List[Any] = [f"%{term}%"]
    if uf:
        where.append("uf = ?")
        params.append(uf)
    if codigo_modalidade is not None:
        where.append("modalidade_codigo = ?")
        params.append(int(codigo_modalidade))
    sql = f"""
        SELECT numero_pncp, objeto, orgao, municipio, uf, modalidade_nome, valor_global,
               situacao, ano_compra, sequencial_compra
        FROM pncp_contratos
        WHERE {' AND '.join(where)}
        ORDER BY updated_at DESC
        LIMIT ?
    """
    params.append(max(1, min(int(limit), 2000)))
    with _conn() as c:
        rows = c.execute(sql, params).fetchall()
    itens = [
        {
            "numero_pncp": r["numero_pncp"],
            "objeto_resumido": r["objeto"],
            "orgao": r["orgao"],
            "municipio": r["municipio"],
            "uf": r["uf"],
            "modalidade": r["modalidade_nome"],
            "valor_global": r["valor_global"],
            "situacao": r["situacao"],
            "ano_compra": r["ano_compra"],
            "sequencial_compra": r["sequencial_compra"],
            "origem": "base_local",
        }
        for r in rows
    ]
    return {"ok": True, "itens": itens, "stats": {"total_registros": len(itens)}}


def _normalize_search_text(text: str) -> str:
    return normalize_for_search(text or "")


def _token_variants(token: str) -> List[str]:
    t = _normalize_search_text(token)
    if not t:
        return []
    variants = {t}
    # plural/singular simples para aumentar recall (pneu <-> pneus)
    if t.endswith("s") and len(t) > 3:
        variants.add(t[:-1])
    else:
        variants.add(f"{t}s")
    return sorted(v for v in variants if v)


def _build_search_tokens(termo_busca: str) -> List[List[str]]:
    norm = _normalize_search_text(termo_busca)
    if not norm:
        return []
    raw_tokens = [tok for tok in norm.split(" ") if len(tok) >= 2]
    return [_token_variants(tok) for tok in raw_tokens if _token_variants(tok)]


def _row_matches_search_tokens(text: str, tokens: List[List[str]]) -> bool:
    if not tokens:
        return False
    normalized_text = _normalize_search_text(text)
    if not normalized_text:
        return False
    words = set(normalized_text.split())
    for options in tokens:
        # cada token de busca deve casar ao menos uma variante (AND entre tokens)
        matched = any((opt in words) or (opt in normalized_text) for opt in options)
        if not matched:
            return False
    return True


def _extract_esfera_from_raw_blob(raw_blob: Any) -> tuple[Optional[str], Optional[str], Optional[str]]:
    if not raw_blob:
        return None, None, None
    try:
        if isinstance(raw_blob, memoryview):
            raw_blob = raw_blob.tobytes()
        if isinstance(raw_blob, (bytes, bytearray)):
            payload = zlib.decompress(raw_blob)
            raw = json.loads(payload.decode("utf-8"))
        else:
            return None, None, None
    except Exception:
        return None, None, None
    if not isinstance(raw, dict):
        return None, None, None
    org = raw.get("orgaoEntidade") or {}
    sub = raw.get("orgaoSubRogado") or {}
    esfera = str(org.get("esferaId") or sub.get("esferaId") or "").strip().upper()
    poder = str(org.get("poderId") or sub.get("poderId") or "").strip().upper()
    if esfera == "F":
        esfera_adm = "federal"
    elif esfera == "E":
        esfera_adm = "estadual"
    elif esfera == "M":
        esfera_adm = "municipal"
    elif esfera == "D":
        esfera_adm = "distrital"
    else:
        esfera = ""
        esfera_adm = None
    return (esfera or None), esfera_adm, (poder or None)


def _extract_esfera_from_contract_raw_json(raw_json_text: Any) -> tuple[Optional[str], Optional[str], Optional[str]]:
    if not raw_json_text:
        return None, None, None
    try:
        if isinstance(raw_json_text, (bytes, bytearray, memoryview)):
            raw_json_text = bytes(raw_json_text).decode("utf-8")
        raw = json.loads(str(raw_json_text))
    except Exception:
        return None, None, None
    if not isinstance(raw, dict):
        return None, None, None
    org = raw.get("orgaoEntidade") or {}
    sub = raw.get("orgaoSubRogado") or {}
    esfera = str(org.get("esferaId") or sub.get("esferaId") or "").strip().upper()
    poder = str(org.get("poderId") or sub.get("poderId") or "").strip().upper()
    if esfera == "F":
        esfera_adm = "federal"
    elif esfera == "E":
        esfera_adm = "estadual"
    elif esfera == "M":
        esfera_adm = "municipal"
    elif esfera == "D":
        esfera_adm = "distrital"
    else:
        esfera = ""
        esfera_adm = None
    return (esfera or None), esfera_adm, (poder or None)


def _normalize_recortes_geograficos(recortes_geograficos: Optional[List[Any]]) -> List[Dict[str, Optional[str]]]:
    out: List[Dict[str, Optional[str]]] = []
    if not recortes_geograficos:
        return out
    seen: set = set()
    for raw in recortes_geograficos:
        if raw is None:
            continue
        if isinstance(raw, dict):
            u = str(raw.get("uf") or "").strip().upper()[:2]
            m_raw = raw.get("municipio")
        else:
            u = str(getattr(raw, "uf", "") or "").strip().upper()[:2]
            m_raw = getattr(raw, "municipio", None)
        if len(u) != 2:
            continue
        m = (str(m_raw).strip() if m_raw is not None else "") or None
        key = (u, m or "")
        if key in seen:
            continue
        seen.add(key)
        out.append({"uf": u, "municipio": m})
        if len(out) >= 30:
            break
    return out


def local_item_search(
    termo_busca: str,
    *,
    uf: Optional[str] = None,
    municipio: Optional[str] = None,
    recortes_geograficos: Optional[List[Any]] = None,
    codigo_modalidade: Optional[int] = None,
    limit: int = 500,
    cleanup_for_display: bool = True,
) -> Dict[str, Any]:
    ensure_local_index()
    token_groups = _build_search_tokens(termo_busca)
    if not token_groups:
        return {"ok": True, "itens": [], "stats": {"total_registros": 0}}
    # Anchor no SQL para reduzir leitura; match final é feito em Python com variações de token.
    anchor = token_groups[0][0]
    where = ["i.descricao LIKE ?"]
    params: List[Any] = [f"%{anchor}%"]
    rec_norm = _normalize_recortes_geograficos(recortes_geograficos)
    if rec_norm:
        geo_parts: List[str] = []
        for r in rec_norm:
            if r.get("municipio"):
                geo_parts.append(
                    "(i.uf = ? AND pncp_search_norm(COALESCE(i.municipio,'')) = pncp_search_norm(?))"
                )
                params.append(r["uf"])
                params.append(r["municipio"])
            else:
                geo_parts.append("(i.uf = ?)")
                params.append(r["uf"])
        where.append("(" + " OR ".join(geo_parts) + ")")
    elif uf:
        where.append("i.uf = ?")
        params.append(uf)
        muni = (municipio or "").strip()
        if muni:
            where.append("pncp_search_norm(COALESCE(i.municipio, '')) = pncp_search_norm(?)")
            params.append(muni)
    else:
        muni = (municipio or "").strip()
        if muni:
            where.append("pncp_search_norm(COALESCE(i.municipio, '')) = pncp_search_norm(?)")
            params.append(muni)
    if codigo_modalidade is not None:
        modalidade_patterns = {
            6: ["concorr"],
            7: ["chamada publica", "chamada pública"],
            8: ["pregao", "pregão"],
            9: ["dispensa", "compra direta"],
            10: ["inexigibilidade"],
            11: ["leilao", "leilão"],
            12: ["concurso"],
            13: ["dialogo competitivo", "diálogo competitivo"],
        }.get(int(codigo_modalidade), [])
        if modalidade_patterns:
            where.append(
                "(" + " OR ".join(["LOWER(COALESCE(i.modalidade_nome, '')) LIKE ?" for _ in modalidade_patterns]) + ")"
            )
            params.extend([f"%{pattern}%" for pattern in modalidade_patterns])
    sql = f"""
        SELECT i.numero_pncp, i.ano_compra, i.sequencial_compra, i.numero_item, i.descricao, i.material_servico,
               i.quantidade, i.unidade_medida, i.valor_unitario, i.valor_total, i.orgao, i.municipio, i.uf,
               i.modalidade_nome, i.data_publicacao, i.raw_json_zlib, c.raw_json AS contrato_raw_json
        FROM pncp_itens i
        LEFT JOIN pncp_contratos c ON c.numero_pncp = i.numero_pncp
        WHERE {' AND '.join(where)}
        ORDER BY i.updated_at DESC
        LIMIT ?
    """
    sql_limit = max(1, min(int(limit) * 8, 20000))
    params.append(sql_limit)
    with _conn() as c:
        rows = c.execute(sql, params).fetchall()
    itens = []
    for r in rows:
        desc = r["descricao"] or ""
        mat = r["material_servico"] or ""
        texto_item = f"{desc} {mat}".strip()
        if not _row_matches_search_tokens(texto_item, token_groups):
            continue
        esfera_id, esfera_adm, poder_id = _extract_esfera_from_raw_blob(r["raw_json_zlib"])
        if not esfera_id:
            esfera_id, esfera_adm, poder_id = _extract_esfera_from_contract_raw_json(r["contrato_raw_json"])
        entry: Dict[str, Any] = {
            "numero_pncp": r["numero_pncp"],
            "ano_compra": r["ano_compra"],
            "sequencial_compra": r["sequencial_compra"],
            "numero_item": r["numero_item"],
            "descricao_item": r["descricao"],
            "material_servico": r["material_servico"],
            "quantidade": r["quantidade"],
            "unidade_medida": r["unidade_medida"],
            "valor_unitario": r["valor_unitario"],
            "valor_total": r["valor_total"],
            "orgao": r["orgao"],
            "municipio": r["municipio"],
            "uf": r["uf"],
            "modalidade": r["modalidade_nome"],
            "data_publicacao": r["data_publicacao"],
            "esfera_id": esfera_id,
            "esfera_administrativa": esfera_adm,
            "poder_id": poder_id,
            "origem": "base_local_itens",
        }
        if cleanup_for_display:
            apply_item_display_cleanup(entry)
        itens.append(entry)
        if len(itens) >= max(1, min(int(limit), 5000)):
            break
    return {"ok": True, "itens": itens, "stats": {"total_registros": len(itens)}}


def create_research_session(
    *,
    titulo: str,
    termo_busca: str,
    modelo_cotacao: str = "pesquisa_precos_padrao",
    filtros: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ensure_local_index()
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    filtros_json = json.dumps(filtros or {}, ensure_ascii=False)
    titulo_s = (titulo or "").strip()
    termo_s = (termo_busca or "").strip()
    modelo_s = (modelo_cotacao or "").strip() or "pesquisa_precos_padrao"
    with _conn() as c:
        cur = c.execute(
            """
            INSERT INTO pesquisador_sessoes (
                titulo, termo_busca, filtros_json, status, modelo_cotacao, created_at, updated_at
            )
            VALUES (?, ?, ?, 'aberta', ?, ?, ?)
            """,
            (titulo_s, termo_s, filtros_json, modelo_s, now, now),
        )
        sessao_id = int(cur.lastrowid)
    cotacao = {
        "id": sessao_id,
        "titulo": titulo_s,
        "termo_busca": termo_s,
        "modelo_cotacao": modelo_s,
        "filtros": filtros or {},
        "status": "aberta",
        "created_at": now,
    }
    return {
        "ok": True,
        "sessao_id": sessao_id,
        "cotacao_id": sessao_id,
        "titulo": titulo_s,
        "termo_busca": termo_s,
        "modelo_cotacao": modelo_s,
        "filtros": filtros or {},
        "status": "aberta",
        "created_at": now,
        "cotacao": cotacao,
    }


def add_items_to_research_session(sessao_id: int, itens: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    ensure_local_index()
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    inserted = 0
    with _conn() as c:
        row = c.execute(
            "SELECT id FROM pesquisador_sessoes WHERE id = ?",
            (int(sessao_id),),
        ).fetchone()
        if not row:
            return {"ok": False, "error": "Sessão não encontrada.", "sessao_id": int(sessao_id)}
        for it in itens or []:
            if not isinstance(it, dict):
                continue
            source_blob = zlib.compress(json.dumps(it, ensure_ascii=False).encode("utf-8"), level=6)
            c.execute(
                """
                INSERT INTO pesquisador_sessao_itens (
                    sessao_id, numero_pncp, ano_compra, sequencial_compra, numero_item, descricao_item,
                    quantidade, unidade_medida, valor_unitario, valor_total, orgao, municipio, uf, modalidade,
                    source_json_zlib, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(sessao_id),
                    it.get("numero_pncp"),
                    it.get("ano_compra"),
                    it.get("sequencial_compra"),
                    it.get("numero_item"),
                    it.get("descricao_item") or it.get("descricao") or it.get("objeto_resumido"),
                    _safe_float(it.get("quantidade")),
                    it.get("unidade_medida"),
                    _safe_float(it.get("valor_unitario")),
                    _safe_float(it.get("valor_total")) or _safe_float(it.get("valor_global")),
                    it.get("orgao"),
                    it.get("municipio"),
                    it.get("uf"),
                    it.get("modalidade"),
                    source_blob,
                    now,
                ),
            )
            inserted += 1
        c.execute(
            "UPDATE pesquisador_sessoes SET updated_at = ? WHERE id = ?",
            (now, int(sessao_id)),
        )
    return {"ok": True, "sessao_id": int(sessao_id), "itens_inseridos": inserted}


def get_research_session(sessao_id: int) -> Dict[str, Any]:
    ensure_local_index()
    with _conn() as c:
        s = c.execute(
            """
            SELECT id, titulo, termo_busca, filtros_json, status, modelo_cotacao, created_at, updated_at
            FROM pesquisador_sessoes
            WHERE id = ?
            """,
            (int(sessao_id),),
        ).fetchone()
        if not s:
            return {"ok": False, "error": "Sessão não encontrada.", "sessao_id": int(sessao_id)}
        rows = c.execute(
            """
            SELECT id, numero_pncp, ano_compra, sequencial_compra, numero_item, descricao_item,
                   quantidade, unidade_medida, valor_unitario, valor_total, orgao, municipio, uf, modalidade, created_at
            FROM pesquisador_sessao_itens
            WHERE sessao_id = ?
            ORDER BY id DESC
            """,
            (int(sessao_id),),
        ).fetchall()
    return {
        "ok": True,
        "sessao": {
            "id": s["id"],
            "titulo": s["titulo"],
            "termo_busca": s["termo_busca"],
            "modelo_cotacao": s["modelo_cotacao"] or "pesquisa_precos_padrao",
            "filtros": json.loads(s["filtros_json"] or "{}"),
            "status": s["status"],
            "created_at": s["created_at"],
            "updated_at": s["updated_at"],
        },
        "itens": [
            {
                "id": r["id"],
                "numero_pncp": r["numero_pncp"],
                "ano_compra": r["ano_compra"],
                "sequencial_compra": r["sequencial_compra"],
                "numero_item": r["numero_item"],
                "descricao_item": r["descricao_item"],
                "quantidade": r["quantidade"],
                "unidade_medida": r["unidade_medida"],
                "valor_unitario": r["valor_unitario"],
                "valor_total": r["valor_total"],
                "orgao": r["orgao"],
                "municipio": r["municipio"],
                "uf": r["uf"],
                "modalidade": r["modalidade"],
                "created_at": r["created_at"],
            }
            for r in rows
        ],
        "stats": {"total_itens": len(rows)},
    }


def list_research_sessions(limit: int = 100) -> Dict[str, Any]:
    ensure_local_index()
    with _conn() as c:
        rows = c.execute(
            """
            SELECT s.id, s.titulo, s.termo_busca, s.status, s.modelo_cotacao, s.created_at, s.updated_at,
                   (SELECT COUNT(*) FROM pesquisador_sessao_itens si WHERE si.sessao_id = s.id) AS total_itens
            FROM pesquisador_sessoes s
            ORDER BY s.id DESC
            LIMIT ?
            """,
            (max(1, min(int(limit), 1000)),),
        ).fetchall()
    return {
        "ok": True,
        "sessoes": [
            {
                "id": r["id"],
                "titulo": r["titulo"],
                "termo_busca": r["termo_busca"],
                "modelo_cotacao": r["modelo_cotacao"] or "pesquisa_precos_padrao",
                "status": r["status"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "total_itens": r["total_itens"],
            }
            for r in rows
        ],
    }


def update_research_session(
    sessao_id: int,
    *,
    titulo: Optional[str] = None,
    status: Optional[str] = None,
    termo_busca: Optional[str] = None,
    modelo_cotacao: Optional[str] = None,
) -> Dict[str, Any]:
    ensure_local_index()
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    with _conn() as c:
        row = c.execute(
            "SELECT id, titulo, status, termo_busca, modelo_cotacao FROM pesquisador_sessoes WHERE id = ?",
            (int(sessao_id),),
        ).fetchone()
        if not row:
            return {"ok": False, "error": "Sessão não encontrada.", "sessao_id": int(sessao_id)}

        next_titulo = row["titulo"] if titulo is None else str(titulo).strip()
        next_status = row["status"] if status is None else str(status).strip() or row["status"]
        next_termo = row["termo_busca"]
        if termo_busca is not None:
            t = str(termo_busca).strip()
            if t:
                next_termo = t
        base_modelo = row["modelo_cotacao"] or "pesquisa_precos_padrao"
        next_modelo = base_modelo
        if modelo_cotacao is not None:
            m = str(modelo_cotacao).strip()
            if m:
                next_modelo = m

        c.execute(
            """
            UPDATE pesquisador_sessoes
            SET titulo = ?, status = ?, termo_busca = ?, modelo_cotacao = ?, updated_at = ?
            WHERE id = ?
            """,
            (next_titulo, next_status, next_termo, next_modelo, now, int(sessao_id)),
        )

    return {
        "ok": True,
        "sessao_id": int(sessao_id),
        "titulo": next_titulo,
        "status": next_status,
        "termo_busca": next_termo,
        "modelo_cotacao": next_modelo,
        "updated_at": now,
    }


async def backfill_local_index(
    *,
    months: Optional[int] = None,
    max_paginas: Optional[int] = None,
    tamanho_pagina: int = 50,
    uf: Optional[str] = None,
    codigo_municipio_ibge: Optional[str] = None,
    include_items: Optional[bool] = None,
) -> Dict[str, Any]:
    ensure_local_index()
    m = max(1, int(months or PNCP_LOCAL_BACKFILL_MONTHS))
    end = datetime.utcnow().date()
    start = end - timedelta(days=30 * m)
    data_inicial = start.strftime("%Y%m%d")
    data_final = end.strftime("%Y%m%d")
    modalidades = PNCP_MODALIDADES_DEFAULT
    total_paginas = 0
    total_upserts = 0
    total_upserts_itens = 0
    erros_modalidade: List[Dict[str, Any]] = []
    use_items = PNCP_LOCAL_INCLUDE_ITEMS if include_items is None else bool(include_items)
    unlimited_pages = max_paginas is None or int(max_paginas) <= 0
    paginas_limite = 0 if unlimited_pages else int(max_paginas)
    async with create_pncp_http_client() as http:
        for modalidade in modalidades:
            pagina = 1
            while True:
                try:
                    batch = await search_contracts(
                        data_inicial=data_inicial,
                        data_final=data_final,
                        codigo_modalidade=modalidade,
                        uf=uf,
                        codigo_municipio_ibge=codigo_municipio_ibge,
                        pagina=pagina,
                        tamanho_pagina=tamanho_pagina,
                        client=http,
                    )
                except PNCPClientError as e:
                    erros_modalidade.append(
                        {
                            "modalidade": modalidade,
                            "pagina": pagina,
                            "erro": str(e),
                        }
                    )
                    # Em erro persistente de modalidade/página, segue para próxima modalidade.
                    break
                total_paginas += 1
                if not batch:
                    break
                total_upserts += upsert_contracts(batch)
                if use_items:
                    for raw in batch:
                        cnpj = (
                            (raw.get("orgaoEntidade") or {}).get("cnpj")
                            or (raw.get("orgaoEntidade") or {}).get("cnpjOrgaoEntidade")
                            or raw.get("cnpjOrgaoEntidade")
                        )
                        numero = str(raw.get("numeroControlePNCP") or "")
                        if (not cnpj) and "-" in numero:
                            cnpj = numero.split("-")[0]
                        ano = raw.get("anoCompra")
                        seq = raw.get("sequencialCompra")
                        if not cnpj or ano is None or seq is None:
                            continue
                        try:
                            rows = await get_contract_items(str(cnpj), ano, seq, client=http)
                        except Exception:
                            rows = []
                        if rows:
                            total_upserts_itens += upsert_contract_items(raw, rows)
                if len(batch) < 10:
                    break
                if (not unlimited_pages) and pagina >= paginas_limite:
                    break
                pagina += 1
    stats = local_index_stats()
    stats.update(
        {
            "data_inicial": data_inicial,
            "data_final": data_final,
            "meses_lookback": m,
            "paginas_processadas": total_paginas,
            "upserts_executados": total_upserts,
            "upserts_itens_executados": total_upserts_itens,
            "include_items": use_items,
            "unbounded_paginas": unlimited_pages,
            "max_paginas_efetivo": None if unlimited_pages else paginas_limite,
            "erros_modalidade": erros_modalidade,
        }
    )
    return stats
