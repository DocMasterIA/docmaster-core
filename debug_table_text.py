#!/usr/bin/env python3
"""
Debug do texto da tabela
Verifica o formato exato do texto na tabela
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

from backend.app.models import Template
from docx import Document

def debug_table_text():
    """Debug do texto da tabela."""
    
    print("🔍 DEBUG DO TEXTO DA TABELA")
    print("=" * 40)
    
    # 1. Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Usando template: {template.name}")
    
    # 2. Carregar documento
    doc = Document(template.file.path)
    
    # 3. Procurar em tabelas
    print("\n🔍 Procurando em tabelas...")
    for table_idx, table in enumerate(doc.tables):
        print(f"\n📊 Tabela {table_idx}:")
        for row_idx, row in enumerate(table.rows):
            for cell_idx, cell in enumerate(row.cells):
                for paragraph in cell.paragraphs:
                    if paragraph.text.strip():
                        print(f"  Célula [{row_idx}][{cell_idx}]: {repr(paragraph.text)}")
                        if "PREÇO TOTAL MÉDIO" in paragraph.text:
                            print(f"  ✅ ENCONTRADO: {repr(paragraph.text)}")
    
    return True

if __name__ == "__main__":
    try:
        sucesso = debug_table_text()
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
