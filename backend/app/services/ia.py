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
    Gera dados estruturados para renderização contextual inteligente.
    
    Extrai informações específicas do prompt do usuário para aplicar alterações precisas.
    
    Args:
        template: Template object
        user_prompt: Prompt do usuário descrevendo o documento desejado
        llm_api_key: Chave da API (opcional)
    
    Returns:
        dict: Dados estruturados para renderização contextual
    """
    import re
    
    # Extrair valor do prompt se mencionado
    valor_estimado = '1000000.00'  # Valor padrão
    valor_match = re.search(r'R\$\s*([\d.,]+)', user_prompt)
    if valor_match:
        # Converter valor para formato numérico
        valor_str = valor_match.group(1).replace('.', '').replace(',', '.')
        try:
            valor_float = float(valor_str)
            valor_estimado = f"{valor_float:.2f}"
        except ValueError:
            pass
    
    # Extrair número do edital do prompt se mencionado
    numero_edital = '001/2024'  # Valor padrão
    
    # Procurar especificamente por "número do edital" ou "edital" seguido de número
    edital_patterns = [
        r'edital\s+para\s+(\d+/\d+)',  # "edital para 456/2024"
        r'edital\s+(\d+/\d+)',         # "edital 456/2024"
        r'número\s+do\s+edital\s+para\s+(\d+/\d+)',  # "número do edital para 456/2024"
        r'número\s+do\s+edital\s+(\d+/\d+)',         # "número do edital 456/2024"
        r'altere\s+o\s+número\s+do\s+edital\s+para\s+(\d+/\d+)',  # "altere o número do edital para 456/2024"
        r'altere\s+o\s+número\s+do\s+edital\s+(\d+/\d+)',         # "altere o número do edital 456/2024"
    ]
    
    for pattern in edital_patterns:
        numero_match = re.search(pattern, user_prompt, re.IGNORECASE)
        if numero_match:
            numero_edital = numero_match.group(1)
            break
    
    # Extrair data de abertura
    data_abertura = None
    data_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', user_prompt)
    if data_match:
        data_abertura = data_match.group(1)
    
    # Extrair local/órgão
    local_orgao = None
    if 'BRASÍLIA' in user_prompt.upper() or 'brasília' in user_prompt.lower():
        local_orgao = 'BRASÍLIA'
    elif 'ITAJÁ' in user_prompt.upper() or 'itajá' in user_prompt.lower():
        local_orgao = 'ITAJÁ'
    
    # Extrair órgão específico
    orgao_especifico = 'Prefeitura Municipal'
    if 'SECRETARIA MUNICIPAL DE SAÚDE' in user_prompt.upper():
        orgao_especifico = 'SECRETARIA MUNICIPAL DE SAÚDE'
    elif 'SECRETARIA' in user_prompt.upper() and 'SAÚDE' in user_prompt.upper():
        orgao_especifico = 'SECRETARIA MUNICIPAL DE SAÚDE'
    
    # Extrair prazo de execução
    prazo_execucao = None
    prazo_match = re.search(r'(\d+)\s*dias?', user_prompt, re.IGNORECASE)
    if prazo_match:
        prazo_execucao = prazo_match.group(1)
    
    # Detectar se deve adicionar cláusula de julgamento
    adicionar_clausula_julgamento = 'julgamento' in user_prompt.lower() and ('técnica' in user_prompt.lower() or 'preço' in user_prompt.lower())
    
    # Detectar se deve adicionar observação prática
    adicionar_observacao_pratica = 'observação' in user_prompt.lower() and 'prática' in user_prompt.lower()
    
    # Extrair cláusulas específicas solicitadas usando IA
    clausulas_especificas = extrair_clausulas_com_ia(user_prompt)
    
    # Retornar dados estruturados para renderização contextual
    return {
        'numero_edital': numero_edital,
        'modalidade': 'Pregão Eletrônico',
        'objeto': 'Contratação conforme especificado',
        'orgao': orgao_especifico,
        'valor_estimado': valor_estimado,
        'data_abertura': data_abertura,
        'local_orgao': local_orgao,
        'prazo_execucao': prazo_execucao,
        'adicionar_clausula_julgamento': adicionar_clausula_julgamento,
        'adicionar_observacao_pratica': adicionar_observacao_pratica,
        'clausulas_especificas': clausulas_especificas,
        'user_prompt': user_prompt
    }


def extrair_clausulas_com_ia(user_prompt):
    """
    Usa IA para extrair cláusulas específicas do prompt de forma inteligente.
    Reconhece diferentes variações e formatos de solicitação de cláusulas.
    
    Args:
        user_prompt: Prompt do usuário
    
    Returns:
        list: Lista de cláusulas detectadas com tipo e descrição
    """
    try:
        from openai import OpenAI
        from django.conf import settings
        
        client = OpenAI(api_key=getattr(settings, 'OPENAI_API_KEY', ''))
        
        system_prompt = """Você é um especialista em licitações públicas e Lei 14.133/2021.

