"""
Extrai tamanho de embalagem (unidades por pacote/caixa) do termo de busca e do item PNCP.

A informação aparece em lugares diferentes: descrição («PCT C/100 UN»), unidade_medida
(«PACOTE 50,00 UN»), quantidade (qtd de pacotes comprados — não confundir com tamanho).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .search_text_clean import normalize_for_search


@dataclass
class PackSizeHints:
    """Unidades por embalagem inferidas (ex.: pacote com 100 unidades)."""

    pack_units: Optional[int] = None
    candidates: List[int] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)


# Embalagem: C/100 UN, CX 100 UNIDADES, PACOTE COM 100, PCT C/100
_PACK_PATTERNS = (
    re.compile(
        r"(?:\bc/|\bc\s+|contem\s+|com\s+)\s*(\d{1,5})\s*(?:unidades?|unids?|und\.?|un\b|pecas?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:pacote|pct|pc|cx|caixa|embalagem|caixa\s+com)[^\d]{0,24}(\d{1,5})\s*(?:unidades?|unids?|und\.?|un\b|pecas?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:pacote|pct|pc)\s*(?:c/?\s*)?(\d{1,5})\s*(?:,|\s|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(\d{1,5})\s*,?\s*00\s*un\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(\d{1,5})\s*un(?:idades?)?\s*(?:por\s+)?(?:pacote|pct|caixa|embalagem)",
        re.IGNORECASE,
    ),
)

# Evita confundir dimensão (1,50 cm) ou volume (120 ml) com embalagem.
_SKIP_NEARBY = re.compile(
    r"(?:\d+[,.]?\d*\s*(?:cm|mm|ml|mg|g\b|kg|l\b|m\b|x\d|g½))",
    re.IGNORECASE,
)


def _plausible_pack(n: int) -> bool:
    return 1 <= n <= 9999


def _extract_pack_numbers_from_text(text: str, *, source: str) -> List[tuple[int, str]]:
    raw = (text or "").strip()
    if not raw:
        return []
    norm = normalize_for_search(raw)
    if not norm:
        return []
    found: List[tuple[int, str]] = []
    seen: Set[int] = set()
    for pat in _PACK_PATTERNS:
        for m in pat.finditer(norm):
            start = max(0, m.start() - 12)
            window = norm[start : m.end() + 8]
            if _SKIP_NEARBY.search(window) and "un" not in window[max(0, m.start() - start) :]:
                continue
            try:
                val = int(m.group(1))
            except (TypeError, ValueError):
                continue
            if not _plausible_pack(val):
                continue
            if val in seen:
                continue
            seen.add(val)
            found.append((val, source))
    return found


def extract_pack_hints_from_term(termo: str) -> PackSizeHints:
    """Lê embalagem do pedido ANTES do preprocess remover «C/100 UNIDADES»."""
    hits = _extract_pack_numbers_from_text(termo, source="termo")
    if not hits:
        return PackSizeHints()
    nums = [n for n, _ in hits]
    # Termo costuma ter uma embalagem explícita; preferir o maior número em contexto C/ ou pacote.
    primary = nums[0]
    for n, src in hits:
        if n >= primary:
            primary = n
    return PackSizeHints(
        pack_units=primary,
        candidates=nums,
        sources=[s for _, s in hits],
    )


def _item_text_blobs(item: Dict[str, Any]) -> List[tuple[str, str]]:
    blobs: List[tuple[str, str]] = []
    for key, src in (
        ("descricao_item", "descricao"),
        ("descricao_item_original", "descricao_original"),
        ("descricao", "descricao"),
        ("material_servico", "material"),
        ("material_servico_original", "material_original"),
        ("unidade_medida", "unidade"),
    ):
        val = str(item.get(key) or "").strip()
        if val:
            blobs.append((val, src))
    return blobs


def extract_pack_hints_from_item(item: Dict[str, Any]) -> PackSizeHints:
    """
    Coleta candidatos a «unidades por embalagem» no item PNCP.
    unidade_medida tem peso (ex.: «PACOTE 50,00 UN»); quantidade sozinha não entra.
    """
    all_hits: List[tuple[int, str]] = []
    for text, src in _item_text_blobs(item):
        all_hits.extend(_extract_pack_numbers_from_text(text, source=src))

    if not all_hits:
        return PackSizeHints()

    # Prioridade: unidade > descrição (campo unidade_medida é mais confiável para tamanho de pct)
    priority = {"unidade": 0, "descricao": 1, "descricao_original": 2, "material": 3, "material_original": 4}
    all_hits.sort(key=lambda x: (priority.get(x[1], 9), -x[0]))

    candidates: List[int] = []
    sources: List[str] = []
    seen: Set[int] = set()
    for n, src in all_hits:
        if n in seen:
            continue
        seen.add(n)
        candidates.append(n)
        sources.append(src)

    primary = candidates[0] if candidates else None
    return PackSizeHints(pack_units=primary, candidates=candidates, sources=sources)


def pack_size_rerank_adjustment(termo_raw: str, item: Dict[str, Any]) -> float:
    """
    Bônus/penalidade no rerank local quando embalagem do termo conflita ou casa com o item.
    Retorno típico: -45..+30.
    """
    term = extract_pack_hints_from_term(termo_raw)
    if term.pack_units is None:
        return 0.0

    want = int(term.pack_units)
    item_hints = extract_pack_hints_from_item(item)
    if not item_hints.candidates:
        return 0.0

    cands = item_hints.candidates
    if want in cands:
        # Match exato; se houver também valor conflitante na unidade, priorizar unidade.
        if "unidade" in item_hints.sources:
            u_hints = extract_pack_hints_from_item(
                {**item, "descricao_item": "", "descricao": "", "material_servico": ""}
            )
            if u_hints.pack_units is not None and u_hints.pack_units != want:
                return -38.0
        return 28.0

    # Conflito claro: item declara outro tamanho de pacote (ex.: 50 vs 100).
    unit_only = extract_pack_hints_from_item(
        {
            **item,
            "descricao_item": "",
            "descricao_item_original": "",
            "descricao": "",
            "material_servico": "",
            "material_servico_original": "",
        }
    )
    if unit_only.pack_units is not None and unit_only.pack_units != want:
        return -42.0

    # Só na descrição: penalidade mais suave se nenhum candidato bate.
    if all(abs(c - want) / max(want, 1) > 0.15 for c in cands):
        best = min(cands, key=lambda c: abs(c - want))
        if abs(best - want) >= 20:
            return -32.0
        if abs(best - want) >= 10:
            return -18.0
    return -8.0
