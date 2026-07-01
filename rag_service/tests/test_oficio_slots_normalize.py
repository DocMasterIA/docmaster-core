"""Normalização de slots do Ofício."""

from __future__ import annotations

from app.deprecated_cargo_slots import strip_deprecated_cargo_override
from app.oficio_slots import normalize_oficio_slots_override


def test_normalize_maps_preset_keys_to_oficio_slots():
    raw = {
        "solicitacao_destinatario_tratamento_cargo": "Senhor",
        "solicitacao_destinatario_cargo": "Secretário Municipal",
        "solicitacao_destinatario_nome": "Maria Silva",
    }
    out = normalize_oficio_slots_override(raw)
    assert out["senhor_senhora_genero"] == "Senhor"
    assert out["sol_oficio_destinatario_cargo"] == "Secretário Municipal"
    assert out["sol_oficio_destinatario_nome"] == "Maria Silva"


def test_strip_deprecated_keeps_oficio_destinatario_slots():
    raw = {
        "senhor_senhora_genero": "Senhora",
        "sol_oficio_destinatario_cargo": "Diretora",
        "sol_oficio_responsavel_cargo": "Fantasma",
    }
    out = strip_deprecated_cargo_override(raw)
    assert out["senhor_senhora_genero"] == "Senhora"
    assert out["sol_oficio_destinatario_cargo"] == "Diretora"
    assert "sol_oficio_responsavel_cargo" not in out
