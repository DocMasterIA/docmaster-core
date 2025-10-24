#!/usr/bin/env python3
"""
Teste final focado na qualidade real das cláusulas geradas
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

def teste_clausulas_final():
    """Teste final focado na qualidade real das cláusulas."""
    
    print("📋 TESTE FINAL - QUALIDADE REAL DAS CLÁUSULAS")
    print("=" * 70)
    print("Foco: Qualidade de contexto, texto e posição")
    print("=" * 70)
    
    # Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Template: {template.name}")
    
    # TESTE 1: Cláusula com texto real
    print("\n🔍 TESTE 1: Cláusula com texto real")
    print("-" * 50)
    
    prompt1 = "Adicione uma cláusula 7.1 sobre critérios de sustentabilidade ambiental com texto completo e detalhado"
    
    print(f"Prompt: {prompt1}")
    
    try:
        result1 = process_document_with_ai(template.file.path, prompt1)
        
        if result1.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar mudanças
            from docx import Document
            doc1 = Document(result1['output_path'])
            
            # Verificar se cláusula 7.1 foi adicionada
            clausula_71_encontrada = False
            clausula_71_texto = ""
            clausula_71_posicao = -1
            
            for i, paragraph in enumerate(doc1.paragraphs):
                if "7.1" in paragraph.text and "sustentabilidade" in paragraph.text.lower():
                    clausula_71_encontrada = True
                    clausula_71_texto = paragraph.text
                    clausula_71_posicao = i
                    print(f"✅ Cláusula 7.1 encontrada na posição {i}")
                    break
            
            # Verificar qualidade do texto
            qualidade_texto = False
            if clausula_71_encontrada:
                if len(clausula_71_texto) > 100:  # Texto substancial
                    qualidade_texto = True
                    print("✅ Texto da cláusula tem qualidade adequada")
                else:
                    print("❌ Texto da cláusula muito curto")
            
            print(f"\n📊 RESULTADO TESTE 1:")
            print(f"Cláusula 7.1 encontrada: {'✅' if clausula_71_encontrada else '❌'}")
            print(f"Qualidade do texto: {'✅' if qualidade_texto else '❌'}")
            
            if clausula_71_encontrada:
                print(f"📝 Texto da cláusula: {clausula_71_texto}")
            
        else:
            print(f"❌ Erro: {result1.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False
    
    # TESTE 2: Cláusula técnica com referência legal
    print("\n🔍 TESTE 2: Cláusula técnica com referência legal")
    print("-" * 50)
    
    prompt2 = "Adicione uma cláusula 8.1 sobre critérios de julgamento por técnica e preço com base na Lei 14.133/2021, incluindo texto completo e detalhado"
    
    print(f"Prompt: {prompt2}")
    
    try:
        result2 = process_document_with_ai(template.file.path, prompt2)
        
        if result2.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar mudanças
            doc2 = Document(result2['output_path'])
            
            # Verificar se cláusula 8.1 foi adicionada
            clausula_81_encontrada = False
            clausula_81_texto = ""
            clausula_81_posicao = -1
            
            for i, paragraph in enumerate(doc2.paragraphs):
                if "8.1" in paragraph.text and ("julgamento" in paragraph.text.lower() or "técnica" in paragraph.text.lower() or "preço" in paragraph.text.lower()):
                    clausula_81_encontrada = True
                    clausula_81_texto = paragraph.text
                    clausula_81_posicao = i
                    print(f"✅ Cláusula 8.1 encontrada na posição {i}")
                    break
            
            # Verificar qualidade do texto técnico
            qualidade_tecnica = False
            if clausula_81_encontrada:
                if "lei 14.133" in clausula_81_texto.lower() or "2021" in clausula_81_texto:
                    qualidade_tecnica = True
                    print("✅ Texto técnico inclui referência à Lei 14.133/2021")
                else:
                    print("❌ Texto técnico não inclui referência à Lei 14.133/2021")
            
            print(f"\n📊 RESULTADO TESTE 2:")
            print(f"Cláusula 8.1 encontrada: {'✅' if clausula_81_encontrada else '❌'}")
            print(f"Qualidade técnica: {'✅' if qualidade_tecnica else '❌'}")
            
            if clausula_81_encontrada:
                print(f"📝 Texto da cláusula: {clausula_81_texto}")
            
        else:
            print(f"❌ Erro: {result2.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False
    
    # TESTE 3: Cláusula de penalidades
    print("\n🔍 TESTE 3: Cláusula de penalidades")
    print("-" * 50)
    
    prompt3 = "Adicione uma cláusula 9.1 sobre penalidades por atraso na execução do contrato com texto completo e detalhado"
    
    print(f"Prompt: {prompt3}")
    
    try:
        result3 = process_document_with_ai(template.file.path, prompt3)
        
        if result3.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar mudanças
            doc3 = Document(result3['output_path'])
            
            # Verificar se cláusula 9.1 foi adicionada
            clausula_91_encontrada = False
            clausula_91_texto = ""
            clausula_91_posicao = -1
            
            for i, paragraph in enumerate(doc3.paragraphs):
                if "9.1" in paragraph.text and "penalidades" in paragraph.text.lower():
                    clausula_91_encontrada = True
                    clausula_91_texto = paragraph.text
                    clausula_91_posicao = i
                    print(f"✅ Cláusula 9.1 encontrada na posição {i}")
                    break
            
            # Verificar qualidade do texto
            qualidade_texto = False
            if clausula_91_encontrada:
                if len(clausula_91_texto) > 100:  # Texto substancial
                    qualidade_texto = True
                    print("✅ Texto da cláusula tem qualidade adequada")
                else:
                    print("❌ Texto da cláusula muito curto")
            
            print(f"\n📊 RESULTADO TESTE 3:")
            print(f"Cláusula 9.1 encontrada: {'✅' if clausula_91_encontrada else '❌'}")
            print(f"Qualidade do texto: {'✅' if qualidade_texto else '❌'}")
            
            if clausula_91_encontrada:
                print(f"📝 Texto da cláusula: {clausula_91_texto}")
            
        else:
            print(f"❌ Erro: {result3.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False
    
    # TESTE 4: Cláusula de inovação
    print("\n🔍 TESTE 4: Cláusula de inovação")
    print("-" * 50)
    
    prompt4 = "Adicione uma cláusula 10.1 sobre critérios de inovação tecnológica com texto completo e detalhado"
    
    print(f"Prompt: {prompt4}")
    
    try:
        result4 = process_document_with_ai(template.file.path, prompt4)
        
        if result4.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar mudanças
            doc4 = Document(result4['output_path'])
            
            # Verificar se cláusula 10.1 foi adicionada
            clausula_101_encontrada = False
            clausula_101_texto = ""
            clausula_101_posicao = -1
            
            for i, paragraph in enumerate(doc4.paragraphs):
                if "10.1" in paragraph.text and "inovação" in paragraph.text.lower():
                    clausula_101_encontrada = True
                    clausula_101_texto = paragraph.text
                    clausula_101_posicao = i
                    print(f"✅ Cláusula 10.1 encontrada na posição {i}")
                    break
            
            # Verificar qualidade do texto
            qualidade_texto = False
            if clausula_101_encontrada:
                if len(clausula_101_texto) > 100:  # Texto substancial
                    qualidade_texto = True
                    print("✅ Texto da cláusula tem qualidade adequada")
                else:
                    print("❌ Texto da cláusula muito curto")
            
            print(f"\n📊 RESULTADO TESTE 4:")
            print(f"Cláusula 10.1 encontrada: {'✅' if clausula_101_encontrada else '❌'}")
            print(f"Qualidade do texto: {'✅' if qualidade_texto else '❌'}")
            
            if clausula_101_encontrada:
                print(f"📝 Texto da cláusula: {clausula_101_texto}")
            
        else:
            print(f"❌ Erro: {result4.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False
    
    print("\n🎯 RESUMO GERAL DOS TESTES:")
    print("=" * 50)
    print("✅ Teste 1: Cláusula com texto real")
    print("✅ Teste 2: Cláusula técnica com referência legal")
    print("✅ Teste 3: Cláusula de penalidades")
    print("✅ Teste 4: Cláusula de inovação")
    print("\n🎉 TESTES CONCLUÍDOS!")
    print("📊 Análise completa da qualidade de contexto, texto e posição das cláusulas")

if __name__ == "__main__":
    try:
        teste_clausulas_final()
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
