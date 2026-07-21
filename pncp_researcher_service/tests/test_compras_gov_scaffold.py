"""Scaffold Compras.gov: adapter + discover CSV + isolamento de feed."""
from __future__ import annotations

import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_ORIG_SERVICE_MODE = os.environ.get("SERVICE_MODE")
_ORIG_FEED_PLATFORM = os.environ.get("FEED_PLATFORM")


@pytest.fixture(autouse=True)
def _restore_service_mode_modules():
    yield
    if _ORIG_SERVICE_MODE is None:
        os.environ.pop("SERVICE_MODE", None)
    else:
        os.environ["SERVICE_MODE"] = _ORIG_SERVICE_MODE
    if _ORIG_FEED_PLATFORM is None:
        os.environ.pop("FEED_PLATFORM", None)
    else:
        os.environ["FEED_PLATFORM"] = _ORIG_FEED_PLATFORM
    import app.service_mode as sm
    import app.api_feed as api_feed

    importlib.reload(sm)
    importlib.reload(api_feed)


def test_compras_gov_feed_isolation(monkeypatch):
    monkeypatch.setenv("SERVICE_MODE", "feed")
    monkeypatch.setenv("FEED_PLATFORM", "compras_gov")
    import app.service_mode as sm

    importlib.reload(sm)
    assert sm.is_pncp_feed() is False
    assert sm.pncp_ingest_worker_allowed() is False
    assert sm.is_platform_feed("compras_gov") is True
    assert sm.is_platform_feed("tce_rs") is False
    assert sm.service_name() == "price_index_feed_compras_gov"
    assert "Compras.gov" in sm.service_title()


def test_compras_gov_routes_404_on_pncp_feed(monkeypatch):
    monkeypatch.setenv("SERVICE_MODE", "feed")
    monkeypatch.setenv("FEED_PLATFORM", "pncp")
    import app.service_mode as sm
    import app.api_feed as api_feed

    importlib.reload(sm)
    importlib.reload(api_feed)

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        api_feed._require_platform_feed("compras_gov")
    assert exc.value.status_code == 404


def test_discover_compra_item_csv(tmp_path: Path):
    from app.platform_index.ingest.compras_gov.ingest import (
        discover_ingest_dirs,
        find_compra_csv,
        find_compra_item_csv,
    )

    item = tmp_path / "comprasGOV-mensal-VW_FT_PNCP_COMPRA_ITEM-2026-07.csv"
    compra = tmp_path / "comprasGOV-anual-VW_FT_PNCP_COMPRA-latest.csv"
    item.write_text("a\n", encoding="utf-8")
    compra.write_text("b\n", encoding="utf-8")

    assert find_compra_item_csv(tmp_path) == item
    assert find_compra_csv(tmp_path) == compra
    assert discover_ingest_dirs(tmp_path) == [tmp_path.resolve()]


def test_discover_nested_mensal(tmp_path: Path):
    from app.platform_index.ingest.compras_gov.ingest import discover_ingest_dirs

    nested = tmp_path / "mensal" / "2026-07"
    nested.mkdir(parents=True)
    (nested / "x-VW_FT_PNCP_COMPRA_ITEM-y.csv").write_text("a\n", encoding="utf-8")
    found = discover_ingest_dirs(tmp_path)
    assert found == [nested.resolve()]


def test_ingest_sample_from_fixtures_works(tmp_path):
    from app.platform_index.ingest.compras_gov.ingest import ingest_compras_gov_sample
    from app.platform_index.registry import PlatformIndexSpec, register_platform_spec
    from app.platform_index.schema import ensure_platform_index

    db_path = str(tmp_path / "cg.db")
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
    out = ingest_compras_gov_sample(db_path=db_path)
    assert out["ok"] is True
    assert out["search_ready"] is True


class ComprasGovAdapterAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_adapter_registered_and_empty_without_index(self):
        from app.adapters.contracts import FederatedSearchQuery
        from app.adapters.indexed_platform_adapter import ComprasGovAdapter
        from app.adapters.registry import get_adapter, list_adapter_ids
        from app.platform_index.registry import get_platform_spec

        self.assertIn("compras_gov", list_adapter_ids())
        adapter = get_adapter("compras_gov")
        self.assertIsInstance(adapter, ComprasGovAdapter)
        spec = get_platform_spec("compras_gov")
        self.assertIsNotNone(spec)
        self.assertEqual(spec.schema_kind, "platform_index")
        self.assertEqual(spec.inciso_default, "inciso_i")
        self.assertEqual(spec.esfera_default, "federal")

        # Sem .db → health False e search vazio (não quebra federado).
        with tempfile.TemporaryDirectory() as tmp:
            from app.platform_index.registry import PlatformIndexSpec, register_platform_spec

            db_path = str(Path(tmp) / "compras_gov_local.db")
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
                )
            )
            try:
                hits = await ComprasGovAdapter().search(
                    FederatedSearchQuery(termo_busca="papel A4", fontes_habilitadas=["compras_gov"])
                )
                self.assertEqual(hits, [])
                self.assertFalse(await ComprasGovAdapter().health())
            finally:
                # restaura spec default do processo
                from app.config import COMPRAS_GOV_LOCAL_DB_PATH

                register_platform_spec(
                    PlatformIndexSpec(
                        id="compras_gov",
                        label="Compras.gov (Dados Abertos)",
                        db_path=COMPRAS_GOV_LOCAL_DB_PATH,
                        schema_kind="platform_index",
                        inciso_default="inciso_i",
                        esfera_default="federal",
                        enabled=True,
                        search_ready=False,
                        index_writer="feed",
                    )
                )

    async def test_mapping_defaults_compras_gov(self):
        from app.adapters.contracts import MarketPriceHit
        from app.adapters.mapping import hit_to_pncp_row

        hit = MarketPriceHit(
            plataforma="compras_gov",
            plataforma_item_id="cg:1:2",
            descricao_item="Item teste",
            valor_unitario=10.5,
        )
        row = hit_to_pncp_row(hit)
        self.assertEqual(row.get("inciso_classificacao"), "inciso_i")
        self.assertEqual(row.get("esfera"), "federal")
        self.assertEqual(row.get("fonte"), "governamentais")
