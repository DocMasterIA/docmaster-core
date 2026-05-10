"""
Preenchimento dos slots do TR via IA.

A partir de user_prompt (e opcionalmente contexto/slots enviados pelo usuário),
chama o llm_agent para interpretar e a LLM para preencher o JSON de slots.
Os valores enviados pelo usuário (slots_override) têm prioridade sobre a IA.
"""
from __future__ import annotations

import json
import os
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

TR_SLOTS_INCLUDE_RAG_EXAMPLES: bool = os.getenv("TR_SLOTS_INCLUDE_RAG_EXAMPLES", "0").strip() not in ("0", "false", "False", "no")
TR_SLOTS_ENABLE_OBJETO_REWRITE: bool = os.getenv("TR_SLOTS_ENABLE_OBJETO_REWRITE", "0").strip() not in ("0", "false", "False", "no")
TR_SLOTS_ENABLE_INCISO_LLM: bool = os.getenv("TR_SLOTS_ENABLE_INCISO_LLM", "0").strip() not in ("0", "false", "False", "no")


TR_SLOTS_SYSTEM_PROMPT = """Você preenche os campos (slots) de um Termo de Referência com base no pedido do usuário e no contexto.

REGRAS:
- Responda APENAS com um JSON válido, sem texto antes ou depois.
- O JSON deve ter pelo menos estas chaves: objeto, objeto_escopo, objeto_entregas, objeto_resultados, dispensa, itens, justificativa, problema_administrativo, beneficio_esperado, fiscal, dotacao.
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
- objeto: redigir como cláusula formal completa, declarativa e robusta (prosa contínua, sem lista solta).
  - Estrutura argumentativa obrigatória do objeto:
    * Núcleo material: declarar com precisão o que será adquirido/contratado (com substantivo técnico adequado ao item).
    * Delimitação funcional: explicitar a finalidade pública e o contexto administrativo de uso.
    * Fechamento normativo: concluir com referência a especificações técnicas, quantitativos e condições do Termo de Referência.
  - Modelo de qualidade esperado (referência de estilo, não template rígido):
    * "Aquisição/contratação do objeto demandado, com delimitação da finalidade administrativa e referência às especificações técnicas, quantitativos e condições estabelecidas neste Termo de Referência."
  - Regras fortes de redação:
    * Produza texto original para o caso concreto; não faça parafraseamento mecânico do pedido do usuário.
    * Evite frase curta telegráfica. O objeto deve soar como cláusula administrativa madura.
    * Use construção declarativa, com encadeamento lógico e fluidez sintática.
    * Prefira 1 período principal completo; aceite 2 períodos apenas se necessário para clareza técnica.
  - Regras de conteúdo:
    * Se houver quantidade e unidade explícitas, incorpore obrigatoriamente no objeto.
    * Sempre que natural, use "número + (extenso)" para reforçar precisão formal.
    * Em aquisição, prefira fechamento com "conforme quantidades e demais condições estabelecidas neste Termo de Referência".
    * Em contratação (qualquer natureza), prefira fechamento com "conforme requisitos técnicos e demais condições estabelecidas neste Termo de Referência".
    * Quando houver muitos itens de aquisição (lista extensa), NÃO enumerar item por item no objeto; resumir em poucos MACROGRUPOS (idealmente 3 a 5 termos), p.ex. "Aquisição de pneus, peças, insumos e acessórios automotivos", e manter o detalhamento no array "itens" (tabela). NÃO liste nominalmente cada tipo (válvulas, pastilhas, óleo 5W30 etc.). NÃO use "incluindo" seguido de quantidades/modelos; NÃO recoloque algarismos ou medidas (kg, litros, unidades) no objeto — isso fica na tabela.
    * Não mencionar preço/valor unitário/estimado, salvo se o usuário tiver informado explicitamente.
    * Não remeter a "itens abaixo", "tabela", "anexo" ou equivalentes.
  - Consistência semântica obrigatória:
    * "aquisição" = compra de bens/produtos/materiais/insumos/equipamentos.
    * "contratação" = serviços/obras/locação/manutenção/execução continuada.
    * Não misturar termos de forma incoerente ("contratação de aquisição", "aquisição de serviços").
    * Em cenário híbrido (fornecimento + instalação), declarar natureza principal e complemento sem contradição.
  - Proibições explícitas:
    * Não devolver objeto genérico ("Aquisição de pneus.", "Serviços de manutenção.", "Material de escritório.").
    * Não usar bordões vazios ("de forma eficiente", "de modo adequado") sem vínculo técnico com o objeto.
    * Não usar reticências, linguagem coloquial, metacomentários ou autoexplicações.
    * NÃO usar "Inclui:", "Compreende:", "Engloba:", "Abrangendo os seguintes itens" nem listas com traços (-), asteriscos ou numeração no campo objeto; o detalhamento nominal fica exclusivamente no array "itens".
  - Checklist obrigatório antes de finalizar o campo objeto:
    * O texto identifica claramente o item/serviço principal?
    * O texto explicita finalidade administrativa concreta?
    * Há coerência plena entre aquisição x contratação?
    * Há completude técnica mínima (sem ficar curto/telegráfico)?
    * Não há lista com marcadores (-, *, •), "Inclui:" nem itens numerados após a prosa?
    * A redação final parece cláusula de TR assinável por órgão público?
- objeto_escopo: texto complementar (1 a 2 frases) com delimitação do escopo técnico/operacional do objeto.
- objeto_entregas: texto complementar (1 a 2 frases) com principais entregas/resultados verificáveis esperados da contratação.
- objeto_resultados: texto complementar (1 a 2 frases) com impactos/resultados esperados para a Administração e usuários do serviço.
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

OBJETO_REWRITE_SYSTEM_PROMPT = """Você é redator público especializado em cláusulas de OBJETO para Termo de Referência (Lei 14.133/2021).

OBJETIVO:
Reescrever exclusivamente a cláusula de objeto com padrão técnico-jurídico elevado, redação declarativa robusta, fluidez e precisão.

SAÍDA:
- Entregar APENAS o texto final do objeto (sem JSON, sem bullets, sem observações, sem "Inclui:" ou enumeração após o parágrafo).

PADRÃO OBRIGATÓRIO DE COMPOSIÇÃO:
1) Abertura material: declarar o que será adquirido/contratado (em listas extensas de aquisição, use só macrogrupos; não detalhe cada SKU/tipo).
2) Delimitação funcional: explicitar a finalidade administrativa e o interesse público atendido.
3) Fechamento técnico: vincular o objeto às especificações técnicas, quantitativos e condições do Termo de Referência.

REGRAS DE QUALIDADE:
- O texto deve parecer cláusula pronta para documento oficial; não pode soar rascunho.
- Evitar frase telegráfica. Se necessário, ampliar com informação substantiva e útil.
- Preferir 1 período principal denso e bem articulado; admitir 2 períodos apenas quando indispensável.
- Manter coesão, regência e concordância corretas; evitar repetição de palavras e vícios de linguagem.

REGRAS DE CONTEÚDO:
- Preservar natureza semântica:
  * aquisição = bens/produtos/materiais/insumos/equipamentos;
  * contratação = serviços/obras/locação/manutenção.
- Se houver quantidade/unidade explícitas, incorporar obrigatoriamente quando o objeto for unitário ou a lista de itens for curta.
- Se o usuário informar números em algarismo, preserve os algarismos no texto final (podendo complementar com extenso entre parênteses), EXCETO quando a mensagem do usuário pedir resumo por macrogrupos ou houver lista extensa de aquisição: aí não inclua algarismos, modelos nem medidas no objeto.
- Quando for natural no contexto formal (e não for lista extensa resumida), usar número seguido do extenso entre parênteses.
- Não inventar preço, prazo, marca, secretaria, localidade ou qualquer dado ausente.

