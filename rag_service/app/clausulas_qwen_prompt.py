"""
Prompt para objeto/justificativa via gateway cloud (Qwen).

Dispensa normal e rápida (art. 75): redação técnica densa, sem verborragia.
"""
from __future__ import annotations

CLAUSULAS_QWEN_SYSTEM_PROMPT = """Você é redator de Termo de Referência (Lei 14.133/2021, dispensa de licitação — art. 75).

Com base APENAS no pedido do usuário, redija o objeto em português claro e a justificativa em linguagem técnica, específica e contextualizada — sem verborragia, sem repetir ideias e sem frases de enchimento.

OBJETO (1 período completo e bem articulado; até 2 se indispensável):
- Cláusula declarativa com profundidade administrativa: NÃO reduza a uma frase telegráfica; inclua, quando couber pelo pedido, (1) natureza da contratação, (2) tipo ou modalidade do serviço/bem, (3) equipamento, material ou público atendido, (4) setor/unidade/local de destino, (5) finalidade operacional em linguagem acessível.
- Português claro: palavras compreensíveis por qualquer servidor; evite termos raros, latinismos ou jargão desnecessário (ex.: evite "cocção" — prefira "fogão a gás" ou "equipamento de cozinha a gás"; evite "plena operacionalidade do ativo" — prefira "pleno funcionamento do equipamento" ou "continuidade do serviço").
- Mantenha o mesmo nível de detalhe de uma cláusula madura, trocando só vocabulário difícil por equivalente comum — não simplifique demais.
- Modelo de profundidade (adaptar ao pedido; não copiar literalmente): "Contratação de serviço especializado de manutenção corretiva do fogão a gás da cozinha, destinado ao uso da Secretaria de Administração, visando restabelecer o pleno funcionamento do equipamento."
- Anti-modelo (proibido — objeto pobre): "Contratação de serviço de conserto do fogão da cozinha da Secretaria de Administração." ou "Aquisição de medicamentos para a UBS Leontino." sem tipo de assistência, destino administrativo ou finalidade.
- Em dispensa normal: redação genérica institucional sobre o tema, sem nominalizar cada item da tabela.
- OBRIGATÓRIO no objeto: feche com vírgula + «conforme quantidades e demais condições estabelecidas neste Termo de Referência». Use sempre «neste Termo de Referência»; proibido «requisitos técnicos» no fechamento.
- PROIBIDO no objeto: «a execução obedecerá…», riscos da não contratação ou argumentação de justificativa.
- PROIBIDO usar nos textos: órgão/unidade do cabeçalho administrativo, prefeitura, município, processo, cabeçalho do documento ou qualquer metadado que não esteja explicitamente em «O que será contratado» ou «Setor/secretaria atendido».

JUSTIFICATIVA (exatamente 3 parágrafos em prosa corrida, separados por linha em branco — pare após o 3º):
- Proibido listas com marcadores (-, *, números), bullets, tópicos ou continuação após o 3º parágrafo.
- Cada eixo argumentativo aparece UMA vez: 1º necessidade; 2º riscos da não contratação; 3º adequação/interesse público. Proibido reformular ou resumir um eixo já tratado.
- 1º parágrafo: necessidade concreta da contratação ligada ao contratado e ao setor/secretaria informados.
- 2º parágrafo: riscos técnicos e operacionais da não contratação (continuidade do serviço público, eficiência, segurança ou desempenho institucional), com profundidade técnica proporcional ao objeto.
- 3º parágrafo: adequação da medida ao interesse público e continuidade administrativa; características mínimas somente se informadas.
- Cada parágrafo: 3 a 4 frases técnicas e objetivas. Proibido texto genérico aplicável a qualquer contratação sem citar o contratado; proibido eco entre parágrafos.
- Encerre o JSON imediatamente após o 3º parágrafo — não acrescente síntese, conclusão extra nem parágrafo adicional.

Responda APENAS JSON válido UTF-8, sem markdown:
{"objeto":"...","justificativa":"..."}

Na chave justificativa, use "\\n\\n" entre os três parágrafos.

Use somente dados do pedido. Não invente órgão, município, processo, valores ou quantidades não informadas."""

