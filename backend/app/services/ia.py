from django.core.files import File
import tempfile, os
import json
import re
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def process_document_with_ai(template_path, user_prompt, llm_api_key=None):
    """
    FUNCIONA EXATAMENTE COMO CHATGPT: Recebe documento + prompt, retorna documento modificado.
    """
    try:
        from openai import OpenAI
        from docx import Document
        
        # Configurar cliente OpenAI
        api_key = llm_api_key or getattr(settings, 'OPENAI_API_KEY', None)
        if not api_key:
            logger.error("No OpenAI API key provided")
            return {"error": "Chave da API OpenAI não configurada"}
        
        client = OpenAI(api_key=api_key)
        
        # Carregar documento
        doc = Document(template_path)
        
        # Extrair texto do documento
        document_text = extract_document_text_simple(doc)
        
        # Prompt simples como ChatGPT
        system_prompt = """Você é um assistente que edita documentos.

INSTRUÇÕES:
1. Receba o texto do documento
2. Faça as modificações solicitadas pelo usuário
3. Retorne o texto modificado

REGRAS:
- Mantenha a estrutura original
- Faça apenas as mudanças solicitadas
- Não adicione códigos ou formatação extra
- Retorne apenas o texto modificado"""
        
        user_prompt_full = f"""TEXTO DO DOCUMENTO:
{document_text}

INSTRUÇÃO DO USUÁRIO: {user_prompt}

Retorne o texto modificado."""
        
        # Chamada para OpenAI
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt_full}
            ],
            max_tokens=4000,
            temperature=0.1
        )
        
        # Obter texto modificado
        modified_text = response.choices[0].message.content
        
        # Aplicar mudanças ao documento
        modified_doc = apply_text_to_document(doc, modified_text)
        
        # Salvar documento modificado
        output_path = save_modified_document(modified_doc, template_path)
        
        return {
            "success": True,
            "output_path": output_path,
            "changes_made": ["Documento modificado conforme solicitado"],
            "message": "Documento modificado com sucesso"
        }
        
    except Exception as e:
        logger.error(f"Erro ao processar documento com IA: {str(e)}")
        return {"error": f"Erro na IA: {str(e)}"}


def extract_document_text_simple(doc):
    """
    Extrai texto do documento de forma simples.
    """
    text_parts = []
    
    # Extrair parágrafos
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            text_parts.append(paragraph.text.strip())
    
    # Incluir texto de tabelas
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join([cell.text.strip() for cell in row.cells])
            if row_text.strip():
                text_parts.append(row_text)
    
    # Limitar tamanho total do texto
    full_text = "\n".join(text_parts)
    if len(full_text) > 8000:  # Limite de caracteres
        full_text = full_text[:8000] + "\n... [TEXTO TRUNCADO]"
    
    return full_text


def extract_document_text_conservative(doc):
    """
    Extrai texto do documento de forma conservadora, mantendo estrutura.
    """
    text_parts = []
    
    # Extrair apenas os primeiros 30 parágrafos para evitar limite de tokens
    for i, paragraph in enumerate(doc.paragraphs[:30]):
        if paragraph.text.strip():
            text_parts.append(f"Parágrafo {i+1}: {paragraph.text.strip()}")
    
    # Incluir texto de tabelas (limitado)
    for i, table in enumerate(doc.tables[:2]):  # Máximo 2 tabelas
        text_parts.append(f"\n--- TABELA {i+1} ---")
        for row in table.rows[:5]:  # Máximo 5 linhas por tabela
            row_text = " | ".join([cell.text.strip() for cell in row.cells])
            if row_text.strip():
                text_parts.append(row_text)
    
    # Limitar tamanho total do texto
    full_text = "\n".join(text_parts)
    if len(full_text) > 6000:  # Limite menor para ser mais conservador
        full_text = full_text[:6000] + "\n... [TEXTO TRUNCADO]"
    
    return full_text


def extract_document_text(doc):
    """
    Função de compatibilidade.
    """
    return extract_document_text_simple(doc)


