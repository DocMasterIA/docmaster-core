#!/usr/bin/env python3
"""
Teste da solução para substituição específica em tabelas
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

def teste_solucao_tabela():
    """Teste da solução para tabelas."""
    
    print("🔧 TESTE SOLUÇÃO - SUBSTITUIÇÃO ESPECÍFICA EM TABELAS")
    print("=" * 70)
    
    # Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Template: {template.name}")
    
    # Teste: Prompt específico para tabela
    print("\n🔍 TESTE: Modalidade na tabela")
    print("-" * 50)
    
    prompt = "Mude a MODALIDADE DA LICITAÇÃO na tabela para Pregão Eletrônico GGF"
    
    print(f"Prompt: {prompt}")
    
    try:
        result = process_document_with_ai(template.file.path, prompt)
        
        if result.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar mudanças
            from docx import Document
            doc = Document(result['output_path'])
            
            print("\n📊 ANÁLISE DETALHADA:")
            print("-" * 30)
            
            # Verificar modalidade na tabela
            modalidade_tabela = False
            for table_idx, table in enumerate(doc.tables):
                for row_idx, row in enumerate(table.rows):
                    for cell_idx, cell in enumerate(row.cells):
                        if "PREGÃO ELETRÔNICO GGF" in cell.text.upper():
                            modalidade_tabela = True
                            print(f"✅ Modalidade alterada na tabela {table_idx+1}, linha {row_idx+1}, coluna {cell_idx+1}: PREGÃO ELETRÔNICO GGF")
                            break
                    if modalidade_tabela:
                        break
                if modalidade_tabela:
                    break
            
            # Verificar se ainda há PREGÃO ELETRÔNICO SRP na tabela
            srp_tabela = False
            for table_idx, table in enumerate(doc.tables):
                for row_idx, row in enumerate(table.rows):
                    for cell_idx, cell in enumerate(row.cells):
                        if "PREGÃO ELETRÔNICO SRP" in cell.text.upper():
                            srp_tabela = True
                            print(f"❌ Ainda há PREGÃO ELETRÔNICO SRP na tabela {table_idx+1}, linha {row_idx+1}, coluna {cell_idx+1}")
                            break
                    if srp_tabela:
                        break
                if srp_tabela:
                    break
            
            # Verificar modalidade em parágrafos (não deveria ter mudado)
            modalidade_paragrafos = False
            for paragraph in doc.paragraphs:
                if "PREGÃO ELETRÔNICO GGF" in paragraph.text.upper():
                    modalidade_paragrafos = True
                    print("❌ Modalidade alterada em parágrafos (não deveria ter mudado)")
                    break
            
            print(f"\n📊 RESULTADO:")
            print(f"Modalidade na tabela: {'✅' if modalidade_tabela else '❌'}")
            print(f"SRP restante na tabela: {'❌' if srp_tabela else '✅'}")
            print(f"Modalidade em parágrafos: {'❌' if modalidade_paragrafos else '✅'}")
            
            # Resultado final
            if modalidade_tabela and not srp_tabela and not modalidade_paragrafos:
                print("\n🎉 SUCESSO: Substituição específica em tabelas funcionando!")
                return True
            else:
                print("\n❌ FALHA: Substituição específica em tabelas precisa melhorar")
                return False
            
        else:
            print(f"❌ Erro: {result.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False

if __name__ == "__main__":
    try:
        sucesso = teste_solucao_tabela()
        if sucesso:
            print("\n🎉 TESTE CONCLUÍDO COM SUCESSO!")
            print("✅ Substituição específica em tabelas funcionando perfeitamente")
        else:
            print("\n❌ TESTE FALHOU")
            print("❌ Substituição específica em tabelas precisa melhorar")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
