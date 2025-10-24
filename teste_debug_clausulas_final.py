#!/usr/bin/env python3
"""
Teste de debug para verificar se as cláusulas estão sendo aplicadas
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

def teste_debug_clausulas_final():
    """Teste de debug para verificar aplicação de cláusulas."""
    
    print("🔍 TESTE DEBUG - APLICAÇÃO DE CLAUSULAS")
    print("=" * 70)
    
    # Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Template: {template.name}")
    
    # Teste simples
    print("\n🔍 TESTE: Cláusula 2.9")
    print("-" * 50)
    
    prompt = "Adicione uma cláusula 2.9 sobre critérios de responsabilidade social"
    
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
            clausula_29_posicao = -1
            clausula_29_texto = ""
            
            for i, paragraph in enumerate(doc.paragraphs):
                if "2.9" in paragraph.text:
                    clausula_29_encontrada = True
                    clausula_29_posicao = i
                    clausula_29_texto = paragraph.text
                    print(f"✅ Cláusula 2.9 encontrada na posição {i}")
                    print(f"📝 Texto: {paragraph.text[:100]}...")
                    break
            
            # Verificar se foi adicionada após 2.8
            clausula_28_posicao = -1
            for i, paragraph in enumerate(doc.paragraphs):
                if "2.8" in paragraph.text:
                    clausula_28_posicao = i
                    print(f"✅ Cláusula 2.8 encontrada na posição {i}")
                    break
            
            # Verificar se foi adicionada após 3.1 (vício)
            clausula_31_posicao = -1
            for i, paragraph in enumerate(doc.paragraphs):
                if "3.1" in paragraph.text and "Os trabalhos serão conduzidos" in paragraph.text:
                    clausula_31_posicao = i
                    print(f"✅ Parágrafo 3.1 encontrado na posição {i}")
                    break
            
            # Verificar posição relativa
            if clausula_29_encontrada and clausula_28_posicao != -1:
                if clausula_29_posicao > clausula_28_posicao:
                    print("✅ Cláusula 2.9 está após 2.8 (correto)")
                else:
                    print("❌ Cláusula 2.9 não está após 2.8")
            
            if clausula_29_encontrada and clausula_31_posicao != -1:
                if abs(clausula_29_posicao - clausula_31_posicao) <= 5:
                    print("❌ Cláusula 2.9 está muito próxima do 3.1 (vício)")
                else:
                    print("✅ Cláusula 2.9 está em posição adequada")
            
            print(f"\n📊 RESULTADO:")
            print(f"Cláusula 2.9 encontrada: {'✅' if clausula_29_encontrada else '❌'}")
            
            # Buscar por "responsabilidade social" em qualquer lugar
            if not clausula_29_encontrada:
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
        teste_debug_clausulas_final()
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
