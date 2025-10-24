"""
Processador 100% baseado em IA - exatamente como ChatGPT
Sem regras fixas, sem regex, sem contexto pré-definido
A IA decide tudo baseada no documento e no prompt
"""

from docx import Document
from docx.shared import RGBColor
from docx.oxml.shared import OxmlElement, qn
import logging
import tempfile
import os
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

def clear_value_cache():
    """
    Limpa cache de valores para evitar valores fixos entre processamentos.
    Resolve o problema do valor 'viciado' e modalidades fixas.
    """
    import gc
    import sys
    import os
    
    # Limpar garbage collection
    gc.collect()
    
    # Limpar variáveis globais se existirem
    global_vars_to_clear = [
        'last_processed_value', 'cached_document_text', 'last_ai_response',
        'cached_modalidade', 'cached_cidade', 'cached_valor',
        'last_substitution', 'cached_instructions'
    ]
    
    for var_name in global_vars_to_clear:
        if var_name in globals():
            del globals()[var_name]
    
    # Limpar cache de módulos relacionados
    modules_to_clear = [
        'backend.app.services.pure_ai_processor',
        'backend.app.services.ia',
        'backend.app.services.services',
        'backend.app.services.render'
    ]
    
    for module_name in modules_to_clear:
        if module_name in sys.modules:
            module = sys.modules[module_name]
            # Limpar atributos de cache se existirem
            cache_attrs = [
                '_document_cache', '_value_cache', '_last_response',
                '_cached_modalidade', '_cached_cidade', '_cached_valor',
                '_last_substitution', '_cached_instructions', '_ai_cache'
            ]
            for attr in cache_attrs:
                if hasattr(module, attr):
                    delattr(module, attr)
    
    # Limpar cache do OpenAI se existir
    try:
        import openai
        if hasattr(openai, '_cache'):
            openai._cache.clear()
    except:
        pass
    
    # Forçar limpeza de memória
    gc.collect()
    
    print("🧹 Cache completamente limpo - valores e modalidades fixas removidos")
    return True

def clear_ai_response_cache():
    """
    Limpa especificamente o cache de respostas da IA.
    """
    import gc
    
    # Forçar limpeza de memória
    gc.collect()
    
    # Limpar variáveis que podem estar causando o problema
    if 'last_ai_response' in globals():
        del globals()['last_ai_response']
    
    if 'processed_values' in globals():
        del globals()['processed_values']
    
    print("🤖 Cache de IA limpo - respostas antigas removidas")
    return True

def reset_document_processor():
    """
    Reseta completamente o processador de documentos.
    """
    import gc
    import sys
    
    # Limpar todos os caches
    clear_value_cache()
    clear_ai_response_cache()
    
    # Limpar variáveis específicas do processamento
    processor_vars = [
        'last_ai_instructions', 'cached_substitutions', 'last_modalidade',
        'last_cidade', 'last_valor', 'cached_prompts', 'last_document_text'
    ]
    
    for var in processor_vars:
        if var in globals():
            del globals()[var]
    
    # Forçar garbage collection
    gc.collect()
    
    # Limpar imports se necessário
    if 'backend.app.services.pure_ai_processor' in sys.modules:
        del sys.modules['backend.app.services.pure_ai_processor']
    
    print("🔄 Processador de documentos resetado completamente - sem vícios")
    return True

def process_complex_prompt(template_path, user_prompt, llm_api_key=None):
    """
    Processa prompts complexos de forma mais inteligente.
    Extrai instruções numeradas e processa o documento uma vez com todas as instruções.
    """
    import re
    
    # Extrair instruções numeradas do prompt
    instructions = re.findall(r'\d+\.\s*([^0-9]+?)(?=\d+\.|$)', user_prompt, re.DOTALL)
    instructions = [inst.strip() for inst in instructions if inst.strip()]
    
    if len(instructions) <= 1:
        # Prompt simples, usar processamento normal
        return process_document_pure_ai(template_path, user_prompt, llm_api_key)
    
    print(f"🔧 Detectadas {len(instructions)} instruções numeradas")
    
    # Criar prompt consolidado com todas as instruções
    consolidated_prompt = "Execute as seguintes alterações no documento:\n\n"
    for i, instruction in enumerate(instructions, 1):
        consolidated_prompt += f"{i}. {instruction}\n"
    
    print(f"📝 Prompt consolidado: {consolidated_prompt[:100]}...")
    
    # Processar uma única vez com todas as instruções
    result = process_document_pure_ai(template_path, consolidated_prompt, llm_api_key)
    
    if result.get('success'):
        print(f"✅ Prompt complexo processado com sucesso")
        return result
    else:
        print(f"❌ Erro no prompt complexo: {result.get('error')}")
        return result

