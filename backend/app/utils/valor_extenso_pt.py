"""
Conversão de valores monetários para texto por extenso (pt-BR).

Uso previsto: cotações PNCP, relatórios, TR/DFD e demais documentos.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re
from typing import Any, Optional, Union

Number = Union[int, float, str, Decimal]

_UNIDADES = (
    "zero",
    "um",
    "dois",
    "três",
    "quatro",
    "cinco",
    "seis",
    "sete",
    "oito",
    "nove",
    "dez",
    "onze",
    "doze",
    "treze",
    "catorze",
    "quinze",
    "dezesseis",
    "dezessete",
    "dezoito",
    "dezenove",
)

_DEZENAS = (
    "",
    "",
    "vinte",
    "trinta",
    "quarenta",
    "cinquenta",
    "sessenta",
    "setenta",
    "oitenta",
    "noventa",
)

_CENTENAS = (
    "",
    "cento",
    "duzentos",
    "trezentos",
    "quatrocentos",
    "quinhentos",
    "seiscentos",
    "setecentos",
    "oitocentos",
    "novecentos",
)

_ESCALAS = (
    (10**15, "quadrilhão", "quadrilhões"),
    (10**12, "trilhão", "trilhões"),
    (10**9, "bilhão", "bilhões"),
    (10**6, "milhão", "milhões"),
)


def parse_valor_monetario_br(value: Any) -> Optional[Decimal]:
    """Interpreta moeda BR (R$, milhar com ponto, decimal com vírgula). None se inválido."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (value != value or value in (float("inf"), float("-inf"))):
            return None
        return Decimal(str(value))

    raw = str(value).strip()
    if not raw:
        return None
    cleaned = re.sub(r"(?i)^\s*R\$\s*", "", raw).replace(" ", "").strip()
    if not cleaned:
        return None
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _extenso_0_999(n: int) -> str:
    if n == 0:
        return ""
    if n == 100:
        return "cem"
    if n < 20:
        return _UNIDADES[n]
    if n < 100:
        dezena, unidade = divmod(n, 10)
        if unidade == 0:
            return _DEZENAS[dezena]
        return f"{_DEZENAS[dezena]} e {_UNIDADES[unidade]}"
    centena, resto = divmod(n, 100)
    prefixo = _CENTENAS[centena]
    if resto == 0:
        return prefixo
    return f"{prefixo} e {_extenso_0_999(resto)}"


def _extenso_milhar(n: int) -> str:
    if n < 1000:
        return _extenso_0_999(n)
    mil, resto = divmod(n, 1000)
    esquerda = "mil" if mil == 1 else f"{_extenso_0_999(mil)} mil"
    if resto == 0:
        return esquerda
    if resto < 100:
        return f"{esquerda} e {_extenso_0_999(resto)}"
    return f"{esquerda} {_extenso_0_999(resto)}"


def _extenso_escala(n: int, divisor: int, singular: str, plural: str) -> str:
    if n < divisor:
        return _extenso_milhar(n)
    quociente, resto = divmod(n, divisor)
    if quociente == 1:
        esquerda = f"um {singular}"
    else:
        esquerda = f"{_extenso_0_999(quociente)} {plural}"
    if resto == 0:
        return esquerda
    direita = _extenso_milhar(resto)
    if resto < 1000:
        return f"{esquerda} e {direita}"
    return f"{esquerda} {direita}"


def inteiro_por_extenso(n: int) -> str:
    """Converte inteiro não negativo (0–10¹⁵) para extenso."""
    if n < 0:
        raise ValueError("inteiro_por_extenso aceita apenas valores >= 0")
    if n == 0:
        return "zero"

    valor = int(n)
    for divisor, singular, plural in _ESCALAS:
        if valor >= divisor:
            return _extenso_escala(valor, divisor, singular, plural)
    return _extenso_milhar(valor)


def valor_monetario_por_extenso(
    value: Number,
    *,
    moeda: str = "real",
    incluir_moeda: bool = True,
) -> str:
    """
    Converte valor monetário para extenso em português brasileiro.

    Ex.: 1234.56 → «mil duzentos e trinta e quatro reais e cinquenta e seis centavos»
    """
    parsed = parse_valor_monetario_br(value)
    if parsed is None:
        raise ValueError("valor monetário inválido")

    quantizado = parsed.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if quantizado < 0:
        raise ValueError("valor monetário não pode ser negativo")

    reais = int(quantizado)
    centavos = int((quantizado - Decimal(reais)) * 100)

    moeda = (moeda or "real").strip().lower()
    if moeda not in ("real", "reais"):
        raise ValueError("moeda suportada: real/reais")

    if reais == 0 and centavos == 0:
        return "zero reais" if incluir_moeda else "zero"

    partes: list[str] = []

    if reais > 0:
        texto_reais = inteiro_por_extenso(reais)
        if incluir_moeda:
            partes.append(f"{texto_reais} {'real' if reais == 1 else 'reais'}")
        else:
            partes.append(texto_reais)

    if centavos > 0:
        texto_centavos = inteiro_por_extenso(centavos)
        if incluir_moeda:
            frag = f"{texto_centavos} {'centavo' if centavos == 1 else 'centavos'}"
        else:
            frag = texto_centavos
        if partes:
            partes.append(f"e {frag}")
        else:
            partes.append(frag)

    return " ".join(partes)


def valor_monetario_extenso_payload(value: Number) -> dict[str, Any]:
    """Retorno padronizado para API e integrações futuras."""
    parsed = parse_valor_monetario_br(value)
    if parsed is None:
        raise ValueError("valor monetário inválido")
    quantizado = parsed.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if quantizado < 0:
        raise ValueError("valor monetário não pode ser negativo")

    reais = int(quantizado)
    centavos = int((quantizado - Decimal(reais)) * 100)
    return {
        "valor": float(quantizado),
        "valor_fmt": f"R$ {quantizado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "reais": reais,
        "centavos": centavos,
        "extenso": valor_monetario_por_extenso(quantizado),
    }
