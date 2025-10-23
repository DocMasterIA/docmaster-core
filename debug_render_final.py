#!/usr/bin/env python3
"""
Debug final para renderização
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
from docx import Document

def debug_render_final():
    """Debug final para renderização."""
    
    print("🔍 DEBUG RENDERIZAÇÃO FINAL")
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
    
    print("📊 Dados gerados:")
    for key, value in data.items():
        if key == 'clausulas_especificas':
            print(f"   {key}: {len(value)} cláusulas")
            for i, clausula in enumerate(value):
                print(f"      [{i}] {type(clausula)}: {clausula}")
        else:
            print(f"   {key}: {value}")
    
    print()
    
    # Simular o que acontece no render.py
    print("🔄 Simulando renderização...")
    
    # Carregar documento
    doc = Document(template.file.path)
    print(f"   ✅ Documento carregado: {len(doc.paragraphs)} parágrafos")
    
    # Simular field_map
    field_map = data
    
    print(f"   📊 Field map: {type(field_map)}")
    print(f"   📋 Cláusulas específicas: {field_map.get('clausulas_especificas', [])}")
    
    # Simular processamento de cláusulas
    clausulas_especificas = field_map.get('clausulas_especificas', [])
    
    print(f"   📋 Processando {len(clausulas_especificas)} cláusula(s) específica(s)...")
    
    for i, clausula_info in enumerate(clausulas_especificas):
        print(f"   [{i}] Processando cláusula:")
        print(f"       Tipo: {type(clausula_info)}")
        print(f"       Valor: {clausula_info}")
        
        if isinstance(clausula_info, dict):
            print(f"       ✅ É um dicionário")
            print(f"       tipo: {clausula_info.get('tipo', 'N/A')}")
            print(f"       descricao: {clausula_info.get('descricao', 'N/A')}")
        else:
            print(f"       ❌ NÃO é um dicionário")
        
        print()

if __name__ == "__main__":
    debug_render_final()