_DISPRESA_CLAUSULAS_PEDIDO_KEEP_PREFIXES = (
    "o que será contratado:",
    "o que sera contratado:",
    "setor/secretaria atendido:",
    "características mínimas:",
    "caracteristicas minimas:",
    "tipo de manutenção:",
    "tipo de manutencao:",
    "revisão/km:",
    "revisao/km:",
)

_DISPRESA_CLAUSULAS_PEDIDO_DROP_PREFIXES = (
    "órgão:",
    "orgao:",
    "cabeçalho do documento:",
    "cabeçalho:",
    "cabecalho do documento:",
    "cabecalho:",
    "processo:",
    "gerar documento com base",
    "objeto base:",
    "objeto (o que será contratado):",
    "em objeto e justificativa não liste",
    "em objeto e justificativa nao liste",
)


def dispensa_clausulas_pedido_from_user_prompt(user_prompt: str) -> str:
    """
    Extrai só o pedido permitido para objeto/justificativa (dispensa normal/rápida).
    Remove órgão/unidade, cabeçalho, processo e outros metadados administrativos.
    """
    text = (user_prompt or "").strip()
    if not text:
        return ""
    kept: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        low = stripped.lower()
        if any(low.startswith(p) for p in _DISPRESA_CLAUSULAS_PEDIDO_DROP_PREFIXES):
            continue
        if any(low.startswith(p) for p in _DISPRESA_CLAUSULAS_PEDIDO_KEEP_PREFIXES):
            kept.append(stripped)
            continue
        if low.startswith("setor/secretaria atendido"):
            if ":" in stripped:
                _, _, value = stripped.partition(":")
                kept.append(f"Setor/secretaria atendido: {value.strip()}")
            else:
                kept.append(stripped)
    if kept:
        return "\n".join(kept)
    if not any(
        line.strip().lower().startswith(_DISPRESA_CLAUSULAS_PEDIDO_DROP_PREFIXES)
        for line in text.splitlines()
        if line.strip()
    ):
        return text
    return ""


def clausulas_qwen_system_prompt(fluxo_ui: str = "") -> str:
    """Geração lite: mesmo prompt para normal e rápida (3 parágrafos em «justificativa»)."""
    return CLAUSULAS_QWEN_SYSTEM_PROMPT


def build_clausulas_qwen_user_block(user_prompt: str) -> str:
    """Pedido do formulário, sem regras extras herdadas do modo Ollama."""
    text = (user_prompt or "").strip()
    if text.lower().startswith("pedido do usuário:"):
        return text
    return f"Pedido do usuário:\n{text}"


def build_clausulas_qwen_full_prompt(user_prompt: str, *, fluxo_ui: str = "") -> str:
    user_block = build_clausulas_qwen_user_block(user_prompt)
    fluxo = str(fluxo_ui or "").strip().lower()
    anti_orgao = (
        "\nUse somente «O que será contratado» e «Setor/secretaria atendido» (e características mínimas, se houver). "
        "Não use órgão/unidade do formulário administrativo, prefeitura, município, cabeçalho nem processo."
    )
    if fluxo == "rapida":
        user_block += (
            "\n\nDispensa rápida: mesmo padrão da normal — justificativa com exatamente 3 parágrafos "
            "(\\n\\n entre eles) na chave justificativa; mencione o setor/secretaria do pedido; "
            "responda só com {\"objeto\",\"justificativa\"}."
            + anti_orgao
        )
    elif fluxo == "normal":
        user_block += (
            "\n\nDispensa normal — objeto: cláusula completa (natureza, destino/setor e finalidade); "
            "português claro sem termos difíceis; não cite itens, quantidades ou valores de tabela."
            + anti_orgao
        )
    system = clausulas_qwen_system_prompt(fluxo)
    return f"<<SYSTEM>>\n{system.strip()}\n\n<<USER>>\n{user_block}"
