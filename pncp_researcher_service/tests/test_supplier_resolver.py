from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

# app/ como pacote
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.fornecedor_cache import (  # noqa: E402
    cache_get,
    cache_is_fresh,
    cache_upsert,
    cache_upsert_from_brasilapi_payload,
    ensure_fornecedor_cache_table,
)
from app.supplier_resolver import (  # noqa: E402
    compra_elegivel,
    extract_homologated_pricing,
    extract_supplier_cnpj_only,
    item_elegivel,
    item_homologado_para_busca,
    item_row_needs_resultado_fetch,
    merge_with_cadastro,
    normalize_cnpj,
    resolve_from_contratos_payload,
    resolve_from_resultados_payload,
    resolve_item_supplier_offline,
    resolve_from_item_catalog_row,
)


def _fixture(name: str):
    path = Path(__file__).parent / "fixtures" / name
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class TestSupplierResolver(unittest.TestCase):
    def test_normalize_cnpj(self):
        self.assertEqual(normalize_cnpj("12345678000195"), "12.345.678/0001-95")

    def test_resultado_item_homologado(self):
        payload = _fixture("resultado_item_homologado.json")
        res = resolve_from_resultados_payload(
            payload,
            numero_item="3",
            situacao_compra="Homologada",
            fonte_prefix="pncp_resultado_item",
        )
        self.assertEqual(res.cnpj_fornecedor, "12.345.678/0001-95")
        self.assertEqual(res.fornecedor, "FORNECEDORA EXEMPLO LTDA")
        self.assertTrue(res.fornecedor_elegivel)
        self.assertEqual(res.fornecedor_fonte, "pncp_resultado_item")

    def test_fonte_sufixada_nao_duplica_item(self):
        from app.supplier_resolver import _fonte_sufixada

        self.assertEqual(_fonte_sufixada("pncp_resultado_item", "item"), "pncp_resultado_item")
        self.assertEqual(_fonte_sufixada("pncp_resultado_compra", "compra"), "pncp_resultado_compra")
        self.assertEqual(_fonte_sufixada("pncp_resultado", "item"), "pncp_resultado_item")

    def test_nome_fornecedor_rejeita_metadado_pncp(self):
        from app.supplier_resolver import nome_fornecedor_e_util

        self.assertFalse(nome_fornecedor_e_util("pncp_resultado_item_item"))
        self.assertFalse(nome_fornecedor_e_util("pncp_resultado_item"))
        self.assertTrue(nome_fornecedor_e_util("FORNECEDORA EXEMPLO LTDA"))

    def test_resultado_compra_match_numero_item(self):
        payload = _fixture("resultado_compra_lista.json")
        res = resolve_from_resultados_payload(
            payload,
            numero_item="2",
            situacao_compra="Homologada",
            fonte_prefix="pncp_resultado_compra",
        )
        self.assertEqual(res.cnpj_fornecedor, "12.345.678/0001-95")
        self.assertEqual(res.fornecedor, "FORNECEDORA EXEMPLO LTDA")

    def test_item_catalog_inline(self):
        row = _fixture("item_catalog_inline.json")
        res = resolve_from_item_catalog_row(row, situacao_compra="Homologada")
        self.assertEqual(res.cnpj_fornecedor, "11.222.333/0001-81")
        self.assertEqual(res.fornecedor, "PAPELARIA CENTRAL LTDA")
        self.assertEqual(res.fornecedor_fonte, "pncp_item_inline")

    def test_resolve_offline_priority_item_resultados(self):
        item_row = _fixture("item_catalog_inline.json")
        resultado_item = _fixture("resultado_item_homologado.json")
        res = resolve_item_supplier_offline(
            item_row=item_row,
            resultados_item_payload=resultado_item,
            situacao_compra="Homologada",
        )
        self.assertEqual(res.cnpj_fornecedor, "12.345.678/0001-95")
        self.assertEqual(res.fornecedor, "FORNECEDORA EXEMPLO LTDA")

    def test_merge_brasilapi_nome(self):
        base = resolve_from_resultados_payload(
            _fixture("resultado_item_homologado.json"),
            situacao_compra="Homologada",
        )
        base.fornecedor = ""
        merged = merge_with_cadastro(
            base,
            nome="FORNECEDORA EXEMPLO LTDA",
            cadastro={"cnpj": "12.345.678/0001-95", "municipio": "Brasília"},
            fonte_nome="brasilapi",
        )
        self.assertEqual(merged.fornecedor, "FORNECEDORA EXEMPLO LTDA")
        self.assertIn("brasilapi", merged.fornecedor_fonte)
        self.assertEqual(merged.fornecedor_cadastro.get("municipio"), "Brasília")

    def test_elegibilidade(self):
        self.assertTrue(compra_elegivel("Homologada"))
        self.assertFalse(compra_elegivel("Revogada"))
        self.assertTrue(item_elegivel({"temResultado": True}, situacao_compra="Em andamento"))

    def test_homologado_para_busca_estrito(self):
        self.assertTrue(
            item_homologado_para_busca(
                {"situacaoCompraItemNome": "Homologado"},
                situacao_compra="Em andamento",
            )
        )
        self.assertFalse(
            item_homologado_para_busca(
                {"temResultado": True, "situacaoCompraItemNome": "Em andamento"},
            )
        )
        self.assertFalse(item_homologado_para_busca({"situacaoCompraItemNome": "Revogado"}))

    def test_extract_homologated_pricing_from_resultado(self):
        row = {
            "valorUnitarioHomologado": 21.48,
            "valorTotalHomologado": 170121.6,
            "quantidadeHomologada": 7920,
        }
        out = extract_homologated_pricing(row)
        self.assertEqual(out["valor_unitario_homologado"], 21.48)
        self.assertEqual(out["valor_total_homologado"], 170121.6)
        self.assertEqual(out["quantidade_homologada"], 7920.0)

    def test_item_row_needs_resultado_fetch(self):
        self.assertTrue(item_row_needs_resultado_fetch({"temResultado": True}))
        self.assertFalse(
            item_row_needs_resultado_fetch({"valorUnitarioHomologado": 10.0, "temResultado": True})
        )

    def test_extract_cnpj_ignores_orgao_path(self):
        payload = {
            "orgaoEntidade": {"cnpj": "00000000000191", "razaoSocial": "PREFEITURA X"},
            "niFornecedor": "12345678000195",
        }
        self.assertEqual(extract_supplier_cnpj_only(payload), "12.345.678/0001-95")

    def test_contratos_contratacao_match_numero_item(self):
        payload = _fixture("contrato_contratacao_lista.json")
        res = resolve_from_contratos_payload(payload, numero_item="8")
        self.assertEqual(res.cnpj_fornecedor, "98.765.432/0001-10")
        self.assertIn("CONTRATO", res.fornecedor)
        self.assertIn("contrato", res.fornecedor_fonte)

    def test_offline_contratos_layer(self):
        payload = _fixture("contrato_contratacao_lista.json")
        res = resolve_item_supplier_offline(
            contratos_payload=payload,
            numero_item="8",
        )
        self.assertTrue(res.cnpj_fornecedor)