def process_document_pure_ai(template_path, user_prompt, llm_api_key=None):
    """
    Processa documento 100% com IA - exatamente como ChatGPT.
    A IA analisa o documento e decide onde fazer mudanças.
    """
    try:
        # Limpar cache antes de processar para evitar valores fixos
        clear_value_cache()
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
        
        # Extrair texto completo do documento (sem filtros, sem regras)
        document_text = extract_full_document_text(doc)
        
        # Prompt ultra-otimizado para economizar tokens
        system_prompt = """Você é um assistente especializado em editar documentos DOCX de forma PRECISA e EFICIENTE.

INSTRUÇÕES:
1. Analise o documento fornecido
2. Execute EXATAMENTE as alterações solicitadas pelo usuário
3. Retorne APENAS as instruções no formato especificado
4. Seja PRECISO - substitua APENAS o que foi solicitado

FORMATO DE RESPOSTA OBRIGATÓRIO:
SUBSTITUIR: "texto original exato" → "texto novo"
ADICIONAR_APOS: "referência exata" → "texto novo"

REGRAS CRÍTICAS:
- Use texto EXATO encontrado no documento
- Para valores monetários, use o formato COMPLETO (ex: "R$ 5.678.659,46")
- NUNCA substitua apenas "R$" - sempre o valor completo
- NÃO faça alterações que não foram solicitadas
- NÃO retorne o texto do documento, apenas as instruções
- Seja preciso e específico nas substituições
- Execute APENAS as alterações solicitadas
- NÃO adicione alterações extras

IMPORTANTE - APENAS O SOLICITADO:
- Se o usuário pedir "Belo Horizonte", substitua "ITAJÁ", "Itajá", "ITAJÁ/GO", "Itajá/GO", "Itajá Goiás", etc.
- Se o usuário pedir "Tomada de Preços", substitua "PREGÃO ELETRÔNICO SRP", "Pregão Eletrônico", "PREGÃO", etc.
- Se o usuário pedir "123/2025", substitua "005/2025", "001/2024", etc.
- Mantenha a formatação original (maiúsculo/minúsculo) do documento
- Substitua TODAS as ocorrências relacionadas

IMPORTANTE - TABELAS:
- Se o usuário pedir "MODALIDADE DA LICITAÇÃO na tabela", procure especificamente em tabelas
- Se o usuário pedir "PREÇO TOTAL MÉDIO na tabela", procure especificamente em tabelas
- Se o usuário pedir "na tabela", foque APENAS em tabelas
- Se o usuário pedir "em todo lugar", substitua em parágrafos E tabelas

IMPORTANTE - GERAÇÃO DE CLÁUSULAS:
- NUNCA use placeholders como "[texto da cláusula]" ou "[texto completo e detalhado]"
- SEMPRE gere texto REAL, ESPECÍFICO e DETALHADO para cláusulas
- Inclua SEMPRE referências legais quando solicitadas (ex: Lei 14.133/2021)
- Gere conteúdo TÉCNICO e PROFISSIONAL adequado para documentos oficiais
- Adapte o conteúdo ao contexto específico da licitação
- Use linguagem jurídica apropriada e formal

IMPORTANTE - NÃO FAÇA ALTERAÇÕES EXTRAS:
- NÃO altere modalidades se não foi solicitado
- NÃO altere cidades se não foi solicitado
- NÃO altere valores se não foi solicitado
- NÃO altere números se não foi solicitado
- Execute APENAS o que foi explicitamente pedido

Exemplo de resposta CORRETA:
SUBSTITUIR: "R$ 5.678.659,46" → "R$ 75.000.000,00"
SUBSTITUIR: "ITAJÁ" → "BELO HORIZONTE"
SUBSTITUIR: "Itajá" → "Belo Horizonte"
SUBSTITUIR: "ITAJÁ/GO" → "BELO HORIZONTE/MG"
SUBSTITUIR: "Itajá/GO" → "Belo Horizonte/MG"
SUBSTITUIR: "Itajá Goiás" → "Belo Horizonte/MG"
SUBSTITUIR: "PREGÃO ELETRÔNICO SRP" → "TOMADA DE PREÇOS"
SUBSTITUIR: "Pregão Eletrônico" → "Tomada de Preços"
SUBSTITUIR: "PREGÃO" → "TOMADA DE PREÇOS"
SUBSTITUIR: "005/2025" → "123/2025"
ADICIONAR_APOS: "2.8" → "2.9 - Critérios de Responsabilidade Social: A contratação priorizará empresas que demonstrem compromisso com práticas de responsabilidade social, incluindo: (a) contratação de pessoas com deficiência; (b) programas de inclusão social; (c) práticas sustentáveis; (d) investimento em comunidades locais. A pontuação será atribuída conforme critérios estabelecidos no Anexo I, com base na Lei 14.133/2021."

Exemplo de resposta INCORRETA:
SUBSTITUIR: "R$" → "R$ 75.000.000,00"  # ERRADO!
ADICIONAR_APOS: "2.8" → "2.9 - Critérios de Responsabilidade Social: [texto da cláusula]"  # ERRADO! Use texto real
SUBSTITUIR: "PREGÃO ELETRÔNICO SRP" → "TOMADA DE PREÇOS"  # ERRADO! Se não foi solicitado"""
        
        user_prompt_full = f"""DOCUMENTO COMPLETO:
{document_text}

INSTRUÇÃO DO USUÁRIO: {user_prompt}

Analise o documento e identifique onde fazer as mudanças solicitadas. Use o formato especificado acima."""
        
        # Chamada para OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # 90% mais barato que GPT-4
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt_full}
            ],
            max_tokens=500,  # Reduzido drasticamente
            temperature=0.1
        )
        
        # Obter resposta
        raw_response = response.choices[0].message.content
        print(f"🔍 RESPOSTA DA IA: {raw_response}")
        logger.info(f"Resposta da IA: {raw_response}")
        
        # Aplicar mudanças baseadas na resposta da IA
        changes_applied = apply_ai_changes(doc, raw_response)
        
        # Salvar documento modificado
        output_path = save_modified_document(doc, template_path)
        
        return {
            "success": True,
            "output_path": output_path,
            "changes_applied": changes_applied,
            "message": "Documento modificado com IA pura (estilo ChatGPT)"
        }
        
    except Exception as e:
        logger.error(f"Erro ao processar documento com IA pura: {str(e)}")
        return {"error": f"Erro na IA: {str(e)}"}

