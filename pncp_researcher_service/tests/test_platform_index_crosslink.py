"""Testes de índices SQLite por plataforma e cruzamento cross-platform."""
from __future__ import annotations

import os
import tempfile

import pytest

from app.adapters.contracts import MarketPriceHit
from app.adapters.crosslink import assign_canonical_keys, build_canonical_key
from app.adapters.dedup import dedupe_hits
from app.platform_index.crosslink_db import (
    ensure_crosslink_db,
    resolve_canonical_key,
    upsert_cross_ref,
)
from app.platform_index.schema import ensure_platform_index, platform_index_stats


@pytest.fixture
def tce_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "tce_rs_local.db")
    monkeypatch.setenv("TCE_RS_LOCAL_DB_PATH", db_path)
    monkeypatch.setenv("PRICE_PLATFORM_DATA_ROOT", str(tmp_path))
    # Re-register path via ensure with explicit db_path
    path = ensure_platform_index("tce_rs", db_path=db_path)
    return path


@pytest.fixture
def crosslink_db(tmp_path, monkeypatch):
    path = str(tmp_path / "crosslink.db")
    monkeypatch.setenv("PRICE_CROSSLINK_DB_PATH", path)
    ensure_crosslink_db(path)
    return path


def test_ensure_platform_index_creates_tables(tce_db):
    stats = platform_index_stats(tce_db)
    assert stats["db_exists"] is True
    assert stats["itens_leitura"] == 0


def test_crosslink_same_pncp_merges_platforms(crosslink_db):
    upsert_cross_ref(
        canonical_key="pncp|CNPJ-1-000001/2024|1",
        plataforma="pncp",
        plataforma_item_id="CNPJ-1-000001/2024:1",
        numero_pncp="CNPJ-1-000001/2024",
        numero_item="1",
        db_path=crosslink_db,
    )
    upsert_cross_ref(
        canonical_key="pncp|CNPJ-1-000001/2024|1",
        plataforma="tce_rs",
        plataforma_item_id="lic-99:1",
        numero_pncp="CNPJ-1-000001/2024",
        numero_item="1",
        db_path=crosslink_db,
    )
    key = resolve_canonical_key(
        plataforma="tce_rs",
        plataforma_item_id="lic-99:1",
        numero_pncp="CNPJ-1-000001/2024",
        numero_item="1",
        db_path=crosslink_db,
    )
    assert key == "pncp|CNPJ-1-000001/2024|1"


def test_dedupe_cross_platform_keeps_both_sources():
    """União justa: mesmo canonical_key em PNCP + TCE não apaga uma fonte."""
    h_pncp = MarketPriceHit(
        plataforma="pncp",
        plataforma_item_id="CNPJ-1-000001/2024:1",
        descricao_item="Papel A4",
        valor_unitario=25.0,
        valor_unitario_homologado=25.0,
        raw={"numero_pncp": "CNPJ-1-000001/2024", "numero_item": "1"},
        canonical_key="pncp|CNPJ-1-000001/2024|1",
    )
    h_tce = MarketPriceHit(
        plataforma="tce_rs",
        plataforma_item_id="lic-99:1",
        descricao_item="Papel A4 sulfite",
        valor_unitario=25.0,
        valor_unitario_homologado=25.0,
        raw={"numero_pncp": "CNPJ-1-000001/2024", "numero_item": "1"},
        canonical_key="pncp|CNPJ-1-000001/2024|1",
    )
    out = dedupe_hits([h_pncp, h_tce])
    assert len(out) == 2
    plats = {h.plataforma for h in out}
    assert plats == {"pncp", "tce_rs"}


def test_build_canonical_key_prefers_numero_pncp():
    hit = MarketPriceHit(
        plataforma="tce_rs",
        plataforma_item_id="x:1",
        descricao_item="Item",
        valor_unitario=10.0,
        raw={"numero_pncp": "ABC-1/2024", "numero_item": "1"},
    )
    assert build_canonical_key(hit) == "pncp|ABC-1/2024|1"


def test_assign_canonical_keys_persists(crosslink_db, monkeypatch):
    monkeypatch.setenv("PRICE_CROSSLINK_DB_PATH", crosslink_db)
    hits = [
        MarketPriceHit(
            plataforma="pncp",
            plataforma_item_id="NP:2",
            descricao_item="Tinta",
            valor_unitario=5.0,
            raw={"numero_pncp": "NP", "numero_item": "2"},
        )
    ]
    linked = assign_canonical_keys(hits, persist=True, db_path=crosslink_db)
    assert linked[0].canonical_key == "pncp|NP|2"
    stored = resolve_canonical_key(
        plataforma="pncp",
        plataforma_item_id="NP:2",
        db_path=crosslink_db,
    )
    assert stored == "pncp|NP|2"
