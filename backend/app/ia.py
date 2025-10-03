from django.core.files import File
import tempfile, os

import requests
import json

# Exemplo: função que chama a OpenAI (ou outro endpoint). Substituir conforme sua infra.
def call_llm_for_mapping(doc_structure, user_instructions="", llm_api_key=None):
    """
    doc_structure: output de extract_docx_structure
    user_instructions: texto extra que o usuário possa enviar ("detecte data_inicio,data_fim,orgao")
    Retorna um dict parseado (o JSON esperado descrito depois).
    """
    # montar prompt (few-shot + instruções)
    prompt = f"""
You will receive a document structure (blocks). Detect likely fields for auto-fill such as:
- data_inicio (start date)
- data_final (end date)
- orgao (contracting body)
- objeto (object)
- valor_estimado (estimated value)
Return only JSON with keys: fields (array) and notes.

User instructions: {user_instructions}

Document blocks:
{json.dumps(doc_structure['blocks'][:60], ensure_ascii=False, indent=2)}
    """

    # Exemplo simples: se usar OpenAI SDK, aqui chamaria openai.ChatCompletion.create...
    # Aqui um mock: POST to your LLM endpoint
    resp = requests.post(
        "https://api.example-llm.local/generate",
        headers={"Authorization": f"Bearer {llm_api_key}"},
        json={"prompt": prompt, "max_tokens": 8000}
    )
    resp.raise_for_status()
    raw = resp.text
    # o LLM deve retornar JSON — parsear
    try:
        parsed = json.loads(raw)
    except Exception:
        # tenta extrair JSON dentro do texto
        import re
        m = re.search(r'(\{.*\})', raw, re.S)
        parsed = json.loads(m.group(1)) if m else {}
    return parsed


def create_document_from_ai(template, owner, ai_data):
    """
    Cria DocumentInstance a partir dos dados fornecidos pela IA.
    ai_data deve ser um dict contendo:
      - campos como tipo_documento, modalidade, objeto, orgao, valor_estimado, etc.
      - snippets: {"intro": [...], "clause": [...], "conclusion": [...]}
    """
    from .models import DocumentInstance
    from .services import render_docx_from_template, generate_pdf_from_docx

    # Cria draft inicial
    inst = DocumentInstance.objects.create(
        template=template,
        owner=owner,
        data=ai_data,
        status="draft"
    )

    # Monta contexto completo incluindo snippets
    context = ai_data.copy()
    context.setdefault("snippets_intro", ai_data.get("snippets", {}).get("intro", []))
    context.setdefault("snippets_clause", ai_data.get("snippets", {}).get("clause", []))
    context.setdefault("snippets_conclusion", ai_data.get("snippets", {}).get("conclusion", []))

    tmpdir = tempfile.gettempdir()
    docx_path = render_docx_from_template(template.file.path, context, dest_dir=tmpdir)
    pdf_path = generate_pdf_from_docx(docx_path)

    # Salva arquivos
    with open(docx_path, "rb") as f:
        inst.file_docx.save(os.path.basename(docx_path), File(f), save=False)
    with open(pdf_path, "rb") as f:
        inst.file_pdf.save(os.path.basename(pdf_path), File(f), save=False)

    inst.status = "final"
    inst.save()

    # Limpa temporários
    try:
        os.remove(docx_path)
        os.remove(pdf_path)
    except OSError:
        pass

    return inst
