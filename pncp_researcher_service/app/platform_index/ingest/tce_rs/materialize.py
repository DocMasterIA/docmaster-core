from __future__ import annotations

import hashlib
import json
import zlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ...connection import platform_conn
from ...schema import ensure_platform_index
from .config import PLATFORM_ID
from .parser import pick_best_propostas, resolve_item_price


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _compress_json(data: Dict[str, Any]) -> bytes:
    return zlib.compress(json.dumps(data, ensure_ascii=False).encode("utf-8"), level=6)


def _processo_id(licitacao_id: str) -> str:
    return f"{PLATFORM_ID}:{licitacao_id}"


def _item_fingerprint(processo_id: str, numero_item: str, descricao: str) -> str:
    base = f"{processo_id}|{numero_item}|{descricao[:160]}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()


def _cnpj_digits(v: Optional[str]) -> Optional[str]:
    if not v:
        return None
    digits = "".join(ch for ch in str(v) if ch.isdigit())
    return digits or None


def materialize_tce_rs_parsed(
    parsed: Dict[str, Any],
    *,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Grava licitacao + item + item_prop (+ pessoas já enriquecidas) no platform_index.
    Preço: item.homologado → proposta vencedora → item.estimado.
    """
    path = ensure_platform_index(PLATFORM_ID, db_path=db_path)
    licitacoes: List[Dict[str, Any]] = list(parsed.get("licitacoes") or [])
    itens: List[Dict[str, Any]] = list(parsed.get("itens") or [])
    propostas: List[Dict[str, Any]] = list(parsed.get("propostas") or [])
    proposta_by_key = pick_best_propostas(propostas)

    lic_by_id = {row["licitacao_id"]: row for row in licitacoes}
    now = _utc_now()
    stats = {
        "processos_upserted": 0,
        "itens_bruto_upserted": 0,
        "itens_leitura_upserted": 0,
        "itens_sem_licitacao": 0,
        "itens_sem_preco": 0,
        "preco_origem": {
            "item_homologado": 0,
            "proposta_homologada": 0,
            "proposta": 0,
            "item_estimado": 0,
        },
    }

    with platform_conn(path) as c:
        for lic in licitacoes:
            proc_id = _processo_id(lic["licitacao_id"])
            raw_blob = _compress_json(lic.get("raw") or {})
            c.execute(
                """
                INSERT INTO platform_processos(
                    id, plataforma, numero_processo, numero_pncp, orgao, municipio, uf,
                    objeto, data_publicacao, updated_at, raw_json_zlib
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    numero_processo=excluded.numero_processo,
                    numero_pncp=excluded.numero_pncp,
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
                    lic.get("numero_processo"),
                    lic.get("numero_pncp"),
                    lic.get("orgao"),
                    lic.get("municipio"),
                    "RS",
                    lic.get("objeto"),
                    lic.get("data_publicacao"),
                    now,
                    raw_blob,
                ),
            )
            stats["processos_upserted"] += 1

        for item in itens:
            lic = lic_by_id.get(item["licitacao_id"])
            if lic is None:
                stats["itens_sem_licitacao"] += 1
                continue
            proc_id = _processo_id(item["licitacao_id"])
            num_item = str(item["numero_item"])
            desc = str(item["descricao"])
            fp = _item_fingerprint(proc_id, num_item, desc)
            prop = proposta_by_key.get((item["licitacao_id"], num_item), {})
            valor, homolog, origem = resolve_item_price(item, prop)
            if origem in stats["preco_origem"]:
                stats["preco_origem"][origem] += 1

            data_ref = (
                (prop or {}).get("data_homologacao")
                or lic.get("data_publicacao")
            )
            url = lic.get("url_origem") or None
            fornecedor = (prop or {}).get("fornecedor_nome")
            cnpj = _cnpj_digits((prop or {}).get("cnpj_fornecedor"))
            if not cnpj:
                cnpj = _cnpj_digits(item.get("nr_documento"))

            bruto_raw = {
                "item": item.get("raw"),
                "proposta": (prop or {}).get("raw"),
                "preco_origem": origem,
            }
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
                    None,
                    item.get("quantidade"),
                    item.get("unidade_medida"),
                    valor,
                    homolog,
                    fornecedor,
                    cnpj,
                    fp,
                    now,
                    _compress_json(bruto_raw),
                ),
            )
            stats["itens_bruto_upserted"] += 1

            if not valor or float(valor) <= 0:
                stats["itens_sem_preco"] += 1
                continue

            plat_item_id = f"{proc_id}:{num_item}"
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
                    fornecedor_nome=excluded.fornecedor_nome,
                    cnpj_fornecedor=excluded.cnpj_fornecedor,
                    data_referencia=excluded.data_referencia,
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
                    None,
                    float(valor),
                    float(homolog) if homolog else None,
                    item.get("unidade_medida"),
                    item.get("quantidade"),
                    lic.get("orgao"),
                    lic.get("municipio"),
                    "RS",
                    fornecedor,
                    cnpj,
                    data_ref,
                    "inciso_ii",
                    "estadual",
                    url,
                    lic.get("numero_pncp"),
                    lic.get("numero_processo"),
                    now,
                ),
            )
            stats["itens_leitura_upserted"] += 1

        rows_total = int(
            c.execute("SELECT COUNT(*) AS n FROM platform_itens_leitura").fetchone()["n"] or 0
        )
        c.execute(
            """
            INSERT INTO platform_ingest_state(scope_key, watermark, last_error, rows_total, updated_at)
            VALUES ('tce_rs_full', ?, NULL, ?, ?)
            ON CONFLICT(scope_key) DO UPDATE SET
                watermark=excluded.watermark,
                last_error=NULL,
                rows_total=excluded.rows_total,
                updated_at=excluded.updated_at
            """,
            (now, rows_total, now),
        )

    stats["db_path"] = path
    stats["rows_total_leitura"] = rows_total
    return stats
