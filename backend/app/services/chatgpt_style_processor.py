"""
Processador de documentos estilo ChatGPT
Replica o comportamento do ChatGPT onde você anexa um arquivo e ele modifica contextualmente
"""

from docx import Document
from docx.shared import RGBColor
from docx.oxml.shared import OxmlElement, qn
import re
import logging

logger = logging.getLogger(__name__)

def process_document_chatgpt_style(template_path, user_prompt, llm_api_key=None):
    """
    Processa documento exatamente como o ChatGPT:
    1. Analisa o documento completo
    2. Identifica onde fazer mudanças contextualmente
    3. Aplica mudanças no local correto
    4. Adiciona conteúdo onde faz sentido
    """
    try:
        from openai import OpenAI
        from django.conf import settings
        
        # Configurar cliente OpenAI
        api_key = llm_api_key or getattr(settings, 'OPENAI_API_KEY', None)
        if not api_key:
            logger.error("No OpenAI API key provided")
            return {"error": "Chave da API OpenAI não configurada"}
        
        client = OpenAI(api_key=api_key)
        
        # Carregar documento
        doc = Document(template_path)
        
        # Extrair texto completo com contexto estrutural
        document_analysis = extract_document_with_context(doc)
        
        # Prompt estilo ChatGPT
        system_prompt = """Você é um assistente especializado em editar documentos oficiais, especialmente editais de licitação.

INSTRUÇÕES:
1. Analise o documento e identifique onde fazer mudanças
2. Para SUBSTITUIÇÕES: use o formato exato do texto original
3. Para ADIÇÕES: identifique o local contextual apropriado
4. Para VALORES: encontre o valor exato no documento
5. Seja preciso e contextual

FORMATO DE RESPOSTA:
SUBSTITUIR: "texto original exato" → "texto novo"
ADICIONAR_APOS: "texto de referência exato" → "texto a ser adicionado"

EXEMPLOS:
SUBSTITUIR: "R$ 5.678.659,46" → "R$ 2.500.000,00"
SUBSTITUIR: "MUNICÍPIO DE ITAJÁ/GO" → "MUNICÍPIO DE BRASÍLIA/DF"
ADICIONAR_APOS: "3.4.14" → "3.4.15. O julgamento das propostas será realizado mediante análise técnica e de preço, conforme disposto no art. 46 da Lei 14.133/2021."
ADICIONAR_APOS: "15.16" → "OBSERVAÇÃO PRÁTICA: Recomenda-se que o pregoeiro mantenha registro detalhado de todas as etapas do processo."

IMPORTANTE:
- Use o texto EXATO do documento
- Para ADICIONAR_APOS, use apenas o número da seção (ex: "3.4.14", "15.16")
- Identifique o local contextual correto
- Mantenha a numeração sequencial
- Preserve a estrutura legal"""
        
        user_prompt_full = f"""DOCUMENTO PARA ANÁLISE:
{document_analysis}

INSTRUÇÃO DO USUÁRIO: {user_prompt}

Analise o documento e identifique as mudanças necessárias. Use o formato especificado acima."""
        
        # Chamada para OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Usar modelo mais barato
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt_full}
            ],
            max_tokens=2000,  # Reduzir tokens
            temperature=0.1
        )
        
        # Obter resposta
        raw_response = response.choices[0].message.content
        logger.info(f"Resposta da IA: {raw_response}")
        
        # Processar resposta e aplicar mudanças
        changes_applied = apply_chatgpt_style_changes(doc, raw_response)
        
        # Salvar documento modificado
        output_path = save_modified_document(doc, template_path)
        
        return {
            "success": True,
            "output_path": output_path,
            "changes_applied": changes_applied,
            "message": "Documento modificado com sucesso no estilo ChatGPT"
        }
        
    except Exception as e:
        logger.error(f"Erro ao processar documento estilo ChatGPT: {str(e)}")
        return {"error": f"Erro na IA: {str(e)}"}