Analise o prompt do usuário e identifique todas as cláusulas específicas solicitadas, independente da ordem das palavras ou formato.

TIPOS DE CLÁUSULAS RECONHECIDAS:
- garantia_execucao: Garantia de execução, garantia contratual, caução
- penalidade_atraso: Penalidade por atraso, multa por atraso, penalidade
- fornecimento_garantia: Garantia de fornecimento, garantia de qualidade, garantia de produtos
- criterio_desempate: Critério de desempate, desempate, critério de classificação
- prazo_entrega: Prazo de entrega, prazo de fornecimento, prazo de entrega
- documentacao_complementar: Documentação complementar, documentos adicionais
- julgamento_tecnica_preco: Julgamento por técnica e preço, critério de julgamento
- garantia_qualidade: Garantia de qualidade, garantia de conformidade
- prazo_execucao: Prazo de execução, prazo contratual
- reajuste_precos: Reajuste de preços, atualização de preços

INSTRUÇÕES:
1. Identifique TODAS as cláusulas mencionadas no prompt
2. Use sinônimos e variações (ex: "garantia de fornecimento" = "fornecimento de garantia")
3. Seja flexível com a ordem das palavras
4. Para cada cláusula, determine:
   - O tipo correto
   - A descrição original do usuário
   - Se deve ter observação prática
5. NÃO force posições específicas - deixe isso para análise posterior do documento
6. Retorne APENAS o JSON, sem explicações

FORMATO DE RESPOSTA:
{
  "clausulas": [
    {
      "tipo": "tipo_da_clausula",
      "descricao": "descrição original do usuário",
      "confianca": 0.9
    }
  ],
  "observacao_pratica": true/false
}"""

        user_prompt_ia = f"""Analise este prompt e identifique todas as cláusulas específicas solicitadas:

"{user_prompt}"