PROIBIÇÕES:
- Não usar listas com traço (-), asterisco, numeração, "Inclui:", "Compreende:", "Engloba:" nem "Abrangendo os seguintes itens"; todo item nominal vai na tabela, não no objeto.
- Não usar "conforme itens abaixo", "conforme tabela", "etc.", "entre outros", "de forma adequada" sem conteúdo técnico.
- Não devolver objeto curto vazio de conteúdo (ex.: só "Aquisição de materiais."); em lista extensa, macrogrupos como "pneus, peças, insumos e acessórios automotivos" são válidos.
- Não usar metacomentário, justificativa do modelo ou explicação do processo.
- Não inserir marcas, modelos, quantidades, unidades ou características técnicas que não estejam no pedido do usuário, no rascunho ou nos itens estruturados.

CRITÉRIO DE ACEITAÇÃO:
- O texto final deve responder, em uma leitura única:
  "o que", "em que extensão mínima", "para qual finalidade administrativa" e "sob quais balizas técnicas".
- Se houver lista extensa de itens de aquisição, o núcleo material deve ter no máximo 3 a 5 macrogrupos (ex.: pneus, peças, insumos e acessórios automotivos), sem listar cada insumo nominalmente, deixando o detalhe na tabela. Porém a cláusula NÃO pode ser telegráfica: inclua obrigatoriamente uma oração clara de finalidade administrativa (ex.: atendimento à manutenção da frota, continuidade operacional, suporte ao funcionamento dos veículos da Administração), antes do fechamento normativo. Proibido: "incluindo ... 300 unidades ...", enumeração de modelos, blocos "Inclui:" com traços e fechamento que re-lista quantitativos.
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
        "\nPreencha o JSON de slots do Termo de Referência (objeto, objeto_escopo, objeto_entregas, objeto_resultados, dispensa, itens, justificativa, problema_administrativo, beneficio_esperado, fiscal, dotacao). Saída: apenas o JSON."
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


def _parse_llm_json_response_resilient(text: str) -> Dict[str, Any]:
    """
    Parse resiliente para respostas quase-JSON da LLM.
    Tenta parse normal e, se falhar, aplica correções sintáticas comuns.
    """
    try:
        return _parse_llm_json_response(text)
    except json.JSONDecodeError:
        pass

    t = (text or "").strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", t)
    if m:
        raw = m.group(1).strip()
    else:
        start = t.find("{")
        end = t.rfind("}") + 1
        raw = t[start:end] if start >= 0 and end > start else t

    # Correções frequentes em saídas de LLM
    fixed = raw
    fixed = fixed.replace("“", '"').replace("”", '"').replace("’", "'")
    fixed = re.sub(r",\s*([}\]])", r"\1", fixed)  # vírgula sobrando antes de fechar objeto/lista
    fixed = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", fixed)  # controles inválidos

    return json.loads(fixed)


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


async def _rewrite_objeto_clause(
    user_prompt: str,
    draft_objeto: str,
    itens: List[ItemSlot],
    max_items: int = 5,
) -> str:
    """Reescreve a cláusula de objeto em chamada dedicada, curta e focada."""
    itens_lines: List[str] = []
    for it in itens[: max(1, max_items)]:
        desc = (getattr(it, "descricao", "") or "").strip()
        un = (getattr(it, "unidade", "") or "").strip()
        qtd = getattr(it, "quantidade", None)
        if desc:
            itens_lines.append(f"- descricao={desc}; unidade={un or '-'}; quantidade={qtd if qtd is not None else '-'}")

    user_parts = [
        f"Pedido do usuário: {user_prompt.strip()}",
        f"Rascunho atual do objeto: {draft_objeto.strip() or '[vazio]'}",
    ]
    if itens_lines:
        user_parts.append("Itens estruturados:\n" + "\n".join(itens_lines))

    full_prompt = f"<<SYSTEM>>\n{OBJETO_REWRITE_SYSTEM_PROMPT.strip()}\n\n<<USER>>\n" + "\n".join(user_parts)
    url = f"{LLM_ORCHESTRATION_BASE_URL}{LLM_ORCHESTRATION_GENERATE_PATH}"
    payload = {"prompt": full_prompt, "stream": False}

    try:
        async with httpx.AsyncClient(timeout=RAG_HTTP_TIMEOUT) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            body = resp.json()
    except Exception:
        return draft_objeto

    data = body.get("data", body) if isinstance(body, dict) else {}
    text = data.get("response", data.get("text", "")) if isinstance(data, dict) else str(data)
    rewritten = (text or "").strip()
    if not rewritten:
        return draft_objeto
    rewritten = rewritten.strip().strip('"').strip("'")
    return rewritten or draft_objeto


def _looks_like_item_by_item_enumeration(text: str) -> bool:
    """Detecta objeto que ainda enumera quantidades/modelos (detalhe que deve ir só na tabela)."""
    raw = (text or "").strip()
    if not raw:
        return False
    t = raw.lower()
    # Introduz colagem típica do modelo: "Inclui:" + bullets (detalhe só na tabela)
    if re.search(r"(?i)\b(?:inclui|compreende|engloba)\s*:", raw):
        return True
    if re.search(r"(?i)\babrangendo\s+os\s+seguintes(?:\s+itens)?\b", raw):
        return True
    if re.search(r"(?m)^\s*[-*•]\s+\S", raw):
        return True
    if re.search(r"(?m)^\s*\d+[\.)]\s+\S", raw):
        return True
    # "incluindo 300 unidades..." ou similar
    if re.search(r"\bincluindo\b", t) and re.search(r"\b\d{2,6}\b", t):
        return True
    # Várias ocorrências de quantidade + unidade de medida
    qty_unit_hits = len(
        re.findall(
            r"\b\d{1,6}\s*(?:unidades?|kg|litros?|m[lL]\b|gal[õo]es?|cx|caixas?)\b",
            t,
        )
    )
    if qty_unit_hits >= 2:
        return True
    # Muitos algarismos isolados = lista de quantitativos no texto
    if len(re.findall(r"\b\d{2,6}\b", t)) >= 4:
        return True
    enum_markers = 0
    if len(re.findall(r"\b\d{1,6}\b", t)) >= 3:
        enum_markers += 1
    if len(re.findall(r"\bmodelo\s*[a-z0-9.-]+", t)) >= 2:
        enum_markers += 1
    if len(re.findall(r"(?:^|[^\w])(?:aro\s*)?r\d{1,2}(?:[.,]\d)?\b", t)) >= 2:
        enum_markers += 1
    if t.count(",") >= 4 and re.search(r"\b\d{2,6}\b", t):
        enum_markers += 1
    return enum_markers >= 2


def _needs_ultra_macro_objeto_summary(text: str) -> bool:
    """Núcleo após 'Aquisição de' ainda lista dezenas de tipos; pedir compressão para macrogrupos."""
    t = (text or "").strip()
    if not t:
        return False
    first = re.split(r"(?<=[.!?])\s+", t, maxsplit=1)[0]
    m = re.search(r"(?i)^aquisi(?:c|ç)[aã]o\s+de\s+(.+)$", first.strip())
    if not m:
        return False
    nucleus = m.group(1).strip()
    if nucleus.count(",") >= 3:
        return True
    if nucleus.lower().count(" e ") >= 3:
        return True
    if len(nucleus.split()) > 35:
        return True
    return False


