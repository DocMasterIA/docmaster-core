"""Cálculo de faixa regional de preço (valor base + variação % + sentido)."""

from __future__ import annotations

from typing import Optional, Tuple

SENTIDOS_VALIDOS = frozenset({"ambos", "baixo", "cima"})


def normalize_variacao_sentido(sentido: Optional[str]) -> str:
    s = str(sentido or "ambos").strip().lower()
    return s if s in SENTIDOS_VALIDOS else "ambos"


def compute_faixa_regional(
    valor_base: float,
    variacao_pct: float,
    *,
    sentido: Optional[str] = None,
) -> Tuple[float, float]:
    """
    Retorna (min, max) inclusivos para preço unitário.
    - ambos: base ± pct%
    - baixo: [base*(1-pct/100), base]
    - cima:  [base, base*(1+pct/100)]
    """
    base = float(valor_base)
    pct = max(0.0, float(variacao_pct))
    fator = pct / 100.0
    sent = normalize_variacao_sentido(sentido)
    if sent == "baixo":
        return max(0.0, base * (1.0 - fator)), base
    if sent == "cima":
        return base, base * (1.0 + fator)
    margem = base * fator
    return max(0.0, base - margem), base + margem


def faixa_regional_ativa(valor_base: Optional[float], variacao_pct: Optional[float]) -> bool:
    if valor_base is None or variacao_pct is None:
        return False
    try:
        return float(valor_base) > 0.0 and float(variacao_pct) >= 0.0
    except (TypeError, ValueError):
        return False


def format_faixa_prompt_text(
    *,
    valor_base: float,
    variacao_pct: float,
    faixa_min: float,
    faixa_max: float,
    sentido: Optional[str] = None,
) -> str:
    sent = normalize_variacao_sentido(sentido)
    if sent == "baixo":
        tol = f"até {variacao_pct:.1f}% abaixo do valor base (sem preços acima do base)"
    elif sent == "cima":
        tol = f"até {variacao_pct:.1f}% acima do valor base (sem preços abaixo do base)"
    else:
        tol = f"tolerância de ±{variacao_pct:.1f}% sobre o valor base"
    return (
        "\n**Faixa regional de preço (obrigatória):** o item de referência tem valor base "
        f"R$ {valor_base:.2f} com {tol}.\n"
        f"Apenas candidatos cujo preço unitário estiver entre **R$ {faixa_min:.2f}** e "
        f"**R$ {faixa_max:.2f}** (inclusive) podem ser escolhidos.\n"
        "Candidatos fora dessa faixa **nunca** devem ser selecionados.\n"
    )
