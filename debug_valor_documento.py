#!/usr/bin/env python3
"""
Debug para encontrar o valor no documento.
"""

import os
import sys
import django

# Configurar Django
sys.path.append('/home/adryan/Downloads/mdlicitatech-system/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mdlicitatech.settings')
django.setup()

from backend.app.models import Template
from docx import Document


def debug_documento():
    """
    Debug do documento para encontrar o valor.
    """
    print("🔍 Debug do documento")
    print("=" * 60)
    
    # Buscar o template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return
    
    print(f"📄 Template: {template.name}")
    
    # Carregar documento
    doc = Document(template.file.path)
    
    print(f"📊 Estrutura do documento:")
    print(f"   - Parágrafos: {len(doc.paragraphs)}")
    print(f"   - Tabelas: {len(doc.tables)}")
    
    # Procurar por valores específicos em parágrafos
    print("\n🔍 Procurando em parágrafos:")
    for i, paragraph in enumerate(doc.paragraphs):
        text = paragraph.text
        if "5.678.659,46" in text or "PREÇO TOTAL MÉDIO" in text:
            print(f"   Parágrafo {i+1}: {text}")
    
    # Procurar por valores específicos em tabelas
    print("\n🔍 Procurando em tabelas:")
    for i, table in enumerate(doc.tables):
        print(f"   --- TABELA {i+1} ---")
        for row_idx, row in enumerate(table.rows):
            for cell_idx, cell in enumerate(row.cells):
                for paragraph in cell.paragraphs:
                    text = paragraph.text
                    if "5.678.659,46" in text or "PREÇO TOTAL MÉDIO" in text:
                        print(f"   Tabela {i+1}, Linha {row_idx+1}, Célula {cell_idx+1}: {text}")
    
    # Extrair todo o texto das tabelas
    print("\n📊 Todo o conteúdo das tabelas:")
    for i, table in enumerate(doc.tables):
        print(f"   --- TABELA {i+1} ---")
        for row_idx, row in enumerate(table.rows):
            row_text = " | ".join([cell.text.strip() for cell in row.cells])
            if row_text.strip():
                print(f"   Linha {row_idx+1}: {row_text}")
    
    # Procurar por padrões de valor
    print("\n🔍 Procurando padrões de valor:")
    for i, paragraph in enumerate(doc.paragraphs):
        text = paragraph.text
        if "R$" in text and any(char.isdigit() for char in text):
            print(f"   Parágrafo {i+1}: {text}")
    
    # Procurar em tabelas
    for i, table in enumerate(doc.tables):
        for row_idx, row in enumerate(table.rows):
            for cell_idx, cell in enumerate(row.cells):
                for paragraph in cell.paragraphs:
                    text = paragraph.text
                    if "R$" in text and any(char.isdigit() for char in text):
                        print(f"   Tabela {i+1}, Linha {row_idx+1}, Célula {cell_idx+1}: {text}")


if __name__ == "__main__":
    debug_documento()
