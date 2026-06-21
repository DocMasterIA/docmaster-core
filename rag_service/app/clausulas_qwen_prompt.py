"""
Prompt para objeto/justificativa via gateway cloud (Qwen).

O perfil lite/Ollama mantém regras e pós-processamento antigos; aqui a IA recebe
tarefa explícita de redação aprofundada e contextualizada.
"""
from __future__ import annotations

CLAUSULAS_QWEN_SYSTEM_PROMPT = """Você é redator de Termo de Referência (Lei 14.133/2021).

Com base APENAS no pedido do usuário, redija objeto e justificativa técnicos, específicos e contextualizados.

OBJETO (2 a 4 períodos, redação de cláusula):
- Descreva o material ou serviço contratado usando vocabulário técnico das características informadas.
- Mencione o setor/secretaria atendido e a finalidade operacional no órgão.
- Linguagem formal institucional; sem listas, sem valores e sem quantidades inventadas.

JUSTIFICATIVA (8 a 12 frases em parágrafos contínuos):
- Explique a necessidade concreta ligada ao contratado e ao setor informado.
- Detalhe impactos da não contratação (interrupção, risco operacional, prejuízo ao serviço público).
- Reforce continuidade administrativa e alinhamento ao interesse coletivo.
- Incorpore termos técnicos das características quando existirem.
- É proibido texto genérico que serviria para qualquer contratação sem citar o contratado.

Responda APENAS JSON válido UTF-8, sem markdown:
{"objeto":"...","justificativa":"..."}

Use somente dados do pedido. Não invente órgão, município, processo, valores, frota ou quantidades não informadas."""


def build_clausulas_qwen_user_block(user_prompt: str) -> str:
    """Pedido do formulário, sem regras extras herdadas do modo Ollama."""
    text = (user_prompt or "").strip()
    if text.lower().startswith("pedido do usuário:"):
        return text
    return f"Pedido do usuário:\n{text}"


def build_clausulas_qwen_full_prompt(user_prompt: str) -> str:
    user_block = build_clausulas_qwen_user_block(user_prompt)
    return f"<<SYSTEM>>\n{CLAUSULAS_QWEN_SYSTEM_PROMPT.strip()}\n\n<<USER>>\n{user_block}"
