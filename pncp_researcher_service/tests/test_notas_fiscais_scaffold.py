"""Scaffold Notas Fiscais: adapter + discover CSV + isolamento de feed."""
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


def test_notas_fiscais_feed_isolation(monkeypatch):
    monkeypatch.setenv("SERVICE_MODE", "feed")
    monkeypatch.setenv("FEED_PLATFORM", "notas_fiscais")
    import app.service_mode as sm

    importlib.reload(sm)
    assert sm.is_pncp_feed() is False
    assert sm.pncp_ingest_worker_allowed() is False
    assert sm.is_platform_feed("notas_fiscais") is True
    assert sm.is_platform_feed("compras_gov") is False
    assert sm.service_name() == "price_index_feed_notas_fiscais"
    assert "Notas Fiscais" in sm.service_title()


def test_notas_fiscais_routes_404_on_pncp_feed(monkeypatch):
    monkeypatch.setenv("SERVICE_MODE", "feed")
    monkeypatch.setenv("FEED_PLATFORM", "pncp")
    import app.service_mode as sm
    import app.api_feed as api_feed

    importlib.reload(sm)
    importlib.reload(api_feed)

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        api_feed._require_platform_feed("notas_fiscais")
    assert exc.value.status_code == 404


def test_discover_item_csv(tmp_path: Path):
    from app.platform_index.ingest.notas_fiscais import (
        discover_ingest_dirs,
        find_item_csv,
        find_nota_csv,
    )

    item = tmp_path / "202601_NFe_NotaFiscalItem.csv"
    nota = tmp_path / "202601_NFe_NotaFiscal.csv"
    item.write_text("a\n", encoding="utf-8")
    nota.write_text("b\n", encoding="utf-8")

    assert find_item_csv(tmp_path) == item
    assert find_nota_csv(tmp_path) == nota
    assert discover_ingest_dirs(tmp_path) == [tmp_path.resolve()]


def test_discover_nested_yyyy_mm(tmp_path: Path):
    from app.platform_index.ingest.notas_fiscais import discover_ingest_dirs

    nested = tmp_path / "2026" / "01"
    nested.mkdir(parents=True)
    (nested / "202601_NFe_NotaFiscalItem.csv").write_text("a\n", encoding="utf-8")
    found = discover_ingest_dirs(tmp_path)
    assert found == [nested.resolve()]


def test_discover_prefers_yyyy_mm_over_root(tmp_path: Path):
    from app.platform_index.ingest.notas_fiscais import discover_ingest_dirs

    (tmp_path / "latest_NFe_NotaFiscalItem.csv").write_text("a\n", encoding="utf-8")
    month = tmp_path / "2026" / "01"
    month.mkdir(parents=True)
    (month / "202601_NFe_NotaFiscalItem.csv").write_text("a\n", encoding="utf-8")
    found = discover_ingest_dirs(tmp_path)
    assert found == [month.resolve()]


def test_ingest_sample_from_fixtures_works(tmp_path):
    from app.platform_index.ingest.notas_fiscais import ingest_notas_fiscais_sample
    from app.platform_index.registry import PlatformIndexSpec, register_platform_spec
    from app.platform_index.schema import ensure_platform_index

    db_path = str(tmp_path / "nf.db")
    ensure_platform_index("notas_fiscais", db_path=db_path)
    register_platform_spec(
        PlatformIndexSpec(
            id="notas_fiscais",
            label="Notas Fiscais (Portal da Transparência)",
            db_path=db_path,
            schema_kind="platform_index",
            inciso_default="inciso_v",
            esfera_default="federal",
            enabled=True,
            search_ready=False,
            index_writer="feed",
        )
    )
    out = ingest_notas_fiscais_sample(db_path=db_path)
    assert out["ok"] is True
    assert out["search_ready"] is True
    # 2 itens da nota autorizada; item da nota "Sem informação" não entra
    assert (out.get("parsed") or {}).get("itens") == 2
    assert (out.get("materialize") or {}).get("itens_leitura_upserted") == 2



def test_ensure_creates_empty_schema(tmp_path: Path):
    from app.platform_index.ingest.notas_fiscais import ensure_notas_fiscais_db
    from app.platform_index.registry import PlatformIndexSpec, register_platform_spec

    db_path = str(tmp_path / "nf.db")
    register_platform_spec(
        PlatformIndexSpec(
            id="notas_fiscais",
            label="Notas Fiscais (Portal da Transparência)",
            db_path=db_path,
            schema_kind="platform_index",
            inciso_default="inciso_v",
            esfera_default="federal",
            enabled=True,
            search_ready=False,
            index_writer="feed",
        )
    )
    out = ensure_notas_fiscais_db(db_path=db_path)
    assert out["ok"] is True
    assert out["search_ready"] is False
    assert Path(db_path).is_file()


class NotasFiscaisAdapterAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_adapter_registered_and_empty_without_index(self):
        from app.adapters.contracts import FederatedSearchQuery
        from app.adapters.indexed_platform_adapter import NotasFiscaisAdapter
        from app.adapters.registry import get_adapter, list_adapter_ids
        from app.platform_index.registry import get_platform_spec

        self.assertIn("notas_fiscais", list_adapter_ids())
        adapter = get_adapter("notas_fiscais")
        self.assertIsInstance(adapter, NotasFiscaisAdapter)
        spec = get_platform_spec("notas_fiscais")
        self.assertIsNotNone(spec)
        self.assertEqual(spec.schema_kind, "platform_index")
        self.assertEqual(spec.inciso_default, "inciso_v")
        self.assertEqual(spec.esfera_default, "federal")

        with tempfile.TemporaryDirectory() as tmp:
            from app.platform_index.registry import PlatformIndexSpec, register_platform_spec

            db_path = str(Path(tmp) / "notas_fiscais_local.db")
            register_platform_spec(
                PlatformIndexSpec(
                    id="notas_fiscais",
                    label="Notas Fiscais (Portal da Transparência)",
                    db_path=db_path,
                    schema_kind="platform_index",
                    inciso_default="inciso_v",
                    esfera_default="federal",
                    enabled=True,
                    search_ready=False,
                )
            )
            try:
                hits = await NotasFiscaisAdapter().search(
                    FederatedSearchQuery(
                        termo_busca="papel A4",
                        fontes_habilitadas=["notas_fiscais"],
                    )
                )
                self.assertEqual(hits, [])
                self.assertFalse(await NotasFiscaisAdapter().health())
            finally:
                from app.config import NOTAS_FISCAIS_LOCAL_DB_PATH
                from app.platform_index.registry import PlatformIndexSpec, register_platform_spec

                register_platform_spec(
                    PlatformIndexSpec(
                        id="notas_fiscais",
                        label="Notas Fiscais (Portal da Transparência)",
                        db_path=NOTAS_FISCAIS_LOCAL_DB_PATH,
                        schema_kind="platform_index",
                        inciso_default="inciso_v",
                        esfera_default="federal",
                        enabled=True,
                        search_ready=False,
                        index_writer="feed",
                    )
                )
