#!/usr/bin/env python3
"""
Debug para entender por que cláusulas estão sendo adicionadas em posições incorretas
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

def debug_contexto_clausulas():
    """Debug para entender posicionamento incorreto de cláusulas."""
    
    print("🔍 DEBUG - CONTEXTO DE CLAUSULAS")
    print("=" * 70)
    print("Investigando por que cláusulas estão em posições incorretas")
    print("=" * 70)
    
    # Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Template: {template.name}")
    
    # TESTE 1: Cláusula 2.9
    print("\n🔍 TESTE 1: Cláusula 2.9")
    print("-" * 50)
    
    prompt1 = "Adicione uma cláusula 2.9 sobre critérios de responsabilidade social"
    
    try:
        result1 = process_document_with_ai(template.file.path, prompt1)
        
        if result1.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar mudanças
            from docx import Document
            doc1 = Document(result1['output_path'])
            
            # Buscar cláusula 2.9
            clausula_29_posicao = -1
            clausula_29_texto = ""
            
            for i, paragraph in enumerate(doc1.paragraphs):
                if "2.9" in paragraph.text and "responsabilidade social" in paragraph.text.lower():
                    clausula_29_posicao = i
                    clausula_29_texto = paragraph.text
                    print(f"✅ Cláusula 2.9 encontrada na posição {i}")
                    print(f"📝 Texto: {paragraph.text[:100]}...")
                    break
            
            # Verificar o que está antes da cláusula 2.9
            if clausula_29_posicao > 0:
                anterior = doc1.paragraphs[clausula_29_posicao - 1]
                print(f"📋 Parágrafo anterior (posição {clausula_29_posicao - 1}): {anterior.text[:100]}...")
                
                # Verificar se contém números que poderiam confundir
                import re
                numeros = re.findall(r'\d+\.\d+', anterior.text)
                if numeros:
                    print(f"🔢 Números encontrados no parágrafo anterior: {numeros}")
            
            # Verificar se há 2.8 no documento
            print("\n🔍 Busca por 2.8 no documento:")
            for i, paragraph in enumerate(doc1.paragraphs):
                if "2.8" in paragraph.text:
                    print(f"  Posição {i}: {paragraph.text[:100]}...")
            
            # Verificar se há 2.7 no documento
            print("\n🔍 Busca por 2.7 no documento:")
            for i, paragraph in enumerate(doc1.paragraphs):
                if "2.7" in paragraph.text:
                    print(f"  Posição {i}: {paragraph.text[:100]}...")
            
        else:
            print(f"❌ Erro: {result1.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # TESTE 2: Cláusula 4.2
    print("\n🔍 TESTE 2: Cláusula 4.2")
    print("-" * 50)
    
    prompt2 = "Adicione uma cláusula 4.2 sobre sustentabilidade ambiental após o parágrafo 4.1"
    
    try:
        result2 = process_document_with_ai(template.file.path, prompt2)
        
        if result2.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar mudanças
            doc2 = Document(result2['output_path'])
            
            # Buscar cláusula 4.2
            clausula_42_posicao = -1
            
            for i, paragraph in enumerate(doc2.paragraphs):
                if "4.2" in paragraph.text and "sustentabilidade" in paragraph.text.lower():
                    clausula_42_posicao = i
                    print(f"✅ Cláusula 4.2 encontrada na posição {i}")
                    print(f"📝 Texto: {paragraph.text[:100]}...")
                    break
            
            # Verificar o que está antes da cláusula 4.2
            if clausula_42_posicao > 0:
                anterior = doc2.paragraphs[clausula_42_posicao - 1]
                print(f"📋 Parágrafo anterior (posição {clausula_42_posicao - 1}): {anterior.text[:100]}...")
                
                # Verificar se contém números que poderiam confundir
                import re
                numeros = re.findall(r'\d+\.\d+', anterior.text)
                if numeros:
                    print(f"🔢 Números encontrados no parágrafo anterior: {numeros}")
            
            # Verificar se há 4.1 no documento
            print("\n🔍 Busca por 4.1 no documento:")
            for i, paragraph in enumerate(doc2.paragraphs):
                if "4.1" in paragraph.text:
                    print(f"  Posição {i}: {paragraph.text[:100]}...")
            
        else:
            print(f"❌ Erro: {result2.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        debug_contexto_clausulas()
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
