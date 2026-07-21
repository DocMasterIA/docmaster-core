"""
Falhas + fluxo contínuo Compras.gov no researcher (federado IA / lista completa / feed).
"""
from __future__ import annotations

import importlib
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

from app.adapters.contracts import FederatedSearchQuery, MarketPriceHit
from app.adapters.federated import federated_search
from app.adapters.indexed_platform_adapter import ComprasGovAdapter
from app.adapters.mapping import hit_to_pncp_row
from app.adapters.pncp_adapter import PncpAdapter
from app.adapters.registry import get_adapter, list_adapter_ids


def _cg_hit(**overrides) -> MarketPriceHit:
    base = dict(
        plataforma="compras_gov",
        plataforma_item_id="cg:compra1:item1",
        descricao_item="PAPEL A4 COMPRAS.GOV",
        valor_unitario=18.5,
        valor_unitario_homologado=18.5,
        unidade_medida="RESMA",
        quantidade=10.0,
        orgao="MINISTERIO DA EDUCACAO",
        municipio="Brasília",
        uf="DF",
        fornecedor_nome="FORNECEDOR CG LTDA",
        fornecedor_cnpj="12345678000199",
        data_referencia="2026-01-15",
        inciso_classificacao="inciso_i",
        esfera="federal",
        url_origem="https://example.gov.br/compra/1",
    )
    base.update(overrides)
    return MarketPriceHit(**base)


def _pncp_hit(**overrides) -> MarketPriceHit:
    base = dict(
        plataforma="pncp",
        plataforma_item_id="12345678000195-1-000001/2024:1",
        descricao_item="PAPEL A4 PNCP",
        valor_unitario=20.0,
        valor_unitario_homologado=20.0,
        fornecedor_nome="FORNECEDOR PNCP LTDA",
        fornecedor_cnpj="98765432000111",
        inciso_classificacao="inciso_i",
        esfera="federal",
    )
    base.update(overrides)
    return MarketPriceHit(**base)


_ORIG_SERVICE_MODE = os.environ.get("SERVICE_MODE")
_ORIG_FEED_PLATFORM = os.environ.get("FEED_PLATFORM")


@pytest.fixture(autouse=True)
def _restore_feed_env():
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


# ── Falhas / resiliência ─────────────────────────────────────────────────────


def test_unknown_fonte_in_adapters_list_is_skipped():
    from app.adapters.registry import get_adapters

    assert get_adapters(["compras_gov", "fonte_fantasma", "pncp"])
    ids = [a.id for a in get_adapters(["compras_gov", "fonte_fantasma", "pncp"])]
    assert "fonte_fantasma" not in ids
    assert "compras_gov" in ids
    assert "pncp" in ids


def test_discover_empty_dir_raises(tmp_path: Path):
    from app.platform_index.ingest.compras_gov.ingest import discover_ingest_dirs

    empty = tmp_path / "vazio"
    empty.mkdir()
    with pytest.raises(FileNotFoundError):
        discover_ingest_dirs(empty)


def test_discover_compra_without_item_is_not_bundle(tmp_path: Path):
    from app.platform_index.ingest.compras_gov.ingest import (
        discover_ingest_dirs,
        is_compras_gov_bundle_dir,
    )

    (tmp_path / "VW_FT_PNCP_COMPRA.csv").write_text("a\n", encoding="utf-8")
    assert is_compras_gov_bundle_dir(tmp_path) is False
    with pytest.raises(FileNotFoundError):
        discover_ingest_dirs(tmp_path)


def test_ingest_sample_requires_writable_db(tmp_path, monkeypatch):
    """Sample usa fixtures reais; precisa db_path gravável (não /data do container)."""
    from app.platform_index.ingest.compras_gov.ingest import ingest_compras_gov_sample
    from app.platform_index.registry import PlatformIndexSpec, register_platform_spec
    from app.platform_index.schema import ensure_platform_index

    db_path = str(tmp_path / "cg_sample.db")
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


def test_ingest_status_marks_not_implemented():
    from app.platform_index.ingest.compras_gov import compras_gov_ingest_status

    st = compras_gov_ingest_status(db_path="/tmp/compras_gov_status_test_missing.db")
    assert st["ok"] is True
    assert st["platform_id"] == "compras_gov"
    assert st["structure_ready"] is True
    assert "column_map" in st


def test_pncp_feed_rejects_compras_gov_routes(monkeypatch):
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


def test_tce_feed_rejects_compras_gov_routes(monkeypatch):
    monkeypatch.setenv("SERVICE_MODE", "feed")
    monkeypatch.setenv("FEED_PLATFORM", "tce_rs")
    import app.service_mode as sm
    import app.api_feed as api_feed

    importlib.reload(sm)
    importlib.reload(api_feed)

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        api_feed._require_platform_feed("compras_gov")
    assert exc.value.status_code == 404
    api_feed._require_platform_feed("tce_rs")  # não levanta


class ComprasGovFailureAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_adapter_health_false_without_db(self):
        with tempfile.TemporaryDirectory() as tmp:
            from app.platform_index.registry import PlatformIndexSpec, register_platform_spec
            from app.config import COMPRAS_GOV_LOCAL_DB_PATH

            db_path = str(Path(tmp) / "missing.db")
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
                self.assertFalse(await ComprasGovAdapter().health())
                hits = await ComprasGovAdapter().search(
                    FederatedSearchQuery(termo_busca="papel", fontes_habilitadas=["compras_gov"])
                )
                self.assertEqual(hits, [])
            finally:
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

    async def test_federated_survives_compras_gov_adapter_error(self):
        """Falha na fonte Compras.gov não derruba o federado (PNCP segue)."""
        pncp = _pncp_hit()

        async def _orch(query, hits, **kwargs):
            return {
                "ok": True,
                "itens": [hit_to_pncp_row(h) for h in hits],
                "stats": {
                    "federated": True,
                    "fontes": kwargs.get("source_stats") or {},
                    "fontes_habilitadas": list(query.fontes_habilitadas or []),
                },
            }

        with patch.object(PncpAdapter, "search", new=AsyncMock(return_value=[pncp])), patch.object(
            ComprasGovAdapter, "search", new=AsyncMock(side_effect=RuntimeError("índice corrompido"))
        ), patch(
            "app.adapters.federated.assign_canonical_keys",
            side_effect=lambda hits, persist=True: hits,
        ), patch(
            "app.adapters.federated.orchestrate_federated_hits",
            new=AsyncMock(side_effect=_orch),
        ):
            out = await federated_search(
                FederatedSearchQuery(
                    termo_busca="PAPEL A4",
                    fontes_habilitadas=["pncp", "compras_gov"],
                )
            )

        self.assertTrue(out.get("ok"))
        itens = out.get("itens") or []
        self.assertEqual(len(itens), 1)
        self.assertEqual(itens[0].get("plataforma"), "pncp")
        fontes = (out.get("stats") or {}).get("fontes") or {}
        self.assertIn("compras_gov", fontes)
        self.assertTrue(fontes["compras_gov"].get("erro"))
        self.assertEqual(fontes["compras_gov"].get("hits"), 0)

    async def test_federated_unknown_fonte_returns_erro_stats(self):
        async def _orch(query, hits, **kwargs):
            return {
                "ok": True,
                "itens": [hit_to_pncp_row(h) for h in hits],
                "stats": {"fontes": kwargs.get("source_stats") or {}},
            }

        with patch.object(PncpAdapter, "search", new=AsyncMock(return_value=[_pncp_hit()])), patch(
            "app.adapters.federated.assign_canonical_keys",
            side_effect=lambda hits, persist=True: hits,
        ), patch(
            "app.adapters.federated.orchestrate_federated_hits",
            new=AsyncMock(side_effect=_orch),
        ):
            out = await federated_search(
                FederatedSearchQuery(
                    termo_busca="x",
                    fontes_habilitadas=["pncp", "plataforma_inexistente"],
                )
            )
        fontes = (out.get("stats") or {}).get("fontes") or {}
        self.assertIn("plataforma_inexistente", fontes)
        self.assertIn("desconhecida", str(fontes["plataforma_inexistente"].get("erro") or "").lower())


# ── Fluxo contínuo (pesquisa IA multi-fonte) ─────────────────────────────────


