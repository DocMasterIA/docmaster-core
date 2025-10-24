#!/usr/bin/env python3
"""
Teste de debug para investigar problema na geração de cláusulas
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

def teste_debug_clausulas():
    """Teste de debug para cláusulas."""
    
    print("🔍 TESTE DEBUG - GERAÇÃO DE CLÁUSULAS")
    print("=" * 70)
    
    # Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Template: {template.name}")
    
    # Teste simples
    print("\n🔍 TESTE: Cláusula simples")
    print("-" * 50)
    
    prompt = "Adicione uma nova cláusula 2.9 sobre critérios de responsabilidade social"
    
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
            
            # Verificar se cláusula 2.9 foi adicionada
            clausula_29_encontrada = False
            clausula_29_texto = ""
            clausula_29_posicao = -1
            
            for i, paragraph in enumerate(doc.paragraphs):
                if "2.9" in paragraph.text:
                    clausula_29_encontrada = True
                    clausula_29_texto = paragraph.text
                    clausula_29_posicao = i
                    print(f"✅ Cláusula 2.9 encontrada na posição {i}")
                    print(f"📝 Texto: {paragraph.text}")
                    break
            
            # Verificar se foi adicionada após 2.8
            clausula_28_posicao = -1
            for i, paragraph in enumerate(doc.paragraphs):
                if "2.8" in paragraph.text:
                    clausula_28_posicao = i
                    print(f"✅ Cláusula 2.8 encontrada na posição {i}")
                    print(f"📝 Texto: {paragraph.text}")
                    break
            
            # Verificar posição correta
            posicao_correta = False
            if clausula_28_posicao != -1 and clausula_29_posicao != -1:
                if clausula_29_posicao > clausula_28_posicao:
                    posicao_correta = True
                    print("✅ Cláusula 2.9 está após 2.8")
                else:
                    print("❌ Cláusula 2.9 não está após 2.8")
            
            # Verificar se há texto sobre responsabilidade social
            responsabilidade_social = False
            for paragraph in doc.paragraphs:
                if "responsabilidade social" in paragraph.text.lower():
                    responsabilidade_social = True
                    print(f"✅ Texto sobre responsabilidade social encontrado: {paragraph.text[:100]}...")
                    break
            
            print(f"\n📊 RESULTADO:")
            print(f"Cláusula 2.9 encontrada: {'✅' if clausula_29_encontrada else '❌'}")
            print(f"Posição correta: {'✅' if posicao_correta else '❌'}")
            print(f"Responsabilidade social: {'✅' if responsabilidade_social else '❌'}")
            
            # Verificar se há texto sobre responsabilidade social em qualquer lugar
            if not responsabilidade_social:
                print("\n🔍 BUSCA POR 'responsabilidade social' em todo o documento:")
                for i, paragraph in enumerate(doc.paragraphs):
                    if "responsabilidade" in paragraph.text.lower() or "social" in paragraph.text.lower():
                        print(f"  Posição {i}: {paragraph.text[:100]}...")
            
        else:
            print(f"❌ Erro: {result.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        teste_debug_clausulas()
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
