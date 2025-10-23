#!/usr/bin/env python3
"""
Debug simples para cláusulas
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

from backend.app.services.ia import generate_document_data_from_prompt, gerar_clausula_especifica
from backend.app.models import Template

def debug_clausulas_simples():
    """Debug simples para cláusulas."""
    
    print("🔍 DEBUG SIMPLES DE CLÁUSULAS")
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
    
    print("📊 Cláusulas específicas:")
    for i, clausula in enumerate(data['clausulas_especificas']):
        print(f"   [{i}] Tipo: {clausula['tipo']}")
        print(f"       Descrição: {clausula['descricao']}")
        print(f"       Texto completo: {clausula['texto_completo']}")
        print()
    
    # Testar geração de cláusula para cada tipo
    print("🧪 Testando geração de cláusulas:")
    for clausula_info in data['clausulas_especificas']:
        try:
            print(f"   Testando: {clausula_info['tipo']} - {clausula_info['descricao']}")
            clausula = gerar_clausula_especifica(
                clausula_info['tipo'], 
                clausula_info['descricao']
            )
            print(f"   ✅ Sucesso: {clausula['texto'][:50]}...")
        except Exception as e:
            print(f"   ❌ Erro: {e}")
        print()

if __name__ == "__main__":
    debug_clausulas_simples()
