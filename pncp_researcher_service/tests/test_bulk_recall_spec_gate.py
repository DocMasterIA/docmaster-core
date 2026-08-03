"""Top-3 bulk (busca_lote): matcher de título PNCP + gates category/spec."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.service import _build_bulk_manual_recall_pool  # noqa: E402


class BulkRecallSpecGateTests(unittest.TestCase):
    def test_titulo_desconectado_nao_entra_no_pool_top3(self):
        """Gate genérico de título (tiers) + spec numérico — sem dicionário de produto."""
        termo = "MANILHA DE CONCRETO SIMPLES 200MM, COMPRIMENTO 1,00M."
        itens = [
            {
                "descricao_item": (
                    "Papel Embrulho tipo papel: papel manilha, apresentação: bobina, "
                    "largura: 150, comprimento: 100, cor: parda, aplicação: embalagem"
                ),
                "valor_unitario_homologado": 10.0,
                "origem": "base_local_itens",
                "search_tier": "flex",
            },
            {
                "descricao_item": "MANILHA DE CONCRETO SIMPLES 300MM, COMPRIMENTO 1,00M.",
                "valor_unitario_homologado": 20.0,
                "origem": "federated_compras_gov",
                "search_tier": "flex",
            },
            {
                "descricao_item": (
                    "MANILHA ACO CARBONO GALVANIZADO COMPRIMENTO UTIL 66 ABERTURA 22 RAIO 20"
                ),
                "valor_unitario_homologado": 30.0,
                "origem": "federated_tce_rs",
                "search_tier": "flex",
            },
            {
                "descricao_item": "MANILHA DE CONCRETO SIMPLES 200MM COMPRIMENTO 1,00M",
                "valor_unitario_homologado": 40.0,
                "origem": "base_local_itens",
                "search_tier": "strict",
            },
        ]
        pool, funil = _build_bulk_manual_recall_pool(
            itens,
            termo_busca=termo,
            termo_busca_raw=termo,
            faixa_min=None,
            faixa_max=None,
            min_ok=55,
        )
        descs = [str(x.get("descricao_item") or "") for x in pool]
        self.assertEqual(len(pool), 1, descs)
        self.assertIn("200MM", descs[0].upper())
        self.assertNotIn("papel", descs[0].lower())
        self.assertGreaterEqual(int(funil.get("eliminados_spec_categoria_recall") or 0), 3)

    def test_fio_nylon_rejeita_luva_no_pool(self):
        termo = "FIO NYLON N° 4.0 COR PRETA COM AGULHA 4 CM"
        itens = [
            {
                "descricao_item": (
                    "LUVA, de seguranca, antiestatico, cor cinza, tamanho M, "
                    "tricotada em fios de nylon ou poliamida"
                ),
                "valor_unitario_homologado": 5.0,
                "origem": "federated_tce_rs",
                "search_tier": "flex",
            },
            {
                "descricao_item": "FIO DE SUTURA NYLON N° 4.0 PRETO COM AGULHA 4 CM",
                "valor_unitario_homologado": 8.0,
                "origem": "federated_compras_gov",
                "search_tier": "core",
            },
        ]
        pool, funil = _build_bulk_manual_recall_pool(
            itens,
            termo_busca=termo,
            termo_busca_raw=termo,
            faixa_min=None,
            faixa_max=None,
            min_ok=55,
        )
        descs = [str(x.get("descricao_item") or "").upper() for x in pool]
        self.assertEqual(len(pool), 1, descs)
        self.assertTrue(descs[0].startswith("FIO"))
        self.assertGreaterEqual(int(funil.get("eliminados_spec_categoria_recall") or 0), 1)


if __name__ == "__main__":
    unittest.main()
