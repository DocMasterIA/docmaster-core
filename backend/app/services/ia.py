from django.core.files import File
import tempfile, os
import json
import re
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def _get_mock_ai_response(doc_structure, user_instructions):
    """
    Função mock para simular resposta da IA quando a cota está esgotada.
    """
    # Simula análise baseada em palavras-chave comuns
    fields = []
    blocks = doc_structure.get('blocks', [])
    
    # Palavras-chave para detectar campos
    field_patterns = {
        'data_inicio': ['data de início', 'início', 'data inicio', 'inicio'],
        'data_final': ['data final', 'final', 'data de fim', 'fim'],
        'orgao': ['órgão', 'orgao', 'prefeitura', 'municipal', 'estado'],
        'objeto': ['objeto', 'contratação', 'serviço', 'servico'],
        'valor_estimado': ['valor', 'estimado', 'r$', 'reais'],
        'modalidade': ['modalidade', 'pregão', 'pregao', 'concorrência', 'concorrencia'],
        'responsavel': ['responsável', 'responsavel', 'técnico', 'tecnico']
    }
    
    for i, block in enumerate(blocks):
        text = block.get('text', '').lower()
        
        for field_key, patterns in field_patterns.items():
            if any(pattern in text for pattern in patterns):
                # Verifica se já existe este campo
                if not any(f['key'] == field_key for f in fields):
                    fields.append({
                        "key": field_key,
                        "label": field_key.replace('_', ' ').title(),
                        "type": "date" if "data" in field_key else "text",
                        "required": True,
                        "description": f"Campo detectado automaticamente: {field_key}",
                        "block_indices": [i]
                    })
    
    return {
        "fields": fields,
        "notes": f"Análise mock realizada. Detectados {len(fields)} campos baseados em palavras-chave."
    }

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
        
        # Check if we should use mock mode
        use_mock = getattr(settings, 'AI_USE_MOCK', False)
        if use_mock:
            logger.info("Using mock data generation for testing")
            return _get_mock_document_data(user_prompt)
        
        # Configure OpenAI client
        client = openai.OpenAI(api_key=api_key)
        
        # Get template schema if available
        schema = getattr(template, 'schema', None)
        schema_fields = []
        if schema and schema.schema:
            schema_fields = schema.schema.get('fields', [])
        
        # Build system prompt for data generation
        system_prompt = f"""Você é um especialista em documentos jurídicos e licitações públicas brasileiras.
        
        Sua tarefa é gerar dados estruturados para preenchimento de um template de documento baseado no prompt do usuário.
        
        Template: {template.name}
        
        Campos disponíveis no template:
        {json.dumps([f['key'] for f in schema_fields], ensure_ascii=False) if schema_fields else 'Nenhum schema disponível'}
        
        Retorne APENAS um JSON válido com os dados para preenchimento do template.
        Inclua todos os campos necessários para um documento de licitação completo.
        """
        
        user_prompt_enhanced = f"""
        Gere dados para um documento de licitação baseado na seguinte descrição:
        
        {user_prompt}
        
        Certifique-se de incluir:
        - Informações do órgão contratante
        - Objeto da licitação
        - Modalidade de licitação
        - Valores estimados
        - Prazos e datas
        - Responsável técnico
        - Qualquer outra informação relevante para o documento
        
        Retorne apenas o JSON com os dados estruturados.
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


def _get_mock_document_data(user_prompt):
    """
    Função mock para gerar dados de exemplo quando a IA não está disponível.
    """
    # Simula geração de dados baseada em palavras-chave do prompt
    prompt_lower = user_prompt.lower()
    
    # Dados base para diferentes tipos de licitação
    base_data = {
        "tipo_documento": "Edital de Licitação",
        "orgao": "Prefeitura Municipal de Exemplo",
        "modalidade": "Pregão Eletrônico",
        "objeto": "Contratação de serviços",
        "valor_estimado": "R$ 100.000,00",
        "prazo_execucao": "12 meses",
        "responsavel": "João Silva",
        "data_inicio": "01/01/2024",
        "data_final": "31/12/2024",
        "observacoes": "Documento gerado automaticamente"
    }
    
    # Personaliza baseado no prompt
    if "limpeza" in prompt_lower:
        base_data.update({
            "objeto": "Contratação de serviços de limpeza urbana",
            "valor_estimado": "R$ 500.000,00"
        })
    elif "construção" in prompt_lower or "obra" in prompt_lower:
        base_data.update({
            "objeto": "Execução de obra pública",
            "modalidade": "Concorrência",
            "valor_estimado": "R$ 2.000.000,00"
        })
    elif "fornecimento" in prompt_lower:
        base_data.update({
            "objeto": "Fornecimento de materiais",
            "modalidade": "Pregão Eletrônico",
            "valor_estimado": "R$ 50.000,00"
        })
    
    return base_data
