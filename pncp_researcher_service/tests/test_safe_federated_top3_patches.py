from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.adapters.indexed_platform_adapter import TceRsAdapter  # noqa: E402
from app.adapters.contracts import FederatedSearchQuery  # noqa: E402
from app.service import (  # noqa: E402
    _ensure_top3_from_pool,
    _ia_item_key,
    _merge_unique_items,
    _select_top3_mixed_literal_similar,
)


def _row(**kwargs):
    base = {
        "numero_pncp": "",
        "numero_item": "1",
        "descricao_item": "FIO NYLON N 4.0",
        "orgao": "HOSPITAL X",
        "valor_unitario": 2.5,
        "literal_match": 40.0,
        "score_aprovacao": 70,
        "plataforma": "tce_rs",
    }
    base.update(kwargs)
    return base


class TestSafeTop3FederatedPatches(unittest.TestCase):
    def test_ia_item_key_distinguishes_same_desc_different_platform_ids(self):
        a = _row(plataforma_item_id="tce-1", valor_unitario=2.1)
        b = _row(plataforma_item_id="tce-2", valor_unitario=2.2)
        c = _row(plataforma="compras_gov", plataforma_item_id="cg-1", valor_unitario=2.3)
        self.assertNotEqual(_ia_item_key(a), _ia_item_key(b))
        self.assertNotEqual(_ia_item_key(a), _ia_item_key(c))

    def test_ensure_top3_does_not_collapse_tce_twins(self):
        """Regressão: 200 TCE com mesma descrição colapsavam em 1 chave sem plataforma."""
        pool = [
            _row(plataforma_item_id=f"tce-{i}", valor_unitario=2.0 + i * 0.1, score_aprovacao=70 + i)
            for i in range(5)
        ]
        got = _ensure_top3_from_pool([pool[0]], pool, target=3, termo_busca="FIO NYLON")
        self.assertEqual(len(got), 3)
        keys = {_ia_item_key(x) for x in got}
        self.assertEqual(len(keys), 3)

    def test_merge_unique_keeps_cross_platform_same_desc(self):
        a = _row(plataforma="pncp", numero_pncp="99", plataforma_item_id="")
        b = _row(plataforma="tce_rs", plataforma_item_id="tce-9")
        merged = _merge_unique_items([a], [b])
        self.assertEqual(len(merged), 2)

    def test_mixed_literal_similar_fills_when_max_similar_allows(self):
        literal = [_row(plataforma_item_id="lit-1", literal_match=50, score_aprovacao=85)]
        similar = [
            _row(
                plataforma_item_id="sim-1",
                literal_match=8,
                score_aprovacao=60,
                similaridade_encontrada=True,
            ),
            _row(
                plataforma_item_id="sim-2",
                literal_match=7,
                score_aprovacao=58,
                similaridade_encontrada=True,
            ),
        ]
        # Cap antigo (=1) deixava top incompleto; fill seguro usa max_similar=2.
        got = _select_top3_mixed_literal_similar(literal, similar, max_similar=2)
        self.assertEqual(len(got), 3)


class TestPlatformSearchLimit(unittest.IsolatedAsyncioTestCase):
    async def test_adapter_uses_config_limit_not_hardcoded_50(self):
        captured = {}

        def fake_search(spec, *, termo, uf, limit):
            captured["limit"] = limit
            return []

        with patch("app.adapters.indexed_platform_adapter.get_platform_spec") as gs, patch(
            "app.adapters.indexed_platform_adapter.platform_item_search",
            side_effect=fake_search,
        ), patch(
            "app.adapters.indexed_platform_adapter.PNCP_FEDERATED_PLATFORM_SEARCH_LIMIT",
            200,
        ):
            spec = type(
                "S",
                (),
                {
                    "schema_kind": "platform_index",
                    "uf_scope": "RS",
                    "inciso_default": "inciso_ii",
                    "esfera_default": "estadual",
                },
            )()
            gs.return_value = spec
            adapter = TceRsAdapter()
            q = FederatedSearchQuery(termo_busca="fio nylon", tamanho_pagina=200, uf="RS")
            await adapter.search(q)
        self.assertEqual(captured.get("limit"), 200)


if __name__ == "__main__":
    unittest.main()
