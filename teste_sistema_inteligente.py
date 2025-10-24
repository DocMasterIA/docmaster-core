#!/usr/bin/env python3
"""
Teste do sistema inteligente para substituição em tabelas
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

def teste_sistema_inteligente():
    """Teste do sistema inteligente."""
    
    print("🧠 TESTE SISTEMA INTELIGENTE - SUBSTITUIÇÃO EM TABELAS")
    print("=" * 70)
    
    # Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Template: {template.name}")
    
    # Teste 1: Prompt específico para tabela
    print("\n🔍 TESTE 1: Modalidade na tabela")
    print("-" * 50)
    
    prompt1 = "Mude a MODALIDADE DA LICITAÇÃO na tabela para Pregão Eletrônico GGF"
    
    print(f"Prompt: {prompt1}")
    
    try:
        result1 = process_document_with_ai(template.file.path, prompt1)
        
        if result1.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar mudanças
            from docx import Document
            doc1 = Document(result1['output_path'])
            
            # Verificar modalidade na tabela
            modalidade_tabela = False
            for table_idx, table in enumerate(doc1.tables):
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
            for table_idx, table in enumerate(doc1.tables):
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
            
            print(f"\n📊 RESULTADO TESTE 1:")
            print(f"Modalidade na tabela: {'✅' if modalidade_tabela else '❌'}")
            print(f"SRP restante na tabela: {'❌' if srp_tabela else '✅'}")
            
        else:
            print(f"❌ Erro: {result1.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False
    
    # Teste 2: Prompt completo
    print("\n🔍 TESTE 2: Prompt completo")
    print("-" * 50)
    
    prompt2 = "Adapte este documento para uma licitação de serviços de limpeza urbana no Rio de Janeiro. Altere o PREÇO TOTAL MÉDIO na tabela para R$ 8.000.000,00. Mude a MODALIDADE DA LICITAÇÃO na tabela para Pregão Eletrônico GGF."
    
    print(f"Prompt: {prompt2}")
    
    try:
        result2 = process_document_with_ai(template.file.path, prompt2)
        
        if result2.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar mudanças
            doc2 = Document(result2['output_path'])
            
            # Verificar cidade
            rio_encontrado = False
            for paragraph in doc2.paragraphs:
                if "RIO DE JANEIRO" in paragraph.text.upper():
                    rio_encontrado = True
                    print("✅ Cidade alterada para RIO DE JANEIRO")
                    break
            
            # Verificar valor na tabela
            valor_tabela = False
            for table_idx, table in enumerate(doc2.tables):
                for row_idx, row in enumerate(table.rows):
                    for cell_idx, cell in enumerate(row.cells):
                        if "R$ 8.000.000,00" in cell.text:
                            valor_tabela = True
                            print(f"✅ Valor alterado na tabela {table_idx+1}, linha {row_idx+1}, coluna {cell_idx+1}: R$ 8.000.000,00")
                            break
                    if valor_tabela:
                        break
                if valor_tabela:
                    break
            
            # Verificar modalidade na tabela
            modalidade_tabela = False
            for table_idx, table in enumerate(doc2.tables):
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
            
            print(f"\n📊 RESULTADO TESTE 2:")
            print(f"Cidade: {'✅' if rio_encontrado else '❌'}")
            print(f"Valor na tabela: {'✅' if valor_tabela else '❌'}")
            print(f"Modalidade na tabela: {'✅' if modalidade_tabela else '❌'}")
            
        else:
            print(f"❌ Erro: {result2.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False

if __name__ == "__main__":
    try:
        teste_sistema_inteligente()
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
