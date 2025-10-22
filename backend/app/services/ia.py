from django.core.files import File
import tempfile, os
import json
import re
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Função de integração com LLM/Agente IA para sugerir schema de campos a partir da estrutura do DOCX.
def call_llm_for_mapping(doc_structure, user_instructions="", llm_api_key=None):
    """
    doc_structure: output de extract_docx_structure
    user_instructions: texto extra que o usuário possa enviar ("detecte data_inicio,data_fim,orgao")
    Retorna um dict parseado (o JSON esperado descrito depois).
    """
    try:
        # Import OpenAI here to avoid import errors if not installed
        import openai
        
        # Use provided API key or fallback to settings
        api_key = llm_api_key or getattr(settings, 'OPENAI_API_KEY', None)
        if not api_key:
            logger.error("No OpenAI API key provided")
            return {"fields": [], "notes": "Erro: Chave da API OpenAI não configurada"}
        
        # Configure OpenAI client
        client = openai.OpenAI(api_key=api_key)
        
        # Montar prompt otimizado para análise de documentos jurídicos
        system_prompt = """Você é um especialista em análise de documentos jurídicos e licitações públicas. 
        Sua tarefa é analisar a estrutura de um documento DOCX e identificar campos que podem ser preenchidos automaticamente.
        
        Retorne APENAS um JSON válido com a seguinte estrutura:
        {
            "fields": [
                {
                    "key": "nome_do_campo",
                    "label": "Nome Amigável",
                    "type": "text|date|number|select",
                    "required": true/false,
                    "description": "Descrição do campo",
                    "block_indices": [0, 1, 2]
                }
            ],
            "notes": "Observações sobre a análise"
        }
        
        Campos comuns em licitações:
        - data_inicio, data_final (datas)
        - orgao (órgão contratante)
        - objeto (objeto da licitação)
        - valor_estimado (valor estimado)
        - modalidade (modalidade de licitação)
        - prazo_execucao (prazo de execução)
        - responsavel (responsável técnico)
        """
        
        user_prompt = f"""
Analise a estrutura do documento abaixo e identifique campos para preenchimento automático.

Instruções específicas do usuário: {user_instructions}

Estrutura do documento (primeiros 60 blocos):
{json.dumps(doc_structure['blocks'][:60], ensure_ascii=False, indent=2)}

Total de blocos no documento: {doc_structure.get('n_blocks', 0)}
        """
        
        # Chamada para OpenAI
        response = client.chat.completions.create(
            model=getattr(settings, 'AI_MODEL', 'gpt-4'),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=getattr(settings, 'AI_MAX_TOKENS', 4000),
            temperature=0.1,  # Baixa temperatura para respostas mais consistentes
            response_format={"type": "json_object"}  # Força resposta em JSON
        )
        
        # Extrair resposta
        raw_response = response.choices[0].message.content
        
        # Parsear JSON
        try:
            parsed = json.loads(raw_response)
            logger.info(f"AI mapping successful: {len(parsed.get('fields', []))} fields detected")
            return parsed
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            # Tentar extrair JSON do texto
            json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
            if json_match:
                try:
                    parsed = json.loads(json_match.group())
                    return parsed
                except json.JSONDecodeError:
                    pass
            
            return {
                "fields": [],
                "notes": f"Erro ao processar resposta da IA: {str(e)}"
            }
    
    except ImportError:
        logger.error("OpenAI library not installed. Install with: pip install openai")
        return {
            "fields": [],
            "notes": "Erro: Biblioteca OpenAI não instalada. Execute: pip install openai"
        }
    
    except Exception as e:
        logger.error(f"AI mapping error: {str(e)}")
        return {
            "fields": [],
            "notes": f"Erro na análise da IA: {str(e)}"
        }


# Cria uma instância de documento a partir de dados estruturados vindos da IA.
# Cria DocumentInstance a partir dos dados fornecidos pela IA.
# ai_data deve conter campos usuais (tipo_documento, modalidade, objeto, orgao, valor_estimado, ...)
# e opcionalmente "snippets" para montar blocos textuais.
def create_document_from_ai(template, owner, ai_data):
    """
    Cria DocumentInstance a partir dos dados fornecidos pela IA.
    """
    from app.models import DocumentInstance
    from .services import generate_pdf_from_docx
    from .render import render_docx_from_template

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
