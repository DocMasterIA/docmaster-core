#!/usr/bin/env python3
"""
Teste para verificar se a correção da cláusula 7.1 funcionou
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

def teste_correcao_71():
    """Teste para verificar se a correção da cláusula 7.1 funcionou."""
    
    print("🔍 TESTE - CORREÇÃO CLAUSULA 7.1")
    print("=" * 70)
    print("Verificando se cláusula 7.1 é gerada corretamente")
    print("=" * 70)
    
    # Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Template: {template.name}")
    
    # TESTE: Cláusula 7.1
    print("\n🔍 TESTE: Cláusula 7.1")
    print("-" * 50)
    
    prompt = "Adicione uma cláusula 7.1 sobre julgamento por técnica e preço com base na Lei 14.133/2021"
    
    print(f"Prompt: {prompt}")
    
    try:
        result = process_document_with_ai(template.file.path, prompt)
        
        if result.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar mudanças
            from docx import Document
            doc = Document(result['output_path'])
            
            # Buscar cláusula 7.1 no documento novo
            clausula_71_encontrada = False
            clausula_71_posicao = -1
            clausula_71_texto = ""
            
            for i, paragraph in enumerate(doc.paragraphs):
                if "7.1" in paragraph.text and "julgamento" in paragraph.text.lower():
                    clausula_71_encontrada = True
                    clausula_71_posicao = i
                    clausula_71_texto = paragraph.text
                    print(f"✅ Cláusula 7.1 encontrada na posição {i}")
                    print(f"📝 Texto: {paragraph.text}")
                    break
            
            if not clausula_71_encontrada:
                print("❌ Cláusula 7.1 não encontrada no documento")
            else:
                # Verificar se contém "3.2" (problema)
                if "3.2" in clausula_71_texto:
                    print("❌ PROBLEMA: Cláusula contém '3.2' em vez de '7.1'")
                else:
                    print("✅ CORREÇÃO: Cláusula não contém '3.2'")
                
                # Verificar se começa com "7.1"
                if clausula_71_texto.strip().startswith("7.1"):
                    print("✅ CORREÇÃO: Cláusula começa corretamente com '7.1'")
                else:
                    print("❌ PROBLEMA: Cláusula não começa com '7.1'")
                
                # Verificar o que está antes da cláusula 7.1
                if clausula_71_posicao > 0:
                    anterior = doc.paragraphs[clausula_71_posicao - 1]
                    print(f"📋 Parágrafo anterior (posição {clausula_71_posicao - 1}): {anterior.text[:100]}...")
            
        else:
            print(f"❌ Erro: {result.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n🎯 RESUMO DO TESTE:")
    print("=" * 50)
    print("✅ Teste concluído")
    print("📊 Verificar se cláusula 7.1 é gerada corretamente")

if __name__ == "__main__":
    try:
        teste_correcao_71()
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
