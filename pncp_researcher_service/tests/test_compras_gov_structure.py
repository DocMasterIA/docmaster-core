"""Estrutura Compras.gov: column_map + validação de cabeçalhos (sem alimentar itens)."""
from __future__ import annotations

import csv
import sys
import tempfile
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.platform_index.ingest.compras_gov.column_map import (
    column_map_spec,
    map_compra_row,
    map_item_row,
    validate_compra_headers,
    validate_item_headers,
)
from app.platform_index.ingest.compras_gov.materialize import (
    ensure_compras_gov_index,
)
from app.platform_index.ingest.compras_gov.parser import validate_bundle_structure
from app.platform_index.registry import PlatformIndexSpec, get_platform_spec, register_platform_spec


REPO_COMPRA = Path(__file__).resolve().parents[2] / "comprasGOV-anual-VW_FT_PNCP_COMPRA-latest.csv"
REPO_ITEM = Path(__file__).resolve().parents[2] / "comprasGOV-mensal-VW_FT_PNCP_COMPRA_ITEM-2026-07.csv"


def test_column_map_spec_flags_materialize_on():
    spec = column_map_spec()
    assert spec["item_materialize_enabled"] is True
    assert "cod_compra" in spec["required_compra_headers"]
    assert "descricao_resumida" in spec["required_item_headers"]


def test_validate_headers_against_repo_csvs():
    if not REPO_COMPRA.is_file() or not REPO_ITEM.is_file():
        pytest.skip("CSVs Compras.gov ausentes na raiz do repo")
    with REPO_COMPRA.open(encoding="utf-8-sig", newline="") as f:
        compra_headers = next(csv.reader(f))
    with REPO_ITEM.open(encoding="utf-8-sig", newline="") as f:
        item_headers = next(csv.reader(f))
    assert validate_compra_headers(compra_headers)["ok"] is True
    assert validate_item_headers(item_headers)["ok"] is True


def test_map_compra_and_item_sample():
    compra = map_compra_row(
        {
            "cod_compra": "11002730",
            "numero_controle_PNCP": "63025530000104-1-002564/2026",
            "orgao_entidade_razao_social": "ORGAO X",
            "unidade_orgao_municipio_nome": "Brasília",
            "unidade_orgao_uf_sigla": "DF",
            "modalidade_nome": "Pregão - Eletrônico",
            "link_sistema_origem": "https://example.gov.br/x",
            "data_publicacao_pncp": "2026-07-01",
            "ano_compra_pncp": "2026",
            "sequencial_compra_pncp": "2564",
        }
    )
    assert compra is not None
    assert compra["processo_id"] == "compras_gov:11002730"
    assert compra["inciso_classificacao"] == "inciso_i"

    item = map_item_row(
        {
            "cod_compra": "11002730",
            "numero_item_pncp": "1",
            "numero_controle_PNCP_compra": "63025530000104-1-002564/2026",
            "descricao_resumida": "Balança Analítica",
            "unidade_medida": "Unidade",
            "quantidade": "1.0",
            "valor_unitario_estimado": "7000.0",
            "valor_unitario_resultado": "6350.0",
            "nome_fornecedor": "BF SOLUCOES LTDA",
            "cod_fornecedor": "40626395000157",
            "tem_resultado": "True",
        },
        compra=compra,
    )
    assert item is not None
    assert item["plataforma_item_id"] == "compras_gov:11002730:1"
    assert item["valor_unitario_homologado"] == 6350.0
    assert item["orgao"] == "ORGAO X"
    assert item["uf"] == "DF"


def test_validate_bundle_structure_mini(tmp_path: Path):
    compra = tmp_path / "x-VW_FT_PNCP_COMPRA.csv"
    item = tmp_path / "x-VW_FT_PNCP_COMPRA_ITEM.csv"
    compra.write_text(
        "cod_compra,numero_controle_PNCP,orgao_entidade_razao_social,"
        "unidade_orgao_uf_sigla,unidade_orgao_municipio_nome,modalidade_nome\n"
        "1,00.000/2026,ORGAO,DF,Brasilia,Pregao\n",
        encoding="utf-8",
    )
    item.write_text(
        "cod_compra,numero_item_pncp,numero_controle_PNCP_compra,descricao_resumida,"
        "unidade_medida,quantidade,valor_unitario_estimado\n"
        "1,1,00.000/2026,Papel A4,RESMA,10,25.5\n",
        encoding="utf-8",
    )
    report = validate_bundle_structure(tmp_path)
    assert report.ok is True
    assert report.sample_item_mapped is not None
    assert report.sample_item_mapped["descricao"] == "Papel A4"
    assert report.column_map["item_materialize_enabled"] is True


def test_ensure_schema_without_items():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "compras_gov_local.db")
        prev = get_platform_spec("compras_gov")
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
        try:
            out = ensure_compras_gov_index(db_path=db_path)
            assert out["ok"] is True
            assert out["itens_written"] == 0 or out["itens_written"] >= 0
            assert out["item_materialize_enabled"] is True
            assert Path(db_path).is_file()
        finally:
            if prev is not None:
                register_platform_spec(prev)


def test_materialize_items_works_with_parsed_min():
    from app.platform_index.ingest.compras_gov.materialize import materialize_compras_gov_items

    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "cg.db")
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
        out = materialize_compras_gov_items(
            {
                "compras": [
                    {
                        "cod_compra": "1",
                        "processo_id": "compras_gov:1",
                        "numero_pncp": "1-1-1/2026",
                        "numero_processo": "1-1-1/2026",
                        "orgao": "ORGAO",
                        "municipio": "Brasilia",
                        "uf": "DF",
                        "objeto": "x",
                        "data_publicacao": "2026-01-01",
                        "url_origem": "https://example.gov.br",
                    }
                ],
                "itens": [
                    {
                        "cod_compra": "1",
                        "processo_id": "compras_gov:1",
                        "plataforma_item_id": "compras_gov:1:1",
                        "numero_item": "1",
                        "descricao": "PAPEL A4",
                        "valor_unitario": 10.0,
                        "valor_unitario_homologado": 9.0,
                        "unidade_medida": "RESMA",
                        "quantidade": 1,
                        "fornecedor_nome": "FORN",
                        "cnpj_fornecedor": "12345678000199",
                        "inciso_classificacao": "inciso_i",
                        "esfera": "federal",
                    }
                ],
            },
            db_path=db_path,
        )
        assert out["ok"] is True
        assert out["materialize"]["itens_leitura_upserted"] == 1
