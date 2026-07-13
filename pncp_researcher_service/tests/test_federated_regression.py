"""
Regressão Parte 0 multi-fonte: garante paridade com market_search_intelligent,
bulk/lote, faixa regional e formatação de payload — sem degradar melhorias anteriores.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.adapters.contracts import FederatedSearchQuery
from app.adapters.federated import federated_search
from app.adapters.mapping import hit_to_pncp_row, pncp_row_to_hit
from app.schemas import MarketSearchRequest
from app.service import market_search_intelligent


def _homolog_item(
    *,
    desc: str = "PAPEL A4 REGRESSAO",
    price: float = 25.0,
    fornecedor: str = "Fornecedor Teste LTDA",
    cnpj: str = "12345678000199",
    numero_pncp: str = "12345678000195-1-000001/2024",
    numero_item: str = "1",
    score: float = 88.0,
) -> dict:
    return {
        "descricao_item": desc,
        "material_servico": "Material",
        "valor_unitario": price,
        "valor_unitario_homologado": price,
        "fornecedor": fornecedor,
        "cnpj_fornecedor": cnpj,
        "item_homologado": True,
        "numero_pncp": numero_pncp,
        "ano_compra": 2024,
        "sequencial_compra": 1,
        "numero_item": numero_item,
        "origem": "base_local_itens",
        "search_tier": "strict",
        "score_aprovacao": score,
        "confiabilidade": "Alta",
        "risco": "Baixo",
        "status": "Aprovado",
        "uf": "SC",
        "municipio": "Florianópolis",
        "orgao": "Prefeitura Teste",
        "situacao_compra": "Homologada",
        "similaridade_encontrada": True,
    }


def _local_result(itens: list[dict]) -> dict:
    return {"ok": True, "itens": itens, "stats": {"sql_rows_fetched": len(itens)}}


def _patch_search_stack():
    """Mesmo stack de mocks usado nos testes de bulk/lote."""
    return (
        patch(
            "app.service.local_item_search",
            return_value=_local_result([_homolog_item(), _homolog_item(numero_item="2", price=26.0)]),
        ),
        patch(
            "app.service.market_search",
            new_callable=AsyncMock,
            return_value={"ok": True, "itens": [], "stats": {}},
        ),
        patch(
            "app.service.enrich_homolog_items_from_pncp",
            new_callable=AsyncMock,
            return_value=0,
        ),
    )


class FederatedParityTests(unittest.IsolatedAsyncioTestCase):
    async def test_federated_pncp_only_matches_intelligent_itens(self):
        payload = MarketSearchRequest(
            termo_busca="PAPEL A4 REGRESSAO",
            somente_homologados=False,
            fontes_habilitadas=["pncp"],
        )
        query = FederatedSearchQuery.from_market_request(payload)

        with patch(
            "app.service.local_item_search",
            return_value=_local_result([_homolog_item()]),
        ), patch(
            "app.service.market_search",
            new_callable=AsyncMock,
            return_value={"ok": True, "itens": [], "stats": {}},
        ), patch(
            "app.service.enrich_homolog_items_from_pncp",
            new_callable=AsyncMock,
            return_value=0,
        ):
            direct = await market_search_intelligent(payload)
            federated = await federated_search(query)

        self.assertTrue(direct.get("ok"))
        self.assertTrue(federated.get("ok"))
        self.assertEqual(len(direct.get("itens") or []), len(federated.get("itens") or []))
        d0 = (direct.get("itens") or [])[0]
        f0 = (federated.get("itens") or [])[0]
        for key in (
            "descricao_item",
            "valor_unitario_homologado",
            "score_aprovacao",
            "numero_pncp",
            "cnpj_fornecedor",
            "search_tier",
            "similaridade_encontrada",
        ):
            self.assertEqual(f0.get(key), d0.get(key), msg=key)
        self.assertEqual(f0.get("plataforma"), "pncp")

    async def test_federated_pncp_fast_path_calls_intelligent_once(self):
        payload = MarketSearchRequest(termo_busca="PAPEL A4", fontes_habilitadas=["pncp"])
        query = FederatedSearchQuery.from_market_request(payload)
        mock_intel = AsyncMock(
            return_value={"ok": True, "filtros": {}, "stats": {}, "itens": [_homolog_item()]}
        )
        with patch("app.service.market_search_intelligent", mock_intel):
            await federated_search(query)
        self.assertEqual(mock_intel.await_count, 1)

    async def test_federated_bulk_lote_preserves_recall_behavior(self):
        """Bulk com hit: 1 tentativa de termo (mesma regra de recall do lote)."""
        payload = MarketSearchRequest(
            termo_busca="PAPEL A4 REGRESSAO",
            busca_lote=True,
            somente_homologados=False,
            fontes_habilitadas=["pncp"],
        )
        query = FederatedSearchQuery.from_market_request(payload)
        calls: list[str] = []

        def _track(term, **kwargs):
            calls.append(term)
            return _local_result([_homolog_item()])

        with patch(
            "app.service.local_item_search", side_effect=_track
        ), patch(
            "app.service.market_search",
            new_callable=AsyncMock,
            return_value={"ok": True, "itens": [], "stats": {}},
        ), patch(
            "app.service.enrich_homolog_items_from_pncp",
            new_callable=AsyncMock,
            return_value=0,
        ):
            federated = await federated_search(query)

        self.assertEqual(len(calls), 1, f"esperava 1 termo no bulk, obteve {calls}")
        self.assertTrue(federated.get("ok"))
        self.assertGreaterEqual(len(federated.get("itens") or []), 1)
        self.assertEqual(federated.get("itens", [{}])[0].get("plataforma"), "pncp")

    async def test_federated_faixa_regional_filtros_inalterados(self):
        payload = MarketSearchRequest(
            termo_busca="ALCOOL ETILICO 70",
            max_paginas=10,
            tamanho_pagina=80,
            valor_base_referencia=15.0,
            variacao_percentual_referencia=20.0,
            variacao_sentido_referencia="baixo",
            somente_homologados=False,
            fontes_habilitadas=["pncp"],
        )
        query = FederatedSearchQuery.from_market_request(payload)

        with patch(
            "app.service.local_item_search",
            return_value=_local_result([_homolog_item(desc="ALCOOL ETILICO 70", price=14.0)]),
        ), patch(
            "app.service.market_search",
            new_callable=AsyncMock,
            return_value={"ok": True, "itens": [], "stats": {}},
        ), patch(
            "app.service.enrich_homolog_items_from_pncp",
            new_callable=AsyncMock,
            return_value=0,
        ):
            direct = await market_search_intelligent(payload)
            federated = await federated_search(query)

        for key in ("faixa_regional_min", "faixa_regional_max", "variacao_sentido_referencia"):
            self.assertEqual(
                federated.get("filtros", {}).get(key),
                direct.get("filtros", {}).get(key),
                msg=key,
            )

    async def test_federated_disabled_does_not_crash(self):
        query = FederatedSearchQuery(termo_busca="teste", fontes_habilitadas=["pncp"])
        with patch("app.adapters.federated.PNCP_FEDERATED_SEARCH_ENABLED", False):
            out = await federated_search(query)
        self.assertFalse(out.get("ok"))
        self.assertEqual(out.get("stats", {}).get("erro"), "federated_disabled")


class MappingRegressionTests(unittest.TestCase):
    def test_mapping_preserves_scoring_and_display_fields(self):
        row = _homolog_item()
        hit = pncp_row_to_hit(row)
        out = hit_to_pncp_row(hit)
        for key in (
            "score_aprovacao",
            "confiabilidade",
            "risco",
            "status",
            "search_tier",
            "similaridade_encontrada",
            "origem",
        ):
            self.assertEqual(out.get(key), row.get(key), msg=key)
        self.assertEqual(out.get("plataforma"), "pncp")

    def test_mapping_does_not_drop_extra_raw_fields(self):
        row = _homolog_item()
        row["ia_interpretacao_item"] = "Interpretação IA preservada"
        hit = pncp_row_to_hit(row)
        out = hit_to_pncp_row(hit)
        self.assertEqual(out.get("ia_interpretacao_item"), "Interpretação IA preservada")


class SchemaRegressionTests(unittest.TestCase):
    def test_fontes_habilitadas_from_comma_string(self):
        p = MarketSearchRequest(termo_busca="papel", fontes_habilitadas="pncp, tce_rs")
        self.assertEqual(p.fontes_habilitadas, ["pncp", "tce_rs"])

    def test_federated_query_from_request_preserves_faixa(self):
        p = MarketSearchRequest(
            termo_busca="papel",
            valor_base_referencia=100.0,
            variacao_percentual_referencia=10.0,
            variacao_sentido_referencia="ambos",
            fontes_habilitadas=["pncp"],
        )
        q = FederatedSearchQuery.from_market_request(p)
        self.assertEqual(q.valor_base_referencia, 100.0)
        self.assertEqual(q.variacao_percentual_referencia, 10.0)
        self.assertEqual(q.variacao_sentido_referencia, "ambos")
        back = q.to_market_request()
        self.assertEqual(back.valor_base_referencia, 100.0)


class ApiEndpointRegressionTests(unittest.IsolatedAsyncioTestCase):
    async def test_price_sources_lists_pncp(self):
        import importlib
        import os

        # Garante app em modo researcher (testes de FEED_PLATFORM podem ter sujado o módulo).
        os.environ["SERVICE_MODE"] = "all"
        os.environ.pop("FEED_PLATFORM", None)
        import app.service_mode as sm
        import app.api as api_mod
        import app.main as main_mod

        importlib.reload(sm)
        importlib.reload(api_mod)
        importlib.reload(main_mod)

        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=main_mod.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/pncp-research/price-sources")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body.get("ok"))
        ids = [f.get("id") for f in body.get("fontes") or []]
        self.assertIn("pncp", ids)


if __name__ == "__main__":
    unittest.main()
