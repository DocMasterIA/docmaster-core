#!/usr/bin/env python3
"""
Teste específico para verificar se modalidades estão sendo alteradas
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

def teste_modalidade():
    """Teste específico para modalidades."""
    
    print("🔧 TESTE: ALTERAÇÃO DE MODALIDADE")
    print("=" * 60)
    
    # Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Template: {template.name}")
    
    # Teste 1: Alterar modalidade para GFV
    print("\n🔍 TESTE 1: Alterar modalidade para 'Pregão Eletrônico GFV'")
    print("-" * 50)
    
    prompt1 = "Mude a modalidade da licitação para Pregão Eletrônico GFV"
    
    print(f"Prompt: {prompt1}")
    
    try:
        result1 = process_document_with_ai(template.file.path, prompt1)
        
        if result1.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar se a modalidade foi alterada
            from docx import Document
            doc1 = Document(result1['output_path'])
            
            modalidade_alterada = False
            modalidade_antiga = False
            
            for paragraph in doc1.paragraphs:
                text = paragraph.text.upper()
                if "PREGÃO ELETRÔNICO GFV" in text:
                    modalidade_alterada = True
                    print("✅ Modalidade alterada para 'PREGÃO ELETRÔNICO GFV'")
                if "PREGÃO ELETRÔNICO SRP" in text:
                    modalidade_antiga = True
                    print("❌ Modalidade antiga ainda presente: 'PREGÃO ELETRÔNICO SRP'")
            
            # Verificar em tabelas também
            for table in doc1.tables:
                for row in table.rows:
                    for cell in row.cells:
                        text = cell.text.upper()
                        if "PREGÃO ELETRÔNICO GFV" in text:
                            modalidade_alterada = True
                            print("✅ Modalidade alterada para 'PREGÃO ELETRÔNICO GFV' (em tabela)")
                        if "PREGÃO ELETRÔNICO SRP" in text:
                            modalidade_antiga = True
                            print("❌ Modalidade antiga ainda presente: 'PREGÃO ELETRÔNICO SRP' (em tabela)")
            
            if modalidade_alterada and not modalidade_antiga:
                print("✅ TESTE 1: PASSOU - Modalidade alterada com sucesso")
                return True
            else:
                print("❌ TESTE 1: FALHOU - Modalidade não foi alterada corretamente")
                return False
        else:
            print(f"❌ TESTE 1: Erro - {result1.get('error')}")
            return False
    except Exception as e:
        print(f"❌ TESTE 1: Exceção - {e}")
        return False

if __name__ == "__main__":
    try:
        sucesso = teste_modalidade()
        if sucesso:
            print("\n🎉 TESTE CONCLUÍDO COM SUCESSO!")
            print("✅ A modalidade foi alterada corretamente")
        else:
            print("\n❌ TESTE FALHOU")
            print("❌ A modalidade não foi alterada")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
