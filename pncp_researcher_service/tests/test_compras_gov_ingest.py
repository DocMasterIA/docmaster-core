"""E2E Compras.gov: fixtures → ingest → FTS/adapter (como TCE-RS)."""
from __future__ import annotations

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
from app.adapters.indexed_platform_adapter import ComprasGovAdapter
from app.adapters.mapping import hit_to_pncp_row
from app.platform_index.ingest.compras_gov.config import FIXTURES_DIR
from app.platform_index.ingest.compras_gov.ingest import (
    ingest_compras_gov_sample,
    compras_gov_ingest_status,
)
from app.platform_index.ingest.compras_gov.parser import parse_compras_gov_directory
from app.platform_index.registry import PlatformIndexSpec, register_platform_spec
from app.platform_index.schema import ensure_platform_index, platform_index_stats
from app.platform_index.search import platform_item_search


@pytest.fixture
def cg_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "compras_gov_local.db")
    monkeypatch.setenv("COMPRAS_GOV_LOCAL_DB_PATH", db_path)
    monkeypatch.setenv("PRICE_PLATFORM_DATA_ROOT", str(tmp_path))
    ensure_platform_index("compras_gov", db_path=db_path)
    register_platform_spec(
        PlatformIndexSpec(
            id="compras_gov",
            label="Compras.gov (Dados Abertos)",
            db_path=db_path,
            schema_kind="platform_index",
            inciso_default="inciso_i",
            esfera_default="federal",
            enabled=True,
            search_ready=False,
            index_writer="feed",
        )
    )
    return db_path


def _cg_spec(db_path: str) -> PlatformIndexSpec:
    return PlatformIndexSpec(
        id="compras_gov",
        label="Compras.gov (Dados Abertos)",
        db_path=db_path,
        schema_kind="platform_index",
        inciso_default="inciso_i",
        esfera_default="federal",
        enabled=True,
        search_ready=True,
        index_writer="feed",
    )


def test_fixtures_exist_and_parse():
    assert FIXTURES_DIR.is_dir()
    parsed = parse_compras_gov_directory(FIXTURES_DIR)
    assert parsed["ok"] is True
    assert parsed["files"]["compra"]
    assert parsed["files"]["compra_item"]
    assert len(parsed["compras"]) >= 2
    assert len(parsed["itens"]) >= 4
    assert any("PAPEL A4" in str(i.get("descricao") or "") for i in parsed["itens"])
    assert any((i.get("valor_unitario_homologado") or 0) > 0 for i in parsed["itens"])
    assert any(i.get("fornecedor_nome") for i in parsed["itens"])


def test_ingest_sample_populates_index(cg_db):
    out = ingest_compras_gov_sample(db_path=cg_db)
    assert out["ok"] is True
    assert out["search_ready"] is True
    assert (out.get("materialize") or {}).get("itens_leitura_upserted", 0) >= 4
    stats = platform_index_stats(cg_db)
    assert stats["itens_leitura"] >= 4
    assert stats["search_ready"] is True


def test_ingest_sample_keeps_supplier_and_url(cg_db):
    from app.platform_index.connection import platform_conn

    ingest_compras_gov_sample(db_path=cg_db)
    with platform_conn(cg_db) as c:
        row = c.execute(
            """
            SELECT fornecedor_nome, cnpj_fornecedor, url_origem, orgao, uf
            FROM platform_itens_leitura
            WHERE descricao LIKE '%PAPEL A4%'
            LIMIT 1
            """
        ).fetchone()
    assert row is not None
    assert "FIXTURE" in str(row["fornecedor_nome"] or "").upper()
    assert str(row["cnpj_fornecedor"] or "").isdigit()
    assert "http" in str(row["url_origem"] or "")
    assert row["uf"] == "DF"
    assert "COMPRAS" in str(row["orgao"] or "").upper()


def test_search_after_ingest_finds_papel(cg_db):
    ingest_compras_gov_sample(db_path=cg_db)
    spec = _cg_spec(cg_db)
    rows = platform_item_search(spec, termo="PAPEL A4", uf=None, limit=20)
    assert len(rows) >= 1
    assert any("PAPEL" in str(r.get("descricao") or "").upper() for r in rows)


def test_ingest_status_after_sample(cg_db):
    ingest_compras_gov_sample(db_path=cg_db)
    status = compras_gov_ingest_status(db_path=cg_db)
    assert status["ok"] is True
    assert status["ingest_implemented"] is True
    assert status["search_ready"] is True
    assert status["item_materialize_enabled"] is True


class ComprasGovIngestAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self._tmp.name) / "compras_gov_local.db")
        ensure_platform_index("compras_gov", db_path=self.db_path)
        register_platform_spec(
            PlatformIndexSpec(
                id="compras_gov",
                label="Compras.gov (Dados Abertos)",
                db_path=self.db_path,
                schema_kind="platform_index",
                inciso_default="inciso_i",
                esfera_default="federal",
                enabled=True,
                search_ready=False,
                index_writer="feed",
            )
        )
        ingest_compras_gov_sample(db_path=self.db_path)

    async def asyncTearDown(self):
        self._tmp.cleanup()

    async def test_adapter_search_after_ingest(self):
        adapter = ComprasGovAdapter()
        self.assertTrue(await adapter.health())
        hits = await adapter.search(
            FederatedSearchQuery(termo_busca="PAPEL A4", fontes_habilitadas=["compras_gov"])
        )
        self.assertGreaterEqual(len(hits), 1)
        self.assertEqual(hits[0].plataforma, "compras_gov")
        self.assertEqual(hits[0].inciso_classificacao, "inciso_i")

    async def test_federated_returns_compras_gov_hit(self):
        async def _orch(query, hits, **kwargs):
            return {
                "ok": True,
                "itens": [hit_to_pncp_row(h) for h in hits],
                "stats": {"fontes": kwargs.get("source_stats") or {}},
            }

        with patch(
            "app.adapters.federated.assign_canonical_keys",
            side_effect=lambda hits, persist=True: hits,
        ), patch(
            "app.adapters.federated.orchestrate_federated_hits",
            new=AsyncMock(side_effect=_orch),
        ):
            out = await federated_search(
                FederatedSearchQuery(
                    termo_busca="PAPEL A4",
                    fontes_habilitadas=["compras_gov"],
                )
            )
        self.assertTrue(out.get("ok"))
        plats = {str(i.get("plataforma")) for i in (out.get("itens") or [])}
        self.assertIn("compras_gov", plats)
