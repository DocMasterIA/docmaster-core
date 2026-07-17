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


def _doc_digits(doc_key: Optional[str], raw_doc: Optional[str] = None) -> Optional[str]:
    return _cnpj_digits(raw_doc) or _cnpj_digits(doc_key)


def _resolve_supplier(
    item: Dict[str, Any],
    prop: Dict[str, Any],
    lic: Dict[str, Any],
    pessoas_by_doc: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Waterfall interno do fornecedor: item_prop C → item doc1/doc2 →
    licitação vencedor/fornecedor. O join em pessoas só acontece por doc_key.
    """
    candidates = [
        (
            "item_prop",
            prop.get("doc_key"),
            prop.get("cnpj_fornecedor"),
            prop.get("fornecedor_nome"),
        ),
        (
            "item_doc1",
            item.get("doc_key"),
            item.get("nr_documento"),
            None,
        ),
        (
            "item_doc2",
            item.get("doc_key_2"),
            item.get("nr_documento_2"),
            None,
        ),
        (
            "licitacao_vencedor",
            lic.get("doc_key_vencedor"),
            lic.get("nr_documento_vencedor"),
            None,
        ),
        (
            "licitacao_fornecedor",
            lic.get("doc_key_fornecedor"),
            lic.get("nr_documento_fornecedor"),
            None,
        ),
    ]

    for origem, dk, raw_doc, direct_name in candidates:
        if not dk and not raw_doc and not direct_name:
            continue
        person = pessoas_by_doc.get(str(dk or ""))
        fornecedor = direct_name or (person or {}).get("fornecedor_nome")
        cnpj = _doc_digits(str(dk) if dk else None, raw_doc)
        if fornecedor or cnpj:
            return {
                "fornecedor_nome": fornecedor,
                "cnpj_fornecedor": cnpj,
                "fornecedor_doc_key": dk,
                "fornecedor_origem": origem,
                "fornecedor_uf": (person or {}).get("uf") or prop.get("fornecedor_uf"),
                "fornecedor_municipio_ibge": (
                    (person or {}).get("municipio_ibge")
                    or prop.get("fornecedor_municipio_ibge")
                ),
            }

    # Último fallback: nome já presente na proposta sem documento utilizável.
    if prop.get("fornecedor_nome"):
        return {
            "fornecedor_nome": prop.get("fornecedor_nome"),
            "cnpj_fornecedor": None,
            "fornecedor_doc_key": None,
            "fornecedor_origem": "item_prop_nome",
            "fornecedor_uf": prop.get("fornecedor_uf"),
            "fornecedor_municipio_ibge": prop.get("fornecedor_municipio_ibge"),
        }
    return {
        "fornecedor_nome": None,
        "cnpj_fornecedor": None,
        "fornecedor_doc_key": None,
        "fornecedor_origem": "sem_fornecedor",
        "fornecedor_uf": None,
        "fornecedor_municipio_ibge": None,
    }


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
    pessoas_by_doc: Dict[str, Dict[str, Any]] = dict(parsed.get("pessoas_by_doc") or {})
    if not pessoas_by_doc:
        pessoas_by_doc = {
            str(p.get("doc_key")): p
            for p in (parsed.get("pessoas") or [])
            if p.get("doc_key")
        }
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
        "fornecedor_origem": {},
        "itens_sem_fornecedor": 0,
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
            supplier = _resolve_supplier(item, prop or {}, lic, pessoas_by_doc)
            fornecedor = supplier.get("fornecedor_nome")
            cnpj = supplier.get("cnpj_fornecedor")
            fornecedor_origem = str(supplier.get("fornecedor_origem") or "sem_fornecedor")
            stats["fornecedor_origem"][fornecedor_origem] = (
                int(stats["fornecedor_origem"].get(fornecedor_origem) or 0) + 1
            )
            if not fornecedor and not cnpj:
                stats["itens_sem_fornecedor"] += 1

            bruto_raw = {
                "item": item.get("raw"),
                "proposta": (prop or {}).get("raw"),
                "preco_origem": origem,
                "fornecedor_origem": fornecedor_origem,
                "fornecedor_doc_key": supplier.get("fornecedor_doc_key"),
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
                    None,
                    float(valor),
                    float(homolog) if homolog else None,
                    item.get("unidade_medida"),
                    item.get("quantidade"),
                    lic.get("orgao"),
                    lic.get("municipio") or supplier.get("fornecedor_municipio_ibge"),
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
