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
        
        # Prompt especializado em licitações públicas e Lei 14.133/21
        system_prompt = """Aja como um especialista em licitações públicas e na Lei 14.133/21, com foco na elaboração de editais completos, interpretação de cláusulas e criação de matrizes de risco. Você deve dominar todos os tipos de contratação previstos na lei (obras, serviços, fornecimentos e serviços de engenharia).

        --- Instruções ---
        
        Suas respostas devem ser claras, objetivas e com linguagem apropriada para documentos oficiais.
        
        Sempre que possível, baseie-se em dispositivos atualizados da Lei 14.133/21, citando os artigos aplicáveis.
        
        Use exemplos práticos quando for útil para ilustrar a aplicação.
        
        Quando eu solicitar algo como "cláusula de julgamento por técnica e preço", forneça o texto sugerido para o edital, a base legal e orientações práticas.
        
        Adapte o nível de profundidade para respostas diretas e aplicáveis no cotidiano do setor público.
        
        --- Formato de resposta sugerido ---
        
        Comece respondendo com um resumo direto, seguido de:
        - Texto sugerido para o edital
        - Base legal (com artigo)
        - Observação prática (se aplicável)
        
        Sua tarefa é analisar a estrutura de um documento DOCX e identificar campos que devem ser preenchidos automaticamente.
        
        Retorne APENAS um JSON válido com a seguinte estrutura:
        {
            "fields": [
                {
                    "key": "nome_do_campo",
                    "label": "Nome Amigável",
                    "type": "text|date|number|select",
                    "required": true/false,
                    "description": "Descrição do campo com base legal",
                    "base_legal": "Artigo da Lei 14.133/21 aplicável",
                    "block_indices": [0, 1, 2]
                }
            ],
            "notes": "Observações sobre a análise com citações legais"
        }
        
        Campos essenciais para licitações (Lei 14.133/21):
        - objeto (objeto da licitação - Art. 40)
        - modalidade (modalidade de licitação - Art. 22)
        - valor_estimado (valor estimado - Art. 23)
        - orgao (órgão contratante - Art. 6º)
        - data_inicio, data_final (prazos - Art. 40, § 1º)
        - prazo_execucao (prazo de execução - Art. 40, § 2º)
        - responsavel (responsável técnico - Art. 40, § 3º)
        - criterio_julgamento (critério de julgamento - Art. 45)
        - garantia_contratual (garantia contratual - Art. 90)
        - penalidades (penalidades - Art. 91)
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


def generate_document_data_from_prompt(template, user_prompt, llm_api_key=None):
    """
    Gera dados estruturados para preenchimento do template baseado no prompt do usuário.
    
    Args:
        template: Template object
        user_prompt: Prompt do usuário descrevendo o documento desejado
        llm_api_key: Chave da API (opcional)
    
    Returns:
        dict: Dados estruturados para preenchimento
    """
    try:
        # Import OpenAI here to avoid import errors if not installed
        import openai
        
        # Use provided API key or fallback to settings
        api_key = llm_api_key or getattr(settings, 'OPENAI_API_KEY', None)
        if not api_key:
            logger.error("No OpenAI API key provided")
            return {"error": "Chave da API OpenAI não configurada"}

        # Configure OpenAI client
        client = openai.OpenAI(api_key=api_key)
        
        # Get template schema if available
        schema = getattr(template, 'schema', None)
        schema_fields = []
        if schema and schema.schema:
            schema_fields = schema.schema.get('fields', [])
        
        # Prompt especializado em licitações públicas e Lei 14.133/21
        system_prompt = f"""Aja como um especialista em licitações públicas e na Lei 14.133/21, com foco na elaboração de editais completos, interpretação de cláusulas e criação de matrizes de risco. Você deve dominar todos os tipos de contratação previstos na lei (obras, serviços, fornecimentos e serviços de engenharia).

        --- Instruções ---
        
        Suas respostas devem ser claras, objetivas e com linguagem apropriada para documentos oficiais.
        
        Sempre que possível, baseie-se em dispositivos atualizados da Lei 14.133/21, citando os artigos aplicáveis.
        
        Use exemplos práticos quando for útil para ilustrar a aplicação.
        
        Quando eu solicitar algo como "cláusula de julgamento por técnica e preço", forneça o texto sugerido para o edital, a base legal e orientações práticas.
        
        Adapte o nível de profundidade para respostas diretas e aplicáveis no cotidiano do setor público.
        
        --- Formato de resposta sugerido ---
        
        Comece respondendo com um resumo direto, seguido de:
        - Texto sugerido para o edital
        - Base legal (com artigo)
        - Observação prática (se aplicável)
        
        Sua tarefa é gerar dados estruturados para preenchimento de um template de edital de licitação baseado no prompt do usuário.
        
        Template: {template.name}
        
        Campos disponíveis no template:
        {json.dumps([f['key'] for f in schema_fields], ensure_ascii=False) if schema_fields else 'Nenhum schema disponível'}
        
        Retorne APENAS um JSON válido com os dados para preenchimento do template, incluindo:
        - Informações básicas do órgão contratante
        - Objeto da licitação detalhado
        - Modalidade adequada conforme Lei 14.133/21
        - Valores estimados realistas
        - Prazos e datas conforme legislação
        - Critérios de julgamento apropriados
        - Cláusulas contratuais essenciais
        - Garantias e penalidades
        """
        
        user_prompt_enhanced = f"""
        {user_prompt}
        
        Retorne apenas o JSON com os dados estruturados para preenchimento do template.
        """
        
        # Call OpenAI
        response = client.chat.completions.create(
            model=getattr(settings, 'AI_MODEL', 'gpt-3.5-turbo'),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt_enhanced}
            ],
            max_tokens=getattr(settings, 'AI_MAX_TOKENS', 4000),
            temperature=0.3,  # Slightly higher for more creative data generation
            response_format={"type": "json_object"}
        )
        
        # Extract and parse response
        raw_response = response.choices[0].message.content
        
        try:
            data = json.loads(raw_response)
            logger.info(f"AI data generation successful: {len(data)} fields generated")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            # Try to extract JSON from text
            json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    return data
                except json.JSONDecodeError:
                    pass
            
            return {"error": f"Erro ao processar resposta da IA: {str(e)}"}
    
    except ImportError:
        logger.error("OpenAI library not installed")
        return {"error": "Biblioteca OpenAI não instalada"}
    
    except Exception as e:
        logger.error(f"AI data generation error: {str(e)}")
        return {"error": f"Erro na geração de dados: {str(e)}"}


