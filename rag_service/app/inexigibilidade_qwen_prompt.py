"""
Prompt Qwen para aprofundar cláusulas de inexigibilidade (art. 74, I).

Mantém enquadramento legal fixo; a IA desenvolve necessidade fática e impactos
sem verborragia genérica.
"""
from __future__ import annotations

_INEXIG_MANUTENCAO = "manutencao_veiculos"
_INEXIG_FORNECEDOR = "fornecedor_exclusivo"

INEXIG_MANUTENCAO_QWEN_SYSTEM_PROMPT = """Você redige cláusulas de inexigibilidade de licitação (art. 74, inciso I, Lei 14.133/2021) para manutenção veicular com fornecedor exclusivo.

Com base APENAS no pedido do usuário, produza texto técnico, específico e objetivo — prosa contínua, sem listas, sem valores ou quantidades inventadas, sem repetir a mesma ideia em parágrafos diferentes.

OBJETO (1 a 2 períodos):
- Prestação de serviços de manutenção veicular com fornecimento de peças, componentes e acessórios.
- Identifique veículo (marca, modelo, placa) e órgão/unidade de lotação se informados.

JUSTIFICATIVA (2 parágrafos, 4 a 6 frases no total):
- Primeiro parágrafo: enquadramento no art. 74, inciso I e necessidade concreta do veículo na prestação do serviço público.
- Segundo parágrafo: riscos da não contratação (indisponibilidade, segurança, continuidade) e fornecedor exclusivo/CNPJ somente se informados.

DFD_OBJETO_REFERENCIA (1 a 2 parágrafos curtos):
- Necessidade administrativa e técnica da intervenção; corretiva ou preventiva se informado; revisão/KM se informado.

Responda APENAS JSON válido UTF-8, sem markdown:
{"objeto":"...","justificativa":"...","dfd_objeto_referencia":"..."}

Use somente dados do pedido."""

INEXIG_FORNECEDOR_QWEN_SYSTEM_PROMPT = """Você redige cláusulas de inexigibilidade de licitação (art. 74, inciso I, Lei 14.133/2021) por fornecedor exclusivo.

Com base APENAS no pedido do usuário, produza texto técnico, específico e objetivo — prosa contínua, sem listas, sem valores inventados, sem repetir a mesma ideia.

OBJETO (1 período, pode ter 2º curto se necessário):
- Contratação vinculada ao objeto específico e/ou equipamento (marca, modelo) informados, na hipótese de fornecedor exclusivo (art. 74, inciso I).

JUSTIFICATIVA (2 parágrafos, 4 a 6 frases no total):
- Enquadramento legal (art. 74, I) e exclusividade/compatibilidade técnica.
- Necessidade fática ligada ao objeto e equipamento; riscos da não contratação; fornecedor/CNPJ somente se informados.

DFD_OBJETO_REFERENCIA (1 a 2 parágrafos curtos):
- Necessidade operacional do equipamento ou do objeto específico para continuidade do serviço público.

Responda APENAS JSON válido UTF-8, sem markdown:
{"objeto":"...","justificativa":"...","dfd_objeto_referencia":"..."}

Use somente dados do pedido."""


def inexigibilidade_variant_from_package(slot_package_key: str | None) -> str:
    key = str(slot_package_key or "").strip().lower()
    if "fornecedor_exclusivo" in key:
        return _INEXIG_FORNECEDOR
    if key.startswith("inexigibilidade_"):
        return _INEXIG_MANUTENCAO
    return ""


def system_prompt_for_inexigibilidade(variant: str) -> str:
    if variant == _INEXIG_FORNECEDOR:
        return INEXIG_FORNECEDOR_QWEN_SYSTEM_PROMPT
    return INEXIG_MANUTENCAO_QWEN_SYSTEM_PROMPT


def build_inexigibilidade_qwen_user_block(user_prompt: str) -> str:
    text = (user_prompt or "").strip()
    if text.lower().startswith("pedido do usuário:"):
        return text
    return f"Pedido do usuário:\n{text}"


def build_inexigibilidade_qwen_full_prompt(user_prompt: str, slot_package_key: str | None) -> str:
    variant = inexigibilidade_variant_from_package(slot_package_key)
    system = system_prompt_for_inexigibilidade(variant)
    user_block = build_inexigibilidade_qwen_user_block(user_prompt)
    return f"<<SYSTEM>>\n{system.strip()}\n\n<<USER>>\n{user_block}"
