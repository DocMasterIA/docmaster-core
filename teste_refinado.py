#!/usr/bin/env python3
"""
Teste refinado para verificar melhorias no sistema
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

def teste_refinado():
    """Teste refinado do sistema."""
    
    print("🔧 TESTE REFINADO - SISTEMA OTIMIZADO")
    print("=" * 70)
    
    # Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Template: {template.name}")
    
    # Teste 1: Modalidade em tabela
    print("\n🔍 TESTE 1: Modalidade em tabela")
    print("-" * 50)
    
    prompt1 = "Mude a modalidade de PREGÃO ELETRÔNICO SRP para Tomada de Preços"
    
    print(f"Prompt: {prompt1}")
    
    try:
        result1 = process_document_with_ai(template.file.path, prompt1)
        
        if result1.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar mudanças
            from docx import Document
            doc1 = Document(result1['output_path'])
            
            # Verificar modalidade em parágrafos
            modalidade_paragrafos = False
            for paragraph in doc1.paragraphs:
                if "TOMADA DE PREÇOS" in paragraph.text.upper():
                    modalidade_paragrafos = True
                    print("✅ Modalidade alterada em parágrafos: TOMADA DE PREÇOS")
                    break
            
            # Verificar modalidade em tabelas
            modalidade_tabelas = False
            for table in doc1.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if "TOMADA DE PREÇOS" in cell.text.upper():
                            modalidade_tabelas = True
                            print("✅ Modalidade alterada em tabelas: TOMADA DE PREÇOS")
                            break
                    if modalidade_tabelas:
                        break
                if modalidade_tabelas:
                    break
            
            # Verificar se ainda há PREGÃO ELETRÔNICO SRP
            srp_restante = False
            for paragraph in doc1.paragraphs:
                if "PREGÃO ELETRÔNICO SRP" in paragraph.text.upper():
                    srp_restante = True
                    print("❌ Ainda há PREGÃO ELETRÔNICO SRP em parágrafos")
                    break
            
            for table in doc1.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if "PREGÃO ELETRÔNICO SRP" in cell.text.upper():
                            srp_restante = True
                            print("❌ Ainda há PREGÃO ELETRÔNICO SRP em tabelas")
                            break
                    if srp_restante:
                        break
                if srp_restante:
                    break
            
            print(f"\n📊 RESULTADO TESTE 1:")
            print(f"Modalidade em parágrafos: {'✅' if modalidade_paragrafos else '❌'}")
            print(f"Modalidade em tabelas: {'✅' if modalidade_tabelas else '❌'}")
            print(f"SRP restante: {'❌' if srp_restante else '✅'}")
            
        else:
            print(f"❌ Erro: {result1.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False
    
    # Teste 2: Cláusula numerada
    print("\n🔍 TESTE 2: Cláusula numerada")
    print("-" * 50)
    
    prompt2 = "Adicione uma nova cláusula 2.9 sobre critérios de responsabilidade social"
    
    print(f"Prompt: {prompt2}")
    
    try:
        result2 = process_document_with_ai(template.file.path, prompt2)
        
        if result2.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar mudanças
            doc2 = Document(result2['output_path'])
            
            # Verificar se cláusula 2.9 foi adicionada
            clausula_29_encontrada = False
            clausula_29_texto = ""
            for paragraph in doc2.paragraphs:
                if "2.9" in paragraph.text and "responsabilidade social" in paragraph.text.lower():
                    clausula_29_encontrada = True
                    clausula_29_texto = paragraph.text
                    print("✅ Cláusula 2.9 encontrada")
                    break
            
            # Verificar se foi adicionada após 2.8
            clausula_28_encontrada = False
            clausula_29_posicao = -1
            clausula_28_posicao = -1
            
            for i, paragraph in enumerate(doc2.paragraphs):
                if "2.8" in paragraph.text:
                    clausula_28_encontrada = True
                    clausula_28_posicao = i
                    print(f"✅ Cláusula 2.8 encontrada na posição {i}")
                if "2.9" in paragraph.text and "responsabilidade social" in paragraph.text.lower():
                    clausula_29_posicao = i
                    print(f"✅ Cláusula 2.9 encontrada na posição {i}")
            
            # Verificar se 2.9 está após 2.8
            posicao_correta = False
            if clausula_28_posicao != -1 and clausula_29_posicao != -1:
                if clausula_29_posicao > clausula_28_posicao:
                    posicao_correta = True
                    print("✅ Cláusula 2.9 está após 2.8")
                else:
                    print("❌ Cláusula 2.9 não está após 2.8")
            
            print(f"\n📊 RESULTADO TESTE 2:")
            print(f"Cláusula 2.9 encontrada: {'✅' if clausula_29_encontrada else '❌'}")
            print(f"Cláusula 2.8 encontrada: {'✅' if clausula_28_encontrada else '❌'}")
            print(f"Posição correta: {'✅' if posicao_correta else '❌'}")
            
            if clausula_29_encontrada:
                print(f"📝 Texto da cláusula: {clausula_29_texto[:100]}...")
            
        else:
            print(f"❌ Erro: {result2.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False
    
    # Teste 3: Prompt completo e eficiente
    print("\n🔍 TESTE 3: Prompt completo e eficiente")
    print("-" * 50)
    
    prompt3 = "Modifique este documento para uma licitação de equipamentos de informática em São Paulo. Altere o PREÇO TOTAL MÉDIO na tabela para R$ 2.500.000,00. Mude a modalidade de PREGÃO ELETRÔNICO SRP para Tomada de Preços. Adicione uma nova cláusula 2.9 sobre critérios de responsabilidade social."
    
    print(f"Prompt: {prompt3}")
    
    try:
        result3 = process_document_with_ai(template.file.path, prompt3)
        
        if result3.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar mudanças
            doc3 = Document(result3['output_path'])
            
            # Verificar cidade
            sao_paulo_encontrado = False
            for paragraph in doc3.paragraphs:
                if "SÃO PAULO" in paragraph.text.upper():
                    sao_paulo_encontrado = True
                    print("✅ Cidade alterada para SÃO PAULO")
                    break
            
            # Verificar valor
            valor_alterado = False
            for table in doc3.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if "R$ 2.500.000,00" in cell.text:
                            valor_alterado = True
                            print("✅ Valor alterado para R$ 2.500.000,00")
                            break
                    if valor_alterado:
                        break
                if valor_alterado:
                    break
            
            # Verificar modalidade
            modalidade_alterada = False
            for paragraph in doc3.paragraphs:
                if "TOMADA DE PREÇOS" in paragraph.text.upper():
                    modalidade_alterada = True
                    print("✅ Modalidade alterada para TOMADA DE PREÇOS")
                    break
            
            # Verificar cláusula
            clausula_encontrada = False
            for paragraph in doc3.paragraphs:
                if "2.9" in paragraph.text and "responsabilidade social" in paragraph.text.lower():
                    clausula_encontrada = True
                    print("✅ Cláusula 2.9 adicionada")
                    break
            
            print(f"\n📊 RESULTADO TESTE 3:")
            print(f"Cidade: {'✅' if sao_paulo_encontrado else '❌'}")
            print(f"Valor: {'✅' if valor_alterado else '❌'}")
            print(f"Modalidade: {'✅' if modalidade_alterada else '❌'}")
            print(f"Cláusula: {'✅' if clausula_encontrada else '❌'}")
            
        else:
            print(f"❌ Erro: {result3.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False

if __name__ == "__main__":
    try:
        teste_refinado()
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