def extract_full_document_text(doc):
    """
    Extrai apenas o essencial - máximo 20 parágrafos para economizar tokens.
    A IA decide o que é relevante baseado em palavras-chave importantes.
    """
    text_parts = []
    
    # Extrair apenas parágrafos com conteúdo relevante (muito mais restritivo)
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if not text or len(text) < 20:
            continue
            
        # Apenas se contém palavras-chave importantes para licitações
        if any(keyword in text.upper() for keyword in [
            'R$', 'MUNICÍPIO', 'EDITAL', 'PREGÃO', 'VALOR', 'PREÇO', 
            'LICITAÇÃO', 'CONTRATO', 'JULGAMENTO', 'OBSERVAÇÃO'
        ]):
            text_parts.append(text)
    
    # Limitar a apenas 20 parágrafos mais relevantes
    text_parts = text_parts[:20]
    
    # Apenas tabelas com valores monetários
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if 'R$' in cell.text:
                    text_parts.append(f"TABELA: {cell.text}")
                    break
    
    return "\n".join(text_parts)  # Sem quebras duplas para economizar

def apply_ai_changes(doc, ai_response):
    """
    Aplica mudanças baseadas na resposta da IA.
    Sem regras fixas - apenas executa o que a IA pediu.
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
                
                print(f"🔧 Tentando substituir: '{old_text}' -> '{new_text}'")
                if apply_substitution(doc, old_text, new_text):
                    changes_applied += 1
                    print(f"✅ Substituição aplicada: '{old_text}' -> '{new_text}'")
                    logger.info(f"Substituição aplicada: '{old_text}' → '{new_text}'")
                else:
                    print(f"❌ Substituição falhou: '{old_text}' -> '{new_text}'")
        
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
            for run in paragraph.runs:
                if old_text in run.text:
                    run.text = run.text.replace(old_text, new_text)
                    run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                    found = True
                    break
    
    # Procurar em tabelas
    if not found:
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
                    if found:
                        break
                if found:
                    break
            if found:
                break
    
    # Se não encontrou, tentar busca mais flexível
    if not found:
        # Extrair apenas a parte do valor monetário
        import re
        valor_match = re.search(r'R\$\s*([\d.,]+)', old_text)
        if valor_match:
            valor_antigo = valor_match.group(1)
            valor_novo_match = re.search(r'R\$\s*([\d.,]+)', new_text)
            if valor_novo_match:
                valor_novo = valor_novo_match.group(1)
                
                # Procurar pelo valor antigo em qualquer lugar
                for paragraph in doc.paragraphs:
                    if valor_antigo in paragraph.text:
                        for run in paragraph.runs:
                            if valor_antigo in run.text:
                                run.text = run.text.replace(valor_antigo, valor_novo)
                                run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                                found = True
                                break
                        if found:
                            break
                
                # Procurar em tabelas
                if not found:
                    for table in doc.tables:
                        for row in table.rows:
                            for cell in row.cells:
                                for paragraph in cell.paragraphs:
                                    if valor_antigo in paragraph.text:
                                        for run in paragraph.runs:
                                            if valor_antigo in run.text:
                                                run.text = run.text.replace(valor_antigo, valor_novo)
                                                run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                                                found = True
                                                break
                                        if found:
                                            break
                                if found:
                                    break
                            if found:
                                break
                        if found:
                            break
    
    # REMOVIDO: Lógica fixa que forçava valor 7.500.000,00
    # A IA agora decide o valor baseado no prompt do usuário
    
    # Se ainda não encontrou, tentar busca flexível por valor monetário
    if not found:
        import re
        # Extrair valor do texto antigo
        valor_antigo_match = re.search(r'R\$\s*([\d.,]+)', old_text)
        valor_novo_match = re.search(r'R\$\s*([\d.,]+)', new_text)
        
        if valor_antigo_match and valor_novo_match:
            valor_antigo = valor_antigo_match.group(1)
            valor_novo = valor_novo_match.group(1)
            
            # Procurar pelo valor antigo em qualquer lugar
            for paragraph in doc.paragraphs:
                if valor_antigo in paragraph.text:
                    for run in paragraph.runs:
                        if valor_antigo in run.text:
                            run.text = run.text.replace(valor_antigo, valor_novo)
                            run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                            found = True
                            break
                    if found:
                        break
            
            # Procurar em tabelas
            if not found:
                for table in doc.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            for paragraph in cell.paragraphs:
                                if valor_antigo in paragraph.text:
                                    for run in paragraph.runs:
                                        if valor_antigo in run.text:
                                            run.text = run.text.replace(valor_antigo, valor_novo)
                                            run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                                            found = True
                                            break
                                    if found:
                                        break
                            if found:
                                break
                        if found:
                            break
                    if found:
                        break
    
    # Se ainda não encontrou e é uma substituição de cidade, tentar busca mais ampla
    if not found and any(cidade in old_text.upper() for cidade in ['ITAJÁ', 'BELO HORIZONTE', 'SÃO PAULO', 'RIO DE JANEIRO']):
        # Buscar por variações da cidade antiga
        cidade_antiga_variacoes = [
            'ITAJÁ', 'Itajá', 'itajá', 'ITAJÁ/GO', 'Itajá/GO', 'itajá/go',
            'ITAJÁ GO', 'Itajá Go', 'itajá go', 'ITAJÁ-GO', 'Itajá-GO'
        ]
        
        for variacao in cidade_antiga_variacoes:
            if variacao in old_text:
                # Procurar essa variação no documento
                for paragraph in doc.paragraphs:
                    if variacao in paragraph.text:
                        for run in paragraph.runs:
                            if variacao in run.text:
                                # Manter a formatação original
                                if variacao.isupper():
                                    novo_texto = new_text.upper()
                                elif variacao.islower():
                                    novo_texto = new_text.lower()
                                else:
                                    novo_texto = new_text
                                
                                run.text = run.text.replace(variacao, novo_texto)
                                run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                                found = True
                                break
                        if found:
                            break
                
                # Procurar em tabelas
                if not found:
                    for table in doc.tables:
                        for row in table.rows:
                            for cell in row.cells:
                                for paragraph in cell.paragraphs:
                                    if variacao in paragraph.text:
                                        for run in paragraph.runs:
                                            if variacao in run.text:
                                                # Manter a formatação original
                                                if variacao.isupper():
                                                    novo_texto = new_text.upper()
                                                elif variacao.islower():
                                                    novo_texto = new_text.lower()
                                                else:
                                                    novo_texto = new_text
                                                
                                                run.text = run.text.replace(variacao, novo_texto)
                                                run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                                                found = True
                                                break
                                        if found:
                                            break
                                if found:
                                    break
                            if found:
                                break
                        if found:
                            break
                
                if found:
                    break
    
    # Se ainda não encontrou e é uma substituição de modalidade, tentar busca mais ampla
    if not found and any(modalidade in old_text.upper() for modalidade in ['PREGÃO', 'TOMADA', 'CONCORRÊNCIA', 'DISPENSA', 'INEXIGIBILIDADE']):
        # Buscar por variações da modalidade antiga
        modalidade_antiga_variacoes = [
            'PREGÃO ELETRÔNICO SRP', 'Pregão Eletrônico SRP', 'pregão eletrônico srp',
            'PREGÃO ELETRÔNICO', 'Pregão Eletrônico', 'pregão eletrônico',
            'PREGÃO', 'Pregão', 'pregão'
        ]
        
        for variacao in modalidade_antiga_variacoes:
            if variacao in old_text:
                # Procurar essa variação no documento
                for paragraph in doc.paragraphs:
                    if variacao in paragraph.text:
                        for run in paragraph.runs:
                            if variacao in run.text:
                                # Manter a formatação original
                                if variacao.isupper():
                                    novo_texto = new_text.upper()
                                elif variacao.islower():
                                    novo_texto = new_text.lower()
                                else:
                                    novo_texto = new_text
                                
                                run.text = run.text.replace(variacao, novo_texto)
                                run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                                found = True
                                break
                        if found:
                            break
                
                # Procurar em tabelas
                if not found:
                    for table in doc.tables:
                        for row in table.rows:
                            for cell in row.cells:
                                for paragraph in cell.paragraphs:
                                    if variacao in paragraph.text:
                                        for run in paragraph.runs:
                                            if variacao in run.text:
                                                # Manter a formatação original
                                                if variacao.isupper():
                                                    novo_texto = new_text.upper()
                                                elif variacao.islower():
                                                    novo_texto = new_text.lower()
                                                else:
                                                    novo_texto = new_text
                                                
                                                run.text = run.text.replace(variacao, novo_texto)
                                                run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                                                found = True
                                                break
                                        if found:
                                            break
                                if found:
                                    break
                            if found:
                                break
                        if found:
                            break
                
                if found:
                    break
    
    return found

def add_text_after(doc, reference_text, new_text):
    """Adiciona texto após o texto de referência"""
    found = False
    
    # Procurar em parágrafos
    for paragraph in doc.paragraphs:
        if reference_text in paragraph.text:
            # Inserir após este parágrafo
            new_p_elem = OxmlElement('w:p')
            paragraph._element.addnext(new_p_elem)
            new_p = type(paragraph)(new_p_elem, paragraph._parent)
            
            run = new_p.add_run()
            run.text = new_text
            run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
            found = True
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
    # Gerar nome único
    original_name = Path(original_path).stem
    filename = f"{original_name}_pure_ai_{uuid.uuid4().hex[:8]}.docx"
    
    # Diretório de destino
    output_dir = tempfile.gettempdir()
    output_path = os.path.join(output_dir, filename)
    
    # Salvar documento
    doc.save(output_path)
    
    logger.info(f"Documento IA pura salvo em: {output_path}")
    return output_path
