"""
Layout e saneamento de texto do relatório de pesquisa de preços (HTML / WeasyPrint).

Centraliza limites de caracteres e truncamento para reduzir risco de sobreposição
de glifos e vazamento visual no PDF. Ajuste apenas aqui para revisar a «garantia» de densidade.
"""
from __future__ import annotations

from typing import Any, Dict, List

# --- Capa e metadados ---
PDF_CAPA_ORGAO_MAX_CHARS = 160
PDF_CAPA_TITULO_COTACAO_MAX = 380
PDF_CAPA_RESPONSAVEL_MAX = 120
PDF_TERMO_PNCP_MAX = 240

# --- Cartões de fonte (detalhamento) ---
PDF_FONTE_TEXTO_MAX: Dict[str, int] = {
    "fornecedor": 160,
    "descricao_fonte": 220,
    "orgao": 160,
    "endereco": 180,
    "email": 72,
    "telefone": 36,
    "link_pncp": 512,
    "ajuste": 72,
    "municipio_uf": 44,
    "tipo": 72,
    "cnpj": 22,
    "valor": 28,
    "data": 14,
    "quantidade": 24,
}

PDF_GRUPO_NOME_ITEM_MAX = 220


def truncar_texto_pdf(s: Any, max_len: int) -> str:
    t = str(s or "").strip()
    if max_len <= 0:
        return ""
    if len(t) <= max_len:
        return t
    if max_len <= 1:
        return "…"
    return t[: max_len - 1].rstrip() + "…"


def sanear_fonte_dict_para_pdf(f: Dict[str, Any]) -> None:
    """Trunca strings no dict de fonte (mutação in-place)."""
    if not isinstance(f, dict):
        return
    for k, mx in PDF_FONTE_TEXTO_MAX.items():
        if k not in f or f[k] is None:
            continue
        f[k] = truncar_texto_pdf(f[k], mx)


def sanear_grupo_relatorio_para_pdf(g: Dict[str, Any]) -> None:
    if not isinstance(g, dict):
        return
    if "nome" in g:
        g["nome"] = truncar_texto_pdf(g.get("nome") or "", PDF_GRUPO_NOME_ITEM_MAX)
    for row in g.get("fontes") or []:
        if isinstance(row, dict):
            sanear_fonte_dict_para_pdf(row)


def sanear_grupos_relatorio_para_pdf(grupos: List[Dict[str, Any]]) -> None:
    for g in grupos or []:
        sanear_grupo_relatorio_para_pdf(g)


def sanear_texto_capa_pdf(texto: str, *, max_chars: int = PDF_CAPA_ORGAO_MAX_CHARS) -> str:
    return truncar_texto_pdf(texto, max_chars)
