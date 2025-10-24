#!/usr/bin/env python3
"""
Debug para encontrar onde está a ocorrência restante de ITAJÁ
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

from backend.app.services.ia import process_document_with_ai
from backend.app.models import Template

def debug_itaja_restante():
    """Debug para encontrar onde está a ocorrência restante de ITAJÁ."""
    
    print("🔍 DEBUG: ENCONTRAR OCORRÊNCIA RESTANTE DE ITAJÁ")
    print("=" * 60)
    
    # Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Template: {template.name}")
    
    # Processar documento
    prompt = "Modifique o documento para uma licitação em Belo Horizonte e o valor R$ 200.000.000,00 e adicione cláusulas de penalidades por atraso."
    
    try:
        result = process_document_with_ai(template.file.path, prompt)
        
        if result.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Analisar documento para encontrar ITAJÁ restante
            from docx import Document
            doc = Document(result['output_path'])
            
            print("\n🔍 PROCURANDO OCORRÊNCIAS DE 'ITAJÁ':")
            print("-" * 50)
            
            # Procurar em parágrafos
            for i, paragraph in enumerate(doc.paragraphs):
                if 'ITAJÁ' in paragraph.text.upper():
                    print(f"📍 Parágrafo {i+1}: {paragraph.text.strip()}")
            
            # Procurar em tabelas
            for table_idx, table in enumerate(doc.tables):
                for row_idx, row in enumerate(table.rows):
                    for cell_idx, cell in enumerate(row.cells):
                        if 'ITAJÁ' in cell.text.upper():
                            print(f"📍 Tabela {table_idx+1}, Linha {row_idx+1}, Coluna {cell_idx+1}: {cell.text.strip()}")
            
            # Contar ocorrências
            itaja_count = 0
            belo_horizonte_count = 0
            
            for paragraph in doc.paragraphs:
                text = paragraph.text.upper()
                itaja_count += text.count('ITAJÁ')
                belo_horizonte_count += text.count('BELO HORIZONTE')
            
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        text = cell.text.upper()
                        itaja_count += text.count('ITAJÁ')
                        belo_horizonte_count += text.count('BELO HORIZONTE')
            
            print(f"\n📊 RESUMO:")
            print(f"Ocorrências de 'ITAJÁ' restantes: {itaja_count}")
            print(f"Ocorrências de 'BELO HORIZONTE' encontradas: {belo_horizonte_count}")
            
            if itaja_count == 0:
                print("✅ SUCESSO: Todas as ocorrências de ITAJÁ foram alteradas!")
            else:
                print("❌ AINDA HÁ OCORRÊNCIAS DE ITAJÁ NÃO ALTERADAS")
            
            return itaja_count == 0
        else:
            print(f"❌ Erro: {result.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False

if __name__ == "__main__":
    try:
        sucesso = debug_itaja_restante()
        if sucesso:
            print("\n🎉 DEBUG CONCLUÍDO: Todas as ocorrências foram alteradas!")
        else:
            print("\n❌ DEBUG: Ainda há ocorrências não alteradas")
    except Exception as e:
        print(f"❌ Erro no debug: {e}")
        import traceback
        traceback.print_exc()
