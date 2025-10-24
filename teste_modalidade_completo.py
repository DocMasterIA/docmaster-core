#!/usr/bin/env python3
"""
Teste completo para verificar todas as modalidades
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

def teste_modalidade_completo():
    """Teste completo para modalidades."""
    
    print("🔧 TESTE COMPLETO: ALTERAÇÃO DE MODALIDADE")
    print("=" * 60)
    
    # Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Template: {template.name}")
    
    # Teste: Alterar modalidade para GFV
    print("\n🔍 TESTE: Alterar modalidade para 'Pregão Eletrônico GFV'")
    print("-" * 50)
    
    prompt = "Mude a modalidade da licitação para Pregão Eletrônico GFV"
    
    print(f"Prompt: {prompt}")
    
    try:
        result = process_document_with_ai(template.file.path, prompt)
        
        if result.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar todas as ocorrências
            from docx import Document
            doc = Document(result['output_path'])
            
            print("\n📊 ANÁLISE DETALHADA:")
            print("-" * 30)
            
            # Contar ocorrências
            srp_count = 0
            gfv_count = 0
            
            # Procurar em parágrafos
            for i, paragraph in enumerate(doc.paragraphs):
                text = paragraph.text.upper()
                if "PREGÃO ELETRÔNICO SRP" in text:
                    srp_count += 1
                    print(f"❌ Parágrafo {i+1}: 'PREGÃO ELETRÔNICO SRP' encontrado")
                if "PREGÃO ELETRÔNICO GFV" in text:
                    gfv_count += 1
                    print(f"✅ Parágrafo {i+1}: 'PREGÃO ELETRÔNICO GFV' encontrado")
            
            # Procurar em tabelas
            for table_idx, table in enumerate(doc.tables):
                for row_idx, row in enumerate(table.rows):
                    for cell_idx, cell in enumerate(row.cells):
                        text = cell.text.upper()
                        if "PREGÃO ELETRÔNICO SRP" in text:
                            srp_count += 1
                            print(f"❌ Tabela {table_idx+1}, Linha {row_idx+1}, Coluna {cell_idx+1}: 'PREGÃO ELETRÔNICO SRP' encontrado")
                        if "PREGÃO ELETRÔNICO GFV" in text:
                            gfv_count += 1
                            print(f"✅ Tabela {table_idx+1}, Linha {row_idx+1}, Coluna {cell_idx+1}: 'PREGÃO ELETRÔNICO GFV' encontrado")
            
            print(f"\n📊 RESUMO:")
            print(f"Ocorrências de 'PREGÃO ELETRÔNICO SRP' restantes: {srp_count}")
            print(f"Ocorrências de 'PREGÃO ELETRÔNICO GFV' encontradas: {gfv_count}")
            
            if srp_count == 0 and gfv_count > 0:
                print("✅ SUCESSO: Todas as modalidades foram alteradas!")
                return True
            else:
                print("❌ FALHA: Ainda há modalidades antigas não alteradas")
                return False
        else:
            print(f"❌ Erro: {result.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False

if __name__ == "__main__":
    try:
        sucesso = teste_modalidade_completo()
        if sucesso:
            print("\n🎉 TESTE CONCLUÍDO COM SUCESSO!")
            print("✅ Todas as modalidades foram alteradas")
        else:
            print("\n❌ TESTE FALHOU")
            print("❌ Ainda há modalidades não alteradas")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
