from __future__ import annotations

from typing import Dict

import httpx

from .config import (
    RAG_HTTP_TIMEOUT,
    TEXT_CORRECTOR_BASE_URL,
    TEXT_CORRECTOR_ENABLED,
)


def _mode_from_document_type(document_type: str | None) -> str:
    dt = (document_type or "").lower()
    if "termo" in dt:
        return "tr"
    if "etp" in dt or "estudo" in dt:
        return "etp"
    if "dfd" in dt or "formalizacao" in dt:
        return "dfd"
    return "generic"


async def correct_section_texts(
    section_texts: Dict[str, str],
    document_type: str | None = None,
) -> Dict[str, str]:
    """
    Corrige automaticamente os textos das seções via text_corrector_service.
    Em falha/indisponibilidade, retorna o conteúdo original.
    """
    if not TEXT_CORRECTOR_ENABLED:
        return section_texts
    if not isinstance(section_texts, dict) or not section_texts:
        return section_texts

    mode = _mode_from_document_type(document_type)
    corrected: Dict[str, str] = {}
    url = f"{TEXT_CORRECTOR_BASE_URL}/correct"

    async with httpx.AsyncClient(timeout=RAG_HTTP_TIMEOUT) as client:
        for key, raw_value in section_texts.items():
            value = raw_value if isinstance(raw_value, str) else str(raw_value or "")
            if not value.strip():
                corrected[key] = value
                continue
            try:
                resp = await client.post(
                    url,
                    json={"text": value, "mode": mode, "language": "pt-BR"},
                )
                resp.raise_for_status()
                data = resp.json() if resp.content else {}
                text = data.get("corrected_text") if isinstance(data, dict) else None
                lt_applied = bool(data.get("language_tool_applied")) if isinstance(data, dict) else False
                # Garante dependência principal do LanguageTool:
                # sem LT ativo, preserva texto original (evita depender apenas de regras manuais).
                if lt_applied and isinstance(text, str) and text.strip():
                    corrected[key] = text
                else:
                    corrected[key] = value
            except Exception:
                corrected[key] = value

    return corrected
