"""
Monta contexto do usuário para envio ao rag_service (geração de documentos via LLM).

Usado pela API gerar-via-llm para incluir nome, secretaria e prefeitura do usuário
logado nos prompts de geração.
"""


def build_llm_context_from_request(request):
    """
    Monta o dicionário context para envio ao rag_service.

    Args:
        request: HttpRequest com request.user autenticado

    Returns:
        dict com chaves usuario (nome_completo, secretaria, prefeitura, orgao),
        template_id e document_type_hint quando aplicável.
    """
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False) or not user.is_authenticated:
        return {}

    ctx = {}
    nome = f"{user.first_name or ''} {user.last_name or ''}".strip() or (user.email or "")
    pref = getattr(user, "prefeitura", None)
    sec = getattr(user, "secretaria", None)

    ctx["usuario"] = {
        "nome_completo": nome or None,
        "secretaria": str(sec) if sec else None,
        "prefeitura": pref.nome_municipio if pref else None,
        "orgao": f"Prefeitura Municipal de {pref.nome_municipio}" if pref else None,
    }
    return ctx