Retorne apenas o JSON com as cláusulas detectadas."""

        response = client.chat.completions.create(
            model=getattr(settings, 'AI_MODEL', 'gpt-3.5-turbo'),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt_ia}
            ],
            max_tokens=1000,
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        # Parsear resposta
        raw_response = response.choices[0].message.content
        parsed = json.loads(raw_response)
        
        clausulas_detectadas = []
        for clausula in parsed.get('clausulas', []):
            clausulas_detectadas.append({
                'tipo': clausula.get('tipo', 'clausula'),
                'descricao': clausula.get('descricao', ''),
                'texto_completo': clausula.get('descricao', ''),
                'confianca': clausula.get('confianca', 0.8)
            })
        
        logger.info(f"IA detectou {len(clausulas_detectadas)} cláusulas: {[c['tipo'] for c in clausulas_detectadas]}")
        return clausulas_detectadas
        
    except Exception as e:
        logger.error(f"Erro ao extrair cláusulas com IA: {e}")
        # Fallback para detecção básica
        return extrair_clausulas_fallback(user_prompt)


def extrair_clausulas_fallback(user_prompt):
    """
    Fallback para detecção básica de cláusulas quando a IA falha.
    """
    clausulas_especificas = []
    
    # Padrões básicos como fallback
    clausula_patterns = [
        (r'cláusula\s+de\s+([^,\.]+)', 'clausula'),
        (r'adicionar\s+uma\s+cláusula\s+sobre\s+([^,\.]+)', 'clausula'),
        (r'incluir\s+cláusula\s+de\s+([^,\.]+)', 'clausula'),
        (r'garantia\s+de\s+execução', 'garantia_execucao'),
        (r'penalidade\s+por\s+atraso', 'penalidade_atraso'),
        (r'garantia\s+de\s+fornecimento', 'fornecimento_garantia'),
        (r'fornecimento\s+de\s+garantia', 'fornecimento_garantia'),
        (r'critério\s+de\s+desempate', 'criterio_desempate'),
        (r'prazo\s+de\s+entrega', 'prazo_entrega'),
        (r'documentação\s+complementar', 'documentacao_complementar'),
    ]
    
    for pattern, tipo in clausula_patterns:
        matches = re.findall(pattern, user_prompt, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                descricao = match[0] if match else ''
            else:
                descricao = match if match else ''
            
            clausulas_especificas.append({
                'tipo': tipo,
                'descricao': descricao,
                'texto_completo': descricao,
                'confianca': 0.7
            })
    
    return clausulas_especificas


def analisar_documento_e_posicionar_clausulas_com_ia(doc, clausulas_especificas, user_prompt):
    """
    Usa IA para analisar o documento e determinar o posicionamento ideal das cláusulas.
    A IA analisa a estrutura real do documento e decide onde inserir cada cláusula.
    
    Args:
        doc: Documento docx
        clausulas_especificas: Lista de cláusulas detectadas
        user_prompt: Prompt original do usuário
    
    Returns:
        dict: Informações de posicionamento para cada cláusula
    """
    try:
        from openai import OpenAI
        from django.conf import settings
        import re
        
        client = OpenAI(api_key=getattr(settings, 'OPENAI_API_KEY', ''))
        
        # Analisar estrutura completa do documento
        estrutura_doc = []
        for i, p in enumerate(doc.paragraphs):
            texto = p.text.strip()
            if texto:  # Todos os parágrafos com conteúdo
                # Extrair numeração se existir
                numeracao_match = re.search(r'(\d+\.\d+\.?\d*)', texto)
                numeracao = numeracao_match.group(1) if numeracao_match else None
                
                # Extrair palavras-chave para contexto
                palavras_chave = []
                if 'julgamento' in texto.lower():
                    palavras_chave.append('julgamento')
                if 'garantia' in texto.lower():
                    palavras_chave.append('garantia')
                if 'penalidade' in texto.lower():
                    palavras_chave.append('penalidade')
                if 'prazo' in texto.lower():
                    palavras_chave.append('prazo')
                if 'documentação' in texto.lower():
                    palavras_chave.append('documentação')
                if 'desempate' in texto.lower():
                    palavras_chave.append('desempate')
                
                estrutura_doc.append({
                    'linha': i + 1,
                    'texto': texto[:150] + '...' if len(texto) > 150 else texto,
                    'numeracao': numeracao,
                    'palavras_chave': palavras_chave
                })
        
        system_prompt = """Você é um especialista em estruturação de editais de licitação.

Analise a estrutura do documento e determine o posicionamento ideal para as cláusulas solicitadas.

INSTRUÇÕES:
1. Analise a estrutura real do documento
2. Identifique seções apropriadas para cada tipo de cláusula
3. Considere a numeração existente e mantenha sequência lógica
4. Posicione cláusulas em seções que façam sentido contextualmente
5. Seja flexível - não force seções específicas se não fizerem sentido
6. Para cada cláusula, determine:
   - Seção ideal (ex: 3.4, 4.2, 5.1, etc.)
   - Número sequencial apropriado
   - Posição relativa (após qual cláusula inserir)

Retorne APENAS o JSON com as posições calculadas."""

        user_prompt_ia = f"""Estrutura do documento (primeiros 30 parágrafos):
{estrutura_doc[:30]}

Cláusulas a posicionar:
{[c['tipo'] + ': ' + c['descricao'] for c in clausulas_especificas]}