def apply_conservative_changes(doc, ai_response):
    """
    Aplica mudanças de forma conservadora - apenas substituições de texto.
    """
    changes_made = ai_response.get("changes_made", [])
    replacements = ai_response.get("replacements", [])
    
    logger.info(f"Aplicando {len(changes_made)} mudanças conservadoras ao documento")
    
    changes_applied = 0
    
    # Aplicar substituições em parágrafos
    for paragraph in doc.paragraphs:
        original_text = paragraph.text
        new_text = original_text
        
        for replacement in replacements:
            old_text = replacement.get("old", "")
            new_text_replacement = replacement.get("new", "")
            
            if old_text in new_text:
                new_text = new_text.replace(old_text, new_text_replacement)
                changes_applied += 1
                logger.info(f"Substituído: '{old_text}' -> '{new_text_replacement}'")
        
        # Aplicar mudança se houve alteração
        if new_text != original_text:
            # Limpar runs existentes
            for run in list(paragraph.runs):
                paragraph._p.remove(run._r)
            
            # Adicionar novo texto
            paragraph.add_run(new_text)
    
    # Aplicar substituições em tabelas
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    original_text = paragraph.text
                    new_text = original_text
                    
                    for replacement in replacements:
                        old_text = replacement.get("old", "")
                        new_text_replacement = replacement.get("new", "")
                        
                        if old_text in new_text:
                            new_text = new_text.replace(old_text, new_text_replacement)
                            changes_applied += 1
                    
                    # Aplicar mudança se houve alteração
                    if new_text != original_text:
                        # Limpar runs existentes
                        for run in list(paragraph.runs):
                            paragraph._p.remove(run._r)
                        
                        # Adicionar novo texto
                        paragraph.add_run(new_text)
    
    logger.info(f"Total de substituições aplicadas: {changes_applied}")
    return doc


def apply_ai_changes_to_document(doc, ai_response):
    """
    Função de compatibilidade - usa a nova abordagem conservadora.
    """
    return apply_conservative_changes(doc, ai_response)


def save_modified_document(doc, original_path):
    """
    Salva o documento modificado em um novo arquivo.
    """
    import uuid
    from pathlib import Path
    
    # Gerar nome único para o arquivo
    original_name = Path(original_path).stem
    filename = f"{original_name}_modificado_{uuid.uuid4().hex[:8]}.docx"
    
    # Diretório de destino
    output_dir = tempfile.gettempdir()
    output_path = os.path.join(output_dir, filename)
    
    # Salvar documento
    doc.save(output_path)
    
    logger.info(f"Documento salvo em: {output_path}")
    return output_path


def generate_document_data_from_prompt(template, user_prompt, llm_api_key=None):
    """
    Função simplificada que apenas retorna os dados básicos extraídos do prompt.
    Remove toda a complexidade desnecessária.
    """
    import re
    
    # Extrair dados básicos do prompt usando regex simples
    data = {
        'user_prompt': user_prompt,
        'numero_edital': '001/2024',  # Padrão
        'modalidade': 'Pregão Eletrônico',  # Padrão
        'objeto': 'Contratação conforme especificado',
        'orgao': 'Prefeitura Municipal',
        'valor_estimado': '1000000.00',
        'data_abertura': None,
        'local_orgao': None,
        'prazo_execucao': None
    }
    
    # Extrações simples do prompt
    valor_match = re.search(r'R\$\s*([\d.,]+)', user_prompt)
    if valor_match:
        valor_str = valor_match.group(1).replace('.', '').replace(',', '.')
        try:
            data['valor_estimado'] = f"{float(valor_str):.2f}"
        except ValueError:
            pass
    
    edital_match = re.search(r'edital\s+(\d+/\d+)', user_prompt, re.IGNORECASE)
    if edital_match:
        data['numero_edital'] = edital_match.group(1)
    
    data_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', user_prompt)
    if data_match:
        data['data_abertura'] = data_match.group(1)
    
    if 'BRASÍLIA' in user_prompt.upper():
        data['local_orgao'] = 'BRASÍLIA'
    
    return data


