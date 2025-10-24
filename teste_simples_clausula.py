#!/usr/bin/env python3
"""
Teste simples para debug de cláusulas
"""

import os
import sys
import django
from pathlib import Path

# Add the backend directory to Python path
sys.path.append('/home/adryan/mdlicitatech-system/backend')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mdlicitatech.settings')
django.setup()

from backend.app.services.pure_ai_processor import process_document_pure_ai

def teste_simples_clausula():
    """Teste simples para debug de cláusulas."""
    
    print("🔍 TESTE SIMPLES - CLAUSULA 2.9")
    print("=" * 50)
    
    from backend.app.models import Template
    
    # Buscar template do banco
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado no banco")
        return False
    
    template_path = template.file.path
    print(f"📄 Template do banco: {template.name}")
    
    if not os.path.exists(template_path):
        print(f"❌ Template não encontrado: {template_path}")
        return False
    
    print(f"📄 Template: {template_path}")
    
    prompt = "Adicione uma cláusula 2.9 sobre critérios de responsabilidade social"
    
    print(f"Prompt: {prompt}")
    
    try:
        result = process_document_pure_ai(template_path, prompt)
        
        if result.get('success'):
            print("✅ Documento processado com sucesso")
            print(f"📁 Arquivo gerado: {result['output_path']}")
            
            # Verificar se arquivo existe
            if os.path.exists(result['output_path']):
                print("✅ Arquivo de saída existe")
                
                # Ler documento
                from docx import Document
                doc = Document(result['output_path'])
                
                print(f"📊 Total de parágrafos: {len(doc.paragraphs)}")
                
                # Buscar cláusula 2.9
                clausula_29_encontrada = False
                for i, paragraph in enumerate(doc.paragraphs):
                    if "2.9" in paragraph.text:
                        clausula_29_encontrada = True
                        print(f"✅ Cláusula 2.9 encontrada na posição {i}")
                        print(f"📝 Texto: {paragraph.text}")
                        break
                
                if not clausula_29_encontrada:
                    print("❌ Cláusula 2.9 não encontrada")
                    
                    # Buscar por "responsabilidade social"
                    print("\n🔍 Busca por 'responsabilidade social':")
                    for i, paragraph in enumerate(doc.paragraphs):
                        if "responsabilidade" in paragraph.text.lower() and "social" in paragraph.text.lower():
                            print(f"  Posição {i}: {paragraph.text[:100]}...")
                
            else:
                print("❌ Arquivo de saída não existe")
        else:
            print(f"❌ Erro: {result.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        teste_simples_clausula()
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
