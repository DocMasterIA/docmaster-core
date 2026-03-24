"""
Preenchimento dos slots do TR via IA.

A partir de user_prompt (e opcionalmente contexto/slots enviados pelo usuário),
chama o llm_agent para interpretar e a LLM para preencher o JSON de slots.
Os valores enviados pelo usuário (slots_override) têm prioridade sobre a IA.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

import httpx

from .config import (
    CHROMA_COLLECTION,
    LLM_AGENT_BASE_URL,
    LLM_ORCHESTRATION_BASE_URL,
    LLM_ORCHESTRATION_GENERATE_PATH,
    RAG_HTTP_TIMEOUT,
)
from .retrieval import retrieve
from .tr_template import (
    TRTemplateSlots,
    DispensaSlots,
    FiscalSlots,
    ItemSlot,
)


TR_SLOTS_SYSTEM_PROMPT = """Você preenche os campos (slots) de um Termo de Referência com base no pedido do usuário e no contexto.

REGRAS:
- Responda APENAS com um JSON válido, sem texto antes ou depois.
- O JSON deve ter pelo menos estas chaves: objeto, dispensa, itens, justificativa, problema_administrativo, beneficio_esperado, fiscal, dotacao.
- Use linguagem técnica, formal e objetiva, adequada a documentos administrativos. NÃO use gírias, comentários informais ou meta-observações (ex.: "simples até demais", "ficou meio esquisito", "feito direto pelo usuário").

- dispensa: objeto com "artigo" e "inciso".
  - O artigo, neste contexto de Termo de Referência, é sempre o art. 75 da Lei 14.133/2021. Portanto, devolva SEMPRE "artigo": "75".
  - SUA TAREFA é escolher o "inciso" correto DENTRO DO ART. 75, em coerência com o objeto e o contexto, usando EXCLUSIVAMENTE os incisos previstos na lei.
  - O inciso SEMPRE deve ser devolvido como um dos ALGARISMOS ROMANOS válidos do art. 75:
    ["I","II","III","IV","V","VI","VII","VIII","IX","X","XI","XII","XIII","XIV","XV"].
    NUNCA devolva números arábicos como "1", "2", "8" ou "75" no campo "inciso".
  - Diretrizes principais de mapeamento (Lei 14.133/2021, art. 75 – dispensa de licitação):
    * Inciso I  – obras e serviços de engenharia ou serviços de manutenção de veículos automotores, até o limite legal.
    * Inciso II – outros serviços e compras em geral, até o limite legal.
    * Inciso III – repetição de contratação com as mesmas condições de edital recente (sem interessados, propostas inválidas ou preços manifestamente inadequados).
    * Inciso IV – hipóteses específicas como peças/equipamentos em garantia com exclusividade do fornecedor, contratos entre entes da Administração criados para esse fim, P&D limitado a valor, transferência de tecnologia/ICT, gêneros perecíveis, alta complexidade tecnológica/defesa, padronização de materiais de Forças Armadas.
    * Inciso V  – serviços para viabilizar acordo internacional aprovado pelo Congresso, quando vantajosos.
    * Inciso VI – manutenção de equipamentos com assistência técnica exclusiva, acima do limite do inciso I.
    * Inciso VII – contratação de instituição de pesquisa/ensino/desenvolvimento institucional ou de recuperação de preso, sem fins lucrativos e com reputação ilibada.
    * Inciso VIII – emergência ou calamidade pública, para bens/serviços estritamente necessários, no prazo máximo de 1 ano, vedada prorrogação e recontratação com base no mesmo inciso.
    * Inciso IX – aquisição ou locação de imóvel com características de instalações/localização que tornem necessária a escolha.
    * Inciso X – insumos estratégicos para saúde produzidos ou prestados por entidade pública criada para esse fim, com preço compatível com o mercado.
    * Inciso XI – contratação de associações de catadores de materiais recicláveis/reutilizáveis, sem fins lucrativos e integradas por pessoas de baixa renda.
    * Inciso XII – contratação de profissionais de notória especialização para comissão de avaliação de critérios de técnica.
    * Inciso XIII – bens/serviços de empresas que comprovem cumprimento de reserva legal de cargos para pessoas com deficiência ou reabilitados, com acessibilidade adequada.
    * Inciso XIV – serviços prestados por organizações sociais, para atividades previstas em contrato de gestão.
    * Inciso XV – serviços prestados por instituições sem fins lucrativos com certificação de entidade beneficente de assistência social, para serviços de assistência social.
  - Se o objeto indicar obras/serviços de engenharia ou manutenção de veículos até o limite de valor do art. 75, use inciso "I".
  - Se o objeto indicar outros serviços ou compras até o limite de valor do art. 75, use inciso "II".
  - Se o usuário mencionar expressamente emergência ou calamidade pública nos termos da lei, considere a possibilidade de usar o inciso "VIII" do art. 75, se isso for coerente com o contexto.
  - Se o usuário mencionar explicitamente outro inciso (I a XV) e isso for compatível com o objeto, respeite o inciso informado.
  - Se não for possível determinar um inciso com segurança, deixe o inciso vazio "" e apenas preencha o artigo como "75", para que um humano possa complementar depois.

- itens: array de objetos, cada um com "descricao", "unidade" (ex: "un", "cx", "litro"), "quantidade" (número).
  - A "descricao" deve ser uma especificação técnica mínima do item, não apenas uma palavra solta (ex.: "Caneta esferográfica azul, ponta 1.0 mm").
  - Se o usuário já tiver informado descrição/unidade/quantidade, preserve essas informações e apenas complemente de forma técnica quando fizer sentido.
