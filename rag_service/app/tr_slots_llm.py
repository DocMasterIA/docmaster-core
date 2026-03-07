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
    LLM_AGENT_BASE_URL,
    LLM_ORCHESTRATION_BASE_URL,
    LLM_ORCHESTRATION_GENERATE_PATH,
    RAG_HTTP_TIMEOUT,
)
from .tr_template import (
    TRTemplateSlots,
    DispensaSlots,
    FiscalSlots,
    ItemSlot,
)


TR_SLOTS_SYSTEM_PROMPT = """Você preenche os campos (slots) de um Termo de Referência com base no pedido do usuário e no contexto.

REGRAS:
- Responda APENAS com um JSON válido, sem texto antes ou depois.
- O JSON deve ter pelo menos estas chaves: objeto, dispensa, itens, justificativa, fiscal, dotacao.
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
- objeto: campo OBRIGATORIAMENTE redigido como UMA CLÁUSULA FORMAL COMPLETA (nunca lista, nunca palavra solta, nunca cópia do pedido).
  - REGRA INEGOCIÁVEL: o valor do campo "objeto" DEVE começar com uma das fórmulas: "O objeto do presente Termo de Referência é ", "O presente Termo de Referência tem por objeto " ou "O objeto deste Termo de Referência consiste em ", seguida de uma ou mais frases que DESCREVAM em prosa (não em lista) o que será contratado e a finalidade. O texto total do objeto deve ter no mínimo 80 caracteres e pelo menos duas orações (duas frases ou uma frase com pelo menos uma vírgula e continuação).
  - PROIBIÇÃO ABSOLUTA – NUNCA faça isto no campo objeto:
    * Copiar ou colar o texto do pedido do usuário (ex.: se o usuário escrever "Aquisição de 10 pneus 1000R20, 10 câmaras...", o objeto NÃO pode ser esse texto repetido; você DEVE reformular em cláusula contínua).
    * Devolver uma única palavra ou duas palavras (ex.: "pneus", "material de construção", "equipamentos", "material de escritório"). Qualquer resposta com menos de 4 palavras ou menos de 40 caracteres no objeto é INVÁLIDA.
    * Devolver uma lista solta (ex.: "10 pneus, 10 câmaras, 50 válvulas"). O objeto deve ser redação em prosa, não enumeração.
  - OBRIGATÓRIO: a partir do pedido do usuário, INTERPRETE o que foi solicitado e REDIJA uma cláusula de objeto em terceira pessoa, em prosa, com começo formal. Exemplo de formato correto: "O objeto do presente Termo de Referência é a aquisição de pneus, câmaras de ar, válvulas e protetores de câmara, nas quantidades e especificações necessárias ao departamento de Infraestrutura, para atender às necessidades de frota e manutenção veicular da Administração."
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
    parts.append("\nPreencha o JSON de slots do Termo de Referência (objeto, dispensa, itens, justificativa, fiscal, dotacao). Saída: apenas o JSON.")
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
        if lower in generic_terms or len(words) <= 3:
            text = (
                f"O objeto do presente Termo de Referência é a aquisição de {base} "
                "para atender às necessidades da Administração Pública, garantindo a adequada "
                "prestação dos serviços e o atendimento ao interesse público."
            )

    # Remove reticências/múltiplos pontos e outros sinais fortes no final
    text = re.sub(r"[.。…;:,]+$", "", text).strip()
    if not text:
        return ""
    return text


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
                fiscal=fiscal,
                dotacao=dotacao,
                secretaria_usuario=secretaria_usuario,
                nome_usuario=nome_usuario,
                cidade_estado=cidade_estado,
                cidade=cidade,
                horario_entrega=horario_entrega,
                codigo_uf=codigo_uf,
            )
    itens = llm_slots.itens

    return TRTemplateSlots(
        objeto=objeto,
        dispensa=dispensa,
        itens=itens,
        justificativa=justificativa,
        fiscal=fiscal,
        dotacao=dotacao,
        secretaria_usuario=secretaria_usuario,
        nome_usuario=nome_usuario,
        cidade_estado=cidade_estado,
        cidade=cidade,
        horario_entrega=horario_entrega,
        codigo_uf=codigo_uf,
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

    user_prompt_text = _build_tr_slots_user_prompt(user_prompt, context_from_agent, user_context, skip_context_in_prompt)
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
        if not text:
            return True
        stripped = text.strip().strip(".;,")
        return len(stripped) < 5  # ex.: ".", "..", "ok", etc.

    if _is_trivial(llm_slots.objeto) and objeto_fallback:
        # Nunca colar o prompt cru no objeto: formatar como cláusula formal
        if objeto_fallback.strip().lower().startswith(("o objeto", "o presente termo", "a aquisição", "a contratação")):
            llm_slots.objeto = _normalize_objeto(objeto_fallback) or objeto_fallback
        else:
            llm_slots.objeto = _normalize_objeto(
                f"O objeto do presente Termo de Referência é {objeto_fallback.strip().rstrip('.;')}."
            ) or objeto_fallback

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
