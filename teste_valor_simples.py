#!/usr/bin/env python3
"""
Teste simples para verificar se o valor monetário está sendo extraído
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
from backend.app.services.pure_ai_processor import extract_full_document_text
from docx import Document

def teste_extracao_valor():
    """Teste para verificar se o valor está sendo extraído corretamente."""
    
    print("🔍 TESTE DE EXTRAÇÃO DE VALOR")
    print("=" * 50)
    
    # Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Template: {template.name}")
    print(f"📁 Arquivo: {template.file.path}")
    
    # Carregar documento
    doc = Document(template.file.path)
    
    # Extrair texto
    text = extract_full_document_text(doc)
    
    print(f"\n📝 Texto extraído ({len(text)} caracteres):")
    print("-" * 50)
    print(text[:500] + "..." if len(text) > 500 else text)
    
    # Procurar pelo valor específico
    valor_original = "R$ 5.678.659,46"
    if valor_original in text:
        print(f"\n✅ Valor encontrado: {valor_original}")
    else:
        print(f"\n❌ Valor NÃO encontrado: {valor_original}")
        
        # Procurar por valores similares
        import re
        valores = re.findall(r'R\$\s*[\d.,]+', text)
        print(f"💰 Valores encontrados no documento: {valores}")
    
    # Procurar em tabelas especificamente
    print(f"\n🔍 Verificando tabelas:")
    for i, table in enumerate(doc.tables):
        print(f"Tabela {i+1}:")
        for j, row in enumerate(table.rows):
            for k, cell in enumerate(row.cells):
                if "R$" in cell.text:
                    print(f"  Linha {j+1}, Coluna {k+1}: {cell.text.strip()}")
    
    return True

if __name__ == "__main__":
    try:
        teste_extracao_valor()
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