- fiscal: objeto com "nome" (nome completo do fiscal do contrato). Se não houver nome de fiscal claramente informado pelo usuário ou contexto, use "" (não invente nomes).
- dotacao: sempre deve ser retornado como string vazia \"\". A IA NÃO deve sugerir, inferir ou inventar dotação orçamentária; esse campo será preenchido posteriormente pelo sistema ou por outro fluxo.
- objeto: redigir como cláusula formal completa (em prosa, sem lista solta, sem palavra isolada).
  - Preferencialmente iniciar com fórmula formal, como: "O objeto do presente Termo de Referência é ", "O presente Termo de Referência tem por objeto " ou "O objeto deste Termo de Referência consiste em ".
  - O texto deve descrever o que será contratado, para quem e com qual finalidade administrativa, com extensão adequada ao caso (em geral 2 a 5 frases).
  - Evite respostas curtas demais; priorize redação objetiva, técnica e suficientemente detalhada.
  - NÃO faça isto no campo objeto:
    * Copiar ou colar o texto do pedido do usuário (ex.: se o usuário escrever "Aquisição de 10 pneus 1000R20, 10 câmaras...", o objeto NÃO pode ser esse texto repetido; você DEVE reformular em cláusula contínua).
    * Devolver uma única palavra ou duas palavras (ex.: "pneus", "material de construção", "equipamentos", "material de escritório"). Qualquer resposta com menos de 4 palavras ou menos de 40 caracteres no objeto é INVÁLIDA.
    * Devolver uma lista solta (ex.: "10 pneus, 10 câmaras, 50 válvulas"). O objeto deve ser redação em prosa, não enumeração.
  - A partir do pedido do usuário, interprete o que foi solicitado e redija uma cláusula de objeto em terceira pessoa, em prosa e com linguagem formal.
  - Deve incluir: (a) o que será contratado (bens/serviços), em linguagem de cláusula; (b) a finalidade ou o setor/órgão beneficiado quando informado no pedido.
  - É EXPRESSAMENTE PROIBIDO devolver o objeto como expressão curta ou genérica ("materiais de limpeza", "material de escritório", "serviços de manutenção", "equipamentos" sozinhos). Sempre desenvolva em pelo menos uma frase completa com verbo e finalidade.
  - OBJETO = DESCRIÇÃO PURA EM PROSA. NUNCA use "compreendendo os itens descritos abaixo", "conforme itens abaixo", "especificações a seguir", "conforme tabela", "conforme quantitativo" ou equivalentes.
  - NÃO use reticências ("...") nem múltiplos pontos no final.
- justificativa: parágrafo de justificativa técnica/administrativa para a contratação, em linguagem formal. - Deve ser um texto dissertativo-argumentativo extenso, completo e técnico. Não deve ser uma frase curta e simplificada.
  - Deve ser um parágrafo de justificativa técnica/administrativa mais rico (idealmente 3 a 6 frases), em linguagem formal, explicando:
    * por que a contratação é necessária para a Administração,
    * quais riscos existem se a contratação não for realizada (ex.: prejuízo à continuidade dos serviços, impacto no atendimento ao público),
    * como a contratação se relaciona com as competências do órgão e com a melhoria da eficiência/regularidade dos serviços.
  - NÃO invente números, valores, prazos ou dados concretos que não estejam no pedido; limite-se a consequências lógicas e genéricas.
- problema_administrativo: texto técnico (2 a 4 frases) descrevendo o problema atual da Administração que a contratação pretende resolver, com foco em dor operacional/risco de continuidade/impacto no atendimento.
- beneficio_esperado: texto técnico (2 a 4 frases) descrevendo os resultados esperados da contratação (eficiência, continuidade, qualidade, redução de riscos e melhoria do serviço público).
- Se o usuário informar itens (descrição, unidade, quantidade), use-os no array itens; senão sugira itens coerentes com o objeto.
- Cada produto ou serviço diferente mencionado pelo usuário deve virar um item separado no array "itens" (não agrupe vários produtos na mesma "descricao").
- Use Lei 14.133/2021. Não invente dados que não possam ser inferidos do pedido (ex.: fiscal deixe vazio se não informado; dotação sempre deixe vazia, pois não é responsabilidade da IA preencher).
"""


def _format_user_context_for_tr_prompt(user_context: Optional[Dict[str, Any]]) -> str:
    """Formata contexto do usuário logado (Django) para inclusão no prompt do TR."""
    if not user_context or not isinstance(user_context, dict):
        return ""
    usuario = user_context.get("usuario")
    if not usuario or not isinstance(usuario, dict):
        return ""
    parts = []
    if usuario.get("nome_completo"):
        parts.append(f"Nome do solicitante/fiscal: {usuario['nome_completo']}")
    if usuario.get("secretaria"):
        parts.append(f"Secretaria: {usuario['secretaria']}")
    if usuario.get("prefeitura"):
        parts.append(f"Prefeitura: {usuario['prefeitura']}")
    if not parts:
        return ""
    return "\nContexto do solicitante (use no TR quando aplicável): " + "; ".join(parts) + "."


def _build_tr_slots_user_prompt(
    user_prompt: str,
    context_from_agent: Optional[Dict[str, Any]] = None,
    user_context: Optional[Dict[str, Any]] = None,
    skip_context_in_prompt: bool = False,
    rag_objeto_examples: Optional[str] = None,
) -> str:
    """Monta o prompt de usuário para a LLM preencher os slots do TR."""
    parts = [f"Pedido do usuário:\n{user_prompt}"]
    if context_from_agent:
        ctx = context_from_agent.get("context") or {}
        esp = context_from_agent.get("especificacoes")
        if ctx:
            # Não incluir objeto= no prompt: evita que a LLM copie o pedido ou o objeto bruto do llm_agent como redação final
            parts.append(f"\nContexto extraído: órgão={ctx.get('orgao', '')}, modalidade={ctx.get('modalidade', '')}.")
        if esp:
            listas = (esp.get("listas") or {}) if isinstance(esp, dict) else {}
            tabelas = (esp.get("tabelas") or {}) if isinstance(esp, dict) else {}
            if listas or tabelas:
                parts.append(f"\nEspecificações: listas={listas}, tabelas={tabelas}.")
    if not skip_context_in_prompt:
        parts.append(_format_user_context_for_tr_prompt(user_context))
    if rag_objeto_examples:
        parts.append(
            "\nExemplos de redação de OBJETO (documentos reais, preferencialmente Termos de Referência e estudos extraídos de contratações cadastradas no PNCP – use como referência de extensão e estilo; o campo objeto do JSON deve ter esse nível de desenvolvimento em termos de tamanho, formalidade e completude):\n"
            + rag_objeto_examples
        )
        parts.append(
            "\nAo preencher o campo \"objeto\" do JSON, SIGA o mesmo nível de detalhamento, formalidade e extensão destes exemplos. "
            "NÃO resuma o objeto em uma frase curta ou genérica; desenvolva em cláusula contínua completa."
        )
    parts.append(
        "\nPreencha o JSON de slots do Termo de Referência (objeto, dispensa, itens, justificativa, problema_administrativo, beneficio_esperado, fiscal, dotacao). Saída: apenas o JSON."
    )
    return "\n".join(parts)


def _parse_llm_json_response(text: str) -> Dict[str, Any]:
    """Extrai JSON da resposta da LLM (pode vir com markdown ou texto antes/depois)."""
    text = (text or "").strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if m:
        raw = m.group(1).strip()
    else:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            raw = text[start:end]
        else:
            raw = text
    return json.loads(raw)


async def _choose_art75_inciso(objeto: str, itens: List[ItemSlot]) -> str:
    """
    Chama a LLM especificamente para escolher o inciso do art. 75
    que melhor se aplica ao objeto (e, opcionalmente, aos itens).
    """
    objeto = (objeto or "").strip()
    itens_desc = [i.descricao for i in itens if getattr(i, "descricao", None)]
    itens_text = "; ".join(itens_desc)

    system_prompt = """