async def _ultra_compress_objeto_macro_groups(
    texto: str,
    itens: List[ItemSlot],
    user_prompt: str,
) -> str:
    """Força núcleo 'Aquisição de …' com poucos macrogrupos (poucas vírgulas, sem itens nominalmente)."""
    return await _rewrite_objeto_clause(
        user_prompt=(
            f"{user_prompt}\n\n"
            "O objeto abaixo ainda traz lista nominal longa após 'Aquisição de'. "
            "Redija UMA ou DUAS frases completas, com linguagem administrativa madura:\n"
            "(1) Núcleo: NO MÁXIMO 3 a 5 MACROGRUPOS (ex.: pneus, peças, insumos e acessórios automotivos). "
            "Não cite itens específicos (válvulas, pastilhas, óleo, filtro, etc.). Sem algarismos.\n"
            "(2) Finalidade: uma oração clara vinculando ao interesse público (manutenção/suporte da frota, continuidade operacional, "
            "atendimento às necessidades de manutenção da frota e de suporte operacional — ajuste ao contexto do pedido sem inventar órgão ou quantidade).\n"
            "(3) Fechamento: \"conforme quantidades e demais condições estabelecidas neste Termo de Referência\" ou equivalente formal.\n"
            "Não entregue só macrogrupos colados ao fechamento; evite texto de etiqueta.\n\n"
            f"Texto atual:\n{texto.strip()}"
        ),
        draft_objeto=texto,
        itens=itens,
        max_items=12,
    )


def _macro_objeto_telegrafico_demais(text: str) -> bool:
    """Detecta resumo só com macrogrupos + fechamento normativo, sem oração de finalidade administrativa."""
    t = (text or "").strip()
    if not t:
        return False
    low = t.lower()
    if not re.search(r"(?i)\baquisi(?:c|ç)[aã]o\s+de\s+", low):
        return False
    words = re.findall(r"\w+", t, flags=re.UNICODE)
    forte_finalidade = any(
        k in low
        for k in (
            "destinad",
            "finalidade",
            "necessidades",
            "atendimento",
            "manutenção",
            "manutencao",
            "frota",
            "operacional",
            "viatur",
            "veículos",
            "veiculos",
            "continuidade",
            "funcionamento",
        )
    )
    conector_finalidade = bool(
        re.search(
            r"(?i)\b(destinad[oa]s?|com\s+(?:o\s+)?(?:objetivo|intuito|vistas)|para\s+atender|"
            r"garantindo\s+a|visando\s+a|assegurando)\b",
            low,
        )
    )
    if len(words) < 28 and not forte_finalidade:
        return True
    if len(words) < 40 and forte_finalidade and not conector_finalidade:
        return True
    return False


async def _enrich_macro_objeto_add_finalidade(
    texto: str,
    itens: List[ItemSlot],
    user_prompt: str,
) -> str:
    """Amplia cláusula quando ficou curta demais após compressão por macrogrupos."""
    return await _rewrite_objeto_clause(
        user_prompt=(
            f"{user_prompt}\n\n"
            "O objeto abaixo está simples demais (macrogrupos colados ao fechamento normativo). "
            "Mantenha NO MÁXIMO 3 a 5 macrogrupos após 'Aquisição de', sem listar itens nem números. "
            "Insira ENTRE o núcleo e o fechamento uma oração de finalidade administrativa bem redigida "
            "(frota, manutenção veicular, continuidade operacional ou equivalente coerente com o pedido). "
            "Pode usar 2 frases curtas se fluir melhor. Preserve fechamento com "
            "\"conforme quantidades e demais condições estabelecidas neste Termo de Referência\".\n\n"
            f"Texto atual:\n{texto.strip()}"
        ),
        draft_objeto=texto,
        itens=itens,
        max_items=12,
    )


