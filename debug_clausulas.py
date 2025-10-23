#!/usr/bin/env python3
"""
Debug específico para cláusulas
"""

import os
import sys
import django
from pathlib import Path
import tempfile
import shutil
import re

# Add the backend directory to Python path
sys.path.append('/home/adryan/Downloads/mdlicitatech-system/backend')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mdlicitatech.settings')
django.setup()

from backend.app.services.ia import generate_document_data_from_prompt
from backend.app.models import Template

def debug_clausulas():
    """Debug específico para cláusulas."""
    
    print("🔍 DEBUG DE CLÁUSULAS")
    print("=" * 40)
    
    # Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado!")
        return
    
    # Prompt simples
    prompt = "Aja como um especialista em licitações públicas e na Lei 14.133/21. Adicione uma cláusula de garantia de execução."
    
    print(f"📝 Prompt: {prompt}")
    print()
    
    # Gerar dados
    data = generate_document_data_from_prompt(template, prompt)
    
    print("📊 Dados gerados:")
    for key, value in data.items():
        if key == 'clausulas_especificas':
            print(f"   {key}: {len(value)} cláusulas")
            for i, clausula in enumerate(value):
                print(f"      [{i}] {clausula}")
        else:
            print(f"   {key}: {value}")
    
    print()
    
    # Testar função de geração de cláusula
    from backend.app.services.ia import gerar_clausula_especifica
    
    print("🧪 Testando geração de cláusula:")
    try:
        clausula = gerar_clausula_especifica('garantia_execucao', 'garantia de execução')
        print(f"   ✅ Cláusula gerada: {clausula['texto'][:100]}...")
    except Exception as e:
        print(f"   ❌ Erro na geração: {e}")

if __name__ == "__main__":
    debug_clausulas()