Você é um assistente jurídico especializado na Lei 14.133/2021.

Sua tarefa é analisar o objeto de uma contratação (e, quando houver, a descrição resumida dos itens)
e escolher QUAL inciso do art. 75 (dispensa de licitação) se aplica com mais precisão ao caso.

Considere APENAS os incisos I a XV do art. 75, com as seguintes ideias centrais:
- I: obras/serviços de engenharia ou manutenção de veículos até o limite legal.
- II: outros serviços ou compras em geral até o limite legal, quando NÃO houver enquadramento mais específico em outro inciso (III a XV). Use II apenas como categoria residual para compras/serviços comuns por valor.
- III: repetição de contratação com mesmas condições de edital recente sem interessados/propostas válidas ou com preços inadequados (o objeto deve mencionar edital anterior, fracasso/deserto ou preços incompatíveis).
- IV: hipóteses específicas (garantia/exclusividade de fornecedor, contratos entre entes públicos criados para fim específico, P&D até limite, transferência de tecnologia ICT, gêneros perecíveis, alta complexidade/defesa, padronização de material militar).
- V: serviços para viabilizar acordo internacional aprovado pelo Congresso, vantajosos para o Poder Público (menciona acordo internacional, tratado, cooperação internacional).
- VI: manutenção de equipamentos com assistência técnica exclusiva, acima do limite do inciso I (enfatiza exclusividade de assistência técnica do fabricante).
- VII: instituições de pesquisa/ensino/desenvolvimento institucional ou de recuperação de presos, sem fins lucrativos e com reputação ilibada.
- VIII: emergência ou calamidade pública, para bens/serviços estritamente necessários, no prazo máximo de 1 ano (objeto menciona emergência, calamidade, urgência na continuidade de serviço público).
- IX: aquisição ou locação de imóvel com características que tornem necessária sua escolha (objeto menciona imóvel específico, localização/instalações determinantes).
- X: insumos estratégicos para saúde produzidos/prestados por entidade pública criada para esse fim, com preço de mercado.
- XI: associações de catadores de recicláveis, sem fins lucrativos, formadas por pessoas de baixa renda (objeto ligado a coleta/triagem/comercialização de recicláveis por associação de catadores).
- XII: profissionais de notória especialização para comissão de avaliação de critérios de técnica.
- XIII: empresas que cumprem reserva legal de cargos para pessoas com deficiência ou reabilitados e requisitos de acessibilidade (objeto deve mencionar essas exigências como condição relevante).
- XIV: organizações sociais para atividades previstas em contrato de gestão (por exemplo, gestão compartilhada de unidade hospitalar municipal por organização social qualificada, com base em contrato de gestão).
- XV: instituições sem fins lucrativos certificadas como entidades beneficentes de assistência social, para serviços de assistência social (objeto deve indicar essa certificação/beneficência).