Prompt do usuário: "{user_prompt}"

Analise o documento e determine onde cada cláusula deve ser inserida para manter a lógica e estrutura do edital."""

        response = client.chat.completions.create(
            model=getattr(settings, 'AI_MODEL', 'gpt-3.5-turbo'),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt_ia}
            ],
            max_tokens=1500,
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        # Parsear resposta
        raw_response = response.choices[0].message.content
        parsed = json.loads(raw_response)
        
        logger.info(f"IA analisou documento e determinou posicionamento para {len(clausulas_especificas)} cláusulas")
        return parsed
        
    except Exception as e:
        logger.error(f"Erro ao analisar documento com IA: {e}")
        # Fallback para análise básica
        return analisar_documento_basico(doc, clausulas_especificas)


def analisar_documento_basico(doc, clausulas_especificas):
    """
    Análise básica de fallback quando a IA falha.
    """
    import re
    
    # Encontrar seções 3.4.x como fallback
    clausulas_3_4 = []
    for i, p in enumerate(doc.paragraphs):
        texto = p.text.strip()
        match = re.search(r'(?<!\d)3\.4\.(\d+)', texto)
        if match:
            clausulas_3_4.append({
                'linha': i + 1,
                'numero': int(match.group(1)),
                'paragrafo': p
            })
    
    if clausulas_3_4:
        # Ordenar por número
        clausulas_3_4.sort(key=lambda x: x['numero'])
        ultimo_numero = clausulas_3_4[-1]['numero']
        
        return {
            'estrategia': 'sequencial_3_4',
            'secao_alvo': '3.4.x',
            'inserir_apos': f'3.4.{ultimo_numero}',
            'proximo_numero': ultimo_numero + 1
        }
    else:
        # Fallback genérico
        return {
            'estrategia': 'final_documento',
            'secao_alvo': 'final',
            'inserir_apos': 'ultimo_paragrafo'
        }


def gerar_clausula_especifica(tipo_clausula, descricao):
    """
    Gera cláusula específica baseada no tipo e descrição solicitada.
    
    Args:
        tipo_clausula: Tipo da cláusula (garantia_execucao, penalidade_atraso, etc.)
        descricao: Descrição específica da cláusula
    
    Returns:
        dict: Cláusula com texto, base legal e observação prática
    """
    
    clausulas_predefinidas = {
        'garantia_execucao': {
            'texto': '''3.4.16. GARANTIA DE EXECUÇÃO: O contratado deverá apresentar garantia de execução do contrato no valor de 5% (cinco por cento) do valor total do contrato, na forma de caução em dinheiro, títulos da dívida pública federal, estadual ou municipal, ou seguro-garantia, conforme disposto no art. 56 da Lei 14.133/2021.''',
            'base_legal': 'Art. 56 da Lei 14.133/2021',
            'observacao': 'A garantia deve ser apresentada no prazo de 5 dias úteis após a assinatura do contrato.'
        },
        'penalidade_atraso': {
            'texto': '''3.4.17. PENALIDADE POR ATRASO: Em caso de atraso na execução do contrato, será aplicada multa de 0,5% (meio por cento) do valor do contrato por dia de atraso, limitada a 10% (dez por cento) do valor total, conforme art. 57 da Lei 14.133/2021.''',
            'base_legal': 'Art. 57 da Lei 14.133/2021',
            'observacao': 'O atraso será contado a partir do prazo estabelecido no cronograma físico-financeiro.'
        },
        'fornecimento_garantia': {
            'texto': '''3.4.18. GARANTIA DE FORNECIMENTO: O fornecedor deverá apresentar garantia de fornecimento no valor de 2% (dois por cento) do valor total do contrato, garantindo a qualidade e conformidade dos produtos fornecidos, conforme art. 58 da Lei 14.133/2021.''',
            'base_legal': 'Art. 58 da Lei 14.133/2021',
            'observacao': 'A garantia terá validade de 90 dias após a entrega dos produtos.'
        },
        'criterio_desempate': {
            'texto': '''3.4.19. CRITÉRIO DE DESEMPATE: Em caso de empate, será adotado o seguinte critério de desempate: I - maior número de itens oferecidos; II - menor prazo de entrega; III - sorteio público, conforme art. 45 da Lei 14.133/2021.''',
            'base_legal': 'Art. 45 da Lei 14.133/2021',
            'observacao': 'O sorteio será realizado na presença dos licitantes interessados.'
        },
        'prazo_entrega': {
            'texto': '''3.4.20. PRAZO DE ENTREGA: O prazo para entrega dos produtos será de 30 (trinta) dias corridos, contados a partir da assinatura do contrato, conforme cronograma físico-financeiro anexo, nos termos do art. 40, §2º da Lei 14.133/2021.''',
            'base_legal': 'Art. 40, §2º da Lei 14.133/2021',
            'observacao': 'O prazo poderá ser prorrogado mediante justificativa técnica devidamente fundamentada.'
        },
        'documentacao_complementar': {
            'texto': '''3.4.21. DOCUMENTAÇÃO COMPLEMENTAR: O contratado deverá apresentar, no prazo de 5 (cinco) dias úteis após a assinatura do contrato, a documentação complementar especificada no Anexo II, conforme art. 25 da Lei 14.133/2021.''',
            'base_legal': 'Art. 25 da Lei 14.133/2021',
            'observacao': 'A não apresentação da documentação no prazo estabelecido implicará rescisão do contrato.'
        },
        'julgamento_tecnica_preco': {
            'texto': '''3.4.22. JULGAMENTO POR TÉCNICA E PREÇO: O julgamento das propostas será realizado mediante análise técnica e de preço, conforme disposto no art. 46 da Lei 14.133/2021, considerando os critérios de aceitabilidade e economicidade.''',
            'base_legal': 'Art. 46 da Lei 14.133/2021',
            'observacao': 'A análise técnica será realizada por comissão especializada designada pelo pregoeiro.'
        },
        'garantia_qualidade': {
            'texto': '''3.4.23. GARANTIA DE QUALIDADE: O fornecedor garantirá a qualidade e conformidade dos produtos fornecidos, conforme especificações técnicas, pelo prazo de 90 (noventa) dias após a entrega, nos termos do art. 59 da Lei 14.133/2021.''',
            'base_legal': 'Art. 59 da Lei 14.133/2021',
            'observacao': 'A garantia de qualidade é independente da garantia de execução do contrato.'
        },
        'prazo_execucao': {
            'texto': '''3.4.24. PRAZO DE EXECUÇÃO: O prazo para execução do contrato será de 180 (cento e oitenta) dias corridos, contados a partir da assinatura do contrato, conforme cronograma físico-financeiro anexo, nos termos do art. 40 da Lei 14.133/2021.''',
            'base_legal': 'Art. 40 da Lei 14.133/2021',
            'observacao': 'O prazo poderá ser prorrogado mediante justificativa técnica devidamente fundamentada.'
        },
        'reajuste_precos': {
            'texto': '''3.4.25. REAJUSTE DE PREÇOS: Os preços serão reajustados mensalmente pelo Índice Nacional de Preços ao Consumidor Amplo (IPCA), conforme art. 60 da Lei 14.133/2021, a partir do 13º mês de vigência do contrato.''',
            'base_legal': 'Art. 60 da Lei 14.133/2021',
            'observacao': 'O reajuste será aplicado automaticamente, sem necessidade de termo aditivo.'
        }
    }
    
    # Se for uma cláusula predefinida, retornar
    if tipo_clausula in clausulas_predefinidas:
        return clausulas_predefinidas[tipo_clausula]
    
    # Se for uma cláusula genérica, gerar baseada na descrição
    return {
        'texto': f'''3.4.22. {descricao.upper()}: {descricao.capitalize()}, conforme disposto na Lei 14.133/2021 e demais normas aplicáveis.''',
        'base_legal': 'Lei 14.133/2021',
        'observacao': f'Esta cláusula deve ser adequada às especificidades do objeto da licitação.'
    }


