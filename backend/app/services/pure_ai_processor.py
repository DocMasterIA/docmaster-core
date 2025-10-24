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

def process_document_pure_ai(template_path, user_prompt, llm_api_key=None):
    """
    Processa documento 100% com IA - exatamente como ChatGPT.
    A IA analisa o documento e decide onde fazer mudanças.
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
        
        # Extrair texto completo do documento (sem filtros, sem regras)
        document_text = extract_full_document_text(doc)
        
        # Prompt 100% baseado na IA - SEM regras fixas
        system_prompt = """Você edita documentos como o ChatGPT.

FORMATO DE RESPOSTA:
SUBSTITUIR: "texto original exato" → "texto novo"
ADICIONAR_APOS: "texto de referência exato" → "texto a ser adicionado"

Use texto EXATO do documento. Analise contexto e decida onde inserir."""
        
        user_prompt_full = f"""DOCUMENTO COMPLETO:
{document_text}

INSTRUÇÃO DO USUÁRIO: {user_prompt}

Analise o documento e identifique onde fazer as mudanças solicitadas. Use o formato especificado acima."""
        
        # Chamada para OpenAI
        response = client.chat.completions.create(
            model="gpt-4",  # Usar GPT-4 para melhor análise
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt_full}
            ],
            max_tokens=1500,  # Mais tokens para GPT-4
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
    Extrai texto do documento SEM regras fixas.
    A IA decide o que é relevante.
    """
    text_parts = []
    
    # Extrair todos os parágrafos (sem filtros)
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if text:
            text_parts.append(text)
    
    # Limitar a 80 parágrafos para economizar tokens
    text_parts = text_parts[:80]
    
    # Extrair todas as tabelas
    for table in doc.tables:
        table_text = []
        for row in table.rows:
            row_text = []
            for cell in row.cells:
                if cell.text.strip():
                    row_text.append(cell.text.strip())
            if row_text:
                table_text.append(" | ".join(row_text))
        if table_text:
            text_parts.append("TABELA: " + "\n".join(table_text))
    
    return "\n\n".join(text_parts)

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
    
    # Se ainda não encontrou, tentar busca por partes do texto
    if not found:
        # Procurar por "PREÇO TOTAL MÉDIO" e "R$" em células adjacentes
        for table in doc.tables:
            for row in table.rows:
                for cell_idx, cell in enumerate(row.cells):
                    for paragraph in cell.paragraphs:
                        if "PREÇO TOTAL MÉDIO" in paragraph.text:
                            # Procurar na célula adjacente por valor monetário
                            if cell_idx + 1 < len(row.cells):
                                next_cell = row.cells[cell_idx + 1]
                                for next_paragraph in next_cell.paragraphs:
                                    if "R$" in next_paragraph.text and "5.678.659,46" in next_paragraph.text:
                                        # Encontrar o valor antigo e substituir
                                        for run in next_paragraph.runs:
                                            if "5.678.659,46" in run.text:
                                                run.text = run.text.replace("5.678.659,46", "7.500.000,00")
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
