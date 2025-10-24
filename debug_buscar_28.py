#!/usr/bin/env python3
"""
Debug para buscar 2.8 no documento
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

from backend.app.models import Template

def debug_buscar_28():
    """Debug para buscar 2.8 no documento."""
    
    print("🔍 DEBUG - BUSCAR 2.8 NO DOCUMENTO")
    print("=" * 50)
    
    # Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Template: {template.name}")
    
    # Ler documento
    from docx import Document
    doc = Document(template.file.path)
    
    print("\n🔍 BUSCA POR '2.8' no documento:")
    print("-" * 30)
    
    encontrado = False
    for i, paragraph in enumerate(doc.paragraphs):
        if "2.8" in paragraph.text:
            encontrado = True
            print(f"✅ Posição {i}: {paragraph.text}")
        elif "2.7" in paragraph.text:
            print(f"📍 Posição {i}: {paragraph.text}")
        elif "2.6" in paragraph.text:
            print(f"📍 Posição {i}: {paragraph.text}")
        elif "2.5" in paragraph.text:
            print(f"📍 Posição {i}: {paragraph.text}")
        elif "2.4" in paragraph.text:
            print(f"📍 Posição {i}: {paragraph.text}")
        elif "2.3" in paragraph.text:
            print(f"📍 Posição {i}: {paragraph.text}")
        elif "2.2" in paragraph.text:
            print(f"📍 Posição {i}: {paragraph.text}")
        elif "2.1" in paragraph.text:
            print(f"📍 Posição {i}: {paragraph.text}")
    
    if not encontrado:
        print("❌ 2.8 não encontrado no documento")
    
    print("\n🔍 BUSCA POR '2.' no documento:")
    print("-" * 30)
    
    for i, paragraph in enumerate(doc.paragraphs):
        if "2." in paragraph.text and len(paragraph.text) < 200:  # Apenas parágrafos curtos
            print(f"📍 Posição {i}: {paragraph.text}")

if __name__ == "__main__":
    try:
        debug_buscar_28()
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
