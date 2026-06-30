"""
Prompt para objeto/justificativa via gateway cloud (Qwen).

Dispensa normal e rápida (art. 75): redação técnica densa, sem verborragia.
O setor requisitante do DFD (2.1) NÃO entra no pedido — mas «Setor/secretaria atendido» do bloco Objeto da contratação SIM.
"""
from __future__ import annotations

CLAUSULAS_QWEN_SYSTEM_PROMPT = """Você é redator de Termo de Referência (Lei 14.133/2021, dispensa de licitação — art. 75).

Com base APENAS no pedido do usuário, redija o objeto em português claro e a justificativa em linguagem técnica, específica e contextualizada — sem verborragia, sem repetir ideias e sem frases de enchimento.

OBJETO (1 período completo e bem articulado; até 2 se indispensável):
- Cláusula declarativa com profundidade administrativa: NÃO reduza a uma frase telegráfica; inclua, quando couber pelo pedido, (1) natureza da contratação, (2) tipo ou modalidade do serviço/bem, (3) equipamento, material ou público atendido, (4) finalidade operacional em linguagem acessível.
- Português claro: palavras compreensíveis por qualquer servidor; evite termos raros, latinismos ou jargão desnecessário (ex.: evite "cocção" — prefira "fogão a gás" ou "equipamento de cozinha a gás"; evite "plena operacionalidade do ativo" — prefira "pleno funcionamento do equipamento" ou "continuidade do serviço").
- Mantenha o mesmo nível de detalhe de uma cláusula madura, trocando só vocabulário difícil por equivalente comum — não simplifique demais.
- Modelo de profundidade (adaptar ao pedido; não copiar literalmente): "Contratação de serviço especializado de manutenção corretiva do fogão a gás da cozinha, visando restabelecer o pleno funcionamento do equipamento."
- Anti-modelo (proibido — objeto pobre): "Contratação de serviço de conserto do fogão." ou "Aquisição de medicamentos." sem tipo de assistência ou finalidade.
- Se o pedido mencionar destino administrativo (secretaria, unidade, local), pode incorporar ao objeto; não invente setor/unidade ausente do pedido.
- Em dispensa normal: redação genérica institucional sobre o tema, sem nominalizar cada item da tabela.
- OBRIGATÓRIO no objeto: feche com vírgula + «conforme quantidades e demais condições estabelecidas neste Termo de Referência». Use sempre «neste Termo de Referência»; proibido «requisitos técnicos» no fechamento.
- PROIBIDO no objeto: «a execução obedecerá…», riscos da não contratação ou argumentação de justificativa.
- PROIBIDO usar nos textos: órgão/unidade do cabeçalho administrativo, prefeitura, município, processo, cabeçalho do documento, setor requisitante do DFD (2.1) ou metadado fora de «O que será contratado», «Setor/secretaria atendido» e «Características mínimas».

JUSTIFICATIVA (exatamente 3 parágrafos em prosa corrida, separados por linha em branco — pare após o 3º):
- Proibido listas com marcadores (-, *, números), bullets, tópicos ou continuação após o 3º parágrafo.
- Cada eixo argumentativo aparece UMA vez: 1º necessidade; 2º riscos da não contratação; 3º adequação/interesse público. Proibido reformular ou resumir um eixo já tratado.
- 1º parágrafo: necessidade concreta da contratação ligada ao contratado informado.
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
    "características mínimas:",
    "caracteristicas minimas:",
    "tipo de manutenção:",
    "tipo de manutencao:",
    "revisão/km:",
    "revisao/km:",
    "setor/secretaria atendido:",
    "setor/secretaria atendido",
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
    "setor requisitante",
    "2. dfd",
    "2.1 setor requisitante",
    "documento de formalização da demanda",
    "dfd – documento",
    "dfd - documento",
)


def dispensa_clausulas_pedido_from_user_prompt(user_prompt: str) -> str:
    """
    Extrai só o pedido permitido para objeto/justificativa (dispensa normal/rápida).
    Remove órgão/unidade, cabeçalho, processo e setor requisitante do DFD (2.1).
    Mantém «Setor/secretaria atendido» do bloco Objeto da contratação.
    """
    text = (user_prompt or "").strip()
    if not text:
        return ""
    kept: list[str] = []
    capture = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if capture:
                kept.append("")
            continue
        low = stripped.lower()
        if any(low.startswith(p) for p in _DISPRESA_CLAUSULAS_PEDIDO_DROP_PREFIXES):
            capture = False
            continue
        if any(low.startswith(p) for p in _DISPRESA_CLAUSULAS_PEDIDO_KEEP_PREFIXES):
            kept.append(stripped)
            capture = True
            continue
        if capture:
            kept.append(stripped)
    if kept:
        return "\n".join(kept).strip()
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
        "\nUse somente «O que será contratado», «Setor/secretaria atendido» (se houver) e "
        "«Características mínimas» (se houver). "
        "Não use órgão/unidade do formulário administrativo, prefeitura, município, cabeçalho, "
        "processo nem setor requisitante do DFD (2.1)."
    )
    if fluxo == "rapida":
        user_block += (
            "\n\nDispensa rápida: mesmo padrão da normal — justificativa com exatamente 3 parágrafos "
            "(\\n\\n entre eles) na chave justificativa; "
            "responda só com {\"objeto\",\"justificativa\"}."
            + anti_orgao
        )
    elif fluxo == "normal":
        user_block += (
            "\n\nDispensa normal — objeto: cláusula completa (natureza e finalidade); "
            "português claro sem termos difíceis; não cite itens, quantidades ou valores de tabela."
            + anti_orgao
        )
    system = clausulas_qwen_system_prompt(fluxo)
    return f"<<SYSTEM>>\n{system.strip()}\n\n<<USER>>\n{user_block}"
