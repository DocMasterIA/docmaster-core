"""
Camada única de limpeza / normalização de texto para busca PNCP (local + inteligente).

Objetivo:
- reduzir ruído de digitação (espaços unicode, rótulos nº/nr, pontuação);
- uniformizar grafia (minúsculas, sem acentos);
- aproximar equivalências numéricas comuns em PT (extenso ↔ dígitos) sem depender de LLM.

Limitações intencionais:
- não é um parser completo de português (evita falsos positivos complexos);
- "um/uma" só entram em contextos claros (ex.: "um mil", "cento e um", após "e").
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

# Espaços unicode frequentes em PDFs / planilhas
_SPACE_CHARS_RE = re.compile(r"[\u00a0\u1680\u2000-\u200b\u202f\u205f\u3000]+")

# nº, n°, nr., num., nro.
_NUM_LABEL_RE = re.compile(
    r"\b(?:n|nr|num|nro|n\.?ro)\s*[º°]\s*|\b(?:num(?:ero)?|nro)\b\.?\s*",
    flags=re.IGNORECASE,
)

_UNITS: dict[str, int] = {
    "zero": 0,
    "um": 1,
    "uma": 1,
    "dois": 2,
    "duas": 2,
    "tres": 3,
    "quatro": 4,
    "cinco": 5,
    "seis": 6,
    "sete": 7,
    "oito": 8,
    "nove": 9,
}

_TEENS: dict[str, int] = {
    "dez": 10,
    "onze": 11,
    "doze": 12,
    "treze": 13,
    "quatorze": 14,
    "catorze": 14,
    "quinze": 15,
    "dezesseis": 16,
    "dezasseis": 16,
    "dezessete": 17,
    "dezassete": 17,
    "dezoito": 18,
    "dezenove": 19,
    "dezanove": 19,
}

_TENS: dict[str, int] = {
    "vinte": 20,
    "trinta": 30,
    "quarenta": 40,
    "cinquenta": 50,
    "sessenta": 60,
    "setenta": 70,
    "oitenta": 80,
    "noventa": 90,
}

_HUNDREDS: dict[str, int] = {
    "cem": 100,
    "cento": 100,
    "duzentos": 200,
    "trezentos": 300,
    "quatrocentos": 400,
    "quinhentos": 500,
    "seiscentos": 600,
    "setecentos": 700,
    "oitocentos": 800,
    "novecentos": 900,
}


def _fold_accents_lower(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", s) if unicodedata.category(ch) != "Mn")


def _alnum_space(s: str) -> str:
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def pre_clean_raw(text: str) -> str:
    s = (text or "").strip()
    if not s:
        return ""
    s = _SPACE_CHARS_RE.sub(" ", s)
    s = _NUM_LABEL_RE.sub(" ", s)
    return s.strip()


def _read_unit(tokens: List[str], i: int) -> Tuple[Optional[int], int]:
    if i >= len(tokens):
        return None, i
    w = tokens[i]
    if w in _UNITS:
        return _UNITS[w], i + 1
    if w in _TEENS:
        return _TEENS[w], i + 1
    return None, i


def _read_tens_block(tokens: List[str], i: int) -> Tuple[Optional[int], int]:
    """Lê 20-99 como 'vinte', 'vinte e tres'."""
    if i >= len(tokens):
        return None, i
    w = tokens[i]
    if w not in _TENS:
        return None, i
    base = _TENS[w]
    j = i + 1
    if j < len(tokens) and tokens[j] == "e":
        j += 1
        u, j2 = _read_unit(tokens, j)
        if u is None or u > 9:
            return base, j  # 'e' sem unidade válida: mantém só a dezena
        return base + u, j2
    return base, j


def _read_1_999(tokens: List[str], i: int) -> Tuple[Optional[int], int]:
    """
    Lê 1..999 em extenso (ordem típica: centenas + dezenas/unidades).
    Retorna None se não reconhecer nada a partir de i.
    """
    if i >= len(tokens):
        return None, i

    total = 0
    j = i

    if tokens[j] in _HUNDREDS:
        total += _HUNDREDS[tokens[j]]
        j += 1
        if j < len(tokens) and tokens[j] == "e":
            j += 1
        # resto < 100
        v2, j2 = _read_tens_block(tokens, j)
        if v2 is not None:
            total += v2
            j = j2
        else:
            u, j2 = _read_unit(tokens, j)
            if u is not None and u <= 9:
                total += u
                j = j2
        return total if total > 0 else None, j

    v, j2 = _read_tens_block(tokens, j)
    if v is not None:
        return v, j2

    v, j2 = _read_unit(tokens, j)
    if v is not None:
        return v, j2

    return None, i


def _expand_written_numbers_tokens(tokens: List[str]) -> List[str]:
    """Transforma sequências numéricas por extenso em tokens dígitos."""
    out: List[str] = []
    i = 0
    n = len(tokens)
    while i < n:
        # "mil" sozinho -> 1000
        if tokens[i] == "mil":
            out.append("1000")
            i += 1
            continue

        v, j = _read_1_999(tokens, i)
        if v is not None and j < n and tokens[j] == "mil":
            out.append(str(v * 1000))
            i = j + 1
            continue

        if v is not None:
            out.append(str(v))
            i = j
            continue

        out.append(tokens[i])
        i += 1

    return out


def normalize_for_search(text: str) -> str:
    """
    Pipeline único: pré-limpeza leve + fold acentos + alfanumérico + expansão numérica PT.
    """
    s = pre_clean_raw(text)
    if not s:
        return ""
    s = s.lower()
    s = _fold_accents_lower(s)
    s = _alnum_space(s)
    if not s:
        return ""
    toks = [t for t in s.split(" ") if t]
    toks2 = _expand_written_numbers_tokens(toks)
    return " ".join(toks2).strip()


def preprocess_cotacao_search_term(text: str) -> str:
    """
    Normaliza descrições longas de cotação antes da tokenização:
    - compacta dimensões (13 X 4,5 → 13x4.5);
    - extrai calibre (26 G½ → 26g);
    - remove embalagem genérica (CX C/100 UNIDADES).
    """
    s = (text or "").strip()
    if not s:
        return ""
    s = re.sub(r"\s+", " ", s)
    s = re.sub(
        r"\b(?:cx|cxa|caixa)\s*(?:c/?\s*)?\d+\s*(?:unidades?|unids?|und\.?)\b",
        " ",
        s,
        flags=re.IGNORECASE,
    )
    s = re.sub(r"\bc/\s*\d+\s*(?:unidades?|unids?|und\.?)\b", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"\(\s*(\d+)\s*g[^)]*\)", r" \1g ", s, flags=re.IGNORECASE)
    s = re.sub(r"\b(\d+)\s*g\s*½\b", r"\1g", s, flags=re.IGNORECASE)
    s = re.sub(r"\b(\d+)\s*g\b", r"\1g", s, flags=re.IGNORECASE)
    s = re.sub(
        r"(\d+)\s*[xX×]\s*(\d+[,.]?\d*)",
        lambda m: f"{m.group(1)}x{m.group(2).replace(',', '').replace('.', '')}",
        s,
    )
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _truncate_at_word_boundary(text: str, max_len: int) -> str:
    if max_len <= 0 or len(text) <= max_len:
        return text
    cut = text[:max_len]
    sp = cut.rfind(" ")
    if sp > int(max_len * 0.55):
        cut = cut[:sp]
    cut = cut.rstrip(" ,.;-|/:")
    if not cut:
        return text[:max_len].rstrip()
    return f"{cut}…"


def clean_item_description_for_display(
    text: str,
    *,
    max_primary: int = 280,
    max_total: int = 420,
) -> str:
    """
    Reduz descrições PNCP muito longas para exibição (listagens / resultados).

    Heurística típica do PNCP: vários trechos concatenados com " - " (objeto + especificações).
    Mantém o primeiro bloco significativo; se for curto demais, une os dois primeiros.
    """
    s = (text or "").strip()
    if not s:
        return ""
    s = re.sub(r"[\r\n\t]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) <= max_primary:
        return s

    parts = [p.strip() for p in re.split(r"\s*-\s*", s) if p.strip()]
    if len(parts) >= 2:
        head = parts[0]
        if len(head) >= 28:
            out = head
        else:
            out = " - ".join(parts[:2]).strip()
        if len(out) > max_total:
            out = _truncate_at_word_boundary(out, max_total)
        return out

    return _truncate_at_word_boundary(s, max_total)


def apply_item_display_cleanup(
    item: Dict[str, Any],
    *,
    desc_max_primary: int = 280,
    desc_max_total: int = 420,
    material_max: int = 160,
) -> None:
    """
    Ajusta campos de texto do item para resposta HTTP sem alterar o match já feito.
    Preserva texto completo em `*_original` quando houver truncamento.
    """
    full = str(item.get("descricao_item") or "").strip()
    if full:
        short = clean_item_description_for_display(full, max_primary=desc_max_primary, max_total=desc_max_total)
        if short != full:
            item["descricao_item_original"] = full
        item["descricao_item"] = short

    mat = str(item.get("material_servico") or "").strip()
    if mat and len(mat) > material_max:
        short_m = clean_item_description_for_display(mat, max_primary=120, max_total=material_max)
        if short_m != mat:
            item["material_servico_original"] = mat
        item["material_servico"] = short_m
