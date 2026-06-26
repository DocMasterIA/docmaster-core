"""Busca em lote (busca_lote): recall, enrich async, filtro de fornecedor e performance."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.config import PNCP_BULK_ENRICH_HOMOLOG_MAX, PNCP_BULK_LOCAL_ENRICH_HOMOLOG_MAX, PNCP_SEARCH_ENRICH_HOMOLOG_MAX
from app.schemas import MarketSearchRequest
from app.service import market_search_intelligent
from app.supplier_resolver import item_fornecedor_valido_para_busca


def _homolog_item(
    *,
    desc: str = "ITEM TESTE BULK HOMOLOG",
    price: float = 10.0,
    fornecedor: str = "Não se aplica",
    cnpj: str = "",
    numero_pncp: str = "12345678000195-1-000001",
    numero_item: str = "1",
) -> dict:
    return {
        "descricao_item": desc,
        "material_servico": "",
        "valor_unitario": price,
        "fornecedor": fornecedor,
        "cnpj_fornecedor": cnpj,
        "item_homologado": True,
        "numero_pncp": numero_pncp,
        "ano_compra": 2024,
        "sequencial_compra": 1,
        "numero_item": numero_item,
        "origem": "base_local_itens",
        "search_tier": "strict",
        "situacao_compra": "Homologada",
    }


def _local_result(itens: list[dict]) -> dict:
    return {"ok": True, "itens": itens, "stats": {"sql_rows_fetched": len(itens)}}


def _patch_bulk_legacy():
    return patch("app.service.PNCP_BULK_USE_INTELLIGENT_PIPELINE", False)


class BulkSearchLoteRecallTests(unittest.IsolatedAsyncioTestCase):
    async def test_bulk_stops_term_fallbacks_after_one_priced_hit(self):
        payload = MarketSearchRequest(
            termo_busca="ITEM TESTE BULK HOMOLOG",
            busca_lote=True,
            somente_homologados=False,
        )
        calls: list[str] = []

        def _track(term, **kwargs):
            calls.append(term)
            return _local_result([_homolog_item()])

        with _patch_bulk_legacy(), patch("app.service.local_item_search", side_effect=_track), patch(
            "app.service.market_search",
            new_callable=AsyncMock,
            return_value={"ok": True, "itens": [], "stats": {}},
        ), patch(
            "app.service.enrich_homolog_items_from_pncp", new_callable=AsyncMock, return_value=0
        ):
            await market_search_intelligent(payload)

        self.assertEqual(len(calls), 1, f"esperava 1 termo, obteve {len(calls)}: {calls}")

    async def test_bulk_limits_term_attempts_when_index_has_no_price(self):
        payload = MarketSearchRequest(
            termo_busca="PRODUTO INEXISTENTE XYZ 999",
            busca_lote=True,
            somente_homologados=False,
        )
        calls: list[str] = []

        def _empty(term, **kwargs):
            calls.append(term)
            return _local_result([])

        with _patch_bulk_legacy(), patch("app.service.local_item_search", side_effect=_empty), patch(
            "app.service.market_search",
            new_callable=AsyncMock,
            return_value={"ok": True, "itens": [], "stats": {}},
        ), patch(
            "app.service.enrich_homolog_items_from_pncp", new_callable=AsyncMock, return_value=0
        ):
            await market_search_intelligent(payload)

        self.assertGreaterEqual(len(calls), 1)
        self.assertLessEqual(len(calls), 3, f"no máximo 3 termos sem preço, obteve {len(calls)}")

    async def test_manual_search_keeps_supplier_filter_in_local_index(self):
        payload = MarketSearchRequest(
            termo_busca="ITEM MANUAL",
            busca_lote=False,
            somente_homologados=False,
        )
        with patch("app.service.local_item_search", return_value=_local_result([])) as local_mock, patch(
            "app.service.market_search",
            new_callable=AsyncMock,
            return_value={"ok": True, "itens": [], "stats": {}},
        ), patch(
            "app.service.enrich_homolog_items_from_pncp", new_callable=AsyncMock, return_value=0
        ):
            await market_search_intelligent(payload)
        kw = local_mock.call_args.kwargs
        self.assertTrue(kw.get("filtrar_fornecedor_para_exibicao", False))
        self.assertIsNone(kw.get("enrich_homolog_max"))

    async def test_bulk_uses_local_enrich_in_index(self):
        payload = MarketSearchRequest(termo_busca="ITEM TESTE BULK", busca_lote=True)
        with _patch_bulk_legacy(), patch("app.service.local_item_search", return_value=_local_result([])) as local_mock, patch(
            "app.service.market_search",
            new_callable=AsyncMock,
            return_value={"ok": True, "itens": [], "stats": {}},
        ):
            await market_search_intelligent(payload)
        kw = local_mock.call_args.kwargs
        self.assertFalse(kw.get("filtrar_fornecedor_para_exibicao", True))
        self.assertEqual(kw.get("enrich_homolog_max"), max(0, int(PNCP_BULK_LOCAL_ENRICH_HOMOLOG_MAX)))


class BulkSearchSupplierFilterTests(unittest.IsolatedAsyncioTestCase):
    async def test_bulk_keeps_name_only_supplier_for_display_recall(self):
        payload = MarketSearchRequest(
            termo_busca="ITEM NOME SEM CNPJ",
            busca_lote=True,
            somente_homologados=False,
        )
        pool = [
            _homolog_item(
                desc="ITEM NOME SEM CNPJ",
                fornecedor="FORNECEDORA EXEMPLO LTDA",
                cnpj="",
            ),
        ]
        with patch(
            "app.service.local_item_search", return_value=_local_result(pool)
        ), patch(
            "app.service.market_search",
            new_callable=AsyncMock,
            return_value={"ok": True, "itens": [], "stats": {}},
        ), patch(
            "app.service.enrich_homolog_items_from_pncp", new_callable=AsyncMock, return_value=0
        ):
            out = await market_search_intelligent(payload)

        itens = out.get("itens") or []
        self.assertGreaterEqual(len(itens), 1)
        self.assertTrue(item_fornecedor_valido_para_busca(itens[0]))

    async def test_bulk_drops_placeholder_supplier_without_enrich(self):
        payload = MarketSearchRequest(
            termo_busca="ITEM TESTE BULK HOMOLOG",
            busca_lote=True,
            somente_homologados=False,
        )
        pool = [
            _homolog_item(desc="ITEM TESTE BULK HOMOLOG A", price=10.0, numero_item="1"),
            _homolog_item(desc="ITEM TESTE BULK HOMOLOG B", price=11.0, numero_item="2"),
            _homolog_item(desc="ITEM TESTE BULK HOMOLOG C", price=9.0, numero_item="3"),
        ]
        with patch(
            "app.service.local_item_search", return_value=_local_result(pool)
        ), patch(
            "app.service.market_search",
            new_callable=AsyncMock,
            return_value={"ok": True, "itens": [], "stats": {}},
        ), patch(
            "app.service.enrich_homolog_items_from_pncp", new_callable=AsyncMock, return_value=0
        ) as enrich_mock:
            out = await market_search_intelligent(payload)

        enrich_mock.assert_called()
        funil = (out.get("stats") or {}).get("funil_busca") or {}
        self.assertGreater(funil.get("top3_antes_filtro_fornecedor", 0), 0)
        self.assertEqual(funil.get("top3_apos_filtro_fornecedor"), 0)
        self.assertEqual(out.get("itens") or [], [])

    async def test_bulk_lote_returns_up_to_3_when_pool_has_more(self):
        payload = MarketSearchRequest(
            termo_busca="ALCOOL GEL 70",
            busca_lote=True,
            somente_homologados=True,
            valor_base_referencia=15.03,
            variacao_percentual_referencia=50.0,
            variacao_sentido_referencia="ambos",
        )
        pool = [
            _homolog_item(
                desc=f"ALCOOL GEL 70% 500ML LOTE {i}",
                price=10.0 + i * 0.5,
                fornecedor="FORNECEDORA EXEMPLO LTDA",
                cnpj="12.345.678/0001-95",
                numero_item=str(i),
                numero_pncp=f"1234567800019{i}-1-000001",
            )
            for i in range(1, 8)
        ]
        with patch(
            "app.service.local_item_search", return_value=_local_result(pool)
        ), patch(
            "app.service.market_search",
            new_callable=AsyncMock,
            return_value={"ok": True, "itens": [], "stats": {}},
        ), patch(
            "app.service.enrich_homolog_items_from_pncp", new_callable=AsyncMock, return_value=0
        ):
            out = await market_search_intelligent(payload)

        itens = out.get("itens") or []
        self.assertEqual(len(itens), 3)
        funil = (out.get("stats") or {}).get("funil_busca") or {}
        self.assertEqual(funil.get("top3_final"), 3)
        self.assertEqual(funil.get("modo_resposta"), "bulk_intelligent_top3")
        self.assertIn("scored_final_pool", funil)

    async def test_bulk_returns_items_when_async_enrich_fixes_supplier(self):
        payload = MarketSearchRequest(
            termo_busca="ITEM TESTE BULK HOMOLOG",
            busca_lote=True,
            somente_homologados=False,
        )
        pool = [
            _homolog_item(desc="ITEM TESTE BULK HOMOLOG A", price=10.0, numero_item="1"),
            _homolog_item(desc="ITEM TESTE BULK HOMOLOG B", price=11.0, numero_item="2"),
            _homolog_item(desc="ITEM TESTE BULK HOMOLOG C", price=9.0, numero_item="3"),
        ]

        from app.supplier_resolver import item_fornecedor_tem_cnpj_para_salvar

        async def _enrich_fix(itens, max_n=3):
            n = 0
            for it in itens:
                if n >= max_n:
                    break
                if item_fornecedor_tem_cnpj_para_salvar(it):
                    continue
                it["cnpj_fornecedor"] = "12.345.678/0001-95"
                it["fornecedor"] = "FORNECEDORA EXEMPLO LTDA"
                it["fornecedor_busca_pncp"] = True
                n += 1
            return n

        with patch(
            "app.service.local_item_search", return_value=_local_result(pool)
        ), patch(
            "app.service.market_search",
            new_callable=AsyncMock,
            return_value={"ok": True, "itens": [], "stats": {}},
        ), patch(
            "app.service.enrich_homolog_items_from_pncp", side_effect=_enrich_fix
        ):
            out = await market_search_intelligent(payload)

        itens = out.get("itens") or []
        self.assertGreaterEqual(len(itens), 1)
        for it in itens:
            self.assertTrue(item_fornecedor_valido_para_busca(it), it)
            self.assertFalse(
                str(it.get("fornecedor") or "").strip().lower() == "não se aplica",
                it,
            )

    async def test_bulk_keeps_items_with_valid_supplier_without_enrich(self):
        payload = MarketSearchRequest(
            termo_busca="ITEM VALIDO CNPJ",
            busca_lote=True,
            somente_homologados=False,
        )
        pool = [
            _homolog_item(
                desc="ITEM VALIDO CNPJ",
                fornecedor="FORNECEDORA EXEMPLO LTDA",
                cnpj="12.345.678/0001-95",
            ),
        ]
        with patch(
            "app.service.local_item_search", return_value=_local_result(pool)
        ), patch(
            "app.service.market_search",
            new_callable=AsyncMock,
            return_value={"ok": True, "itens": [], "stats": {}},
        ), patch(
            "app.service.enrich_homolog_items_from_pncp", new_callable=AsyncMock, return_value=0
        ) as enrich_mock:
            out = await market_search_intelligent(payload)

        itens = out.get("itens") or []
        self.assertGreaterEqual(len(itens), 1)
        self.assertEqual(itens[0]["cnpj_fornecedor"], "12.345.678/0001-95")
        # enrich pode ser chamado no top3, mas não precisa alterar linhas já válidas
        if enrich_mock.called:
            self.assertGreaterEqual(enrich_mock.return_value, 0)

    async def test_bulk_enrich_cap_matches_config(self):
        payload = MarketSearchRequest(termo_busca="ITEM TESTE BULK HOMOLOG", busca_lote=True)
        pool = [_homolog_item() for _ in range(3)]
        with patch(
            "app.service.local_item_search", return_value=_local_result(pool)
        ), patch(
            "app.service.market_search",
            new_callable=AsyncMock,
            return_value={"ok": True, "itens": [], "stats": {}},
        ), patch(
            "app.service.enrich_homolog_items_from_pncp", new_callable=AsyncMock, return_value=0
        ) as enrich_mock:
            await market_search_intelligent(payload)
        self.assertTrue(enrich_mock.called)
        cap = enrich_mock.call_args.kwargs.get("max_n")
        expected_cap = min(len(pool), max(int(PNCP_SEARCH_ENRICH_HOMOLOG_MAX), int(PNCP_BULK_ENRICH_HOMOLOG_MAX)))
        self.assertLessEqual(cap, expected_cap)
        self.assertGreaterEqual(cap, 1)


class BulkIntelligentPipelineFlagTests(unittest.IsolatedAsyncioTestCase):
    async def test_bulk_intelligent_uses_full_sql_limit_not_frontend_cap(self):
        payload = MarketSearchRequest(
            termo_busca="ITEM TESTE BULK HOMOLOG",
            busca_lote=True,
            max_paginas=3,
            tamanho_pagina=80,
            somente_homologados=False,
        )
        with patch("app.service.local_item_search", return_value=_local_result([])) as local_mock, patch(
            "app.service.market_search",
            new_callable=AsyncMock,
            return_value={"ok": True, "itens": [], "stats": {}},
        ), patch(
            "app.service.enrich_homolog_items_from_pncp", new_callable=AsyncMock, return_value=0
        ):
            await market_search_intelligent(payload)
        kw = local_mock.call_args.kwargs
        from app.config import PNCP_BULK_INTELLIGENT_SQL_LIMIT

        self.assertGreaterEqual(int(kw.get("limit") or 0), int(PNCP_BULK_INTELLIGENT_SQL_LIMIT))

    async def test_bulk_intelligent_pipeline_is_default(self):
        payload = MarketSearchRequest(
            termo_busca="ITEM TESTE BULK HOMOLOG",
            busca_lote=True,
            somente_homologados=False,
        )
        pool = [
            _homolog_item(
                price=10.0 + i,
                fornecedor="FORNECEDORA OK LTDA",
                cnpj="12.345.678/0001-95",
                numero_item=str(i + 1),
                numero_pncp=f"12345678000195-1-00000{i + 1}",
            )
            for i in range(3)
        ]
        with patch("app.service.local_item_search", return_value=_local_result(pool)), patch(
            "app.service.market_search",
            new_callable=AsyncMock,
            return_value={"ok": True, "itens": [], "stats": {}},
        ), patch(
            "app.service.enrich_homolog_items_from_pncp", new_callable=AsyncMock, return_value=0
        ):
            out = await market_search_intelligent(payload)

        funil = (out.get("stats") or {}).get("funil_busca") or {}
        self.assertTrue(funil.get("bulk_intelligent_pipeline"))
        self.assertEqual(funil.get("modo_resposta"), "bulk_intelligent_top3")
        self.assertIn("scored_final_pool", funil)
        self.assertGreaterEqual(len(out.get("itens") or []), 1)

    async def test_bulk_legacy_uses_parity_finalize_when_flag_off(self):
        payload = MarketSearchRequest(
            termo_busca="ITEM TESTE BULK HOMOLOG",
            busca_lote=True,
            somente_homologados=False,
        )
        pool = [
            _homolog_item(
                price=10.0 + i,
                fornecedor="FORNECEDORA OK LTDA",
                cnpj="12.345.678/0001-95",
                numero_item=str(i + 1),
            )
            for i in range(3)
        ]
        with _patch_bulk_legacy(), patch("app.service.local_item_search", return_value=_local_result(pool)), patch(
            "app.service.market_search",
            new_callable=AsyncMock,
            return_value={"ok": True, "itens": [], "stats": {}},
        ), patch(
            "app.service.enrich_homolog_items_from_pncp", new_callable=AsyncMock, return_value=0
        ):
            out = await market_search_intelligent(payload)

        funil = (out.get("stats") or {}).get("funil_busca") or {}
        self.assertFalse(funil.get("bulk_intelligent_pipeline"))
        self.assertEqual(funil.get("modo_resposta"), "busca_lote_top3_parity")


class BulkSearchHybridTests(unittest.IsolatedAsyncioTestCase):
    async def test_bulk_invokes_hybrid_when_no_local_price(self):
        payload = MarketSearchRequest(
            termo_busca="ITEM SEM INDICE",
            busca_lote=True,
            somente_homologados=False,
        )
        live_item = {
            "descricao_item": "ITEM SEM INDICE LIVE",
            "valor_unitario": 7.5,
            "fornecedor": "FORNECEDORA LIVE LTDA",
            "cnpj_fornecedor": "98.765.432/0001-10",
            "numero_pncp": "LIVE-1",
            "origem": "pncp_live_fallback",
            "search_tier": "strict",
        }
        live_mock = AsyncMock(return_value={"ok": True, "itens": [live_item], "stats": {}})
        with patch("app.service.local_item_search", return_value=_local_result([])), patch(
            "app.service.market_search", live_mock
        ), patch(
            "app.service.enrich_homolog_items_from_pncp", new_callable=AsyncMock, return_value=0
        ):
            out = await market_search_intelligent(payload)

        live_mock.assert_called()
        funil = (out.get("stats") or {}).get("funil_busca") or {}
        self.assertTrue(funil.get("hybrid_fallback_used") or (out.get("stats") or {}).get("hybrid_fallback_used"))


if __name__ == "__main__":
    unittest.main()
