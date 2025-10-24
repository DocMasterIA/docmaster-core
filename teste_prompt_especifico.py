#!/usr/bin/env python3
"""
Teste do prompt específico para serviços de limpeza urbana
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

def teste_prompt_especifico():
    """Teste do prompt específico para serviços de limpeza urbana."""
    
    print("🧹 TESTE: SERVIÇOS DE LIMPEZA URBANA - RIO DE JANEIRO")
    print("=" * 70)
    
    # Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Template: {template.name}")
    
    # Teste 1: Prompt original (pode não funcionar bem)
    print("\n🔍 TESTE 1: Prompt original")
    print("-" * 50)
    
    prompt1 = "Adapte este documento para uma licitação de serviços de limpeza urbana no Rio de Janeiro no valor de R$ 8.000.000,00. Altere para Pregão Eletrônico e adicione critérios de responsabilidade social."
    
    print(f"Prompt: {prompt1}")
    
    try:
        result1 = process_document_with_ai(template.file.path, prompt1)
        
        if result1.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar mudanças
            from docx import Document
            doc1 = Document(result1['output_path'])
            
            # Verificar cidade
            rio_encontrado = False
            for paragraph in doc1.paragraphs:
                if "RIO DE JANEIRO" in paragraph.text.upper():
                    rio_encontrado = True
                    print("✅ Cidade alterada para RIO DE JANEIRO")
                    break
            
            # Verificar valor na tabela
            valor_alterado = False
            for table in doc1.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if "R$ 8.000.000,00" in cell.text:
                            valor_alterado = True
                            print("✅ Valor alterado para R$ 8.000.000,00")
                            break
                    if valor_alterado:
                        break
                if valor_alterado:
                    break
            
            # Verificar modalidade
            modalidade_alterada = False
            for paragraph in doc1.paragraphs:
                if "PREGÃO ELETRÔNICO" in paragraph.text.upper():
                    modalidade_alterada = True
                    print("✅ Modalidade alterada para PREGÃO ELETRÔNICO")
                    break
            
            # Verificar responsabilidade social
            responsabilidade_encontrada = False
            for paragraph in doc1.paragraphs:
                if "RESPONSABILIDADE SOCIAL" in paragraph.text.upper():
                    responsabilidade_encontrada = True
                    print("✅ Critérios de responsabilidade social adicionados")
                    break
            
            print(f"\n📊 RESULTADO TESTE 1:")
            print(f"Cidade: {'✅' if rio_encontrado else '❌'}")
            print(f"Valor: {'✅' if valor_alterado else '❌'}")
            print(f"Modalidade: {'✅' if modalidade_alterada else '❌'}")
            print(f"Responsabilidade Social: {'✅' if responsabilidade_encontrada else '❌'}")
            
        else:
            print(f"❌ Erro: {result1.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False
    
    # Teste 2: Prompt mais específico (deve funcionar melhor)
    print("\n🔍 TESTE 2: Prompt mais específico")
    print("-" * 50)
    
    prompt2 = "Adapte este documento para uma licitação de serviços de limpeza urbana no Rio de Janeiro. Altere o PREÇO TOTAL MÉDIO na tabela para R$ 8.000.000,00. Mude a modalidade para Pregão Eletrônico e adicione critérios de responsabilidade social."
    
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
            valor_alterado = False
            for table in doc2.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if "R$ 8.000.000,00" in cell.text:
                            valor_alterado = True
                            print("✅ Valor alterado para R$ 8.000.000,00")
                            break
                    if valor_alterado:
                        break
                if valor_alterado:
                    break
            
            # Verificar modalidade
            modalidade_alterada = False
            for paragraph in doc2.paragraphs:
                if "PREGÃO ELETRÔNICO" in paragraph.text.upper():
                    modalidade_alterada = True
                    print("✅ Modalidade alterada para PREGÃO ELETRÔNICO")
                    break
            
            # Verificar responsabilidade social
            responsabilidade_encontrada = False
            for paragraph in doc2.paragraphs:
                if "RESPONSABILIDADE SOCIAL" in paragraph.text.upper():
                    responsabilidade_encontrada = True
                    print("✅ Critérios de responsabilidade social adicionados")
                    break
            
            print(f"\n📊 RESULTADO TESTE 2:")
            print(f"Cidade: {'✅' if rio_encontrado else '❌'}")
            print(f"Valor: {'✅' if valor_alterado else '❌'}")
            print(f"Modalidade: {'✅' if modalidade_alterada else '❌'}")
            print(f"Responsabilidade Social: {'✅' if responsabilidade_encontrada else '❌'}")
            
            # Comparar resultados
            print(f"\n🎯 COMPARAÇÃO:")
            print(f"Teste 1 (prompt genérico): Valor {'✅' if valor_alterado else '❌'}")
            print(f"Teste 2 (prompt específico): Valor {'✅' if valor_alterado else '❌'}")
            
        else:
            print(f"❌ Erro: {result2.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False

if __name__ == "__main__":
    try:
        teste_prompt_especifico()
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
