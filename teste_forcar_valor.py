#!/usr/bin/env python3
"""
Teste para forçar alteração de valor monetário
Usa prompt mais específico para garantir que a IA altere o valor
"""

import os
import sys
import django
from pathlib import Path
import tempfile

# Add the backend directory to Python path
sys.path.append('/home/adryan/mdlicitatech-system/backend')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mdlicitatech.settings')
django.setup()

from backend.app.services.ia import process_document_with_ai
from backend.app.models import Template

def teste_forcar_valor():
    """Teste para forçar alteração de valor monetário."""
    
    print("💰 TESTE PARA FORÇAR ALTERAÇÃO DE VALOR")
    print("Usando prompt mais específico")
    print("=" * 60)
    
    # 1. Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Usando template: {template.name}")
    
    # 2. Prompt muito específico
    prompt = """
    IMPORTANTE: Altere o valor "R$ 5.678.659,46" para "R$ 99.999.999,99" em qualquer lugar do documento.
    """
    
    print(f"\n🎯 Prompt específico:")
    print("-" * 40)
    print(prompt)
    print("-" * 40)
    
    try:
        result = process_document_with_ai(template.file.path, prompt)
        
        if result.get('success'):
            print("✅ Documento processado com sucesso")
            print(f"📊 Mudanças: {result.get('changes_made', [])}")
            
            # Verificar se o valor foi alterado
            from docx import Document
            doc = Document(result['output_path'])
            
            print("\n🔍 Verificando se o valor foi alterado...")
            
            # Procurar pelo valor novo
            valor_novo_encontrado = False
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            if "R$ 99.999.999,99" in paragraph.text:
                                valor_novo_encontrado = True
                                print(f"✅ Valor novo encontrado na tabela: {paragraph.text}")
                                break
                        if valor_novo_encontrado:
                            break
                    if valor_novo_encontrado:
                        break
                if valor_novo_encontrado:
                    break
            
            # Procurar em parágrafos também
            if not valor_novo_encontrado:
                for paragraph in doc.paragraphs:
                    if "R$ 99.999.999,99" in paragraph.text:
                        valor_novo_encontrado = True
                        print(f"✅ Valor novo encontrado em parágrafo: {paragraph.text}")
                        break
            
            # Verificar se o valor antigo ainda está lá
            valor_antigo_encontrado = False
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            if "R$ 5.678.659,46" in paragraph.text:
                                valor_antigo_encontrado = True
                                print(f"❌ Valor antigo ainda presente: {paragraph.text}")
                                break
                        if valor_antigo_encontrado:
                            break
                    if valor_antigo_encontrado:
                        break
                if valor_antigo_encontrado:
                    break
            
            # Resultado
            if valor_novo_encontrado and not valor_antigo_encontrado:
                print("\n🎉 SUCESSO: Valor monetário alterado com sucesso!")
                return True
            elif valor_novo_encontrado and valor_antigo_encontrado:
                print("\n⚠️ PARCIAL: Valor alterado mas valor antigo ainda presente")
                return False
            else:
                print("\n❌ PROBLEMA: Valor monetário não foi alterado")
                return False
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
        sucesso = teste_forcar_valor()
        if sucesso:
            print("\n🎉 TESTE CONCLUÍDO COM SUCESSO!")
        else:
            print("\n❌ TESTE FALHOU")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