def create_document_from_ai(template, owner, ai_data):
    """
    Função simplificada para criar documento a partir de dados da IA.
    """
    from app.models import DocumentInstance
    from .services import generate_pdf_from_docx

    # Cria instância
    inst = DocumentInstance.objects.create(
        template=template,
        owner=owner,
        data=ai_data,
        status="draft"
    )

    # Processa documento com IA
    result = process_document_with_ai(template.file.path, ai_data.get('user_prompt', ''))
    
    if result.get('success'):
        # Salva arquivo DOCX
        with open(result['output_path'], "rb") as f:
            inst.file_docx.save(os.path.basename(result['output_path']), File(f), save=False)
        
        # Gera PDF
        pdf_path = generate_pdf_from_docx(result['output_path'])
    with open(pdf_path, "rb") as f:
        inst.file_pdf.save(os.path.basename(pdf_path), File(f), save=False)

    inst.status = "final"
    inst.save()

    # Limpa arquivos temporários
    try:
        os.remove(result['output_path'])
        os.remove(pdf_path)
    except OSError:
        pass

    return inst


def save_modified_document_from_bytes(content_bytes, original_path):
    """
    Salva documento modificado a partir de bytes.
    """
    import uuid
    import os
    
    # Gerar nome único para o arquivo
    unique_id = str(uuid.uuid4())
    filename = f"documento_contextual_{unique_id}.docx"
    
    # Caminho de destino
    dest_dir = _ensure_media_subdir("documents", "docx")
    output_path = os.path.join(dest_dir, filename)
    
    # Salvar conteúdo
    with open(output_path, 'wb') as f:
        f.write(content_bytes)
    
    return output_path


def fallback_simple_approach(template_path, user_prompt, client):
    """
    Abordagem fallback simples - extrai texto, modifica, reconstrói.
    """
    try:
        from docx import Document
        
        # Carregar documento
        doc = Document(template_path)
        
        # Extrair texto simples
        document_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        
        # Prompt simples
        system_prompt = """Você é um assistente que edita documentos.

INSTRUÇÕES:
1. Receba o texto do documento
2. Faça as modificações solicitadas
3. Retorne o texto modificado

REGRAS:
- Mantenha a estrutura
- Faça apenas as mudanças solicitadas"""
        
        user_prompt_full = f"""TEXTO DO DOCUMENTO:
{document_text}

INSTRUÇÃO: {user_prompt}

Retorne o texto modificado."""
        
        # Chamada para OpenAI
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt_full}
            ],
            max_tokens=4000,
            temperature=0.1
        )
        
        # Obter texto modificado
        modified_text = response.choices[0].message.content
        
        # Aplicar mudanças simples
        modified_doc = apply_simple_text_changes(doc, modified_text)
        
        # Salvar documento modificado
        output_path = save_modified_document(modified_doc, template_path)
        
        return {
            "success": True,
            "output_path": output_path,
            "changes_made": ["Documento modificado conforme solicitado"],
            "message": "Documento modificado com sucesso"
        }
        
    except Exception as e:
        logger.error(f"Erro no fallback: {str(e)}")
        return {"error": f"Erro no fallback: {str(e)}"}


def apply_text_to_document(doc, modified_text):
    """
    Aplica o texto modificado ao documento de forma simples.
    """
    # Dividir texto modificado em parágrafos
    paragraphs_text = modified_text.split('\n')
    
    # Aplicar aos parágrafos existentes
    for i, paragraph in enumerate(doc.paragraphs):
        if i < len(paragraphs_text):
            # Limpar runs existentes
            for run in list(paragraph.runs):
                paragraph._p.remove(run._r)
            
            # Adicionar novo texto
            paragraph.add_run(paragraphs_text[i])
        else:
            break
    
    return doc


def apply_simple_text_changes(doc, modified_text):
    """
    Aplica mudanças simples de texto.
    """
    return apply_text_to_document(doc, modified_text)


def _ensure_media_subdir(*subdirs):
    """
    Garante que o diretório de mídia existe.
    """
    import os
    from django.conf import settings
    
    media_root = getattr(settings, 'MEDIA_ROOT', 'media')
    full_path = os.path.join(media_root, *subdirs)
    
    if not os.path.exists(full_path):
        os.makedirs(full_path, exist_ok=True)
    
    return full_path


# Função de compatibilidade para manter a API existente
def call_llm_for_mapping(doc_structure, user_instructions="", llm_api_key=None):
    """
    Função de compatibilidade simplificada.
    """
    return {
        "fields": [],
        "notes": "Sistema simplificado - use process_document_with_ai() para processamento direto"
    }