"""
Materialize Compras.gov → platform_index (processos + itens de leitura/bruto).
"""
from __future__ import annotations

import hashlib
import json
import zlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ...connection import platform_conn
from ...schema import ensure_platform_index, platform_index_stats
from .config import PLATFORM_ID


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _compress_json(data: Dict[str, Any]) -> bytes:
    return zlib.compress(json.dumps(data, ensure_ascii=False).encode("utf-8"), level=6)


def _item_fingerprint(processo_id: str, numero_item: str, descricao: str) -> str:
    base = f"{processo_id}|{numero_item}|{(descricao or '')[:160]}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()


def ensure_compras_gov_index(*, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Cria o SQLite/schema (vazio se ainda sem ingest) e backfill de meta a partir de processos."""
    path = ensure_platform_index(PLATFORM_ID, db_path=db_path)
    backfilled = 0
    with platform_conn(path) as c:
        cur = c.execute(
            """
            UPDATE platform_itens_leitura AS i
            SET
              orgao = COALESCE(
                NULLIF(trim(i.orgao), ''),
                (SELECT NULLIF(trim(p.orgao), '') FROM platform_processos p WHERE p.id = i.processo_id)
              ),
              municipio = COALESCE(
                NULLIF(trim(i.municipio), ''),
                (SELECT NULLIF(trim(p.municipio), '') FROM platform_processos p WHERE p.id = i.processo_id)
              ),
              uf = COALESCE(
                NULLIF(trim(i.uf), ''),
                (SELECT NULLIF(trim(p.uf), '') FROM platform_processos p WHERE p.id = i.processo_id)
              ),
              modalidade = COALESCE(
                NULLIF(trim(i.modalidade), ''),
                (SELECT NULLIF(trim(p.modalidade), '') FROM platform_processos p WHERE p.id = i.processo_id)
              )
            WHERE i.plataforma = ?
              AND (
                NULLIF(trim(i.orgao), '') IS NULL
                OR NULLIF(trim(i.municipio), '') IS NULL
                OR NULLIF(trim(i.uf), '') IS NULL
                OR NULLIF(trim(i.modalidade), '') IS NULL
              )
            """,
            (PLATFORM_ID,),
        )
        backfilled = int(cur.rowcount or 0)
    stats = platform_index_stats(path)
    return {
        "ok": True,
        "platform_id": PLATFORM_ID,
        "db_path": path,
        "index_stats": stats,
        "itens_written": int(stats.get("itens_leitura") or 0),
        "meta_backfilled_rows": backfilled,
        "item_materialize_enabled": True,
    }


def materialize_compras_gov_parsed(
    parsed: Dict[str, Any],
    *,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Grava compras + itens já mapeados no platform_index.

    `parsed` esperado:
      compras: List[dict]  (map_compra_row)
      itens: List[dict]    (map_item_row, preferencialmente com join)
    """
    path = ensure_platform_index(PLATFORM_ID, db_path=db_path)
    compras: List[Dict[str, Any]] = list(parsed.get("compras") or [])
    itens: List[Dict[str, Any]] = list(parsed.get("itens") or [])
    compra_by_cod = {str(c.get("cod_compra")): c for c in compras if c.get("cod_compra")}

    now = _utc_now()
    stats = {
        "processos_upserted": 0,
        "itens_bruto_upserted": 0,
        "itens_leitura_upserted": 0,
        "itens_sem_preco": 0,
        "itens_com_homologado": 0,
        "itens_so_estimado": 0,
    }

    with platform_conn(path) as c:
        for compra in compras:
            proc_id = str(compra.get("processo_id") or "")
            if not proc_id:
                continue
            c.execute(
                """
                INSERT INTO platform_processos(
                    id, plataforma, numero_processo, numero_pncp, orgao, municipio, uf,
                    objeto, modalidade, data_publicacao, updated_at, raw_json_zlib
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    numero_processo=excluded.numero_processo,
                    numero_pncp=excluded.numero_pncp,
                    orgao=excluded.orgao,
                    municipio=excluded.municipio,
                    uf=excluded.uf,
                    objeto=excluded.objeto,
                    modalidade=COALESCE(excluded.modalidade, platform_processos.modalidade),
                    data_publicacao=excluded.data_publicacao,
                    updated_at=excluded.updated_at,
                    raw_json_zlib=excluded.raw_json_zlib
                """,
                (
                    proc_id,
                    PLATFORM_ID,
                    compra.get("numero_processo"),
                    compra.get("numero_pncp"),
                    compra.get("orgao"),
                    compra.get("municipio"),
                    compra.get("uf"),
                    compra.get("objeto"),
                    compra.get("modalidade"),
                    compra.get("data_publicacao"),
                    now,
                    _compress_json(compra),
                ),
            )
            stats["processos_upserted"] += 1

        for item in itens:
            cod = str(item.get("cod_compra") or "")
            compra = compra_by_cod.get(cod) or {}
            proc_id = str(item.get("processo_id") or compra.get("processo_id") or "")
            num_item = str(item.get("numero_item") or "").strip()
            desc = str(item.get("descricao") or "").strip()
            if not proc_id or not num_item or not desc:
                continue

            # Enrich from compra if missing
            orgao = item.get("orgao") or compra.get("orgao")
            municipio = item.get("municipio") or compra.get("municipio")
            uf = item.get("uf") or compra.get("uf")
            modalidade = item.get("modalidade") or compra.get("modalidade")
            url = item.get("url_origem") or compra.get("url_origem")
            data_ref = item.get("data_referencia") or compra.get("data_publicacao")
            numero_pncp = item.get("numero_pncp") or compra.get("numero_pncp")

            homolog = item.get("valor_unitario_homologado")
            estimado = item.get("valor_unitario")
            try:
                homolog_f = float(homolog) if homolog is not None else None
            except (TypeError, ValueError):
                homolog_f = None
            try:
                estimado_f = float(estimado) if estimado is not None else None
            except (TypeError, ValueError):
                estimado_f = None

            if homolog_f and homolog_f > 0:
                valor = homolog_f
                stats["itens_com_homologado"] += 1
            elif estimado_f and estimado_f > 0:
                valor = estimado_f
                stats["itens_so_estimado"] += 1
            else:
                stats["itens_sem_preco"] += 1
                continue

            fp = _item_fingerprint(proc_id, num_item, desc)
            plat_item_id = str(item.get("plataforma_item_id") or f"{proc_id}:{num_item}")

            c.execute(
                """
                INSERT INTO platform_itens_bruto(
                    processo_id, plataforma, numero_item, descricao, material_servico,
                    quantidade, unidade_medida, valor_unitario, valor_unitario_homologado,
                    fornecedor_nome, cnpj_fornecedor, item_fingerprint, updated_at, raw_json_zlib
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(processo_id, item_fingerprint) DO UPDATE SET
                    descricao=excluded.descricao,
                    quantidade=excluded.quantidade,
                    unidade_medida=excluded.unidade_medida,
                    valor_unitario=excluded.valor_unitario,
                    valor_unitario_homologado=excluded.valor_unitario_homologado,
                    fornecedor_nome=excluded.fornecedor_nome,
                    cnpj_fornecedor=excluded.cnpj_fornecedor,
                    updated_at=excluded.updated_at,
                    raw_json_zlib=excluded.raw_json_zlib
                """,
                (
                    proc_id,
                    PLATFORM_ID,
                    num_item,
                    desc,
                    item.get("material_servico"),
                    item.get("quantidade"),
                    item.get("unidade_medida"),
                    float(valor),
                    float(homolog_f) if homolog_f and homolog_f > 0 else None,
                    item.get("fornecedor_nome"),
                    item.get("cnpj_fornecedor"),
                    fp,
                    now,
                    _compress_json(item),
                ),
            )
            stats["itens_bruto_upserted"] += 1

            # Processo pode não existir se COMPRA ausente — cria stub mínimo
            c.execute(
                """
                INSERT INTO platform_processos(
                    id, plataforma, numero_processo, numero_pncp, orgao, municipio, uf,
                    objeto, modalidade, data_publicacao, updated_at, raw_json_zlib
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    orgao=COALESCE(NULLIF(trim(excluded.orgao), ''), platform_processos.orgao),
                    municipio=COALESCE(NULLIF(trim(excluded.municipio), ''), platform_processos.municipio),
                    uf=COALESCE(NULLIF(trim(excluded.uf), ''), platform_processos.uf),
                    modalidade=COALESCE(NULLIF(trim(excluded.modalidade), ''), platform_processos.modalidade)
                """,
                (
                    proc_id,
                    PLATFORM_ID,
                    item.get("numero_processo") or numero_pncp or cod,
                    numero_pncp,
                    orgao,
                    municipio,
                    uf,
                    None,
                    modalidade,
                    data_ref,
                    now,
                    _compress_json({"stub": True, "cod_compra": cod}),
                ),
            )

            c.execute(
                """
                INSERT INTO platform_itens_leitura(
                    plataforma, plataforma_item_id, processo_id, numero_item, descricao,
                    material_servico, valor_unitario, valor_unitario_homologado,
                    unidade_medida, quantidade, orgao, municipio, uf, modalidade,
                    fornecedor_nome, cnpj_fornecedor, data_referencia,
                    inciso_classificacao, esfera, url_origem, numero_pncp, numero_processo,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(plataforma, plataforma_item_id) DO UPDATE SET
                    descricao=excluded.descricao,
                    valor_unitario=excluded.valor_unitario,
                    valor_unitario_homologado=excluded.valor_unitario_homologado,
                    unidade_medida=excluded.unidade_medida,
                    quantidade=excluded.quantidade,
                    orgao=COALESCE(NULLIF(trim(excluded.orgao), ''), platform_itens_leitura.orgao),
                    municipio=COALESCE(NULLIF(trim(excluded.municipio), ''), platform_itens_leitura.municipio),
                    uf=COALESCE(NULLIF(trim(excluded.uf), ''), platform_itens_leitura.uf),
                    modalidade=COALESCE(NULLIF(trim(excluded.modalidade), ''), platform_itens_leitura.modalidade),
                    fornecedor_nome=excluded.fornecedor_nome,
                    cnpj_fornecedor=excluded.cnpj_fornecedor,
                    data_referencia=excluded.data_referencia,
                    inciso_classificacao=excluded.inciso_classificacao,
                    esfera=excluded.esfera,
                    url_origem=excluded.url_origem,
                    numero_pncp=excluded.numero_pncp,
                    numero_processo=excluded.numero_processo,
                    updated_at=excluded.updated_at
                """,
                (
                    PLATFORM_ID,
                    plat_item_id,
                    proc_id,
                    num_item,
                    desc,
                    item.get("material_servico"),
                    float(valor),
                    float(homolog_f) if homolog_f and homolog_f > 0 else None,
                    item.get("unidade_medida"),
                    item.get("quantidade"),
                    orgao,
                    municipio,
                    uf,
                    modalidade,
                    item.get("fornecedor_nome"),
                    item.get("cnpj_fornecedor"),
                    data_ref,
                    item.get("inciso_classificacao") or "inciso_i",
                    item.get("esfera") or "federal",
                    url,
                    numero_pncp,
                    item.get("numero_processo") or numero_pncp,
                    now,
                ),
            )
            stats["itens_leitura_upserted"] += 1

        # Completa lacunas de geo/modalidade a partir do processo (qualquer item).
        c.execute(
            """
            UPDATE platform_itens_leitura AS i
            SET
              orgao = COALESCE(
                NULLIF(trim(i.orgao), ''),
                (SELECT NULLIF(trim(p.orgao), '') FROM platform_processos p WHERE p.id = i.processo_id)
              ),
              municipio = COALESCE(
                NULLIF(trim(i.municipio), ''),
                (SELECT NULLIF(trim(p.municipio), '') FROM platform_processos p WHERE p.id = i.processo_id)
              ),
              uf = COALESCE(
                NULLIF(trim(i.uf), ''),
                (SELECT NULLIF(trim(p.uf), '') FROM platform_processos p WHERE p.id = i.processo_id)
              ),
              modalidade = COALESCE(
                NULLIF(trim(i.modalidade), ''),
                (SELECT NULLIF(trim(p.modalidade), '') FROM platform_processos p WHERE p.id = i.processo_id)
              )
            WHERE i.plataforma = ?
              AND (
                NULLIF(trim(i.orgao), '') IS NULL
                OR NULLIF(trim(i.municipio), '') IS NULL
                OR NULLIF(trim(i.uf), '') IS NULL
                OR NULLIF(trim(i.modalidade), '') IS NULL
              )
            """,
            (PLATFORM_ID,),
        )

        c.execute(
            """
            INSERT INTO platform_ingest_state(scope_key, watermark, last_error, rows_total, updated_at)
            VALUES ('compras_gov_full', ?, NULL, ?, ?)
            ON CONFLICT(scope_key) DO UPDATE SET
                watermark=excluded.watermark,
                last_error=NULL,
                rows_total=excluded.rows_total,
                updated_at=excluded.updated_at
            """,
            (now, int(stats["itens_leitura_upserted"]), now),
        )

    index_stats = platform_index_stats(path)
    return {
        "ok": True,
        "platform_id": PLATFORM_ID,
        "db_path": path,
        "materialize": stats,
        "index_stats": index_stats,
        "search_ready": bool(index_stats.get("search_ready")),
        "item_materialize_enabled": True,
    }


# Alias legado do placeholder
def materialize_compras_gov_items(
    parsed: Dict[str, Any],
    *,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    return materialize_compras_gov_parsed(parsed, db_path=db_path)
