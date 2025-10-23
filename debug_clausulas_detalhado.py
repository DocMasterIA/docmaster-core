#!/usr/bin/env python3
"""
Debug detalhado para cláusulas
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

def debug_clausulas_detalhado():
    """Debug detalhado para cláusulas."""
    
    print("🔍 DEBUG DETALHADO DE CLÁUSULAS")
    print("=" * 50)
    
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
    
    print("📊 Dados completos:")
    for key, value in data.items():
        print(f"   {key}: {type(value)} = {value}")
    
    print()
    
    print("📋 Cláusulas específicas detalhadas:")
    clausulas = data.get('clausulas_especificas', [])
    print(f"   Tipo da lista: {type(clausulas)}")
    print(f"   Tamanho: {len(clausulas)}")
    
    for i, clausula in enumerate(clausulas):
        print(f"   [{i}] Tipo: {type(clausula)}")
        print(f"       Valor: {clausula}")
        if isinstance(clausula, dict):
            for k, v in clausula.items():
                print(f"           {k}: {v}")
        print()

if __name__ == "__main__":
    debug_clausulas_detalhado()
