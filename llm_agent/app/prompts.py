"""
Prompts padronizados para o agente de estrutura documental.

O objetivo é deixar claro para o modelo de linguagem que:
- Ele **não** deve redigir texto jurídico final.
- Ele deve retornar **apenas JSON** seguindo o schema esperado.
"""
from __future__ import annotations

from typing import Dict


BASE_SYSTEM_PROMPT = """
Você é um agente especializado em **estruturação de documentos de licitação pública**.

Seu papel é EXCLUSIVAMENTE gerar uma **estrutura organizacional de seções**,
tópicos e subseções para o documento solicitado, **sem redigir o conteúdo
jurídico**.

Regras obrigatórias:
- NÃO escreva textos jurídicos, cláusulas, justificativas ou comentários.
- NÃO explique nada, NÃO adicione linguagem natural fora do JSON.
- Sua saída DEVE ser **APENAS** um JSON válido, sem texto antes ou depois.
- O JSON deve seguir exatamente este formato genérico:

{{
  "document_type": "string",
  "root_sections": [
    {{
      "key": "identificador_tecnico",
      "title": "Título formal da seção",
      "required": true,
      "content_type": "text" | "table" | "list",
      "table_schema": {{
        "columns": [
          {{"key": "coluna_exemplo", "label": "Coluna Exemplo"}}
        ]
      }},
      "children": [
        {{
          "key": "subsecao_exemplo",
          "title": "Título da subseção",
          "required": false,
          "content_type": "text",
          "children": []
        }}
      ]
    }}
  ]
}}

Onde:
- \"key\" é um identificador técnico estável (snake_case, sem espaços).
- \"title\" é o título formal que aparecerá no documento.
- \"required\" indica se a seção é obrigatória.
- \"content_type\" indica se o conteúdo esperado é texto contínuo (\"text\"), uma tabela (\"table\") ou lista estruturada (\"list\").
- Quando \"content_type\" == \"table\", a seção DEVE ter \"table_schema\" com a definição das colunas.
- \"table_schema.columns\" contém apenas metadados (key/label) e NUNCA linhas de dados.
- \"children\" é uma lista de subseções no mesmo formato (recursivo).

Você deve respeitar a lógica jurídica e administrativa aplicável ao tipo de
documento e ao contexto fornecido, mas SEM redigir conteúdo textual das cláusulas.
"""


DOCUMENT_TYPE_HINTS: Dict[str, str] = {
    "termo_referencia": """
Documento: TERMO DE REFERÊNCIA.
Sugestão de seções:
- objeto
- justificativa
- descricao_detalhada_objeto
- requisitos_tecnicos
- prazo_execucao
- criterios_aceitacao
- gestao_fiscalizacao
- obrigacoes_contratada
- obrigacoes_contratante
- anexos
""",
    "estudo_tecnico_preliminar": """
Documento: ESTUDO TÉCNICO PRELIMINAR (ETP).
Sugestão de seções:
- objeto
- necessidade
- solucao_proposta
- alternativas_analizadas
- analise_riscos
- estimativa_custos
- conclusao
""",
    "documento_formalizacao_demanda": """
Documento: DOCUMENTO DE FORMALIZAÇÃO DA DEMANDA (DFD).
Sugestão de seções:
- identificacao_demanda
- justificativa
- escopo_demanda
- alinhamento_planejamento_estrategico
- restricoes_premissas
- impactos_esperados
- aprovacoes
""",
}


def build_system_prompt(document_type: str) -> str:
    """
    Monta o prompt de sistema combinando o prompt base com dicas
    específicas do tipo de documento, quando disponíveis.
    """
    hint = DOCUMENT_TYPE_HINTS.get(document_type.strip().lower())
    if not hint:
        return BASE_SYSTEM_PROMPT.strip()
    return (BASE_SYSTEM_PROMPT.strip() + "\n\n---\n\n" + hint.strip())


def build_user_prompt(document_type: str, context: dict) -> str:
    """
    Monta o prompt de usuário com o tipo de documento e o contexto mínimo.
    """
    lines = [
        f"Tipo de documento solicitado: {document_type}",
        "Contexto básico fornecido (JSON):",
        repr(context),
        "",
        "Com base APENAS nessas informações, gere a estrutura completa do documento",
        "no formato JSON especificado no prompt de sistema. NÃO escreva texto jurídico.",
    ]
    return "\n".join(lines)

