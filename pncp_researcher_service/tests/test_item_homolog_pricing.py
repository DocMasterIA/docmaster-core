import json
import os
import sqlite3
import tempfile

import pytest

from pncp_researcher_service.app import local_index


@pytest.fixture()
def item_db(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setattr(local_index, "PNCP_LOCAL_DB_PATH", path)
    local_index.ensure_local_index()
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


def _fixture(name: str) -> dict:
    base = os.path.join(os.path.dirname(__file__), "fixtures", name)
    with open(base, encoding="utf-8") as f:
        return json.load(f)


def test_upsert_prefers_homologated_pricing(item_db):
    raw = {
        "numeroControlePNCP": "23066640000108-1-000039/2025",
        "anoCompra": 2025,
        "sequencialCompra": 39,
        "orgaoEntidade": {"razaoSocial": "ORGAO TESTE"},
        "unidadeOrgao": {"municipioNome": "Cidade", "ufSigla": "SP"},
        "modalidadeNome": "Pregão",
        "situacaoCompraNome": "Homologado",
    }
    catalog = {
        "numeroItem": 1,
        "descricao": "Consultoria e Assessoria - Recursos Humanos",
        "materialOuServicoNome": "Serviço",
        "quantidade": 1.0,
        "unidadeMedida": "UNIDADE",
        "valorUnitarioEstimado": 157208.73,
        "valorTotal": 157208.73,
        "temResultado": True,
        "situacaoCompraItemNome": "Homologado",
    }
    resultado = _fixture("resultado_item_pricing.json")

    n = local_index.upsert_contract_items(
        raw,
        [catalog],
        resultados_by_item={"1": resultado},
    )
    assert n == 1

    with local_index._conn() as c:
        row = c.execute(
            """
            SELECT valor_unitario, valor_total, quantidade,
                   valor_unitario_estimado, valor_total_estimado,
                   valor_unitario_homologado, valor_total_homologado, quantidade_homologada,
                   cnpj_fornecedor, fornecedor, resultado_resolvido_at
            FROM pncp_itens WHERE numero_pncp = ?
            """,
            (raw["numeroControlePNCP"],),
        ).fetchone()

    assert row["valor_unitario_estimado"] == pytest.approx(157208.73)
    assert row["valor_unitario_homologado"] == pytest.approx(21.48)
    assert row["valor_total_homologado"] == pytest.approx(170121.6)
    assert row["quantidade_homologada"] == pytest.approx(7920.0)
    assert row["valor_unitario"] == pytest.approx(21.48)
    assert row["valor_total"] == pytest.approx(170121.6)
    assert row["quantidade"] == pytest.approx(7920.0)
    assert row["cnpj_fornecedor"] == "01.831.685/0001-80"
    assert "COOPERATIVA" in row["fornecedor"]
    assert row["resultado_resolvido_at"]


def test_apply_resultados_to_stored_items_without_refetch(item_db):
    raw = {
        "numeroControlePNCP": "PNCP-RES-ONLY",
        "anoCompra": 2025,
        "sequencialCompra": 9,
        "orgaoEntidade": {},
        "unidadeOrgao": {},
        "situacaoCompraNome": "Homologado",
    }
    catalog = {
        "numeroItem": 3,
        "descricao": "Serviço X",
        "quantidade": 1.0,
        "valorUnitarioEstimado": 999.0,
        "valorTotal": 999.0,
        "temResultado": True,
        "situacaoCompraItemNome": "Homologado",
    }
    local_index.upsert_contract_items(raw, [catalog])
    resultado = _fixture("resultado_item_pricing.json")
    resultado["numeroItem"] = 3

    n = local_index.apply_resultados_to_stored_items(
        raw["numeroControlePNCP"],
        {"3": resultado},
    )
    assert n == 1

    with local_index._conn() as c:
        row = c.execute(
            """
            SELECT valor_unitario, valor_unitario_estimado, valor_unitario_homologado, resultado_resolvido_at
            FROM pncp_itens WHERE numero_pncp = ?
            """,
            (raw["numeroControlePNCP"],),
        ).fetchone()

    assert row["valor_unitario_estimado"] == pytest.approx(999.0)
    assert row["valor_unitario_homologado"] == pytest.approx(21.48)
    assert row["valor_unitario"] == pytest.approx(21.48)
    assert row["resultado_resolvido_at"]


def test_upsert_updates_existing_row_by_numero_item(item_db):
    raw = {
        "numeroControlePNCP": "PNCP-UPD-1",
        "anoCompra": 2025,
        "sequencialCompra": 1,
        "orgaoEntidade": {},
        "unidadeOrgao": {},
    }
    catalog = {
        "numeroItem": 2,
        "descricao": "Caneta",
        "quantidade": 10,
        "valorUnitarioEstimado": 5.0,
        "valorTotal": 50.0,
    }
    local_index.upsert_contract_items(raw, [catalog])

    local_index.upsert_contract_items(
        raw,
        [catalog],
        resultados_by_item={
            "2": {
                "numeroItem": 2,
                "valorUnitarioHomologado": 3.5,
                "valorTotalHomologado": 35.0,
                "quantidadeHomologada": 10.0,
            }
        },
    )

    with local_index._conn() as c:
        count = c.execute(
            "SELECT COUNT(*) AS n FROM pncp_itens WHERE numero_pncp = ?",
            ("PNCP-UPD-1",),
        ).fetchone()["n"]
        row = c.execute(
            "SELECT valor_unitario, valor_unitario_homologado FROM pncp_itens WHERE numero_pncp = ?",
            ("PNCP-UPD-1",),
        ).fetchone()

    assert count == 1
    assert row["valor_unitario"] == pytest.approx(3.5)
    assert row["valor_unitario_homologado"] == pytest.approx(3.5)
