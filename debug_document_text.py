#!/usr/bin/env python3
"""
Debug do texto do documento
Verifica o que está sendo enviado para a IA
"""

import os
import sys
import django
from pathlib import Path
import tempfile

# Add the backend directory to Python path
sys.path.append('/home/adryan/mdlicitatech-system/backend')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mdlicitatech.settings')
django.setup()

from backend.app.services.pure_ai_processor import extract_full_document_text
from backend.app.models import Template
from docx import Document

def debug_document_text():
    """Debug do texto do documento."""
    
    print("🔍 DEBUG DO TEXTO DO DOCUMENTO")
    print("=" * 40)
    
    # 1. Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Usando template: {template.name}")
    
    # 2. Carregar documento
    doc = Document(template.file.path)
    
    # 3. Extrair texto
    print("\n📝 Extraindo texto do documento...")
    document_text = extract_full_document_text(doc)
    
    print(f"📊 Tamanho do texto: {len(document_text)} caracteres")
    lines = document_text.split('\n')
    print(f"📊 Número de linhas: {len(lines)}")
    
    # 4. Procurar pelo valor original
    print("\n🔍 Procurando pelo valor original...")
    if "R$ 5.678.659,46" in document_text:
        print("✅ Valor original encontrado no texto!")
    else:
        print("❌ Valor original NÃO encontrado no texto!")
    
    # 5. Procurar por variações do valor
    print("\n🔍 Procurando por variações do valor...")
    variations = [
        "5.678.659,46",
        "5.678.659",
        "5678659,46",
        "5678659",
        "PREÇO TOTAL MÉDIO",
        "PREÇO TOTAL"
    ]
    
    for variation in variations:
        if variation in document_text:
            print(f"✅ Encontrado: {variation}")
        else:
            print(f"❌ Não encontrado: {variation}")
    
    # 6. Mostrar parte do texto
    print("\n📝 Primeiros 500 caracteres do texto:")
    print("-" * 50)
    print(document_text[:500])
    print("-" * 50)
    
    # 7. Mostrar parte do texto com valores
    print("\n📝 Procurando por valores monetários...")
    for i, line in enumerate(lines):
        if 'R$' in line:
            print(f"Linha {i}: {line}")
    
    return True

if __name__ == "__main__":
    try:
        sucesso = debug_document_text()
        if sucesso:
            print("\n🎉 DEBUG CONCLUÍDO!")
        else:
            print("\n❌ DEBUG FALHOU")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Erro no debug: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
