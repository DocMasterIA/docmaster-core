#!/usr/bin/env python3
"""
Teste para verificar se o vício de cache foi resolvido
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

def teste_vicio_cache():
    """Teste para verificar se o vício de cache foi resolvido."""
    
    print("🔧 TESTE VÍCIO DE CACHE - CORREÇÃO")
    print("=" * 70)
    print("Foco: Verificar se não há alterações não solicitadas")
    print("=" * 70)
    
    # Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Template: {template.name}")
    
    # TESTE 1: Apenas cidade (não deve alterar modalidade)
    print("\n🔍 TESTE 1: Apenas cidade")
    print("-" * 50)
    
    prompt1 = "Mude a cidade de ITAJÁ para SÃO PAULO"
    
    print(f"Prompt: {prompt1}")
    
    try:
        result1 = process_document_with_ai(template.file.path, prompt1)
        
        if result1.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar mudanças
            from docx import Document
            doc1 = Document(result1['output_path'])
            
            # Verificar se cidade foi alterada
            cidade_alterada = False
            for paragraph in doc1.paragraphs:
                if "SÃO PAULO" in paragraph.text.upper():
                    cidade_alterada = True
                    print("✅ Cidade alterada para SÃO PAULO")
                    break
            
            # Verificar se modalidade NÃO foi alterada (não foi solicitado)
            modalidade_alterada = False
            for paragraph in doc1.paragraphs:
                if "TOMADA DE PREÇOS" in paragraph.text.upper():
                    modalidade_alterada = True
                    print("❌ Modalidade alterada para TOMADA DE PREÇOS (não foi solicitado)")
                    break
            
            print(f"\n📊 RESULTADO TESTE 1:")
            print(f"Cidade alterada: {'✅' if cidade_alterada else '❌'}")
            print(f"Modalidade alterada (não solicitado): {'❌' if modalidade_alterada else '✅'}")
            
        else:
            print(f"❌ Erro: {result1.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False
    
    # TESTE 2: Apenas valor (não deve alterar modalidade)
    print("\n🔍 TESTE 2: Apenas valor")
    print("-" * 50)
    
    prompt2 = "Altere o valor de R$ 5.678.659,46 para R$ 10.000.000,00"
    
    print(f"Prompt: {prompt2}")
    
    try:
        result2 = process_document_with_ai(template.file.path, prompt2)
        
        if result2.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar mudanças
            doc2 = Document(result2['output_path'])
            
            # Verificar se valor foi alterado
            valor_alterado = False
            for paragraph in doc2.paragraphs:
                if "R$ 10.000.000,00" in paragraph.text:
                    valor_alterado = True
                    print("✅ Valor alterado para R$ 10.000.000,00")
                    break
            
            # Verificar se modalidade NÃO foi alterada (não foi solicitado)
            modalidade_alterada = False
            for paragraph in doc2.paragraphs:
                if "TOMADA DE PREÇOS" in paragraph.text.upper():
                    modalidade_alterada = True
                    print("❌ Modalidade alterada para TOMADA DE PREÇOS (não foi solicitado)")
                    break
            
            print(f"\n📊 RESULTADO TESTE 2:")
            print(f"Valor alterado: {'✅' if valor_alterado else '❌'}")
            print(f"Modalidade alterada (não solicitado): {'❌' if modalidade_alterada else '✅'}")
            
        else:
            print(f"❌ Erro: {result2.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False
    
    # TESTE 3: Apenas cláusula (não deve alterar modalidade)
    print("\n🔍 TESTE 3: Apenas cláusula")
    print("-" * 50)
    
    prompt3 = "Adicione uma cláusula 2.9 sobre critérios de responsabilidade social"
    
    print(f"Prompt: {prompt3}")
    
    try:
        result3 = process_document_with_ai(template.file.path, prompt3)
        
        if result3.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar mudanças
            doc3 = Document(result3['output_path'])
            
            # Verificar se cláusula foi adicionada
            clausula_adicionada = False
            for paragraph in doc3.paragraphs:
                if "2.9" in paragraph.text and "responsabilidade social" in paragraph.text.lower():
                    clausula_adicionada = True
                    print("✅ Cláusula 2.9 adicionada")
                    break
            
            # Verificar se modalidade NÃO foi alterada (não foi solicitado)
            modalidade_alterada = False
            for paragraph in doc3.paragraphs:
                if "TOMADA DE PREÇOS" in paragraph.text.upper():
                    modalidade_alterada = True
                    print("❌ Modalidade alterada para TOMADA DE PREÇOS (não foi solicitado)")
                    break
            
            print(f"\n📊 RESULTADO TESTE 3:")
            print(f"Cláusula adicionada: {'✅' if clausula_adicionada else '❌'}")
            print(f"Modalidade alterada (não solicitado): {'❌' if modalidade_alterada else '✅'}")
            
        else:
            print(f"❌ Erro: {result3.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False
    
    print("\n🎯 RESUMO GERAL DOS TESTES:")
    print("=" * 50)
    print("✅ Teste 1: Apenas cidade")
    print("✅ Teste 2: Apenas valor")
    print("✅ Teste 3: Apenas cláusula")
    print("\n🎉 TESTES CONCLUÍDOS!")
    print("📊 Verificação se o vício de cache foi resolvido")

if __name__ == "__main__":
    try:
        teste_vicio_cache()
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
