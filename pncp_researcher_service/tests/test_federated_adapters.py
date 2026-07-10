"""Testes do núcleo federado multi-fonte (Parte 0)."""
from __future__ import annotations

import pytest

from app.adapters.contracts import FederatedSearchQuery, MarketPriceHit
from app.adapters.dedup import dedupe_hits
from app.adapters.mapping import hit_to_pncp_row, pncp_row_to_hit


def test_pncp_row_roundtrip_preserves_plataforma():
    row = {
        "numero_pncp": "12345678000199-1-000001/2024",
        "numero_item": "1",
        "descricao_item": "Papel A4",
        "valor_unitario": 25.5,
        "valor_unitario_homologado": 25.5,
        "orgao": "Prefeitura Teste",
        "uf": "SC",
        "cnpj_fornecedor": "12345678000199",
    }
    hit = pncp_row_to_hit(row)
    assert hit.plataforma == "pncp"
    out = hit_to_pncp_row(hit)
    assert out["plataforma"] == "pncp"
    assert out["descricao_item"] == "Papel A4"


def test_dedupe_hits_merges_same_item():
    h1 = MarketPriceHit(
        plataforma="pncp",
        plataforma_item_id="abc:1",
        descricao_item="Item X",
        valor_unitario=10.0,
    )
    h2 = MarketPriceHit(
        plataforma="pncp",
        plataforma_item_id="abc:1",
        descricao_item="Item X",
        valor_unitario=12.0,
        valor_unitario_homologado=12.0,
    )
    out = dedupe_hits([h1, h2])
    assert len(out) == 1
    assert out[0].valor_unitario_homologado == 12.0


def test_federated_query_defaults_to_pncp():
    q = FederatedSearchQuery(termo_busca="papel")
    assert q.fontes_habilitadas == ["pncp"]