class TestFornecedorCache(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.conn = sqlite3.connect(self.tmp.name)
        self.conn.row_factory = sqlite3.Row
        ensure_fornecedor_cache_table(self.conn)
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        os.unlink(self.tmp.name)

    def test_cache_upsert_and_get(self):
        cache_upsert(
            self.conn,
            "12345678000195",
            razao_social="FORNECEDORA EXEMPLO LTDA",
            nome_fantasia="EXEMPLO",
            cadastro={"uf": "DF"},
        )
        self.conn.commit()
        hit = cache_get(self.conn, "12.345.678/0001-95")
        self.assertIsNotNone(hit)
        assert hit is not None
        self.assertEqual(hit["fornecedor"], "FORNECEDORA EXEMPLO LTDA")
        self.assertEqual(hit["fornecedor_cadastro"].get("uf"), "DF")

    def test_cache_from_brasilapi_payload(self):
        payload = {
            "razao_social": "ACME LTDA",
            "nome_fantasia": "ACME",
            "uf": "SP",
            "municipio": "São Paulo",
        }
        nome, cad = cache_upsert_from_brasilapi_payload(self.conn, "11222333000181", payload)
        self.conn.commit()
        self.assertEqual(nome, "ACME LTDA")
        self.assertEqual(cad.get("uf"), "SP")
        hit = cache_get(self.conn, "11222333000181")
        self.assertIsNotNone(hit)

    def test_cache_stale(self):
        old = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat().replace("+00:00", "Z")
        self.assertFalse(cache_is_fresh(old, max_age_days=90))
        fresh = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        self.assertTrue(cache_is_fresh(fresh, max_age_days=90))


class TestLocalSupplierFromCatalog(unittest.TestCase):
    def test_supplier_from_item_catalog_fixture(self):
        from app.supplier_resolver import resolve_from_item_catalog_row, resolution_to_api_dict

        row = _fixture("item_catalog_inline.json")
        res = resolve_from_item_catalog_row(row, situacao_compra="Homologada")
        out = resolution_to_api_dict(res)
        self.assertEqual(out["cnpj_fornecedor"], "11.222.333/0001-81")
        self.assertEqual(out["fornecedor"], "PAPELARIA CENTRAL LTDA")


class TestLocalIndexMigration(unittest.TestCase):
    def test_migrate_pncp_itens_supplier_columns(self):
        """Migração Fase A sem importar local_index (evita dependência httpx no host)."""
        from app.fornecedor_cache import ensure_fornecedor_cache_table

        db_path = tempfile.mktemp(suffix=".db")
        with sqlite3.connect(db_path) as c:
            c.execute(
                """
                CREATE TABLE pncp_itens (
                    id INTEGER PRIMARY KEY,
                    numero_pncp TEXT,
                    item_fingerprint TEXT
                )
                """
            )
            for name, col_type in [
                ("cnpj_fornecedor", "TEXT"),
                ("fornecedor", "TEXT"),
                ("fornecedor_fonte", "TEXT"),
                ("situacao_item", "TEXT"),
                ("situacao_compra", "TEXT"),
                ("fornecedor_elegivel", "INTEGER NOT NULL DEFAULT 0"),
                ("fornecedor_resolvido_at", "TEXT"),
            ]:
                cols = {row[1] for row in c.execute("PRAGMA table_info(pncp_itens)")}
                if name not in cols:
                    c.execute(f"ALTER TABLE pncp_itens ADD COLUMN {name} {col_type}")
            ensure_fornecedor_cache_table(c)
            c.commit()
            cols = {row[1] for row in c.execute("PRAGMA table_info(pncp_itens)")}
            cache_tables = {
                row[0]
                for row in c.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='pncp_fornecedor_cache'"
                )
            }
        self.assertIn("cnpj_fornecedor", cols)
        self.assertIn("fornecedor_elegivel", cols)
        self.assertTrue(cache_tables)
        os.unlink(db_path)


if __name__ == "__main__":
    unittest.main()
