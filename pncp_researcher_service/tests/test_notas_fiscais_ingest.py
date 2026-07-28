"""Ingest Notas Fiscais: column_map, parse, materialize, sample."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.platform_index.ingest.notas_fiscais.column_map import (
    map_item_row,
    map_nota_row,
    normalize_unidade,
    validate_item_headers,
)
from app.platform_index.ingest.notas_fiscais.parser import parse_notas_fiscais_directory
from app.platform_index.registry import PlatformIndexSpec, register_platform_spec
from app.platform_index.schema import ensure_platform_index, platform_index_stats


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "notas_fiscais"


def test_normalize_unidade_unidad():
    assert normalize_unidade("UNIDAD") == "UN"


def test_validate_real_headers_from_fixture():
    import csv

    item = FIXTURES / "fixture-NotaFiscalItem.csv"
    with item.open(encoding="utf-8", newline="") as f:
        headers = next(csv.reader(f, delimiter=";"))
    assert validate_item_headers(headers)["ok"] is True


def test_map_item_joins_orgao_from_nota():
    nota = map_nota_row(
        {
            "CHAVE DE ACESSO": "ABC",
            "EVENTO MAIS RECENTE": "Autorização de Uso",
            "DATA EMISSÃO": "01/01/2026 00:00:00",
            "ÓRGÃO DESTINATÁRIO": "Universidade Federal",
            "UF DESTINATÁRIO": "ES",
            "NÚMERO": "658",
            "RAZÃO SOCIAL EMITENTE": "FORN LTDA",
            "CPF/CNPJ Emitente": "30848671000178",
        }
    )
    assert nota is not None
    assert nota["evento_ok"] is True

    item = map_item_row(
        {
            "CHAVE DE ACESSO": "ABC",
            "NÚMERO PRODUTO": "1",
            "DESCRIÇÃO DO PRODUTO/SERVIÇO": "EXTENSAO ELETRICA",
            "VALOR UNITÁRIO": "40,00",
            "QUANTIDADE": "7,00",
            "UNIDADE": "UNIDAD",
            "ÓRGÃO DESTINATÁRIO": "Sem informação",
        },
        nota=nota,
    )
    assert item is not None
    assert item["orgao"] == "Universidade Federal"
    assert item["uf"] == "ES"
    assert item["valor_unitario"] == 40.0
    assert item["valor_unitario_homologado"] == 40.0
    assert item["unidade_medida"] == "UN"
    assert item["inciso_classificacao"] == "inciso_v"


def test_map_rejects_sem_informacao_evento():
    nota = map_nota_row(
        {
            "CHAVE DE ACESSO": "XYZ",
            "EVENTO MAIS RECENTE": "Sem informação",
            "DATA EMISSÃO": "01/01/2026",
            "NÚMERO": "1",
        }
    )
    assert nota is not None
    assert nota["evento_ok"] is False
    item = map_item_row(
        {
            "CHAVE DE ACESSO": "XYZ",
            "NÚMERO PRODUTO": "1",
            "DESCRIÇÃO DO PRODUTO/SERVIÇO": "X",
            "VALOR UNITÁRIO": "10,00",
            "QUANTIDADE": "1",
            "UNIDADE": "UN",
        },
        nota=nota,
    )
    assert item is None


def test_parse_and_materialize_fixtures(tmp_path):
    from app.platform_index.ingest.notas_fiscais.materialize import (
        materialize_notas_fiscais_parsed,
    )

    db_path = str(tmp_path / "nf.db")
    ensure_platform_index("notas_fiscais", db_path=db_path)
    register_platform_spec(
        PlatformIndexSpec(
            id="notas_fiscais",
            label="Notas Fiscais",
            db_path=db_path,
            schema_kind="platform_index",
            inciso_default="inciso_v",
            esfera_default="federal",
            enabled=True,
            search_ready=False,
            index_writer="feed",
        )
    )
    parsed = parse_notas_fiscais_directory(FIXTURES)
    assert parsed["stats"]["notas"] == 1
    assert parsed["stats"]["itens"] == 2
    mat = materialize_notas_fiscais_parsed(parsed, db_path=db_path)
    assert mat["ok"] is True
    assert mat["materialize"]["itens_leitura_upserted"] == 2
    stats = platform_index_stats(db_path)
    assert stats["itens_leitura"] == 2
    assert stats["fts_rows"] == 2
    assert stats["search_ready"] is True


@pytest.mark.skipif(
    not (
        Path(__file__).resolve().parents[1]
        / "data"
        / "notas_fiscais"
        / "raw"
        / "2026"
        / "202601_NFe"
    ).is_dir(),
    reason="raw 202601_NFe ausente",
)
def test_parse_real_202601_smoke(tmp_path):
    raw = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "notas_fiscais"
        / "raw"
        / "2026"
        / "202601_NFe"
    )
    parsed = parse_notas_fiscais_directory(raw, max_rows=50)
    assert parsed["stats"]["itens"] == 50
    assert parsed["stats"]["notas"] > 0
    sample = parsed["itens"][0]
    assert sample["valor_unitario_homologado"] == sample["valor_unitario"]
    assert sample["inciso_classificacao"] == "inciso_v"
