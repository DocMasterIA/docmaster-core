"""Prompt Qwen para cláusulas (proxy /api/llm/generate inexigibilidade). Espelha rag_service/app/clausulas_qwen_prompt.py."""
from __future__ import annotations

CLAUSULAS_QWEN_SYSTEM_PROMPT = """Você redige cláusulas de Termo de Referência (Lei 14.133/2021).

Tarefa — com base no pedido do usuário, escreva:
• objeto: o que será contratado, finalidade/setor atendido, redação formal de cláusula;
• justificativa: necessidade da contratação, continuidade do serviço público e riscos de não contratar.

Responda APENAS JSON válido: {"objeto":"...","justificativa":"..."}

Use somente dados do pedido. Não invente órgão, município, valores ou linhas de tabela com quantidades."""


def wrap_clausulas_prompt_for_qwen(user_prompt: str) -> str:
    text = (user_prompt or "").strip()
    return f"<<SYSTEM>>\n{CLAUSULAS_QWEN_SYSTEM_PROMPT.strip()}\n\n<<USER>>\n{text}"
