#!/usr/bin/env python3
"""
Debug para verificar por que cláusula 2.9 não está sendo encontrada
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

from backend.app.services.ia import process_document_with_ai
from backend.app.models import Template

def debug_clausula_29():
    """Debug para verificar cláusula 2.9."""
    
    print("🔍 DEBUG - CLAUSULA 2.9")
    print("=" * 50)
    
    # Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Template: {template.name}")
    
    prompt = "Adicione uma cláusula 2.9 sobre critérios de responsabilidade social"
    
    try:
        result = process_document_with_ai(template.file.path, prompt)
        
        if result.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar mudanças
            from docx import Document
            doc = Document(result['output_path'])
            
            print(f"📊 Total de parágrafos: {len(doc.paragraphs)}")
            
            # Buscar cláusula 2.9
            print("\n🔍 BUSCA POR '2.9':")
            for i, paragraph in enumerate(doc.paragraphs):
                if "2.9" in paragraph.text:
                    print(f"  Posição {i}: {paragraph.text}")
            
            # Buscar por "responsabilidade social"
            print("\n🔍 BUSCA POR 'responsabilidade social':")
            for i, paragraph in enumerate(doc.paragraphs):
                if "responsabilidade" in paragraph.text.lower() and "social" in paragraph.text.lower():
                    print(f"  Posição {i}: {paragraph.text}")
            
            # Buscar por "Critérios de Responsabilidade Social"
            print("\n🔍 BUSCA POR 'Critérios de Responsabilidade Social':")
            for i, paragraph in enumerate(doc.paragraphs):
                if "Critérios de Responsabilidade Social" in paragraph.text:
                    print(f"  Posição {i}: {paragraph.text}")
            
            # Buscar por "contratação priorizará"
            print("\n🔍 BUSCA POR 'contratação priorizará':")
            for i, paragraph in enumerate(doc.paragraphs):
                if "contratação priorizará" in paragraph.text.lower():
                    print(f"  Posição {i}: {paragraph.text}")
            
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
        debug_clausula_29()
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