REGRAS DE SAÍDA:
- Responda APENAS com um JSON no formato {"inciso": "I"}.
- O valor deve ser um ÚNICO algarismo romano entre "I" e "XV".
- Você DEVE testar primeiro se o objeto se enquadra claramente em algum inciso específico (III a XV). Só use o inciso II quando NÃO houver correspondência clara com nenhum inciso específico e o objeto for compra/serviço comum por valor.
- Sempre que o objeto mencionar organização social qualificada, contrato de gestão e gestão de unidade ou serviço público (especialmente unidade hospitalar), você deve, como regra, escolher o inciso XIV, e não o inciso II.
- NUNCA devolva valor vazio; escolha sempre o inciso mais adequado entre I e XV.
"""

    user_parts = [f"Objeto: {objeto or '[não informado]'}"]
    if itens_text:
        user_parts.append(f"Itens (resumo): {itens_text}")
    user_prompt = "\n".join(user_parts)

    full_prompt = f"<<SYSTEM>>\n{system_prompt.strip()}\n\n<<USER>>\n{user_prompt}"

    url = f"{LLM_ORCHESTRATION_BASE_URL}{LLM_ORCHESTRATION_GENERATE_PATH}"
    payload = {"prompt": full_prompt, "stream": False}

    try:
        async with httpx.AsyncClient(timeout=RAG_HTTP_TIMEOUT) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            body = resp.json()
    except Exception:
        return ""

    text = body.get("data", body) if isinstance(body, dict) else body
    if isinstance(text, dict):
        raw_json = text
    else:
        try:
            raw_json = _parse_llm_json_response(str(text))
        except Exception:
            return ""

    inciso_val = str(raw_json.get("inciso", "")).strip().upper()
    valid_incisos = {
        "I",
        "II",
        "III",
        "IV",
        "V",
        "VI",
        "VII",
        "VIII",
        "IX",
        "X",
        "XI",
        "XII",
        "XIII",
        "XIV",
        "XV",
    }
    return inciso_val if inciso_val in valid_incisos else ""

def _normalize_objeto(text: str) -> str:
    """
    Normaliza o campo objeto para ficar mais formal e sem pontuação estranha no final.
    - Remove espaços extras.
    - Remove reticências ou múltiplos pontos/pontuação forte no final.
    - Remove citações que remetem a itens/tabela abaixo (descrição pura apenas).
    """
    text = (text or "").strip()
    if not text:
        return ""

    # Remove frases que remetem a itens/tabela/especificações abaixo (objeto = apenas descrição pura)
    objeto_remover = [
        r",?\s*compreendendo\s+os\s+itens\s+descritos\s+abaixo\.?",
        r",?\s*compreendendo\s+os\s+itens\s+relacionados\s+abaixo\.?",
        r",?\s*conforme\s+itens\s+(descritos\s+)?abaixo\.?",
        r",?\s*conforme\s+especificações\s+(a\s+seguir|abaixo)\.?",
        r",?\s*conforme\s+tabela\s+(a\s+seguir|abaixo|em\s+anexo)\.?",
        r",?\s*conforme\s+quantitativo\s+(a\s+seguir|abaixo)\.?",
        r",?\s*conforme\s+detalhamento\s+(na\s+tabela|abaixo)\.?",
        r",?\s*conforme\s+o\s+quantitativo\s+descrito\s+abaixo\.?",
        r",?\s*detalhados\s+(na\s+tabela|nos\s+itens)\s+abaixo\.?",
        r",?\s*especificados\s+(na\s+tabela|nos\s+itens)\s+abaixo\.?",
    ]
    for pat in objeto_remover:
        text = re.sub(pat, "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s{2,}", " ", text).strip()

    # Heurística extra: evitar objetos extremamente genéricos de 1–3 palavras,
    # como "materiais de limpeza" ou "material de escritório". Nestes casos,
    # expande para uma frase completa padrão, mais adequada ao TR.
    base = re.sub(r"[.。…;:,]+$", "", text).strip()
    if base:
        lower = base.lower()
        generic_terms = {
            "materiais de limpeza",
            "material de limpeza",
            "serviços de limpeza",
            "servico de limpeza",
            "material de escritório",
            "materiais de escritório",
            "material de expediente",
            "materiais de expediente",
        }
        words = lower.split()

        # Caso especial: frases do tipo
        # "O objeto do presente Termo de Referência é serviços de limpeza."
        # ou equivalentes, onde o complemento após "é" é curto e genérico.
        m = re.search(
            r"^o objeto do presente termo de referência é\s+(.*)$",
            lower,
            flags=re.IGNORECASE,
        )
        complemento = None
        comp_words: List[str] = []
        if m:
            complemento = m.group(1).strip()
            complemento = re.sub(r"[.。…;:,]+$", "", complemento).strip()
            comp_words = complemento.split()

        def _clean_head(s: str) -> str:
            s = s.strip()
            # Remove cabeçalhos redundantes como "a contratação de", "contratação de", "elaborar termo de referência para"
            patterns = [
                r"^a\s+contratação\s+de\s+",
                r"^contratação\s+de\s+",
                r"^contratacao\s+de\s+",
                r"^elaborar\s+termo\s+de\s+referência\s+para\s+",
                r"^elaborar\s+termo\s+de\s+referencia\s+para\s+",
                r"^elaborar\s+",
            ]
            for pat in patterns:
                s = re.sub(pat, "", s, flags=re.IGNORECASE)
            return s.strip()

        base_for_clause = base
        use_template = False

        # Dispara template se:
        # - o texto inteiro é muito curto/genérico; OU
        # - o complemento após "é" for curto/genérico.
        if lower in generic_terms or len(words) <= 3:
            base_for_clause = _clean_head(base)
            use_template = True
        elif complemento and (complemento in generic_terms or len(comp_words) <= 3):
            base_for_clause = _clean_head(complemento)
            use_template = True

        if use_template and base_for_clause:
            text = (
                f"O objeto do presente Termo de Referência é a contratação de {base_for_clause} "
                "para atender às necessidades da Administração Pública, garantindo a adequada "
                "prestação dos serviços e o atendimento ao interesse público."
            )

    # Remove reticências/múltiplos pontos e outros sinais fortes no final
    text = re.sub(r"[.。…;:,]+$", "", text).strip()
    if not text:
        return ""
    return text


def _expand_objeto_if_too_short(text: str) -> str:
    """
    Expande objetos muito curtos/simples para um nível mínimo de formalidade
    esperado em TR, sem depender de nova chamada de LLM.
    """
    t = (text or "").strip()
    if not t:
        return t

    words = t.split()
    if len(words) >= 16 and len(t) >= 120:
        return t

    base = re.sub(r"^[Oo]\s+objeto\s+do\s+presente\s+Termo\s+de\s+Refer[êe]ncia\s+[ée]\s+", "", t).strip()
    base = re.sub(r"[.。…;:,]+$", "", base).strip()
    if not base:
        base = t

    return (
        f"O objeto do presente Termo de Referência é a contratação de {base}, "
        "com observância dos requisitos técnicos e operacionais aplicáveis, "
        "de modo a atender às necessidades da Administração Pública com regularidade e eficiência."
    )


def _dict_to_tr_slots(data: Dict[str, Any]) -> TRTemplateSlots:
    """Converte o dicionário retornado pela LLM em TRTemplateSlots."""
    disp = data.get("dispensa") or {}
    if isinstance(disp, dict):
        # Artigo/inciso:
        # - artigo: neste contexto, é SEMPRE o art. 75 (texto fixo do modelo);
        #   mesmo que a IA devolva outra coisa, forçamos "75".
        # - inciso: será escolhido 100% pela etapa dedicada _choose_art75_inciso;
        #   aqui apenas inicializamos vazio.
        artigo_clean = "75"
        inciso_clean = ""
        dispensa = DispensaSlots(artigo=artigo_clean, inciso=inciso_clean)
    else:
        dispensa = DispensaSlots()

    itens: List[ItemSlot] = []
    for elem in data.get("itens") or []:
        if isinstance(elem, dict):
            itens.append(
                ItemSlot(
                    descricao=str(elem.get("descricao", "")).strip(),
                    unidade=str(elem.get("unidade", "")).strip(),
                    quantidade=elem.get("quantidade"),
                )
            )
        elif isinstance(elem, (list, tuple)) and len(elem) >= 3:
            itens.append(
                ItemSlot(
                    descricao=str(elem[0]).strip(),
                    unidade=str(elem[1]).strip(),
                    quantidade=elem[2],
                )
            )

    fisc = data.get("fiscal") or {}
    if isinstance(fisc, dict):
        fiscal = FiscalSlots(nome=str(fisc.get("nome", "")).strip())
    else:
        fiscal = FiscalSlots()

    # Campo dotacao NÃO deve ser preenchido pela IA: sempre vem vazio aqui.
    return TRTemplateSlots(
        objeto=_normalize_objeto(str(data.get("objeto", "")).strip()),
        dispensa=dispensa,
        itens=itens,
        justificativa=str(data.get("justificativa", "")).strip(),
        problema_administrativo=str(data.get("problema_administrativo", "")).strip(),
        beneficio_esperado=str(data.get("beneficio_esperado", "")).strip(),
        fiscal=fiscal,
        dotacao="",
        # Campos adicionais do template que não devem ser inferidos pela IA,
        # mas que podem, opcionalmente, vir do JSON (por exemplo, quando outra
        # camada montar esse JSON manualmente). Se não vierem, permanecem vazios
        # e serão preenchidos com dados do backend/contexto ou mantidos no modelo.
        secretaria_usuario=str(data.get("secretaria_usuario", "")).strip(),
        nome_usuario=str(data.get("nome_usuario", "")).strip(),
        cidade_estado=str(data.get("cidade_estado", "")).strip(),
        cidade=str(data.get("cidade", "")).strip(),
        horario_entrega=str(data.get("horario_entrega", "")).strip(),
        codigo_uf=str(data.get("codigo_uf", "")).strip(),
        endereco_entrega=str(data.get("endereco_entrega", "")).strip(),
        email_envio_propostas=str(data.get("email_envio_propostas", "")).strip(),
        data_termo=str(data.get("data_termo", "")).strip(),
        nome_assinante_termo=str(data.get("nome_assinante_termo", "")).strip(),
        cargo_assinante_termo=str(data.get("cargo_assinante_termo", "")).strip(),
        dfd_setor_requisitante=str(data.get("dfd_setor_requisitante", "")).strip(),
        dfd_numero_processo=str(data.get("dfd_numero_processo", "")).strip(),
        dfd_responsavel_demanda=str(data.get("dfd_responsavel_demanda", "")).strip(),
        dfd_email=str(data.get("dfd_email", "")).strip(),
        dfd_gestor_contratos=str(data.get("dfd_gestor_contratos", "")).strip(),
        dfd_fiscal_contratos=str(data.get("dfd_fiscal_contratos", "")).strip(),
        dfd_assinatura_cargo=str(data.get("dfd_assinatura_cargo", "")).strip(),
        dfd_assinatura_nome=str(data.get("dfd_assinatura_nome", "")).strip(),
        dfd_data=str(data.get("dfd_data", "")).strip(),
    )


def _merge_slots(llm_slots: TRTemplateSlots, override: Dict[str, Any]) -> TRTemplateSlots:
    """
    Mescla slots vindos da IA com override enviado pelo usuário.
    O override tem prioridade: se uma chave estiver presente e não vazia, usa ela.
    """
    if not override:
        return llm_slots

    objeto = (override.get("objeto") or llm_slots.objeto) if override.get("objeto") is not None else llm_slots.objeto
    justificativa = (override.get("justificativa") or llm_slots.justificativa) if override.get("justificativa") is not None else llm_slots.justificativa
    problema_administrativo = (
        (override.get("problema_administrativo") or llm_slots.problema_administrativo)
        if override.get("problema_administrativo") is not None
        else llm_slots.problema_administrativo
    )
    beneficio_esperado = (
        (override.get("beneficio_esperado") or llm_slots.beneficio_esperado)
        if override.get("beneficio_esperado") is not None
        else llm_slots.beneficio_esperado
    )
    dotacao = (override.get("dotacao") or llm_slots.dotacao) if override.get("dotacao") is not None else llm_slots.dotacao

    disp = override.get("dispensa")
    if isinstance(disp, dict) and (disp.get("artigo") is not None or disp.get("inciso") is not None):
        dispensa = DispensaSlots(
            artigo=str(disp.get("artigo", llm_slots.dispensa.artigo)).strip(),
            inciso=str(disp.get("inciso", llm_slots.dispensa.inciso)).strip(),
        )
    else:
        dispensa = llm_slots.dispensa

    fisc = override.get("fiscal")
    if isinstance(fisc, dict) and fisc.get("nome") is not None:
        fiscal = FiscalSlots(nome=str(fisc.get("nome", "")).strip())
    else:
        fiscal = llm_slots.fiscal

    # Campos adicionais simples (não aninhados)
    secretaria_usuario = (
        (override.get("secretaria_usuario") or llm_slots.secretaria_usuario)
        if override.get("secretaria_usuario") is not None
        else llm_slots.secretaria_usuario
    )
    nome_usuario = (
        (override.get("nome_usuario") or llm_slots.nome_usuario)
        if override.get("nome_usuario") is not None
        else llm_slots.nome_usuario
    )
    cidade_estado = (
        (override.get("cidade_estado") or llm_slots.cidade_estado)
        if override.get("cidade_estado") is not None
        else llm_slots.cidade_estado
    )
    cidade = (
        (override.get("cidade") or llm_slots.cidade)
        if override.get("cidade") is not None
        else llm_slots.cidade
    )
    horario_entrega = (
        (override.get("horario_entrega") or llm_slots.horario_entrega)
        if override.get("horario_entrega") is not None
        else llm_slots.horario_entrega
    )
    codigo_uf = (
        (override.get("codigo_uf") or llm_slots.codigo_uf)
        if override.get("codigo_uf") is not None
        else llm_slots.codigo_uf
    )
    endereco_entrega = (
        (override.get("endereco_entrega") or llm_slots.endereco_entrega)
        if override.get("endereco_entrega") is not None
        else llm_slots.endereco_entrega
    )
    email_envio_propostas = (
        (override.get("email_envio_propostas") or llm_slots.email_envio_propostas)
        if override.get("email_envio_propostas") is not None
        else llm_slots.email_envio_propostas
    )
    data_termo = (
        (override.get("data_termo") or llm_slots.data_termo)
        if override.get("data_termo") is not None
        else llm_slots.data_termo
    )
    nome_assinante_termo = (
        (override.get("nome_assinante_termo") or llm_slots.nome_assinante_termo)
        if override.get("nome_assinante_termo") is not None
        else llm_slots.nome_assinante_termo
    )
    cargo_assinante_termo = (
        (override.get("cargo_assinante_termo") or llm_slots.cargo_assinante_termo)
        if override.get("cargo_assinante_termo") is not None
        else llm_slots.cargo_assinante_termo
    )
    dfd_setor_requisitante = (
        (override.get("dfd_setor_requisitante") or llm_slots.dfd_setor_requisitante)
        if override.get("dfd_setor_requisitante") is not None
        else llm_slots.dfd_setor_requisitante
    )
    dfd_numero_processo = (
        (override.get("dfd_numero_processo") or llm_slots.dfd_numero_processo)
        if override.get("dfd_numero_processo") is not None
        else llm_slots.dfd_numero_processo
    )
    dfd_responsavel_demanda = (
        (override.get("dfd_responsavel_demanda") or llm_slots.dfd_responsavel_demanda)
        if override.get("dfd_responsavel_demanda") is not None
        else llm_slots.dfd_responsavel_demanda
    )
    dfd_email = (
        (override.get("dfd_email") or llm_slots.dfd_email)
        if override.get("dfd_email") is not None
        else llm_slots.dfd_email
    )
    dfd_gestor_contratos = (
        (override.get("dfd_gestor_contratos") or llm_slots.dfd_gestor_contratos)
        if override.get("dfd_gestor_contratos") is not None
        else llm_slots.dfd_gestor_contratos
    )
    dfd_fiscal_contratos = (
        (override.get("dfd_fiscal_contratos") or llm_slots.dfd_fiscal_contratos)
        if override.get("dfd_fiscal_contratos") is not None
        else llm_slots.dfd_fiscal_contratos
    )
    dfd_assinatura_cargo = (
        (override.get("dfd_assinatura_cargo") or llm_slots.dfd_assinatura_cargo)
        if override.get("dfd_assinatura_cargo") is not None
        else llm_slots.dfd_assinatura_cargo
    )
    dfd_assinatura_nome = (
        (override.get("dfd_assinatura_nome") or llm_slots.dfd_assinatura_nome)
        if override.get("dfd_assinatura_nome") is not None
        else llm_slots.dfd_assinatura_nome
    )
    dfd_data = (
        (override.get("dfd_data") or llm_slots.dfd_data)
        if override.get("dfd_data") is not None
        else llm_slots.dfd_data
    )

    itens_override = override.get("itens")
    if isinstance(itens_override, list) and len(itens_override) > 0:
        itens = []
        for elem in itens_override:
            if isinstance(elem, dict):
                itens.append(
                    ItemSlot(
                        descricao=str(elem.get("descricao", "")).strip(),
                        unidade=str(elem.get("unidade", "")).strip(),
                        quantidade=elem.get("quantidade"),
                    )
                )
        if itens:
            return TRTemplateSlots(
                objeto=objeto,
                dispensa=dispensa,
                itens=itens,
                justificativa=justificativa,
                problema_administrativo=problema_administrativo,
                beneficio_esperado=beneficio_esperado,
                fiscal=fiscal,
                dotacao=dotacao,
                secretaria_usuario=secretaria_usuario,
                nome_usuario=nome_usuario,
                cidade_estado=cidade_estado,
                cidade=cidade,
                horario_entrega=horario_entrega,
                codigo_uf=codigo_uf,
                endereco_entrega=endereco_entrega,
                email_envio_propostas=email_envio_propostas,
                data_termo=data_termo,
                nome_assinante_termo=nome_assinante_termo,
                cargo_assinante_termo=cargo_assinante_termo,
                dfd_setor_requisitante=dfd_setor_requisitante,
                dfd_numero_processo=dfd_numero_processo,
                dfd_responsavel_demanda=dfd_responsavel_demanda,
                dfd_email=dfd_email,
                dfd_gestor_contratos=dfd_gestor_contratos,
                dfd_fiscal_contratos=dfd_fiscal_contratos,
                dfd_assinatura_cargo=dfd_assinatura_cargo,
                dfd_assinatura_nome=dfd_assinatura_nome,
                dfd_data=dfd_data,
            )
    itens = llm_slots.itens

    return TRTemplateSlots(
        objeto=objeto,
        dispensa=dispensa,
        itens=itens,
        justificativa=justificativa,
        problema_administrativo=problema_administrativo,
        beneficio_esperado=beneficio_esperado,
        fiscal=fiscal,
        dotacao=dotacao,
        secretaria_usuario=secretaria_usuario,
        nome_usuario=nome_usuario,
        cidade_estado=cidade_estado,
        cidade=cidade,
        horario_entrega=horario_entrega,
        codigo_uf=codigo_uf,
        endereco_entrega=endereco_entrega,
        email_envio_propostas=email_envio_propostas,
        data_termo=data_termo,
        nome_assinante_termo=nome_assinante_termo,
        cargo_assinante_termo=cargo_assinante_termo,
        dfd_setor_requisitante=dfd_setor_requisitante,
        dfd_numero_processo=dfd_numero_processo,
        dfd_responsavel_demanda=dfd_responsavel_demanda,
        dfd_email=dfd_email,
        dfd_gestor_contratos=dfd_gestor_contratos,
        dfd_fiscal_contratos=dfd_fiscal_contratos,
        dfd_assinatura_cargo=dfd_assinatura_cargo,
        dfd_assinatura_nome=dfd_assinatura_nome,
        dfd_data=dfd_data,
    )


async def fetch_context_from_agent(user_prompt: str) -> Optional[Dict[str, Any]]:
    """Chama o llm_agent structure-from-prompt para obter context e especificacoes."""
    url = f"{LLM_AGENT_BASE_URL}/api/agent/structure-from-prompt"
    payload = {"user_prompt": user_prompt}
    try:
        async with httpx.AsyncClient(timeout=RAG_HTTP_TIMEOUT) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
        if data.get("ok") and (data.get("structure") or data.get("context") or data.get("especificacoes")):
            return data
    except Exception:
        pass
    return None


async def fill_tr_slots_with_llm(
    user_prompt: str,
    slots_override: Optional[Dict[str, Any]] = None,
    user_context: Optional[Dict[str, Any]] = None,
    skip_context_in_prompt: bool = False,
) -> TRTemplateSlots:
    """
    Preenche os slots do TR usando IA.

    - Chama o llm_agent (structure-from-prompt) para obter contexto e especificações.
    - Chama a LLM para gerar o JSON de slots (objeto, dispensa, itens, justificativa, fiscal, dotacao).
    - Mescla com slots_override (valores enviados pelo usuário têm prioridade). user_context (Django) enriquece o prompt com nome/secretaria/prefeitura, a menos que skip_context_in_prompt=True.
    """
    context_from_agent = await fetch_context_from_agent(user_prompt)

    # Busca exemplos RAG de cláusulas de objeto (como no fluxo generate_full_document) para enriquecer o prompt.
    # Estratégia: priorizar exemplos oriundos do PNCP (fonte="pncp") e, se necessário,
    # complementar com outros TR já ingeridos.
    rag_objeto_examples = ""
    try:
        query_objeto = f"{user_prompt[:200]} cláusula objeto termo de referência"
        # 1) PNCP primeiro
        docs = retrieve(
            query=query_objeto,
            collection_name=CHROMA_COLLECTION,
            top_k=3,
            where={"document_type": "termo_referencia", "fonte": "pncp"},
        )
        # 2) Complementa com outros TR (sem restringir fonte) se necessário
        if len(docs) < 3:
            remaining = 3 - len(docs)
            extra = retrieve(
                query=query_objeto,
                collection_name=CHROMA_COLLECTION,
                top_k=remaining,
                where={"document_type": "termo_referencia"},
            )
            if extra:
                docs.extend(extra)
        # 3) Fallback geral se absolutamente nada vier
        if not docs:
            docs = retrieve(
                query=query_objeto,
                collection_name=CHROMA_COLLECTION,
                top_k=2,
            )
        if docs:
            rag_objeto_examples = "\n\n---\n\n".join(
                (d.get("content", "") or "")[:1800] for d in docs
            )
    except Exception:
        pass

    user_prompt_text = _build_tr_slots_user_prompt(
        user_prompt, context_from_agent, user_context, skip_context_in_prompt, rag_objeto_examples or None
    )
    full_prompt = f"<<SYSTEM>>\n{TR_SLOTS_SYSTEM_PROMPT.strip()}\n\n<<USER>>\n{user_prompt_text}"

    url = f"{LLM_ORCHESTRATION_BASE_URL}{LLM_ORCHESTRATION_GENERATE_PATH}"
    payload = {"prompt": full_prompt, "stream": False}

    try:
        async with httpx.AsyncClient(timeout=RAG_HTTP_TIMEOUT) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 404:
                raise ValueError(
                    "Orquestração LLM retornou 404 (modelo não encontrado no Ollama). "
                    "No host do Ollama execute: ollama pull <modelo> (ex.: ollama pull llama3.2)."
                )
            resp.raise_for_status()
            body = resp.json()
    except httpx.ConnectError as e:
        raise ValueError(
            f"Não foi possível conectar à orquestração LLM ({url}). "
            "Verifique se llm_api está em execução (docker compose up -d llm_api ollama)."
        ) from e

    if isinstance(body, dict) and body.get("detail"):
        detail = str(body["detail"]).strip()
        if any(kw in detail.lower() for kw in ("falha", "erro", "timeout", "error", "404", "modelo")):
            raise ValueError(f"Orquestração LLM retornou erro: {detail}")

    data = body.get("data", body) if isinstance(body, dict) else {}
    text = data.get("response", data.get("text", ""))
    raw = (text or "").strip()
    if not raw:
        raise ValueError("Resposta da LLM vazia para preenchimento dos slots do TR.")

    parsed = _parse_llm_json_response(raw)
    llm_slots = _dict_to_tr_slots(parsed)

    # Se o objeto vier vazio ou praticamente sem conteúdo (ex.: só um "."),
    # tenta recuperar um objeto útil a partir do interpretador (context_from_agent)
    # ou, em último caso, do próprio user_prompt.
    objeto_fallback = ""
    if isinstance(context_from_agent, dict):
        ctx = context_from_agent.get("context") or {}
        if isinstance(ctx, dict):
            objeto_ctx = str(ctx.get("objeto") or "").strip()
            if objeto_ctx:
                objeto_fallback = objeto_ctx
    if not objeto_fallback:
        # Usa o próprio user_prompt como fallback bruto (limitado em tamanho)
        objeto_fallback = user_prompt.strip()[:400]

    def _is_trivial(text: str) -> bool:
        """
        Determina se o objeto vindo da LLM é claramente insuficiente
        (muito curto ou praticamente vazio) a ponto de exigir fallback.
        """
        if not text:
            return True
        stripped = text.strip().strip(".;,")
        # Considera trivial apenas textos extremamente curtos (1–2 palavras muito pequenas),
        # evitando acionar o fallback quando a LLM já produziu uma cláusula razoável.
        if len(stripped) < 15:
            return True
        words = stripped.split()
        return len(words) <= 3

    if _is_trivial(llm_slots.objeto) and objeto_fallback:
        # Nunca colar o prompt cru no objeto: formatar como cláusula formal
        if objeto_fallback.strip().lower().startswith(("o objeto", "o presente termo", "a aquisição", "a contratação")):
            llm_slots.objeto = _normalize_objeto(objeto_fallback) or objeto_fallback
        else:
            llm_slots.objeto = _normalize_objeto(
                f"O objeto do presente Termo de Referência é {objeto_fallback.strip().rstrip('.;')}."
            ) or objeto_fallback

    # Reforço final: evita objeto curto/simples mesmo quando não é "trivial"
    llm_slots.objeto = _expand_objeto_if_too_short(_normalize_objeto(llm_slots.objeto))

    # Campos adicionais do TR: se a LLM não retornar textos dedicados,
    # usa a justificativa como fallback para não deixar placeholder vazio.
    if not (llm_slots.problema_administrativo or "").strip():
        llm_slots.problema_administrativo = (llm_slots.justificativa or "").strip()
    if not (llm_slots.beneficio_esperado or "").strip():
        llm_slots.beneficio_esperado = (llm_slots.justificativa or "").strip()

    # Escolha do inciso do art. 75:
    # - SEMPRE delegada à LLM especializada em _choose_art75_inciso,
    #   usando o texto de objeto (já normalizado/fallback) e os itens.
    # - O JSON de slots inicial NÃO define mais o inciso; ele é apenas artigo=75, inciso="" aqui.
    try:
        chosen_inciso = await _choose_art75_inciso(llm_slots.objeto, llm_slots.itens)
    except Exception:
        chosen_inciso = ""

    if not chosen_inciso:
        # Se, mesmo após a etapa dedicada, a LLM não devolver um inciso válido,
        # usamos um fallback mínimo baseado no próprio texto do objeto/itens.
        base_text = (llm_slots.objeto or "").lower()
        for it in llm_slots.itens:
            desc = getattr(it, "descricao", "")
            if desc:
                base_text += " " + str(desc).lower()

        emergencia_keywords = (
            "emergência",
            "emergencia",
            "calamidade",
            "situação emergencial",
            "situacao emergencial",
            "urgência",
            "urgencia",
        )
        engenharia_keywords = (
            "obra",
            "obras",
            "engenharia",
            "pavimentação",
            "pavimentacao",
            "asfalto",
            "reforma",
            "construção",
            "construcao",
            "manutenção de veículos",
            "manutencao de veiculos",
            "veículo",
            "veiculo",
            "frota",
        )

        if any(k in base_text for k in emergencia_keywords):
            chosen_inciso = "VIII"
        elif any(k in base_text for k in engenharia_keywords):
            chosen_inciso = "I"
        else:
            # Caso padrão: dispensa por valor para outros serviços/compras
            chosen_inciso = "II"

    llm_slots.dispensa.inciso = chosen_inciso

    return _merge_slots(llm_slots, slots_override or {})
