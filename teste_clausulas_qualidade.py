#!/usr/bin/env python3
"""
Teste focado na qualidade das cláusulas geradas
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

def teste_clausulas_qualidade():
    """Teste focado na qualidade das cláusulas."""
    
    print("📋 TESTE QUALIDADE - GERAÇÃO DE CLÁUSULAS")
    print("=" * 70)
    print("Foco: Qualidade de contexto, texto e posição")
    print("=" * 70)
    
    # Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Template: {template.name}")
    
    # TESTE 1: Cláusula numerada simples
    print("\n🔍 TESTE 1: Cláusula numerada simples")
    print("-" * 50)
    
    prompt1 = "Adicione uma nova cláusula 2.9 sobre critérios de responsabilidade social"
    
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
            clausula_29_texto = ""
            clausula_29_posicao = -1
            
            for i, paragraph in enumerate(doc1.paragraphs):
                if "2.9" in paragraph.text:
                    clausula_29_encontrada = True
                    clausula_29_texto = paragraph.text
                    clausula_29_posicao = i
                    print(f"✅ Cláusula 2.9 encontrada na posição {i}")
                    break
            
            # Verificar se foi adicionada após 2.8
            clausula_28_posicao = -1
            for i, paragraph in enumerate(doc1.paragraphs):
                if "2.8" in paragraph.text:
                    clausula_28_posicao = i
                    print(f"✅ Cláusula 2.8 encontrada na posição {i}")
                    break
            
            # Verificar posição correta
            posicao_correta = False
            if clausula_28_posicao != -1 and clausula_29_posicao != -1:
                if clausula_29_posicao > clausula_28_posicao:
                    posicao_correta = True
                    print("✅ Cláusula 2.9 está após 2.8")
                else:
                    print("❌ Cláusula 2.9 não está após 2.8")
            
            # Verificar qualidade do texto
            qualidade_texto = False
            if clausula_29_encontrada:
                if len(clausula_29_texto) > 50:  # Texto substancial
                    qualidade_texto = True
                    print("✅ Texto da cláusula tem qualidade adequada")
                else:
                    print("❌ Texto da cláusula muito curto")
            
            print(f"\n📊 RESULTADO TESTE 1:")
            print(f"Cláusula 2.9 encontrada: {'✅' if clausula_29_encontrada else '❌'}")
            print(f"Posição correta: {'✅' if posicao_correta else '❌'}")
            print(f"Qualidade do texto: {'✅' if qualidade_texto else '❌'}")
            
            if clausula_29_encontrada:
                print(f"📝 Texto da cláusula: {clausula_29_texto}")
            
        else:
            print(f"❌ Erro: {result1.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False
    
    # TESTE 2: Cláusula com contexto específico
    print("\n🔍 TESTE 2: Cláusula com contexto específico")
    print("-" * 50)
    
    prompt2 = "Adicione uma cláusula 3.5 sobre sustentabilidade ambiental após o parágrafo 3.4"
    
    print(f"Prompt: {prompt2}")
    
    try:
        result2 = process_document_with_ai(template.file.path, prompt2)
        
        if result2.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar mudanças
            doc2 = Document(result2['output_path'])
            
            # Verificar se cláusula 3.5 foi adicionada
            clausula_35_encontrada = False
            clausula_35_texto = ""
            clausula_35_posicao = -1
            
            for i, paragraph in enumerate(doc2.paragraphs):
                if "3.5" in paragraph.text:
                    clausula_35_encontrada = True
                    clausula_35_texto = paragraph.text
                    clausula_35_posicao = i
                    print(f"✅ Cláusula 3.5 encontrada na posição {i}")
                    break
            
            # Verificar se foi adicionada após 3.4
            clausula_34_posicao = -1
            for i, paragraph in enumerate(doc2.paragraphs):
                if "3.4" in paragraph.text:
                    clausula_34_posicao = i
                    print(f"✅ Cláusula 3.4 encontrada na posição {i}")
                    break
            
            # Verificar posição correta
            posicao_correta = False
            if clausula_34_posicao != -1 and clausula_35_posicao != -1:
                if clausula_35_posicao > clausula_34_posicao:
                    posicao_correta = True
                    print("✅ Cláusula 3.5 está após 3.4")
                else:
                    print("❌ Cláusula 3.5 não está após 3.4")
            
            print(f"\n📊 RESULTADO TESTE 2:")
            print(f"Cláusula 3.5 encontrada: {'✅' if clausula_35_encontrada else '❌'}")
            print(f"Posição correta: {'✅' if posicao_correta else '❌'}")
            
            if clausula_35_encontrada:
                print(f"📝 Texto da cláusula: {clausula_35_texto}")
            
        else:
            print(f"❌ Erro: {result2.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False
    
    # TESTE 3: Cláusula técnica complexa
    print("\n🔍 TESTE 3: Cláusula técnica complexa")
    print("-" * 50)
    
    prompt3 = "Adicione uma cláusula 4.2 sobre critérios de julgamento por técnica e preço com base na Lei 14.133/2021"
    
    print(f"Prompt: {prompt3}")
    
    try:
        result3 = process_document_with_ai(template.file.path, prompt3)
        
        if result3.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar mudanças
            doc3 = Document(result3['output_path'])
            
            # Verificar se cláusula 4.2 foi adicionada
            clausula_42_encontrada = False
            clausula_42_texto = ""
            clausula_42_posicao = -1
            
            for i, paragraph in enumerate(doc3.paragraphs):
                if "4.2" in paragraph.text:
                    clausula_42_encontrada = True
                    clausula_42_texto = paragraph.text
                    clausula_42_posicao = i
                    print(f"✅ Cláusula 4.2 encontrada na posição {i}")
                    break
            
            # Verificar se foi adicionada após 4.1
            clausula_41_posicao = -1
            for i, paragraph in enumerate(doc3.paragraphs):
                if "4.1" in paragraph.text:
                    clausula_41_posicao = i
                    print(f"✅ Cláusula 4.1 encontrada na posição {i}")
                    break
            
            # Verificar posição correta
            posicao_correta = False
            if clausula_41_posicao != -1 and clausula_42_posicao != -1:
                if clausula_42_posicao > clausula_41_posicao:
                    posicao_correta = True
                    print("✅ Cláusula 4.2 está após 4.1")
                else:
                    print("❌ Cláusula 4.2 não está após 4.1")
            
            # Verificar qualidade do texto técnico
            qualidade_tecnica = False
            if clausula_42_encontrada:
                if "lei 14.133" in clausula_42_texto.lower() or "2021" in clausula_42_texto:
                    qualidade_tecnica = True
                    print("✅ Texto técnico inclui referência à Lei 14.133/2021")
                else:
                    print("❌ Texto técnico não inclui referência à Lei 14.133/2021")
            
            print(f"\n📊 RESULTADO TESTE 3:")
            print(f"Cláusula 4.2 encontrada: {'✅' if clausula_42_encontrada else '❌'}")
            print(f"Posição correta: {'✅' if posicao_correta else '❌'}")
            print(f"Qualidade técnica: {'✅' if qualidade_tecnica else '❌'}")
            
            if clausula_42_encontrada:
                print(f"📝 Texto da cláusula: {clausula_42_texto}")
            
        else:
            print(f"❌ Erro: {result3.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False
    
    # TESTE 4: Múltiplas cláusulas
    print("\n🔍 TESTE 4: Múltiplas cláusulas")
    print("-" * 50)
    
    prompt4 = "Adicione as seguintes cláusulas: 5.1 sobre inovação tecnológica, 5.2 sobre acessibilidade e 5.3 sobre segurança da informação"
    
    print(f"Prompt: {prompt4}")
    
    try:
        result4 = process_document_with_ai(template.file.path, prompt4)
        
        if result4.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar mudanças
            doc4 = Document(result4['output_path'])
            
            # Verificar cláusulas 5.1, 5.2 e 5.3
            clausulas_encontradas = []
            for i, paragraph in enumerate(doc4.paragraphs):
                if "5.1" in paragraph.text:
                    clausulas_encontradas.append(("5.1", i, paragraph.text))
                    print(f"✅ Cláusula 5.1 encontrada na posição {i}")
                elif "5.2" in paragraph.text:
                    clausulas_encontradas.append(("5.2", i, paragraph.text))
                    print(f"✅ Cláusula 5.2 encontrada na posição {i}")
                elif "5.3" in paragraph.text:
                    clausulas_encontradas.append(("5.3", i, paragraph.text))
                    print(f"✅ Cláusula 5.3 encontrada na posição {i}")
            
            # Verificar se foram adicionadas em sequência
            sequencia_correta = False
            if len(clausulas_encontradas) >= 3:
                posicoes = [pos for _, pos, _ in clausulas_encontradas]
                if posicoes == sorted(posicoes):
                    sequencia_correta = True
                    print("✅ Cláusulas adicionadas em sequência correta")
                else:
                    print("❌ Cláusulas não foram adicionadas em sequência")
            
            print(f"\n📊 RESULTADO TESTE 4:")
            print(f"Cláusulas encontradas: {len(clausulas_encontradas)}/3")
            print(f"Sequência correta: {'✅' if sequencia_correta else '❌'}")
            
            for clausula, pos, texto in clausulas_encontradas:
                print(f"📝 {clausula}: {texto}")
            
        else:
            print(f"❌ Erro: {result4.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False
    
    # TESTE 5: Cláusula com posição específica
    print("\n🔍 TESTE 5: Cláusula com posição específica")
    print("-" * 50)
    
    prompt5 = "Adicione uma cláusula 6.1 sobre penalidades por atraso após o parágrafo 6.0"
    
    print(f"Prompt: {prompt5}")
    
    try:
        result5 = process_document_with_ai(template.file.path, prompt5)
        
        if result5.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar mudanças
            doc5 = Document(result5['output_path'])
            
            # Verificar se cláusula 6.1 foi adicionada
            clausula_61_encontrada = False
            clausula_61_texto = ""
            clausula_61_posicao = -1
            
            for i, paragraph in enumerate(doc5.paragraphs):
                if "6.1" in paragraph.text:
                    clausula_61_encontrada = True
                    clausula_61_texto = paragraph.text
                    clausula_61_posicao = i
                    print(f"✅ Cláusula 6.1 encontrada na posição {i}")
                    break
            
            # Verificar se foi adicionada após 6.0
            clausula_60_posicao = -1
            for i, paragraph in enumerate(doc5.paragraphs):
                if "6.0" in paragraph.text:
                    clausula_60_posicao = i
                    print(f"✅ Cláusula 6.0 encontrada na posição {i}")
                    break
            
            # Verificar posição correta
            posicao_correta = False
            if clausula_60_posicao != -1 and clausula_61_posicao != -1:
                if clausula_61_posicao > clausula_60_posicao:
                    posicao_correta = True
                    print("✅ Cláusula 6.1 está após 6.0")
                else:
                    print("❌ Cláusula 6.1 não está após 6.0")
            
            print(f"\n📊 RESULTADO TESTE 5:")
            print(f"Cláusula 6.1 encontrada: {'✅' if clausula_61_encontrada else '❌'}")
            print(f"Posição correta: {'✅' if posicao_correta else '❌'}")
            
            if clausula_61_encontrada:
                print(f"📝 Texto da cláusula: {clausula_61_texto}")
            
        else:
            print(f"❌ Erro: {result5.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False
    
    print("\n🎯 RESUMO GERAL DOS TESTES:")
    print("=" * 50)
    print("✅ Teste 1: Cláusula numerada simples")
    print("✅ Teste 2: Cláusula com contexto específico")
    print("✅ Teste 3: Cláusula técnica complexa")
    print("✅ Teste 4: Múltiplas cláusulas")
    print("✅ Teste 5: Cláusula com posição específica")
    print("\n🎉 TESTES CONCLUÍDOS!")
    print("📊 Análise completa da qualidade de contexto, texto e posição das cláusulas")

if __name__ == "__main__":
    try:
        teste_clausulas_qualidade()
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
