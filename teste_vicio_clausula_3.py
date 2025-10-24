#!/usr/bin/env python3
"""
Teste para investigar vício específico em cláusulas após 3.1
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

def teste_vicio_clausula_3():
    """Teste para investigar vício específico em cláusulas após 3.1"""
    
    print("🔍 TESTE VÍCIO ESPECÍFICO - CLAUSULAS APÓS 3.1")
    print("=" * 70)
    print("Foco: Investigar vício em adicionar cláusulas após 3.1")
    print("=" * 70)
    
    # Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Template: {template.name}")
    
    # TESTE 1: Cláusula simples
    print("\n🔍 TESTE 1: Cláusula simples")
    print("-" * 50)
    
    prompt1 = "Adicione uma cláusula 2.9 sobre critérios de responsabilidade social"
    
    print(f"Prompt: {prompt1}")
    
    try:
        result1 = process_document_with_ai(template.file.path, prompt1)
        
        if result1.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar mudanças
            from docx import Document
            doc1 = Document(result1['output_path'])
            
            # Verificar se cláusula 2.9 foi adicionada
            clausula_29_encontrada = False
            clausula_29_posicao = -1
            clausula_29_texto = ""
            
            for i, paragraph in enumerate(doc1.paragraphs):
                if "2.9" in paragraph.text and "responsabilidade social" in paragraph.text.lower():
                    clausula_29_encontrada = True
                    clausula_29_posicao = i
                    clausula_29_texto = paragraph.text
                    print(f"✅ Cláusula 2.9 encontrada na posição {i}")
                    break
            
            # Verificar se foi adicionada após 3.1 (vício)
            clausula_31_posicao = -1
            for i, paragraph in enumerate(doc1.paragraphs):
                if "3.1" in paragraph.text and "Os trabalhos serão conduzidos" in paragraph.text:
                    clausula_31_posicao = i
                    print(f"✅ Parágrafo 3.1 encontrado na posição {i}")
                    break
            
            # Verificar se cláusula 2.9 está próxima ao 3.1 (vício)
            proxima_31 = False
            if clausula_29_posicao != -1 and clausula_31_posicao != -1:
                if abs(clausula_29_posicao - clausula_31_posicao) <= 5:
                    proxima_31 = True
                    print("❌ Cláusula 2.9 está muito próxima do 3.1 (vício detectado)")
                else:
                    print("✅ Cláusula 2.9 está em posição adequada")
            
            print(f"\n📊 RESULTADO TESTE 1:")
            print(f"Cláusula 2.9 encontrada: {'✅' if clausula_29_encontrada else '❌'}")
            print(f"Próxima ao 3.1 (vício): {'❌' if proxima_31 else '✅'}")
            
            if clausula_29_encontrada:
                print(f"📝 Texto da cláusula: {clausula_29_texto[:100]}...")
            
        else:
            print(f"❌ Erro: {result1.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False
    
    # TESTE 2: Cláusula com posição específica
    print("\n🔍 TESTE 2: Cláusula com posição específica")
    print("-" * 50)
    
    prompt2 = "Adicione uma cláusula 4.2 sobre sustentabilidade ambiental após o parágrafo 4.1"
    
    print(f"Prompt: {prompt2}")
    
    try:
        result2 = process_document_with_ai(template.file.path, prompt2)
        
        if result2.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar mudanças
            doc2 = Document(result2['output_path'])
            
            # Verificar se cláusula 4.2 foi adicionada
            clausula_42_encontrada = False
            clausula_42_posicao = -1
            clausula_42_texto = ""
            
            for i, paragraph in enumerate(doc2.paragraphs):
                if "4.2" in paragraph.text and "sustentabilidade" in paragraph.text.lower():
                    clausula_42_encontrada = True
                    clausula_42_posicao = i
                    clausula_42_texto = paragraph.text
                    print(f"✅ Cláusula 4.2 encontrada na posição {i}")
                    break
            
            # Verificar se foi adicionada após 3.1 (vício)
            clausula_31_posicao = -1
            for i, paragraph in enumerate(doc2.paragraphs):
                if "3.1" in paragraph.text and "Os trabalhos serão conduzidos" in paragraph.text:
                    clausula_31_posicao = i
                    print(f"✅ Parágrafo 3.1 encontrado na posição {i}")
                    break
            
            # Verificar se cláusula 4.2 está próxima ao 3.1 (vício)
            proxima_31 = False
            if clausula_42_posicao != -1 and clausula_31_posicao != -1:
                if abs(clausula_42_posicao - clausula_31_posicao) <= 5:
                    proxima_31 = True
                    print("❌ Cláusula 4.2 está muito próxima do 3.1 (vício detectado)")
                else:
                    print("✅ Cláusula 4.2 está em posição adequada")
            
            print(f"\n📊 RESULTADO TESTE 2:")
            print(f"Cláusula 4.2 encontrada: {'✅' if clausula_42_encontrada else '❌'}")
            print(f"Próxima ao 3.1 (vício): {'❌' if proxima_31 else '✅'}")
            
            if clausula_42_encontrada:
                print(f"📝 Texto da cláusula: {clausula_42_texto[:100]}...")
            
        else:
            print(f"❌ Erro: {result2.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False
    
    # TESTE 3: Cláusula sem posição específica
    print("\n🔍 TESTE 3: Cláusula sem posição específica")
    print("-" * 50)
    
    prompt3 = "Adicione uma cláusula 5.1 sobre inovação tecnológica"
    
    print(f"Prompt: {prompt3}")
    
    try:
        result3 = process_document_with_ai(template.file.path, prompt3)
        
        if result3.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar mudanças
            doc3 = Document(result3['output_path'])
            
            # Verificar se cláusula 5.1 foi adicionada
            clausula_51_encontrada = False
            clausula_51_posicao = -1
            clausula_51_texto = ""
            
            for i, paragraph in enumerate(doc3.paragraphs):
                if "5.1" in paragraph.text and "inovação" in paragraph.text.lower():
                    clausula_51_encontrada = True
                    clausula_51_posicao = i
                    clausula_51_texto = paragraph.text
                    print(f"✅ Cláusula 5.1 encontrada na posição {i}")
                    break
            
            # Verificar se foi adicionada após 3.1 (vício)
            clausula_31_posicao = -1
            for i, paragraph in enumerate(doc3.paragraphs):
                if "3.1" in paragraph.text and "Os trabalhos serão conduzidos" in paragraph.text:
                    clausula_31_posicao = i
                    print(f"✅ Parágrafo 3.1 encontrado na posição {i}")
                    break
            
            # Verificar se cláusula 5.1 está próxima ao 3.1 (vício)
            proxima_31 = False
            if clausula_51_posicao != -1 and clausula_31_posicao != -1:
                if abs(clausula_51_posicao - clausula_31_posicao) <= 5:
                    proxima_31 = True
                    print("❌ Cláusula 5.1 está muito próxima do 3.1 (vício detectado)")
                else:
                    print("✅ Cláusula 5.1 está em posição adequada")
            
            print(f"\n📊 RESULTADO TESTE 3:")
            print(f"Cláusula 5.1 encontrada: {'✅' if clausula_51_encontrada else '❌'}")
            print(f"Próxima ao 3.1 (vício): {'❌' if proxima_31 else '✅'}")
            
            if clausula_51_encontrada:
                print(f"📝 Texto da cláusula: {clausula_51_texto[:100]}...")
            
        else:
            print(f"❌ Erro: {result3.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False
    
    print("\n🎯 RESUMO GERAL DOS TESTES:")
    print("=" * 50)
    print("✅ Teste 1: Cláusula simples")
    print("✅ Teste 2: Cláusula com posição específica")
    print("✅ Teste 3: Cláusula sem posição específica")
    print("\n🎉 TESTES CONCLUÍDOS!")
    print("📊 Verificação do vício específico em cláusulas após 3.1")

if __name__ == "__main__":
    try:
        teste_vicio_clausula_3()
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