def extract_document_with_context(doc):
    """
    Extrai documento com contexto estrutural para análise da IA (otimizado para tokens)
    """
    analysis = []
    
    # Analisar apenas parágrafos relevantes (otimização)
    relevant_paragraphs = []
    
    for i, paragraph in enumerate(doc.paragraphs):
        text = paragraph.text.strip()
        if not text:
            continue
            
        # Filtrar apenas parágrafos relevantes
        if (any(keyword in text.upper() for keyword in ['EDITAL', 'MUNICÍPIO', 'R$', '3.4.', '15.16', 'julgamento', 'observação', 'PREGÃO']) or
            len(text) > 50):  # Parágrafos com conteúdo substancial
            relevant_paragraphs.append((i, text))
    
    # Limitar a 50 parágrafos mais relevantes
    relevant_paragraphs = relevant_paragraphs[:50]
    
    for i, text in relevant_paragraphs:
        content_type = identify_content_type(text)
        analysis.append({
            'index': i,
            'type': content_type,
            'text': text[:200] + "..." if len(text) > 200 else text,  # Limitar tamanho
            'context': get_paragraph_context(text)
        })
    
    # Analisar apenas tabelas com valores monetários
    for table_idx, table in enumerate(doc.tables):
        table_text = extract_table_text(table)
        if 'R$' in table_text or 'PREÇO' in table_text.upper():
            analysis.append({
                'index': f"table_{table_idx}",
                'type': 'table',
                'text': table_text[:300] + "..." if len(table_text) > 300 else table_text,
                'context': 'tabela_valores'
            })
    
    # Formatar para a IA (compacto)
    formatted_analysis = "DOCUMENTO (resumo):\n\n"
    for item in analysis:
        formatted_analysis += f"[{item['index']}] {item['text']}\n"
    
    return formatted_analysis

def identify_content_type(text):
    """Identifica o tipo de conteúdo do parágrafo"""
    text_upper = text.upper()
    
    if re.search(r'^\d+\.\d+\.\d+', text):
        return 'clausula_numerada'
    elif 'EDITAL' in text_upper and 'N' in text_upper:
        return 'cabecalho_edital'
    elif 'MUNICÍPIO' in text_upper:
        return 'cabecalho_municipio'
    elif 'R$' in text and re.search(r'\d+', text):
        return 'valor_monetario'
    elif 'PREGÃO' in text_upper:
        return 'modalidade_licitacao'
    elif 'julgamento' in text_upper.lower():
        return 'secao_julgamento'
    elif 'observação' in text_upper.lower():
        return 'observacao'
    elif re.search(r'^\d+\.', text):
        return 'item_numerado'
    else:
        return 'paragrafo_normal'

def get_paragraph_context(text):
    """Extrai contexto do parágrafo"""
    context = []
    
    if '3.4.' in text:
        context.append('secao_3_4')
    if 'julgamento' in text.lower():
        context.append('julgamento')
    if 'observação' in text.lower():
        context.append('observacao')
    if 'R$' in text:
        context.append('valor')
    if 'município' in text.lower():
        context.append('municipio')
    
    return ', '.join(context) if context else 'geral'

def extract_table_text(table):
    """Extrai texto da tabela de forma estruturada"""
    rows = []
    for row in table.rows:
        cells = [cell.text.strip() for cell in row.cells]
        rows.append(" | ".join(cells))
    return "\n".join(rows)

def apply_chatgpt_style_changes(doc, ai_response):
    """
    Aplica mudanças no estilo ChatGPT - contextualmente no local correto
    """
    changes_applied = 0
    
    # Processar cada linha da resposta
    lines = ai_response.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Processar SUBSTITUIR
        if line.startswith('SUBSTITUIR:'):
            if '→' in line:
                parts = line.split('→', 1)
                old_text = parts[0].replace('SUBSTITUIR:', '').strip().strip('"')
                new_text = parts[1].strip().strip('"')
                
                if apply_substitution(doc, old_text, new_text):
                    changes_applied += 1
                    logger.info(f"Substituição aplicada: '{old_text}' → '{new_text}'")
        
        # Processar ADICIONAR_APOS
        elif line.startswith('ADICIONAR_APOS:'):
            if '→' in line:
                parts = line.split('→', 1)
                reference_text = parts[0].replace('ADICIONAR_APOS:', '').strip().strip('"')
                new_text = parts[1].strip().strip('"')
                
                if add_text_after(doc, reference_text, new_text):
                    changes_applied += 1
                    logger.info(f"Texto adicionado após '{reference_text}': '{new_text[:50]}...'")
        
        # Processar ADICIONAR_ANTES
        elif line.startswith('ADICIONAR_ANTES:'):
            if '→' in line:
                parts = line.split('→', 1)
                reference_text = parts[0].replace('ADICIONAR_ANTES:', '').strip().strip('"')
                new_text = parts[1].strip().strip('"')
                
                if add_text_before(doc, reference_text, new_text):
                    changes_applied += 1
                    logger.info(f"Texto adicionado antes de '{reference_text}': '{new_text[:50]}...'")
    
    return changes_applied