class ComprasGovContinuousFederatedTests(unittest.IsolatedAsyncioTestCase):
    async def test_federated_ia_merges_pncp_and_compras_gov(self):
        pncp = _pncp_hit()
        cg = _cg_hit()

        async def _orch(query, hits, **kwargs):
            rows = [hit_to_pncp_row(h) for h in hits]
            return {
                "ok": True,
                "filtros": {"fontes_habilitadas": list(query.fontes_habilitadas or [])},
                "itens": rows,
                "stats": {
                    "federated": True,
                    "fontes": kwargs.get("source_stats") or {},
                    "fontes_habilitadas": list(query.fontes_habilitadas or []),
                    "total_hits": kwargs.get("total_hits"),
                    "total_apos_dedup": kwargs.get("total_after_dedup"),
                },
            }

        with patch.object(PncpAdapter, "search", new=AsyncMock(return_value=[pncp])), patch.object(
            ComprasGovAdapter, "search", new=AsyncMock(return_value=[cg])
        ), patch(
            "app.adapters.federated.assign_canonical_keys",
            side_effect=lambda hits, persist=True: hits,
        ), patch(
            "app.adapters.federated.orchestrate_federated_hits",
            new=AsyncMock(side_effect=_orch),
        ):
            out = await federated_search(
                FederatedSearchQuery(
                    termo_busca="PAPEL A4",
                    fontes_habilitadas=["pncp", "compras_gov"],
                )
            )

        self.assertTrue(out.get("ok"))
        plats = {str(i.get("plataforma")) for i in (out.get("itens") or [])}
        self.assertEqual(plats, {"pncp", "compras_gov"})
        cg_row = next(i for i in out["itens"] if i["plataforma"] == "compras_gov")
        self.assertEqual(cg_row.get("inciso_classificacao"), "inciso_i")
        self.assertEqual(cg_row.get("esfera"), "federal")
        self.assertEqual(cg_row.get("fonte"), "governamentais")
        self.assertEqual(cg_row.get("plataforma_label"), "Compras.gov")
        fontes = (out.get("stats") or {}).get("fontes") or {}
        self.assertEqual(fontes.get("compras_gov", {}).get("hits"), 1)
        self.assertEqual(fontes.get("pncp", {}).get("hits"), 1)
        self.assertIsNone(fontes.get("compras_gov", {}).get("erro"))

    async def test_federated_compras_gov_only_empty_index_ok(self):
        """Só Compras.gov habilitado + índice vazio → ok com itens=[]."""
        async def _orch(query, hits, **kwargs):
            return {
                "ok": True,
                "itens": [],
                "stats": {"fontes": kwargs.get("source_stats") or {}, "federated": True},
            }

        with patch.object(ComprasGovAdapter, "search", new=AsyncMock(return_value=[])), patch(
            "app.adapters.federated.assign_canonical_keys",
            side_effect=lambda hits, persist=True: hits,
        ), patch(
            "app.adapters.federated.orchestrate_federated_hits",
            new=AsyncMock(side_effect=_orch),
        ):
            out = await federated_search(
                FederatedSearchQuery(
                    termo_busca="qualquer",
                    fontes_habilitadas=["compras_gov"],
                )
            )
        self.assertTrue(out.get("ok"))
        self.assertEqual(out.get("itens") or [], [])
        self.assertEqual((out.get("stats") or {}).get("fontes", {}).get("compras_gov", {}).get("hits"), 0)

    async def test_lista_completa_manual_includes_compras_gov_rows(self):
        """Busca manual (lista_completa): FTS platform_index + mapping."""
        platform_row = {
            "plataforma_item_id": "cg:9:1",
            "descricao_item": "CANETA ESFEROGRAFICA AZUL",
            "valor_unitario": 1.25,
            "valor_unitario_homologado": 1.25,
            "fornecedor_nome": "PAPELARIA CG",
            "cnpj_fornecedor": "11222333000144",
            "orgao": "ORGAO FEDERAL",
            "uf": "SP",
            "municipio": "São Paulo",
        }

        with patch(
            "app.local_index.local_item_search",
            return_value={"ok": True, "itens": [], "stats": {}},
        ), patch(
            "app.platform_index.search.platform_item_search",
            return_value=[platform_row],
        ):
            out = await federated_search(
                FederatedSearchQuery(
                    termo_busca="CANETA",
                    fontes_habilitadas=["compras_gov"],
                    lista_completa=True,
                    tamanho_pagina=50,
                    max_paginas=5,
                )
            )

        self.assertTrue(out.get("ok"))
        self.assertTrue((out.get("stats") or {}).get("lista_completa"))
        itens = out.get("itens") or []
        self.assertEqual(len(itens), 1)
        self.assertEqual(itens[0].get("plataforma"), "compras_gov")
        self.assertEqual(itens[0].get("fonte"), "governamentais")
        self.assertEqual(itens[0].get("inciso_classificacao"), "inciso_i")
        fontes = (out.get("stats") or {}).get("fontes") or {}
        self.assertEqual(fontes.get("compras_gov", {}).get("modo"), "platform_fts")
        self.assertEqual(fontes.get("compras_gov", {}).get("hits"), 1)

    async def test_lista_completa_indisponivel_fonte_desconhecida(self):
        with patch(
            "app.local_index.local_item_search",
            return_value={"ok": True, "itens": [], "stats": {}},
        ):
            out = await federated_search(
                FederatedSearchQuery(
                    termo_busca="x",
                    fontes_habilitadas=["fonte_que_nao_existe"],
                    lista_completa=True,
                )
            )
        self.assertTrue(out.get("ok"))
        fontes = (out.get("stats") or {}).get("fontes") or {}
        self.assertEqual(fontes.get("fonte_que_nao_existe", {}).get("erro"), "fonte indisponível")


def test_adapter_registered_in_catalog():
    assert "compras_gov" in list_adapter_ids()
    adapter = get_adapter("compras_gov")
    assert adapter is not None
    caps = adapter.capabilities()
    assert caps.get("id") == "compras_gov"
    assert "Compras.gov" in str(caps.get("label") or "")


def test_hit_mapping_save_ready_fields():
    row = hit_to_pncp_row(_cg_hit())
    assert row["plataforma"] == "compras_gov"
    assert row["fonte"] == "governamentais"
    assert row["inciso_classificacao"] == "inciso_i"
    assert row["esfera"] == "federal"
    assert row["url_origem"] == "https://example.gov.br/compra/1"
