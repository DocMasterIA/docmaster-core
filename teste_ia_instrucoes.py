#!/usr/bin/env python3
"""
Teste para verificar se a IA está retornando instruções corretas
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

def teste_ia_instrucoes():
    """Teste para verificar instruções da IA."""
    
    print("🔍 TESTE - INSTRUÇÕES DA IA")
    print("=" * 50)
    
    from backend.app.models import Template
    
    # Buscar template do banco
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado no banco")
        return False
    
    template_path = template.file.path
    print(f"📄 Template: {template.name}")
    
    # TESTE 1: Cláusula 4.2
    print("\n🔍 TESTE 1: Cláusula 4.2")
    print("-" * 50)
    
    prompt1 = "Adicione uma cláusula 4.2 sobre sustentabilidade ambiental após o parágrafo 4.1"
    
    print(f"Prompt: {prompt1}")
    
    try:
        result1 = process_document_pure_ai(template_path, prompt1)
        
        if result1.get('success'):
            print("✅ Documento processado com sucesso")
            print(f"📁 Arquivo gerado: {result1['output_path']}")
        else:
            print(f"❌ Erro: {result1.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # TESTE 2: Cláusula 2.9
    print("\n🔍 TESTE 2: Cláusula 2.9")
    print("-" * 50)
    
    prompt2 = "Adicione uma cláusula 2.9 sobre critérios de responsabilidade social"
    
    print(f"Prompt: {prompt2}")
    
    try:
        result2 = process_document_pure_ai(template_path, prompt2)
        
        if result2.get('success'):
            print("✅ Documento processado com sucesso")
            print(f"📁 Arquivo gerado: {result2['output_path']}")
        else:
            print(f"❌ Erro: {result2.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        teste_ia_instrucoes()
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
