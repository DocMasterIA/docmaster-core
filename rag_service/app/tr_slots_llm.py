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
- O JSON deve ter exatamente estas chaves: objeto, dispensa, itens, justificativa, fiscal, dotacao.
- Use linguagem técnica, formal e objetiva, adequada a documentos administrativos. NÃO use gírias, comentários informais ou meta-observações (ex.: "simples até demais", "ficou meio esquisito", "feito direto pelo usuário").
- dispensa: objeto com "artigo" (ex: "75") e "inciso" (ex: "I", "II").
- itens: array de objetos, cada um com "descricao", "unidade" (ex: "un", "cx", "litro"), "quantidade" (número).
  - A "descricao" deve ser uma especificação técnica mínima do item, não apenas uma palavra solta (ex.: "Caneta esferográfica azul, ponta 1.0 mm").
  - Se o usuário já tiver informado descrição/unidade/quantidade, preserve essas informações e apenas complemente de forma técnica quando fizer sentido.
- fiscal: objeto com "nome" (nome completo do fiscal do contrato). Se não houver nome de fiscal claramente informado pelo usuário ou contexto, use "" (não invente nomes).
- dotacao: string com a dotação orçamentária. Se o usuário ou o contexto informar o código (ex: "1.2.3.4.5.00.00.000.0000.0000"), use-o. Se NÃO souber, preencha com uma frase padrão em linguagem formal, por exemplo: "Dotação orçamentária a ser informada pela unidade gestora no ato da contratação" ou "A definir pela secretaria/orçamento". Nunca deixe este campo vazio: o documento deve ter sempre um texto nessa seção.
- objeto: frase completa, formal e específica, descrevendo claramente o objeto da contratação, incluindo finalidade e, quando inferível, área/setor atendido (por exemplo: "Aquisição de materiais de escritório para suprir as necessidades da Secretaria Municipal de Administração").
- justificativa: parágrafo de justificativa técnica/administrativa para a contratação, em linguagem formal.
- Se o usuário informar itens (descrição, unidade, quantidade), use-os no array itens; senão sugira itens coerentes com o objeto.
- Cada produto ou serviço diferente mencionado pelo usuário deve virar um item separado no array "itens" (não agrupe vários produtos na mesma "descricao").
- Use Lei 14.133/2021. Não invente dados que não possam ser inferidos do pedido (ex.: fiscal deixe vazio se não informado; dotação sempre preencha, nem que seja com frase padrão).
"""


def _build_tr_slots_user_prompt(
    user_prompt: str,
    context_from_agent: Optional[Dict[str, Any]] = None,
) -> str:
    """Monta o prompt de usuário para a LLM preencher os slots do TR."""
    parts = [f"Pedido do usuário:\n{user_prompt}"]
    if context_from_agent:
        ctx = context_from_agent.get("context") or {}
        esp = context_from_agent.get("especificacoes")
        if ctx:
            parts.append(f"\nContexto extraído: objeto={ctx.get('objeto', '')}, órgão={ctx.get('orgao', '')}, modalidade={ctx.get('modalidade', '')}.")
        if esp:
            listas = (esp.get("listas") or {}) if isinstance(esp, dict) else {}
            tabelas = (esp.get("tabelas") or {}) if isinstance(esp, dict) else {}
            if listas or tabelas:
                parts.append(f"\nEspecificações: listas={listas}, tabelas={tabelas}.")
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


def _dict_to_tr_slots(data: Dict[str, Any]) -> TRTemplateSlots:
    """Converte o dicionário retornado pela LLM em TRTemplateSlots."""
    disp = data.get("dispensa") or {}
    if isinstance(disp, dict):
        dispensa = DispensaSlots(
            artigo=str(disp.get("artigo", "")).strip(),
            inciso=str(disp.get("inciso", "")).strip(),
        )
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

    return TRTemplateSlots(
        objeto=str(data.get("objeto", "")).strip(),
        dispensa=dispensa,
        itens=itens,
        justificativa=str(data.get("justificativa", "")).strip(),
        fiscal=fiscal,
        dotacao=str(data.get("dotacao", "")).strip(),
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
            return TRTemplateSlots(objeto=objeto, dispensa=dispensa, itens=itens, justificativa=justificativa, fiscal=fiscal, dotacao=dotacao)
    itens = llm_slots.itens

    return TRTemplateSlots(objeto=objeto, dispensa=dispensa, itens=itens, justificativa=justificativa, fiscal=fiscal, dotacao=dotacao)


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
) -> TRTemplateSlots:
    """
    Preenche os slots do TR usando IA.

    - Chama o llm_agent (structure-from-prompt) para obter contexto e especificações.
    - Chama a LLM para gerar o JSON de slots (objeto, dispensa, itens, justificativa, fiscal, dotacao).
    - Mescla com slots_override (valores enviados pelo usuário têm prioridade).
    """
    context_from_agent = await fetch_context_from_agent(user_prompt)

    user_prompt_text = _build_tr_slots_user_prompt(user_prompt, context_from_agent)
    full_prompt = f"<<SYSTEM>>\n{TR_SLOTS_SYSTEM_PROMPT.strip()}\n\n<<USER>>\n{user_prompt_text}"

    url = f"{LLM_ORCHESTRATION_BASE_URL}{LLM_ORCHESTRATION_GENERATE_PATH}"
    payload = {"prompt": full_prompt, "stream": False}

    async with httpx.AsyncClient(timeout=RAG_HTTP_TIMEOUT) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        body = resp.json()

    if isinstance(body, dict) and body.get("detail"):
        detail = str(body["detail"]).strip()
        if any(kw in detail.lower() for kw in ("falha", "erro", "timeout", "error")):
            raise ValueError(f"Orquestração LLM retornou erro: {detail}")

    data = body.get("data", body) if isinstance(body, dict) else {}
    text = data.get("response", data.get("text", ""))
    raw = (text or "").strip()
    if not raw:
        raise ValueError("Resposta da LLM vazia para preenchimento dos slots do TR.")

    parsed = _parse_llm_json_response(raw)
    llm_slots = _dict_to_tr_slots(parsed)
    return _merge_slots(llm_slots, slots_override or {})
