"""
Materialize Notas Fiscais → platform_index (processos + itens leitura/bruto + FTS).
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


def ensure_notas_fiscais_index(*, db_path: Optional[str] = None) -> Dict[str, Any]:
    path = ensure_platform_index(PLATFORM_ID, db_path=db_path)
    stats = platform_index_stats(path)
    return {
        "ok": True,
        "platform_id": PLATFORM_ID,
        "db_path": path,
        "index_stats": stats,
        "itens_written": int(stats.get("itens_leitura") or 0),
        "item_materialize_enabled": True,
    }


def materialize_notas_fiscais_parsed(
    parsed: Dict[str, Any],
    *,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    path = ensure_platform_index(PLATFORM_ID, db_path=db_path)
    notas: List[Dict[str, Any]] = list(parsed.get("notas") or [])
    itens: List[Dict[str, Any]] = list(parsed.get("itens") or [])
    nota_by_chave = {str(n.get("chave")): n for n in notas if n.get("chave")}

    now = _utc_now()
    stats = {
        "processos_upserted": 0,
        "itens_bruto_upserted": 0,
        "itens_leitura_upserted": 0,
        "itens_sem_preco": 0,
    }

    with platform_conn(path) as c:
        for nota in notas:
            proc_id = str(nota.get("processo_id") or "")
            if not proc_id:
                continue
            c.execute(
                """
                INSERT INTO platform_processos(
                    id, plataforma, numero_processo, numero_pncp, orgao, municipio, uf,
                    objeto, data_publicacao, updated_at, raw_json_zlib
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    numero_processo=excluded.numero_processo,
                    orgao=excluded.orgao,
                    municipio=excluded.municipio,
                    uf=excluded.uf,
                    objeto=excluded.objeto,
                    data_publicacao=excluded.data_publicacao,
                    updated_at=excluded.updated_at,
                    raw_json_zlib=excluded.raw_json_zlib
                """,
                (
                    proc_id,
                    PLATFORM_ID,
                    nota.get("numero_processo"),
                    None,
                    nota.get("orgao"),
                    None,
                    nota.get("uf"),
                    nota.get("natureza"),
                    nota.get("data_emissao"),
                    now,
                    _compress_json(nota),
                ),
            )
            stats["processos_upserted"] += 1

        for item in itens:
            proc_id = str(item.get("processo_id") or "")
            num_item = str(item.get("numero_item") or "").strip()
            desc = str(item.get("descricao") or "").strip()
            vu = item.get("valor_unitario")
            try:
                vu_f = float(vu) if vu is not None else None
            except (TypeError, ValueError):
                vu_f = None
            if not proc_id or not num_item or not desc or not vu_f or vu_f <= 0:
                stats["itens_sem_preco"] += 1
                continue

            chave = str(item.get("chave") or "")
            nota = nota_by_chave.get(chave) or {}
            orgao = item.get("orgao") or nota.get("orgao")
            uf = item.get("uf") or nota.get("uf")
            url = item.get("url_origem") or nota.get("url_origem")
            data_ref = item.get("data_referencia") or nota.get("data_emissao")
            plat_item_id = str(
                item.get("plataforma_item_id") or f"{proc_id}:{num_item}"
            )
            fp = _item_fingerprint(proc_id, num_item, desc)

            c.execute(
                """
                INSERT INTO platform_processos(
                    id, plataforma, numero_processo, numero_pncp, orgao, municipio, uf,
                    objeto, data_publicacao, updated_at, raw_json_zlib
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO NOTHING
                """,
                (
                    proc_id,
                    PLATFORM_ID,
                    item.get("numero_processo") or chave,
                    None,
                    orgao,
                    None,
                    uf,
                    None,
                    data_ref,
                    now,
                    _compress_json({"stub": True, "chave": chave}),
                ),
            )

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
                    float(vu_f),
                    float(vu_f),
                    item.get("fornecedor_nome"),
                    item.get("cnpj_fornecedor"),
                    fp,
                    now,
                    _compress_json(item),
                ),
            )
            stats["itens_bruto_upserted"] += 1

            c.execute(
                """
                INSERT INTO platform_itens_leitura(
                    plataforma, plataforma_item_id, processo_id, numero_item, descricao,
                    material_servico, valor_unitario, valor_unitario_homologado,
                    unidade_medida, quantidade, orgao, municipio, uf,
                    fornecedor_nome, cnpj_fornecedor, data_referencia,
                    inciso_classificacao, esfera, url_origem, numero_pncp, numero_processo,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(plataforma, plataforma_item_id) DO UPDATE SET
                    descricao=excluded.descricao,
                    valor_unitario=excluded.valor_unitario,
                    valor_unitario_homologado=excluded.valor_unitario_homologado,
                    unidade_medida=excluded.unidade_medida,
                    quantidade=excluded.quantidade,
                    orgao=excluded.orgao,
                    municipio=excluded.municipio,
                    uf=excluded.uf,
                    fornecedor_nome=excluded.fornecedor_nome,
                    cnpj_fornecedor=excluded.cnpj_fornecedor,
                    data_referencia=excluded.data_referencia,
                    inciso_classificacao=excluded.inciso_classificacao,
                    esfera=excluded.esfera,
                    url_origem=excluded.url_origem,
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
                    float(vu_f),
                    float(vu_f),
                    item.get("unidade_medida"),
                    item.get("quantidade"),
                    orgao,
                    None,
                    uf,
                    item.get("fornecedor_nome"),
                    item.get("cnpj_fornecedor"),
                    data_ref,
                    item.get("inciso_classificacao") or "inciso_v",
                    item.get("esfera") or "federal",
                    url,
                    None,
                    item.get("numero_processo") or chave,
                    now,
                ),
            )
            stats["itens_leitura_upserted"] += 1

        c.execute(
            """
            INSERT INTO platform_ingest_state(scope_key, watermark, last_error, rows_total, updated_at)
            VALUES ('notas_fiscais_full', ?, NULL, ?, ?)
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
