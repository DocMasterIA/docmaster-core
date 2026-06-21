"""
Prompt enxuto para objeto/justificativa via gateway cloud (Qwen).

O perfil lite/Ollama mantém regras e pós-processamento antigos; aqui a IA recebe
tarefa clara e poucos limites — controles jurídicos mínimos no system prompt.
"""
from __future__ import annotations

CLAUSULAS_QWEN_SYSTEM_PROMPT = """Você redige cláusulas de Termo de Referência (Lei 14.133/2021).

Tarefa — com base no pedido do usuário, escreva:
• objeto: o que será contratado, finalidade/setor atendido, redação formal de cláusula;
• justificativa: necessidade da contratação, continuidade do serviço público e riscos de não contratar.

Responda APENAS JSON válido: {"objeto":"...","justificativa":"..."}

Use somente dados do pedido. Não invente órgão, município, valores ou linhas de tabela com quantidades."""


def build_clausulas_qwen_user_block(user_prompt: str) -> str:
    """Pedido do formulário, sem regras extras herdadas do modo Ollama."""
    text = (user_prompt or "").strip()
    if text.lower().startswith("pedido do usuário:"):
        return text
    return f"Pedido do usuário:\n{text}"


def build_clausulas_qwen_full_prompt(user_prompt: str) -> str:
    user_block = build_clausulas_qwen_user_block(user_prompt)
    return f"<<SYSTEM>>\n{CLAUSULAS_QWEN_SYSTEM_PROMPT.strip()}\n\n<<USER>>\n{user_block}"