def _is_objeto_redacao_fraca(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return True
    words = re.findall(r"\w+", t, flags=re.UNICODE)
    if len(words) < 12:
        return True
    low = t.lower()
    has_finalidade = any(k in low for k in ("finalidad", "destinad", "atendimento", "necessidades"))
    return not has_finalidade


async def _summarize_objeto_many_aquisicao_items(
    objeto: str,
    itens: List[ItemSlot],
    user_prompt: str,
) -> str:
    """
    Em aquisições com lista extensa, pede à própria IA para resumir o objeto
    por macrogrupos (sem enumeração item a item), mantendo detalhes na tabela.
    """
    t = (objeto or "").strip()
    if not t or len(itens) < 6:
        return t

    low_prompt = (user_prompt or "").lower()
    low_obj = t.lower()
    is_aquisicao = bool(
        re.search(r"(?i)\baquisi(?:c|ç)[aã]o\b", low_prompt)
        or re.search(r"(?i)\baquisi(?:c|ç)[aã]o\b", low_obj)
    )
    if not is_aquisicao:
        return t

    summarized = await _rewrite_objeto_clause(
        user_prompt=(
            f"{user_prompt}\n\n"
            "Há muitos itens na aquisição. Redija cláusula com redação madura (não telegráfica):\n"
            "- Núcleo: no máximo 3 a 5 MACROGRUPOS (ex.: pneus, peças, insumos e acessórios automotivos), "
            "sem listar cada tipo nominalmente (nada de válvulas, pastilhas, óleo 5W30, etc.). "
            "Detalhe só na tabela de itens. Proibido 'Inclui:', listas com traço (-) ou numeração.\n"
            "- Inclua explicitamente finalidade administrativa (manutenção da frota, continuidade operacional ou suporte às necessidades de manutenção da Administração — conforme o pedido).\n"
            "- Feche com \"conforme quantidades e demais condições estabelecidas neste Termo de Referência\" "
            "ou \"em quantidade conforme estipulado neste Termo de Referência\"."
        ),
        draft_objeto=t,
        itens=itens,
        max_items=12,
    )

    for _ in range(2):
        if not _looks_like_item_by_item_enumeration(summarized):
            break
        summarized = await _rewrite_objeto_clause(
            user_prompt=(
                f"{user_prompt}\n\n"
                f"O texto abaixo ainda traz quantidades, modelos, lista \"incluindo ...\", 'Inclui:' ou bullets (-), proibido no objeto:\n"
                f"{summarized}\n\n"
                "Reescreva com NO MÁXIMO 3 a 5 MACROGRUPOS agregados (ex.: pneus, peças, insumos e acessórios automotivos), "
                "sem citar itens específicos nominalmente, sem algarismos, sem 'incluindo', sem 'Inclui:', sem traços de lista, sem unidades (kg, litros). "
                "Use fechamento: \"conforme quantidades e demais condições estabelecidas neste Termo de Referência\" "
                "ou \"em quantidade conforme estipulado neste Termo de Referência\"."
            ),
            draft_objeto=summarized,
            itens=itens,
            max_items=12,
        )
    if _needs_ultra_macro_objeto_summary(summarized):
        summarized = await _ultra_compress_objeto_macro_groups(summarized, itens, user_prompt)
    if _macro_objeto_telegrafico_demais(summarized):
        summarized = await _enrich_macro_objeto_add_finalidade(summarized, itens, user_prompt)
    return summarized


async def _strip_enumeration_from_summarized_objeto_if_needed(
    objeto: str,
    itens: List[ItemSlot],
    user_prompt: str,
) -> str:
    """Após outras etapas, garante que listas longas de aquisição não voltem com quantidades no texto."""
    t = (objeto or "").strip()
    if not t or len(itens) < 6:
        return t
    low_p = (user_prompt or "").lower()
    if not (
        re.search(r"(?i)\baquisi(?:c|ç)[aã]o\b", low_p) or re.search(r"(?i)\baquisi(?:c|ç)[aã]o\b", t.lower())
    ):
        return t
    if not _looks_like_item_by_item_enumeration(t):
        return t
    return await _rewrite_objeto_clause(
        user_prompt=(
            f"{user_prompt}\n\n"
            f"Corrija o objeto abaixo: ainda há listagem detalhada, quantidades/modelos, 'incluindo ...', 'Inclui:' ou bullets. "
            f"Detalhe só na tabela.\n{t}\n\n"
            "Use NO MÁXIMO 3 a 5 macrogrupos após 'Aquisição de' (ex.: pneus, peças, insumos e acessórios automotivos). "
            "Sem dígitos. Inclua uma oração de finalidade administrativa (não basta colar macrogrupos ao fechamento). "
            "Feche com \"conforme quantidades e demais condições estabelecidas neste Termo de Referência\" "
            "ou \"em quantidade conforme estipulado neste Termo de Referência\"."
        ),
        draft_objeto=t,
        itens=itens,
        max_items=12,
    )


def _numero_extenso_pt_br_ate_9999(n: int, feminino: bool = False) -> str:
    if n < 0 or n > 9999:
        return str(n)

    unidades_m = {
        0: "zero", 1: "um", 2: "dois", 3: "tres", 4: "quatro", 5: "cinco", 6: "seis", 7: "sete", 8: "oito", 9: "nove",
        10: "dez", 11: "onze", 12: "doze", 13: "treze", 14: "quatorze", 15: "quinze", 16: "dezesseis", 17: "dezessete", 18: "dezoito", 19: "dezenove",
    }
    unidades_f = dict(unidades_m)
    unidades_f[1] = "uma"
    unidades_f[2] = "duas"

    dezenas = {20: "vinte", 30: "trinta", 40: "quarenta", 50: "cinquenta", 60: "sessenta", 70: "setenta", 80: "oitenta", 90: "noventa"}
    centenas_m = {100: "cem", 200: "duzentos", 300: "trezentos", 400: "quatrocentos", 500: "quinhentos", 600: "seiscentos", 700: "setecentos", 800: "oitocentos", 900: "novecentos"}
    centenas_f = {100: "cem", 200: "duzentas", 300: "trezentas", 400: "quatrocentas", 500: "quinhentas", 600: "seiscentas", 700: "setecentas", 800: "oitocentas", 900: "novecentas"}

    u = unidades_f if feminino else unidades_m
    c_map = centenas_f if feminino else centenas_m

    if n in u:
        return u[n]
    if n in dezenas:
        return dezenas[n]
    if n in c_map:
        return c_map[n]
    if n < 100:
        d = (n // 10) * 10
        return f"{dezenas[d]} e {u[n - d]}"
    if n < 1000:
        c = (n // 100) * 100
        c_txt = "cento" if c == 100 else c_map[c]
        return f"{c_txt} e {_numero_extenso_pt_br_ate_9999(n - c, feminino=feminino)}"
    milhar = n // 1000
    resto = n % 1000
    mil_txt = "mil" if milhar == 1 else f"{_numero_extenso_pt_br_ate_9999(milhar)} mil"
    if resto == 0:
        return mil_txt
    conector = " e " if resto < 100 else " "
    return f"{mil_txt}{conector}{_numero_extenso_pt_br_ate_9999(resto, feminino=feminino)}"


def _extrair_int_positivo(value: Any) -> Optional[int]:
    if value is None:
        return None
    m = re.search(r"\d+", str(value))
    if not m:
        return None
    try:
        val = int(m.group(0))
    except Exception:
        return None
    return val if val > 0 else None


def _polish_objeto_with_itens(
    objeto: str,
    itens: List[ItemSlot],
    user_prompt: str,
    *,
    skip_item_injection: bool = False,
) -> str:
    """
    Melhora o objeto para padrão técnico quando houver aquisição com itens/quantidade.
    Não substitui indiscriminadamente: atua como lapidação de qualidade.

    skip_item_injection: fluxo «dispensa normal» (UI com tabela) — não recompõe o objeto a partir
    das linhas de itens (evita «100 (cem) Medicamento A…» na cláusula; detalhe fica na tabela do TR).
    """
    t = (objeto or "").strip()
    if not t or not itens:
        return t
    if skip_item_injection:
        return t

    low_prompt = (user_prompt or "").lower()
    is_aquisicao_early = bool(
        re.search(r"(?i)\baquisi(?:c|ç)[aã]o\b", t) or re.search(r"(?i)\baquisi(?:c|ç)[aã]o\b", low_prompt)
    )
    # Listas longas: objeto deve permanecer resumido; não recompor com quantidades item a item.
    if is_aquisicao_early and len(itens) >= 6:
        finalidade = r"destinad[oa]s?\s+ao\s+atendimento\s+das\s+necessidades\s+da\s+administra[cç][aã]o\s+p[úu]blica\s+municipal"
        t = re.sub(
            rf"(?i)\b({finalidade})\b\s*[.,;:]+\s*,?\s*\b\1\b",
            r"\1",
            t,
        )
        return re.sub(r"\s{2,}", " ", t).strip()

    first = itens[0]
    desc = str(getattr(first, "descricao", "") or "").strip()
    qtd = _extrair_int_positivo(getattr(first, "quantidade", None))
    unidade = str(getattr(first, "unidade", "") or "").strip().lower()
    if not desc or not qtd:
        return t

    low_obj = t.lower()

    # Nunca força polimento de aquisição para pedidos de contratação/serviço.
    if any(k in low_prompt for k in ("contratação", "contratacao", "serviço", "servicos", "manutenção", "manutencao")):
        return t

    is_aquisicao = bool(re.search(r"(?i)\baquisi(?:c|ç)[aã]o\b", t) or re.search(r"(?i)\baquisi(?:c|ç)[aã]o\b", low_prompt))
    if not is_aquisicao:
        return t

    feminino = unidade in {"un", "unid", "unidade", "unidades"}
    extenso = _numero_extenso_pt_br_ate_9999(qtd, feminino=feminino)
    unidade_txt = "unidades" if not unidade else (unidade if unidade != "un" else "unidades")
    bloco_qtd = f"{qtd} ({extenso}) {unidade_txt}"

    # Se pedido veio com algarismos e o objeto saiu sem algarismos,
    # recompõe aquisição com base nos itens para preservar fidelidade numérica.
    prompt_has_digits = bool(re.search(r"\b\d{1,6}\b", low_prompt))
    text_has_digits = bool(re.search(r"\b\d{1,6}\b", t))
    if prompt_has_digits and not text_has_digits and len(itens) >= 1 and len(itens) < 6:
        parts: List[str] = []
        for it in itens[:6]:
            qtd_i = _extrair_int_positivo(getattr(it, "quantidade", None))
            desc_i = str(getattr(it, "descricao", "") or "").strip()
            if not qtd_i or not desc_i:
                continue
            ext_i = _numero_extenso_pt_br_ate_9999(qtd_i, feminino=False)
            parts.append(f"{qtd_i} ({ext_i}) {desc_i}")
        if parts:
            lista = ", ".join(parts[:-1]) + (" e " + parts[-1] if len(parts) > 1 else parts[0])
            return (
                f"Aquisição de {lista}, destinados ao atendimento das necessidades da Administração Pública Municipal, "
                "conforme quantidades e demais condições estabelecidas neste Termo de Referência."
            )

    # Só lapida se o texto já guardar aderência mínima ao item (evita injetar tema errado).
    desc_tokens = [tok for tok in re.findall(r"[a-z0-9]{4,}", desc.lower())[:4]]
    if desc_tokens and not any(tok in low_obj for tok in desc_tokens):
        return t

    # Se não houver bloco numérico + extenso, reconstrói o início em padrão formal.
    if not re.search(r"\b\d{1,6}\s*\([^)]{2,}\)", t):
        t = (
            f"Aquisição de {bloco_qtd} de {desc}, destinados ao atendimento das necessidades "
            "da Administração Pública Municipal, conforme especificações técnicas, quantitativos "
            "e condições estabelecidas neste Termo de Referência."
        )
        return t

    # Se já houver número por extenso, apenas garante fechamento institucional.
    if not re.search(r"(?i)administra[cç][aã]o p[úu]blica", t):
        t = t.rstrip(".;:, ") + ", destinados ao atendimento das necessidades da Administração Pública Municipal."

    # Remove duplicação acidental da oração de finalidade quando o texto já a contém.
    finalidade = r"destinad[oa]s?\s+ao\s+atendimento\s+das\s+necessidades\s+da\s+administra[cç][aã]o\s+p[úu]blica\s+municipal"
    t = re.sub(
        rf"(?i)\b({finalidade})\b\s*[.,;:]+\s*,?\s*\b\1\b",
        r"\1",
        t,
    )
    return t


def _strip_item_lists_from_objeto_text(text: str) -> str:
    """
    Remove enumerações que o modelo às vezes cola na cláusula (ex.: "Inclui:" + itens com traço).
    O detalhamento deve permanecer apenas no array itens.
    """
    text = (text or "").strip()
    if not text:
        return ""

    m_intro = re.search(
        r"(?i)\b(?:inclui|compreende|engloba|abrangendo\s+os\s+seguintes(?:\s+itens)?)\s*:",
        text,
    )
    if m_intro:
        text = text[: m_intro.start()].rstrip()

    lines = text.splitlines()
    for i, line in enumerate(lines):
        s = line.strip()
        if re.match(r"^[-*•]\s+\S", s) or re.match(r"^\d+[\.)]\s+\S", s):
            text = "\n".join(lines[:i]).rstrip()
            break

    m_inline = re.search(r"(?<=[.!?])\s+[-*•]\s+\S", text)
    if m_inline:
        text = text[: m_inline.start()].rstrip()

    text = re.sub(r"(?i)\s*(?:inclui|compreende|engloba)\s*:\s*$", "", text).rstrip()
    return text.rstrip(",;: ")


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
    text = _strip_item_lists_from_objeto_text(text)
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
        r",?\s*no\s+valor\s+unit[áa]rio\s+compat[íi]vel\s+com\s+o\s+mercado\.?",
        r",?\s*com\s+valor\s+unit[áa]rio\s+compat[íi]vel\s+com\s+o\s+mercado\.?",
        r",?\s*com\s+pre[çc]o\s+compat[íi]vel\s+com\s+o\s+mercado\.?",
    ]
    for pat in objeto_remover:
        text = re.sub(pat, "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s{2,}", " ", text).strip()

    # Heurística extra: evitar objetos extremamente genéricos de 1–3 palavras.
    # Nestes casos, aplica uma base mínima de redação formal (sem engessar template).
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
            natureza = "Aquisição"
            if re.search(r"(?i)\b(servi[çc]o|manuten[çc][aã]o|loca[çc][aã]o|obra|engenharia)\b", base_for_clause):
                natureza = "Contratação"
            text = (
                f"{natureza} de {base_for_clause}, conforme especificações técnicas, "
                "quantitativos e demais condições estabelecidas neste Termo de Referência."
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
    # Fallback apenas para casos realmente inválidos (quase vazio/telegráfico).
    if len(words) >= 6 or len(t) >= 45:
        return t

    base = re.sub(r"^[Oo]\s+objeto\s+do\s+presente\s+Termo\s+de\s+Refer[êe]ncia\s+[ée]\s+", "", t).strip()
    base = re.sub(r"[.。…;:,]+$", "", base).strip()
    if not base:
        base = t

    # Reescrita mínima, mantendo padrão objetivo do fluxo.
    return (
        f"Aquisição de {base}, conforme especificações técnicas, quantitativos e demais "
        "condições estabelecidas neste Termo de Referência."
    )


def _enforce_objeto_semantic_consistency(text: str) -> str:
    """
    Corrige incoerências comuns no objeto:
    - mistura indevida de aquisição x contratação;
    - construções genéricas pouco conectadas ao objeto.
    """
    t = (text or "").strip()
    if not t:
        return t

    low = t.lower()
    service_hints = (
        "serviço",
        "servicos",
        "prestação",
        "prestacao",
        "manutenção",
        "manutencao",
        "execução",
        "execucao",
        "obra",
        "engenharia",
        "locação",
        "locacao",
    )
    goods_hints = (
        "aquisição",
        "aquisicao",
        "fornecimento",
        "insumo",
        "material",
        "produto",
        "equipamento",
        "medicamento",
        "seringa",
    )

    has_service_nature = any(h in low for h in service_hints)
    has_goods_nature = any(h in low for h in goods_hints)

    # Evita "contratação de aquisição de ..." (duplicidade semântica).
    t = re.sub(
        r"(?i)\bcontrata(?:ç|c)[aã]o\s+de\s+aquisi(?:ç|c)[aã]o\s+de\s+",
        "aquisição de ",
        t,
    )
    # Evita "aquisição de contratação de ..." (duplicidade semântica).
    t = re.sub(
        r"(?i)\baquisi(?:ç|c)[aã]o\s+de\s+contrata(?:ç|c)[aã]o\s+de\s+",
        "contratação de ",
        t,
    )
    # Evita "aquisição de serviços" e afins.
    t = re.sub(
        r"(?i)\baquisi(?:ç|c)[aã]o\s+de\s+servi[çc]os?\b",
        "contratação de serviços",
        t,
    )
    # Evita "contratação de materiais/produtos" quando a natureza é compra.
    t = re.sub(
        r"(?i)\bcontrata(?:ç|c)[aã]o\s+de\s+(materiais?|produtos?|insumos?|equipamentos?|medicamentos?)\b",
        r"aquisição de \1",
        t,
    )

    # Se texto mantém ambiguidade, força forma principal por heurística.
    low_after = t.lower()
    if "aquisição" in low_after and "contratação" in low_after:
        if has_service_nature and not has_goods_nature:
            t = re.sub(r"(?i)\baquisi(?:ç|c)[aã]o\s+de\s+", "contratação de ", t)
        elif has_goods_nature and not has_service_nature:
            t = re.sub(r"(?i)\bcontrata(?:ç|c)[aã]o\s+de\s+", "aquisição de ", t)

    # Fechamento por natureza (aquisição x contratação).
    is_aquisicao = bool(re.search(r"(?i)\b(aquisi(?:ç|c)[aã]o|fornecimento)\b", t)) and not has_service_nature
    if is_aquisicao:
        t = re.sub(
            r"(?i),?\s*(visando|com\s+o\s+intuito\s+de)\s+atender\s+aos?\s+requisitos?\s+t[ée]cnicos?,?\s+quantitativos?\s+e\s+(demais\s+)?condi[çc][õo]es?\s+(delineadas|estabelecidas)\s+neste\s+termo\s+de\s+refer[êe]ncia\.?",
            ", conforme quantidades e demais condições estabelecidas neste Termo de Referência",
            t,
        )
        t = re.sub(
            r"(?i),?\s*conforme\s+especifica(?:ç|c)[õo]es?\s+t[ée]cnicas?,?\s+quantitativos?\s+e\s+condi[çc][õo]es?\s+estabelecidas\s+neste\s+termo\s+de\s+refer[êe]ncia\.?",
            ", conforme quantidades e demais condições estabelecidas neste Termo de Referência",
            t,
        )
    else:
        t = re.sub(
            r"(?i),?\s*conforme\s+quantidades?\s+e\s+demais\s+condi[çc][õo]es?\s+estabelecidas\s+neste\s+termo\s+de\s+refer[êe]ncia\.?",
            ", conforme requisitos técnicos e demais condições estabelecidas neste Termo de Referência",
            t,
        )

    # Mantém liberdade de redação da IA: aqui só sanidade mínima.
    t = re.sub(r"\s{2,}", " ", t).strip()
    # Padroniza a abertura da cláusula com inicial maiúscula.
    t = re.sub(r"(?i)^aquisi(?:ç|c)[aã]o\s+de\s+", "Aquisição de ", t)
    t = re.sub(r"(?i)^contrata(?:ç|c)[aã]o\s+de\s+", "Contratação de ", t)
    t = re.sub(r"[;:,]+\s*$", "", t).strip()
    if t and not t.endswith("."):
        t = f"{t}."
    return t


def _num_pt_br_ate_9999(n: int) -> str:
    if n < 0 or n > 9999:
        return str(n)
    base = {
        0: "zero", 1: "um", 2: "dois", 3: "tres", 4: "quatro", 5: "cinco", 6: "seis", 7: "sete", 8: "oito", 9: "nove",
        10: "dez", 11: "onze", 12: "doze", 13: "treze", 14: "quatorze", 15: "quinze", 16: "dezesseis", 17: "dezessete", 18: "dezoito", 19: "dezenove",
        20: "vinte", 30: "trinta", 40: "quarenta", 50: "cinquenta", 60: "sessenta", 70: "setenta", 80: "oitenta", 90: "noventa",
        100: "cem", 200: "duzentos", 300: "trezentos", 400: "quatrocentos", 500: "quinhentos", 600: "seiscentos", 700: "setecentos", 800: "oitocentos", 900: "novecentos",
    }
    if n in base:
        return base[n]
    if n < 100:
        d = (n // 10) * 10
        return f"{base[d]} e {base[n - d]}"
    if n < 1000:
        c = (n // 100) * 100
        c_text = "cento" if c == 100 else base[c]
        return f"{c_text} e {_num_pt_br_ate_9999(n - c)}"
    m = n // 1000
    r = n % 1000
    mil = "mil" if m == 1 else f"{_num_pt_br_ate_9999(m)} mil"
    if r == 0:
        return mil
    return f"{mil}{' e ' if r < 100 else ' '}{_num_pt_br_ate_9999(r)}"


def _extract_positive_int(value: Any) -> int | None:
    if value is None:
        return None
    m = re.search(r"\d+", str(value))
    if not m:
        return None
    try:
        n = int(m.group(0))
    except Exception:
        return None
    return n if n > 0 else None


def _enrich_objeto_with_quantidade(text: str, itens: List[ItemSlot]) -> str:
    """Complementa o objeto apenas quando a IA omite quantidade explícita dos itens."""
    t = (text or "").strip()
    if not t or not itens:
        return t
    if re.search(r"\b\d{1,6}\b", t):
        return t
    it = itens[0]
    qtd = _extract_positive_int(getattr(it, "quantidade", None))
    desc = str(getattr(it, "descricao", "") or "").strip()
    if not qtd or not desc:
        return t
    extenso = _num_pt_br_ate_9999(qtd)
    bloco_qtd = f"{qtd} ({extenso}) unidades"
    # Ajuste localizado: só injeta quantitativo no trecho inicial de aquisição.
    t = re.sub(
        r"(?i)\baquisi(?:ç|c)[aã]o\s+de\s+",
        f"aquisição de {bloco_qtd} de ",
        t,
        count=1,
    )
    return t


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
                    valor_unitario=elem.get("valor_unitario", ""),
                    valor_total=elem.get("valor_total", ""),
                )
            )
        elif isinstance(elem, (list, tuple)) and len(elem) >= 3:
            itens.append(
                ItemSlot(
                    descricao=str(elem[0]).strip(),
                    unidade=str(elem[1]).strip(),
                    quantidade=elem[2],
                    valor_unitario=elem[3] if len(elem) > 3 else "",
                    valor_total=elem[4] if len(elem) > 4 else "",
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
        objeto_escopo=str(data.get("objeto_escopo", "")).strip(),
        objeto_entregas=str(data.get("objeto_entregas", "")).strip(),
        objeto_resultados=str(data.get("objeto_resultados", "")).strip(),
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
        sol_oficio_artigo_inciso=str(data.get("sol_oficio_artigo_inciso", "")).strip(),
        sol_oficio_destinatario_nome=str(data.get("sol_oficio_destinatario_nome", "")).strip(),
        sol_oficio_destinatario_cargo=str(data.get("sol_oficio_destinatario_cargo", "")).strip(),
        sol_oficio_destinatario_orgao=str(data.get("sol_oficio_destinatario_orgao", "")).strip(),
        sol_oficio_assunto=str(data.get("sol_oficio_assunto", "")).strip(),
        sol_oficio_objeto=str(data.get("sol_oficio_objeto", "")).strip(),
        sol_oficio_justificativa=str(data.get("sol_oficio_justificativa", "")).strip(),
        sol_oficio_prazo_resposta=str(data.get("sol_oficio_prazo_resposta", "")).strip(),
        sol_oficio_responsavel_nome=str(data.get("sol_oficio_responsavel_nome", "")).strip(),
        sol_oficio_responsavel_cargo=str(data.get("sol_oficio_responsavel_cargo", "")).strip(),
        sol_oficio_responsavel_setor=str(data.get("sol_oficio_responsavel_setor", "")).strip(),
        dfd_setor_requisitante=str(data.get("dfd_setor_requisitante", "")).strip(),
        dfd_numero_processo=str(data.get("dfd_numero_processo", "")).strip(),
        dfd_responsavel_demanda=str(data.get("dfd_responsavel_demanda", "")).strip(),
        dfd_email=str(data.get("dfd_email", "")).strip(),
        dfd_gestor_contratos=str(data.get("dfd_gestor_contratos", "")).strip(),
        dfd_fiscal_contratos=str(data.get("dfd_fiscal_contratos", "")).strip(),
        dfd_assinatura_cargo=str(data.get("dfd_assinatura_cargo", "")).strip(),
        dfd_assinatura_nome=str(data.get("dfd_assinatura_nome", "")).strip(),
        dfd_data=str(data.get("dfd_data", "")).strip(),
        dfd_objeto_referencia=str(data.get("dfd_objeto_referencia", "")).strip(),
        dfd_justificativa=str(data.get("dfd_justificativa", "")).strip(),
        numero_processo=str(data.get("numero_processo", "")).strip(),
        marca=str(data.get("marca", "")).strip(),
        modelo=str(data.get("modelo", "")).strip(),
        numero_placa=str(data.get("numero_placa", "")).strip(),
        orgao=str(data.get("orgao", "")).strip(),
        valor_total=str(data.get("valor_total", "")).strip(),
        fornecedor=str(data.get("fornecedor", "")).strip(),
        cnpj_fornecedor=str(data.get("cnpj_fornecedor", "")).strip(),
        ao_senhor_genero=str(data.get("ao_senhor_genero", "")).strip(),
        senhor_senhora_genero=str(data.get("senhor_senhora_genero", "")).strip(),
        objeto_especifico=str(data.get("objeto_especifico", "")).strip(),
        equipamento=str(data.get("equipamento", "")).strip(),
    )


def _merge_slots(llm_slots: TRTemplateSlots, override: Dict[str, Any]) -> TRTemplateSlots:
    """
    Mescla slots vindos da IA com override enviado pelo usuário.
    O override tem prioridade: se uma chave estiver presente e não vazia, usa ela.
    """
    if not override:
        return llm_slots

    objeto = (override.get("objeto") or llm_slots.objeto) if override.get("objeto") is not None else llm_slots.objeto
    objeto_escopo = (
        (override.get("objeto_escopo") or llm_slots.objeto_escopo)
        if override.get("objeto_escopo") is not None
        else llm_slots.objeto_escopo
    )
    objeto_entregas = (
        (override.get("objeto_entregas") or llm_slots.objeto_entregas)
        if override.get("objeto_entregas") is not None
        else llm_slots.objeto_entregas
    )
    objeto_resultados = (
        (override.get("objeto_resultados") or llm_slots.objeto_resultados)
        if override.get("objeto_resultados") is not None
        else llm_slots.objeto_resultados
    )
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
    sol_oficio_artigo_inciso = (
        (override.get("sol_oficio_artigo_inciso") or llm_slots.sol_oficio_artigo_inciso)
        if override.get("sol_oficio_artigo_inciso") is not None
        else llm_slots.sol_oficio_artigo_inciso
    )
    sol_oficio_destinatario_nome = (
        (override.get("sol_oficio_destinatario_nome") or llm_slots.sol_oficio_destinatario_nome)
        if override.get("sol_oficio_destinatario_nome") is not None
        else llm_slots.sol_oficio_destinatario_nome
    )
    sol_oficio_destinatario_cargo = (
        (override.get("sol_oficio_destinatario_cargo") or llm_slots.sol_oficio_destinatario_cargo)
        if override.get("sol_oficio_destinatario_cargo") is not None
        else llm_slots.sol_oficio_destinatario_cargo
    )
    sol_oficio_destinatario_orgao = (
        (override.get("sol_oficio_destinatario_orgao") or llm_slots.sol_oficio_destinatario_orgao)
        if override.get("sol_oficio_destinatario_orgao") is not None
        else llm_slots.sol_oficio_destinatario_orgao
    )
    sol_oficio_assunto = (
        (override.get("sol_oficio_assunto") or llm_slots.sol_oficio_assunto)
        if override.get("sol_oficio_assunto") is not None
        else llm_slots.sol_oficio_assunto
    )
    sol_oficio_objeto = (
        (override.get("sol_oficio_objeto") or llm_slots.sol_oficio_objeto)
        if override.get("sol_oficio_objeto") is not None
        else llm_slots.sol_oficio_objeto
    )
    sol_oficio_justificativa = (
        (override.get("sol_oficio_justificativa") or llm_slots.sol_oficio_justificativa)
        if override.get("sol_oficio_justificativa") is not None
        else llm_slots.sol_oficio_justificativa
    )
    sol_oficio_prazo_resposta = (
        (override.get("sol_oficio_prazo_resposta") or llm_slots.sol_oficio_prazo_resposta)
        if override.get("sol_oficio_prazo_resposta") is not None
        else llm_slots.sol_oficio_prazo_resposta
    )
    sol_oficio_responsavel_nome = (
        (override.get("sol_oficio_responsavel_nome") or llm_slots.sol_oficio_responsavel_nome)
        if override.get("sol_oficio_responsavel_nome") is not None
        else llm_slots.sol_oficio_responsavel_nome
    )
    sol_oficio_responsavel_cargo = (
        (override.get("sol_oficio_responsavel_cargo") or llm_slots.sol_oficio_responsavel_cargo)
        if override.get("sol_oficio_responsavel_cargo") is not None
        else llm_slots.sol_oficio_responsavel_cargo
    )
    sol_oficio_responsavel_setor = (
        (override.get("sol_oficio_responsavel_setor") or llm_slots.sol_oficio_responsavel_setor)
        if override.get("sol_oficio_responsavel_setor") is not None
        else llm_slots.sol_oficio_responsavel_setor
    )
    dfd_setor_requisitante = (
        (override.get("dfd_setor_requisitante") or llm_slots.dfd_setor_requisitante)
        if override.get("dfd_setor_requisitante") is not None
        else llm_slots.dfd_setor_requisitante
    )
    _dfd_np_override = override.get("dfd_numero_processo")
    if _dfd_np_override is None:
        _dfd_np_override = override.get("processo_numero")
    dfd_numero_processo = (
        (_dfd_np_override or llm_slots.dfd_numero_processo)
        if _dfd_np_override is not None
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
    _num_proc_override = override.get("numero_processo")
    if _num_proc_override is None:
        _num_proc_override = override.get("processo_numero")
    numero_processo = (
        (_num_proc_override or llm_slots.numero_processo)
        if _num_proc_override is not None
        else llm_slots.numero_processo
    )
    marca = (
        (override.get("marca") or llm_slots.marca)
        if override.get("marca") is not None
        else llm_slots.marca
    )
    modelo = (
        (override.get("modelo") or llm_slots.modelo)
        if override.get("modelo") is not None
        else llm_slots.modelo
    )
    numero_placa = (
        (override.get("numero_placa") or llm_slots.numero_placa)
        if override.get("numero_placa") is not None
        else llm_slots.numero_placa
    )
    orgao = (
        (override.get("orgao") or llm_slots.orgao)
        if override.get("orgao") is not None
        else llm_slots.orgao
    )
    valor_total = (
        (override.get("valor_total") or llm_slots.valor_total)
        if override.get("valor_total") is not None
        else llm_slots.valor_total
    )
    fornecedor = (
        (override.get("fornecedor") or llm_slots.fornecedor)
        if override.get("fornecedor") is not None
        else llm_slots.fornecedor
    )
    cnpj_fornecedor = (
        (override.get("cnpj_fornecedor") or llm_slots.cnpj_fornecedor)
        if override.get("cnpj_fornecedor") is not None
        else llm_slots.cnpj_fornecedor
    )
    ao_senhor_genero = (
        (override.get("ao_senhor_genero") or llm_slots.ao_senhor_genero)
        if override.get("ao_senhor_genero") is not None
        else llm_slots.ao_senhor_genero
    )
    senhor_senhora_genero = (
        (override.get("senhor_senhora_genero") or llm_slots.senhor_senhora_genero)
        if override.get("senhor_senhora_genero") is not None
        else llm_slots.senhor_senhora_genero
    )
    dfd_objeto_referencia = (
        (override.get("dfd_objeto_referencia") or llm_slots.dfd_objeto_referencia)
        if override.get("dfd_objeto_referencia") is not None
        else llm_slots.dfd_objeto_referencia
    )
    dfd_justificativa = (
        (override.get("dfd_justificativa") or llm_slots.dfd_justificativa)
        if override.get("dfd_justificativa") is not None
        else llm_slots.dfd_justificativa
    )
    objeto_especifico = (
        (override.get("objeto_especifico") or llm_slots.objeto_especifico)
        if override.get("objeto_especifico") is not None
        else llm_slots.objeto_especifico
    )
    equipamento = (
        (override.get("equipamento") or llm_slots.equipamento)
        if override.get("equipamento") is not None
        else llm_slots.equipamento
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
                        valor_unitario=elem.get("valor_unitario", ""),
                        valor_total=elem.get("valor_total", ""),
                    )
                )
        if itens:
            return TRTemplateSlots(
                objeto=objeto,
                objeto_escopo=objeto_escopo,
                objeto_entregas=objeto_entregas,
                objeto_resultados=objeto_resultados,
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
                sol_oficio_artigo_inciso=sol_oficio_artigo_inciso,
                sol_oficio_destinatario_nome=sol_oficio_destinatario_nome,
                sol_oficio_destinatario_cargo=sol_oficio_destinatario_cargo,
                sol_oficio_destinatario_orgao=sol_oficio_destinatario_orgao,
                sol_oficio_assunto=sol_oficio_assunto,
                sol_oficio_objeto=sol_oficio_objeto,
                sol_oficio_justificativa=sol_oficio_justificativa,
                sol_oficio_prazo_resposta=sol_oficio_prazo_resposta,
                sol_oficio_responsavel_nome=sol_oficio_responsavel_nome,
                sol_oficio_responsavel_cargo=sol_oficio_responsavel_cargo,
                sol_oficio_responsavel_setor=sol_oficio_responsavel_setor,
                dfd_setor_requisitante=dfd_setor_requisitante,
                dfd_numero_processo=dfd_numero_processo,
                dfd_responsavel_demanda=dfd_responsavel_demanda,
                dfd_email=dfd_email,
                dfd_gestor_contratos=dfd_gestor_contratos,
                dfd_fiscal_contratos=dfd_fiscal_contratos,
                dfd_assinatura_cargo=dfd_assinatura_cargo,
                dfd_assinatura_nome=dfd_assinatura_nome,
                dfd_data=dfd_data,
                dfd_objeto_referencia=dfd_objeto_referencia,
                dfd_justificativa=dfd_justificativa,
                numero_processo=numero_processo,
                marca=marca,
                modelo=modelo,
                numero_placa=numero_placa,
                orgao=orgao,
                valor_total=valor_total,
                fornecedor=fornecedor,
                cnpj_fornecedor=cnpj_fornecedor,
                ao_senhor_genero=ao_senhor_genero,
                senhor_senhora_genero=senhor_senhora_genero,
                objeto_especifico=objeto_especifico,
                equipamento=equipamento,
            )
    itens = llm_slots.itens

    return TRTemplateSlots(
        objeto=objeto,
        objeto_escopo=objeto_escopo,
        objeto_entregas=objeto_entregas,
        objeto_resultados=objeto_resultados,
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
        sol_oficio_artigo_inciso=sol_oficio_artigo_inciso,
        sol_oficio_destinatario_nome=sol_oficio_destinatario_nome,
        sol_oficio_destinatario_cargo=sol_oficio_destinatario_cargo,
        sol_oficio_destinatario_orgao=sol_oficio_destinatario_orgao,
        sol_oficio_assunto=sol_oficio_assunto,
        sol_oficio_objeto=sol_oficio_objeto,
        sol_oficio_justificativa=sol_oficio_justificativa,
        sol_oficio_prazo_resposta=sol_oficio_prazo_resposta,
        sol_oficio_responsavel_nome=sol_oficio_responsavel_nome,
        sol_oficio_responsavel_cargo=sol_oficio_responsavel_cargo,
        sol_oficio_responsavel_setor=sol_oficio_responsavel_setor,
        dfd_setor_requisitante=dfd_setor_requisitante,
        dfd_numero_processo=dfd_numero_processo,
        dfd_responsavel_demanda=dfd_responsavel_demanda,
        dfd_email=dfd_email,
        dfd_gestor_contratos=dfd_gestor_contratos,
        dfd_fiscal_contratos=dfd_fiscal_contratos,
        dfd_assinatura_cargo=dfd_assinatura_cargo,
        dfd_assinatura_nome=dfd_assinatura_nome,
        dfd_data=dfd_data,
        dfd_objeto_referencia=dfd_objeto_referencia,
        dfd_justificativa=dfd_justificativa,
        numero_processo=numero_processo,
        marca=marca,
        modelo=modelo,
        numero_placa=numero_placa,
        orgao=orgao,
        valor_total=valor_total,
        fornecedor=fornecedor,
        cnpj_fornecedor=cnpj_fornecedor,
        ao_senhor_genero=ao_senhor_genero,
        senhor_senhora_genero=senhor_senhora_genero,
        objeto_especifico=objeto_especifico,
        equipamento=equipamento,
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
    if TR_SLOTS_INCLUDE_RAG_EXAMPLES:
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
    _fluxo_ui = str((slots_override or {}).get("dispensa_fluxo_ui") or "").strip().lower()
    skip_item_injection = _fluxo_ui == "normal"
    if skip_item_injection:
        user_prompt_text += (
            "\n\n[Dispensa normal — cláusula de objeto]\n"
            "Uma única oração institucional genérica (ex.: aquisição de medicamentos para atendimento "
            "às necessidades da saúde/suprimento municipal), sem nomear produto, apresentação, dosagem, "
            "marca, nem quantidades (nada como «100 (cem) unidades de X»). Itens e quantidades ficam só na tabela do TR."
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

    try:
        parsed = _parse_llm_json_response_resilient(raw)
    except json.JSONDecodeError as e:
        raise ValueError(
            "Falha ao interpretar JSON retornado pela LLM durante a geração do TR. "
            f"Detalhe do parser: {e.msg} (linha {e.lineno}, coluna {e.colno})."
        ) from e
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
                f"Aquisição de {objeto_fallback.strip().rstrip('.;')}, conforme especificações técnicas, "
                "quantitativos e demais condições estabelecidas neste Termo de Referência."
            ) or objeto_fallback

    # Etapas de reescrita da cláusula de objeto podem custar múltiplas chamadas LLM;
    # em modo rápido, desabilitamos para evitar timeouts em TR/DFD.
    if TR_SLOTS_ENABLE_OBJETO_REWRITE:
        llm_slots.objeto = await _rewrite_objeto_clause(
            user_prompt=user_prompt,
            draft_objeto=llm_slots.objeto,
            itens=llm_slots.itens,
        )
        if _is_objeto_redacao_fraca(llm_slots.objeto):
            llm_slots.objeto = await _rewrite_objeto_clause(
                user_prompt=(
                    f"{user_prompt}\n\n"
                    "Reescreva o objeto com redação mais completa e elegante, evitando forma telegráfica. "
                    "Inclua finalidade administrativa explícita e mantenha o texto em 1 período bem construído."
                ),
                draft_objeto=llm_slots.objeto,
                itens=llm_slots.itens,
            )
        # Em aquisições com muitos itens, resume objeto por macrogrupos.
        llm_slots.objeto = await _summarize_objeto_many_aquisicao_items(
            llm_slots.objeto,
            llm_slots.itens,
            user_prompt,
        )
    # Lapidação final para cenários de aquisição com quantidade explícita nos itens.
    llm_slots.objeto = _polish_objeto_with_itens(
        llm_slots.objeto,
        llm_slots.itens,
        user_prompt,
        skip_item_injection=skip_item_injection,
    )
    if TR_SLOTS_ENABLE_OBJETO_REWRITE:
        llm_slots.objeto = await _strip_enumeration_from_summarized_objeto_if_needed(
            llm_slots.objeto, llm_slots.itens, user_prompt
        )
    low_p = (user_prompt or "").lower()
    if TR_SLOTS_ENABLE_OBJETO_REWRITE:
        if (
            len(llm_slots.itens) >= 6
            and (
                re.search(r"(?i)\baquisi(?:c|ç)[aã]o\b", low_p)
                or re.search(r"(?i)\baquisi(?:c|ç)[aã]o\b", (llm_slots.objeto or "").lower())
            )
            and _needs_ultra_macro_objeto_summary(llm_slots.objeto)
        ):
            llm_slots.objeto = await _ultra_compress_objeto_macro_groups(
                llm_slots.objeto, llm_slots.itens, user_prompt
            )
        if (
            len(llm_slots.itens) >= 6
            and (
                re.search(r"(?i)\baquisi(?:c|ç)[aã]o\b", (user_prompt or "").lower())
                or re.search(r"(?i)\baquisi(?:c|ç)[aã]o\b", (llm_slots.objeto or "").lower())
            )
            and _macro_objeto_telegrafico_demais(llm_slots.objeto)
        ):
            llm_slots.objeto = await _enrich_macro_objeto_add_finalidade(
                llm_slots.objeto, llm_slots.itens, user_prompt
            )
    # Sanidade mínima pós-LLM (sem engessar estilo).
    llm_slots.objeto = _enforce_objeto_semantic_consistency(_normalize_objeto(llm_slots.objeto))

    # Complementos de objeto: se vierem vazios, derivar automaticamente do objeto final.
    if not (llm_slots.objeto_escopo or "").strip():
        llm_slots.objeto_escopo = (
            "O escopo compreende as atividades técnicas e operacionais indispensáveis à execução do objeto, incluindo planejamento, implementação, controle e validação dos resultados pactuados."
        )
    if not (llm_slots.objeto_entregas or "").strip():
        llm_slots.objeto_entregas = (
            "As entregas deverão ser definidas com critérios objetivos de qualidade, conformidade e desempenho, acompanhadas da documentação comprobatória das etapas efetivamente realizadas."
        )
    if not (llm_slots.objeto_resultados or "").strip():
        llm_slots.objeto_resultados = (
            "Como resultados esperados, projeta-se a melhoria da eficiência operacional, o fortalecimento da continuidade do serviço público e a mitigação de riscos de desatendimento ao interesse coletivo."
        )

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
    chosen_inciso = ""
    if TR_SLOTS_ENABLE_INCISO_LLM:
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
