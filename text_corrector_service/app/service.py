from __future__ import annotations

import re
import unicodedata
from typing import List, Tuple

import httpx

from .config import (
    CORRECTOR_HTTP_TIMEOUT,
    LANGUAGETOOL_BASE_URL,
    LANGUAGETOOL_CHECK_PATH,
)
from .custom_replacements import _CUSTOM_REPLACEMENTS
from .schemas import ChangeItem


def normalize_text(text: str) -> str:
    t = unicodedata.normalize("NFKC", text or "")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def apply_custom_replacements(text: str) -> Tuple[str, List[ChangeItem]]:
    t = text
    changes: List[ChangeItem] = []
    protected_upper_acronyms = {"ME", "EPP", "CPF", "CNPJ"}

    # Aplica substituição por palavra (case-insensitive) para evitar
    # alterar pedaços internos de palavras válidas.
    for bad, good in _CUSTOM_REPLACEMENTS.items():
        pattern = re.compile(rf"\b{re.escape(bad)}\b", flags=re.IGNORECASE)
        if not pattern.search(t):
            continue

        def _replace(match: re.Match[str]) -> str:
            token = match.group(0)
            # Preserva siglas em caixa alta (ex.: ME, EPP, CPF, CNPJ)
            # para não expandir indevidamente para texto comum.
            if token in protected_upper_acronyms:
                return token
            return good

        t_new = pattern.sub(_replace, t)
        if t_new != t:
            t = t_new
            changes.append(ChangeItem(from_text=bad, to_text=good, rule="custom_dictionary"))

    return t, changes


async def language_tool_correct(text: str, language: str = "pt-BR") -> Tuple[str, List[ChangeItem], List[str], bool]:
    """
    Aplica correções automáticas simples usando LanguageTool.
    """
    url = f"{LANGUAGETOOL_BASE_URL}{LANGUAGETOOL_CHECK_PATH}"
    payload = {"text": text, "language": language}
    warnings: List[str] = []
    changes: List[ChangeItem] = []
    corrected = text

    try:
        async with httpx.AsyncClient(timeout=CORRECTOR_HTTP_TIMEOUT) as client:
            resp = await client.post(url, data=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        warnings.append(f"LanguageTool indisponível: {e}")
        return text, changes, warnings, False

    matches = data.get("matches") or []
    if not isinstance(matches, list) or not matches:
        return corrected, changes, warnings, True

    # Aplica substituições da direita para a esquerda para preservar offsets.
    ops: List[Tuple[int, int, str, str]] = []
    for m in matches:
        try:
            offset = int(m.get("offset"))
            length = int(m.get("length"))
            rule_id = str((m.get("rule") or {}).get("id") or "languagetool")
            replacements = m.get("replacements") or []
            if not replacements:
                continue
            replacement = str(replacements[0].get("value") or "")
            if not replacement:
                continue
            original = corrected[offset : offset + length]
            if original == replacement:
                continue
            ops.append((offset, length, replacement, rule_id))
        except Exception:
            continue

    for offset, length, replacement, rule_id in sorted(ops, key=lambda x: x[0], reverse=True):
        original = corrected[offset : offset + length]
        corrected = corrected[:offset] + replacement + corrected[offset + length :]
        changes.append(ChangeItem(from_text=original, to_text=replacement, rule=f"languagetool:{rule_id}"))

    changes.reverse()
    return corrected, changes, warnings, True


def apply_post_rules(text: str) -> Tuple[str, List[ChangeItem]]:
    """
    Regras determinísticas simples para remover meta-linhas comuns.
    """
    changes: List[ChangeItem] = []
    t = text

    if "Este texto foi gerado com base em instruções." in t:
        t = t.replace("Este texto foi gerado com base em instruções.", "").strip()
        changes.append(
            ChangeItem(
                from_text="Este texto foi gerado com base em instruções.",
                to_text="",
                rule="post_rule:remove_meta_generation_line",
            )
        )

    t2 = re.sub(r"(?im)^atenção:\s*", "", t)
    if t2 != t:
        t = t2
        changes.append(ChangeItem(from_text="Atenção:", to_text="", rule="post_rule:strip_atencao_prefix"))

    # Preserva nomenclatura institucional comum em documentos públicos.
    t2 = re.sub(r"\bsecretária\b(?=\s+(?:de|municipal|estadual|da|do)\b)", "secretaria", t, flags=re.IGNORECASE)
    t2 = re.sub(r"\bprefeitura\s+municipal\b", "Prefeitura Municipal", t2, flags=re.IGNORECASE)
    t2 = re.sub(r"\bsecretaria\s+municipal\b", "Secretaria Municipal", t2, flags=re.IGNORECASE)
    t2 = re.sub(r"\bsecretaria\s+de\s+([a-zà-ÿ])", lambda m: "Secretaria de " + m.group(1).upper(), t2, flags=re.IGNORECASE)
    if t2 != t:
        changes.append(
            ChangeItem(
                from_text="formas institucionais inconsistentes",
                to_text="formas institucionais normalizadas",
                rule="post_rule:normalize_institutional_forms",
            )
        )
        t = t2

    # Ajustes gramaticais frequentes em ETP que o LanguageTool pode não capturar.
    t2 = re.sub(
        r"(?i)\bObjeto do Estudo Técnico Preliminar\s+consistente\b",
        "Objeto do Estudo Técnico Preliminar consiste",
        t,
    )
    t2 = re.sub(r"(?i)\babordagem\s+continua-se\s+sustentável\b", "abordagem contínua e sustentável", t2)
    if t2 != t:
        changes.append(
            ChangeItem(
                from_text="construções gramaticais recorrentes em ETP",
                to_text="construções gramaticais normalizadas",
                rule="post_rule:etp_grammar_fixes",
            )
        )
        t = t2

    # Ajustes de regência e sujeito institucional em objetos de contratação.
    t2 = re.sub(
        r"(?i)\bA Administração\s+Prefeitura Municipal\b",
        "A Prefeitura Municipal",
        t,
    )
    t2 = re.sub(
        r"(?i)\batendendo necessidades específicas\b",
        "atendendo às necessidades específicas",
        t2,
    )
    t2 = re.sub(
        r"(?i)\bmelhoria do ambiente urbano e a saúde pública\b",
        "melhoria do ambiente urbano e da saúde pública",
        t2,
    )
    if t2 != t:
        changes.append(
            ChangeItem(
                from_text="regência/sujeito institucional inconsistente",
                to_text="regência/sujeito institucional normalizado",
                rule="post_rule:public_admin_object_fixes",
            )
        )
        t = t2

    return t, changes
