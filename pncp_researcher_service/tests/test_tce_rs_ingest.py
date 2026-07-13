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


def test_fixtures_parse_three_files():
    parsed = parse_tce_rs_directory(FIXTURES_DIR)
    assert parsed["files"]["licitacao"]
    assert parsed["files"]["item"]
    assert parsed["files"]["proposta"]
    assert len(parsed["licitacoes"]) >= 2
    assert len(parsed["itens"]) >= 3
    assert len(parsed["propostas"]) >= 3


def test_ingest_sample_populates_index(tce_db):
    out = ingest_tce_rs_sample(db_path=tce_db)
    assert out["ok"] is True
    assert out["search_ready"] is True
    assert out["materialize"]["itens_leitura_upserted"] >= 3
    stats = platform_index_stats(tce_db)
    assert stats["itens_leitura"] >= 3
    assert stats["search_ready"] is True


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
