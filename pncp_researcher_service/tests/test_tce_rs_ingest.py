"""Integração inicial TCE-RS (LicitaCon) — parser + materialize + busca."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.adapters.contracts import FederatedSearchQuery
from app.adapters.federated import federated_search
from app.adapters.indexed_platform_adapter import TceRsAdapter
from app.platform_index.ingest.tce_rs.config import FIXTURES_DIR
from app.platform_index.ingest.tce_rs.ingest import ingest_tce_rs_sample, tce_rs_ingest_status
from app.platform_index.ingest.tce_rs.parser import parse_tce_rs_directory
from app.platform_index.registry import PlatformIndexSpec, register_platform_spec
from app.platform_index.schema import ensure_platform_index, platform_index_stats
from app.platform_index.search import platform_item_search


@pytest.fixture
def tce_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "tce_rs_local.db")
    monkeypatch.setenv("TCE_RS_LOCAL_DB_PATH", db_path)
    monkeypatch.setenv("PRICE_PLATFORM_DATA_ROOT", str(tmp_path))
    ensure_platform_index("tce_rs", db_path=db_path)
    register_platform_spec(
        PlatformIndexSpec(
            id="tce_rs",
            label="TCE-RS (LicitaCon)",
            db_path=db_path,
            schema_kind="platform_index",
            inciso_default="inciso_ii",
            esfera_default="estadual",
            uf_scope="RS",
        )
    )
    return db_path


def _tce_spec(db_path: str):
    return PlatformIndexSpec(
        id="tce_rs",
        label="TCE-RS (LicitaCon)",
        db_path=db_path,
        schema_kind="platform_index",
        inciso_default="inciso_ii",
        esfera_default="estadual",
        uf_scope="RS",
    )


def test_fixtures_parse_licitacon_files():
    parsed = parse_tce_rs_directory(FIXTURES_DIR)
    assert parsed["files"]["licitacao"]
    assert parsed["files"]["item"]
    assert parsed["files"]["proposta"]
    assert parsed["files"]["pessoas"]
    assert len(parsed["licitacoes"]) >= 2
    assert len(parsed["itens"]) >= 3
    assert len(parsed["propostas"]) >= 3
    # Chave composta LicitaCon (não id fictício).
    assert any(str(l["licitacao_id"]).startswith("48100:2025:62:") for l in parsed["licitacoes"])
    # Pessoas enriquecem proposta vencedora.
    vencedoras = [p for p in parsed["propostas"] if str(p.get("tp_resultado_proposta") or "").upper() == "C"]
    assert any(p.get("fornecedor_nome") for p in vencedoras)
    # Preço no próprio item.
    assert any((i.get("valor_unitario_homologado") or 0) > 0 for i in parsed["itens"])


def test_ingest_sample_populates_index(tce_db):
    out = ingest_tce_rs_sample(db_path=tce_db)
    assert out["ok"] is True
    assert out["search_ready"] is True
    assert out["materialize"]["itens_leitura_upserted"] >= 3
    assert out["materialize"]["preco_origem"]["item_homologado"] >= 1
    stats = platform_index_stats(tce_db)
    assert stats["itens_leitura"] >= 3
    assert stats["search_ready"] is True


def test_ingest_sample_keeps_supplier_and_url(tce_db):
    from app.platform_index.connection import platform_conn

    ingest_tce_rs_sample(db_path=tce_db)
    with platform_conn(tce_db) as c:
        row = c.execute(
            "SELECT fornecedor_nome, url_origem, valor_unitario, orgao "
            "FROM platform_itens_leitura WHERE descricao LIKE '%PAPEL A4%' LIMIT 1"
        ).fetchone()
    assert row is not None
    assert "Papelaria" in (row["fornecedor_nome"] or "")
    assert "portal.tce.rs.gov.br" in (row["url_origem"] or "")
    assert float(row["valor_unitario"]) == 24.50
    assert "FLORES" in (row["orgao"] or "").upper()


def _write_tce_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    lines = [",".join(header)]
    lines.extend(",".join(row) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_waterfall_supplier_uses_second_item_document_pair(tmp_path, tce_db):
    from app.platform_index.connection import platform_conn
    from app.platform_index.ingest.tce_rs.ingest import ingest_tce_rs_from_directory

    data_dir = tmp_path / "raw"
    data_dir.mkdir()
    key_cols = ["CD_ORGAO", "ANO_LICITACAO", "NR_LICITACAO", "CD_TIPO_MODALIDADE"]
    _write_tce_csv(
        data_dir / "licitacao.csv",
        [*key_cols, "NM_ORGAO", "DS_OBJETO", "LINK_LICITACON_CIDADAO"],
        [["1", "2026", "10", "PRD", "Prefeitura Teste", "Objeto", "https://tce.example/10"]],
    )
    _write_tce_csv(
        data_dir / "item.csv",
        [
            *key_cols,
            "NR_LOTE",
            "NR_ITEM",
            "DS_ITEM",
            "VL_UNITARIO_HOMOLOGADO",
            "TP_DOCUMENTO",
            "NR_DOCUMENTO",
            "TP_DOCUMENTO",
            "NR_DOCUMENTO",
        ],
        [["1", "2026", "10", "PRD", "1", "1", "PAPEL A4", "12.34", "", "", "J", "12345678000190"]],
    )
    _write_tce_csv(
        data_dir / "pessoas.csv",
        ["TP_DOCUMENTO", "NR_DOCUMENTO", "NM_PESSOA", "SG_UF", "CD_MUNICIPIO_IBGE"],
        [["J", "12345678000190", "Fornecedor Segundo Documento Ltda", "RS", "4305108"]],
    )

    out = ingest_tce_rs_from_directory(data_dir, db_path=tce_db)
    assert out["materialize"]["fornecedor_origem"]["item_doc2"] == 1
    with platform_conn(tce_db) as c:
        row = c.execute(
            "SELECT fornecedor_nome, cnpj_fornecedor, municipio "
            "FROM platform_itens_leitura WHERE descricao='PAPEL A4'"
        ).fetchone()
    assert row is not None
    assert row["fornecedor_nome"] == "Fornecedor Segundo Documento Ltda"
    assert row["cnpj_fornecedor"] == "12345678000190"
    # Não usa mais IBGE do fornecedor como município do órgão.
    assert row["municipio"] in (None, "")


def test_waterfall_supplier_uses_licitacao_fornecedor(tmp_path, tce_db):
    from app.platform_index.connection import platform_conn
    from app.platform_index.ingest.tce_rs.ingest import ingest_tce_rs_from_directory

    data_dir = tmp_path / "raw"
    data_dir.mkdir()
    key_cols = ["CD_ORGAO", "ANO_LICITACAO", "NR_LICITACAO", "CD_TIPO_MODALIDADE"]
    _write_tce_csv(
        data_dir / "licitacao.csv",
        [
            *key_cols,
            "NM_ORGAO",
            "DS_OBJETO",
            "LINK_LICITACON_CIDADAO",
            "NR_DOCUMENTO_FORNECEDOR",
        ],
        [["2", "2026", "20", "PRD", "Prefeitura Teste", "Objeto", "https://tce.example/20", "98765432000110"]],
    )
    _write_tce_csv(
        data_dir / "item.csv",
        [*key_cols, "NR_LOTE", "NR_ITEM", "DS_ITEM", "VL_UNITARIO_HOMOLOGADO"],
        [["2", "2026", "20", "PRD", "1", "1", "ALCOOL ETILICO", "8.90"]],
    )
    _write_tce_csv(
        data_dir / "pessoas.csv",
        ["TP_DOCUMENTO", "NR_DOCUMENTO", "NM_PESSOA", "SG_UF", "CD_MUNICIPIO_IBGE"],
        [["J", "98765432000110", "Fornecedor da Licitacao Ltda", "RS", "4314902"]],
    )

    out = ingest_tce_rs_from_directory(data_dir, db_path=tce_db)
    assert out["materialize"]["fornecedor_origem"]["licitacao_fornecedor"] == 1
    with platform_conn(tce_db) as c:
        row = c.execute(
            "SELECT fornecedor_nome, cnpj_fornecedor, municipio "
            "FROM platform_itens_leitura WHERE descricao='ALCOOL ETILICO'"
        ).fetchone()
    assert row is not None
    assert row["fornecedor_nome"] == "Fornecedor da Licitacao Ltda"
    assert row["cnpj_fornecedor"] == "98765432000110"
    # Não usa mais IBGE do fornecedor (4314902 = Porto Alegre) como município do órgão.
    assert row["municipio"] in (None, "")


def test_ingest_status_after_sample(tce_db):
    ingest_tce_rs_sample(db_path=tce_db)
    status = tce_rs_ingest_status(db_path=tce_db)
    assert status["ok"] is True
    assert status["search_ready"] is True
    assert status["ingest_state"].get("rows_total", 0) >= 3


def test_platform_search_finds_papel_after_ingest(tce_db):
    ingest_tce_rs_sample(db_path=tce_db)
    rows = platform_item_search(_tce_spec(tce_db), termo="PAPEL A4", uf="RS", limit=10)
    assert any("PAPEL" in (r.get("descricao_item") or "").upper() for r in rows)


class TceRsAdapterAsyncTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.db_path = str(Path(self._tmp) / "tce_rs_local.db")
        os.environ["TCE_RS_LOCAL_DB_PATH"] = self.db_path
        os.environ["PRICE_PLATFORM_DATA_ROOT"] = self._tmp
        ensure_platform_index("tce_rs", db_path=self.db_path)
        register_platform_spec(
            PlatformIndexSpec(
                id="tce_rs",
                label="TCE-RS (LicitaCon)",
                db_path=self.db_path,
                schema_kind="platform_index",
                inciso_default="inciso_ii",
                esfera_default="estadual",
                uf_scope="RS",
            )
        )
        ingest_tce_rs_sample(db_path=self.db_path)

    async def test_tce_rs_adapter_search_after_ingest(self):
        adapter = TceRsAdapter()
        self.assertTrue(await adapter.health())
        hits = await adapter.search(FederatedSearchQuery(termo_busca="ALCOOL ETILICO", uf="RS"))
        self.assertGreaterEqual(len(hits), 1)
        self.assertEqual(hits[0].plataforma, "tce_rs")

    async def test_federated_returns_tce_rs_hit_after_ingest(self):
        query = FederatedSearchQuery(
            termo_busca="PAPEL A4",
            fontes_habilitadas=["pncp", "tce_rs"],
            uf="RS",
            somente_homologados=False,
        )

        async def _fake_search(source_id, q, timeout_s=20.0):
            if source_id == "pncp":
                return source_id, [], None
            hits = await TceRsAdapter().search(q)
            return source_id, hits, None

        with patch(
            "app.adapters.federated._search_adapter_with_timeout",
            side_effect=_fake_search,
        ), patch(
            "app.adapters.federated.assign_canonical_keys",
            side_effect=lambda hits, persist=True: hits,
        ), patch(
            "app.service.enrich_homolog_items_from_pncp",
            new_callable=AsyncMock,
            return_value=0,
        ), patch(
            "app.service._rerank_top3_with_ia",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "app.service._enriquecer_interpretacao_ia_itens",
            new_callable=AsyncMock,
            return_value=None,
        ):
            out = await federated_search(query)

        self.assertTrue(out.get("ok"))
        itens = out.get("itens") or []
        self.assertTrue(any(str(i.get("plataforma") or "") == "tce_rs" for i in itens))


RAW_2025 = _ROOT / "data" / "tce_rs" / "raw" / "2025"
RAW_2026 = _ROOT / "data" / "tce_rs" / "raw" / "2026"
RAW_ROOT = _ROOT / "data" / "tce_rs" / "raw"


@pytest.mark.skipif(not RAW_2025.is_dir(), reason="CSVs LicitaCon 2025 ausentes")
def test_raw_2025_join_smoke_builds_priced_items(tce_db):
    """Amostra dos CSVs reais 2025: junção monta itens com preço e órgão."""
    from app.platform_index.connection import platform_conn
    from app.platform_index.ingest.tce_rs.ingest import ingest_tce_rs_from_directory

    out = ingest_tce_rs_from_directory(RAW_2025, max_rows=80, db_path=tce_db)
    assert out["ok"] is True
    assert out["parsed"]["itens"] >= 1
    assert out["materialize"]["itens_leitura_upserted"] >= 1
    with platform_conn(tce_db) as c:
        row = c.execute(
            "SELECT descricao, valor_unitario, orgao, uf FROM platform_itens_leitura LIMIT 1"
        ).fetchone()
    assert row is not None
    assert (row["descricao"] or "").strip()
    assert float(row["valor_unitario"]) > 0
    assert row["uf"] == "RS"
    assert (row["orgao"] or "").strip()


@pytest.mark.skipif(not RAW_2026.is_dir(), reason="CSVs LicitaCon 2026 ausentes")
def test_raw_2026_itemw_join_smoke_builds_priced_items(tce_db):
    """2026 usa itemw.csv — mesmo contrato de junção/preço."""
    from app.platform_index.connection import platform_conn
    from app.platform_index.ingest.tce_rs.ingest import ingest_tce_rs_from_directory
    from app.platform_index.ingest.tce_rs.parser import find_item_csv

    item_path = find_item_csv(RAW_2026)
    assert item_path is not None
    assert item_path.name.lower() == "itemw.csv"

    out = ingest_tce_rs_from_directory(RAW_2026, max_rows=80, db_path=tce_db)
    assert out["ok"] is True
    assert "2026" in (out.get("years") or [])
    assert out["parsed"]["itens"] >= 1
    assert out["materialize"]["itens_leitura_upserted"] >= 1
    with platform_conn(tce_db) as c:
        row = c.execute(
            "SELECT descricao, valor_unitario, orgao, uf FROM platform_itens_leitura LIMIT 1"
        ).fetchone()
    assert row is not None
    assert float(row["valor_unitario"]) > 0
    assert row["uf"] == "RS"


@pytest.mark.skipif(
    not (RAW_2025.is_dir() and RAW_2026.is_dir()),
    reason="precisa raw/2025 e raw/2026",
)
def test_raw_root_discovers_both_years(tce_db):
    from app.platform_index.ingest.tce_rs.ingest import (
        discover_ingest_dirs,
        ingest_tce_rs_from_directory,
    )

    dirs = discover_ingest_dirs(RAW_ROOT)
    names = [p.name for p in dirs]
    assert "2025" in names
    assert "2026" in names

    out = ingest_tce_rs_from_directory(RAW_ROOT, max_rows=40, db_path=tce_db)
    assert out["ok"] is True
    assert set(out.get("years") or []) >= {"2025", "2026"}
    assert out["parsed"]["itens"] >= 2
    by_year = {y["year"]: y for y in out["parsed"]["by_year"]}
    assert by_year["2025"]["itens"] >= 1
    assert by_year["2026"]["itens"] >= 1
    assert "itemw" in (by_year["2026"]["files"].get("item") or "").lower()