def apply_substitution(doc, old_text, new_text):
    """Aplica substituição de texto no documento"""
    found = False
    
    # Procurar em parágrafos
    for paragraph in doc.paragraphs:
        if old_text in paragraph.text:
            # Substituir texto mantendo formatação
            for run in paragraph.runs:
                if old_text in run.text:
                    run.text = run.text.replace(old_text, new_text)
                    run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                    found = True
                    break
    
    # Procurar em tabelas
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    if old_text in paragraph.text:
                        for run in paragraph.runs:
                            if old_text in run.text:
                                run.text = run.text.replace(old_text, new_text)
                                run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                                found = True
                                break
    
    return found

def add_text_after(doc, reference_text, new_text):
    """Adiciona texto após o texto de referência - MELHORADO para inserção contextual"""
    found = False
    
    # Procurar em parágrafos com busca mais inteligente
    for i, paragraph in enumerate(doc.paragraphs):
        if reference_text in paragraph.text:
            # Inserir após este parágrafo
            new_p_elem = OxmlElement('w:p')
            paragraph._element.addnext(new_p_elem)
            new_p = type(paragraph)(new_p_elem, paragraph._parent)
            
            run = new_p.add_run()
            run.text = new_text
            run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
            found = True
            logger.info(f"Texto adicionado após parágrafo {i}: '{reference_text[:50]}...'")
            break
    
    # Se não encontrou, procurar por variações do texto de referência
    if not found:
        # Buscar por variações mais flexíveis
        variations = [
            reference_text,
            reference_text.replace("3.4.14", "3.4.14."),
            reference_text.replace("3.4.14", "3.4.14:"),
            "3.4.14",  # Buscar apenas o número
            "Critérios de julgamento",  # Buscar por palavras-chave
            "julgamento"  # Buscar por palavra-chave
        ]
        
        for variation in variations:
            for i, paragraph in enumerate(doc.paragraphs):
                if variation in paragraph.text:
                    # Inserir após este parágrafo
                    new_p_elem = OxmlElement('w:p')
                    paragraph._element.addnext(new_p_elem)
                    new_p = type(paragraph)(new_p_elem, paragraph._parent)
                    
                    run = new_p.add_run()
                    run.text = new_text
                    run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                    found = True
                    logger.info(f"Texto adicionado após parágrafo {i} (variação '{variation}'): '{reference_text[:50]}...'")
                    break
            if found:
                break
    
    # Procurar em tabelas
    if not found:
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        if reference_text in paragraph.text:
                            # Inserir após este parágrafo na célula
                            new_p_elem = OxmlElement('w:p')
                            paragraph._element.addnext(new_p_elem)
                            new_p = type(paragraph)(new_p_elem, paragraph._parent)
                            
                            run = new_p.add_run()
                            run.text = new_text
                            run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                            found = True
                            logger.info(f"Texto adicionado em tabela após: '{reference_text[:50]}...'")
                            break
                    if found:
                        break
                if found:
                    break
            if found:
                break
    
    return found

def add_text_before(doc, reference_text, new_text):
    """Adiciona texto antes do texto de referência"""
    found = False
    
    # Procurar em parágrafos
    for paragraph in doc.paragraphs:
        if reference_text in paragraph.text:
            # Inserir antes deste parágrafo
            new_p_elem = OxmlElement('w:p')
            paragraph._element.getparent().insert(
                paragraph._element.getparent().index(paragraph._element),
                new_p_elem
            )
            new_p = type(paragraph)(new_p_elem, paragraph._parent)
            
            run = new_p.add_run()
            run.text = new_text
            run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
            found = True
            break
    
    return found

def save_modified_document(doc, original_path):
    """Salva o documento modificado"""
    import uuid
    import tempfile
    import os
    from pathlib import Path
    
    # Gerar nome único
    original_name = Path(original_path).stem
    filename = f"{original_name}_chatgpt_style_{uuid.uuid4().hex[:8]}.docx"
    
    # Diretório de destino
    output_dir = tempfile.gettempdir()
    output_path = os.path.join(output_dir, filename)
    
    # Salvar documento
    doc.save(output_path)
    
    logger.info(f"Documento estilo ChatGPT salvo em: {output_path}")
    return output_path
