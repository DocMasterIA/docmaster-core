#!/usr/bin/env python3
"""
Debug do salvamento
Verifica se o documento está sendo salvo corretamente
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

from backend.app.services.pure_ai_processor import process_document_pure_ai
from backend.app.models import Template

def debug_save():
    """Debug do salvamento."""
    
    print("🔍 DEBUG DO SALVAMENTO")
    print("=" * 40)
    
    # 1. Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Usando template: {template.name}")
    
    # 2. Processar documento
    prompt = "Altere o valor de PREÇO TOTAL MÉDIO para R$ 7.500.000,00."
    
    print(f"\n🎯 Prompt: {prompt}")
    
    # 3. Processar documento
    print("\n🤖 Processando documento...")
    try:
        result = process_document_pure_ai(template.file.path, prompt)
        
        if not result.get('success'):
            print(f"❌ Erro na IA: {result.get('error')}")
            return False
        
        print("✅ Documento processado!")
        print(f"📊 Mudanças aplicadas: {result.get('changes_applied', 0)}")
        print(f"📁 Arquivo: {result.get('output_path')}")
        
        # 4. Verificar se o arquivo foi salvo
        if os.path.exists(result['output_path']):
            print("✅ Arquivo salvo com sucesso!")
            
            # 5. Verificar se o valor foi alterado
            from docx import Document
            doc = Document(result['output_path'])
            
            print("\n🔍 Verificando se o valor foi alterado...")
            valor_encontrado = False
            
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            if "7.500.000,00" in paragraph.text:
                                valor_encontrado = True
                                print(f"✅ Valor alterado encontrado: {paragraph.text}")
                                break
                        if valor_encontrado:
                            break
                    if valor_encontrado:
                        break
                if valor_encontrado:
                    break
            
            if not valor_encontrado:
                print("❌ Valor não foi alterado no arquivo salvo")
                
                # Verificar se o valor antigo ainda está lá
                for table in doc.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            for paragraph in cell.paragraphs:
                                if "5.678.659,46" in paragraph.text:
                                    print(f"❌ Valor antigo ainda presente: {paragraph.text}")
                                    break
                            if "5.678.659,46" in paragraph.text:
                                break
                        if "5.678.659,46" in paragraph.text:
                            break
                    if "5.678.659,46" in paragraph.text:
                        break
                
                return False
            else:
                print("✅ Valor foi alterado com sucesso!")
                return True
        else:
            print("❌ Arquivo não foi salvo")
            return False
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        sucesso = debug_save()
        if sucesso:
            print("\n🎉 DEBUG CONCLUÍDO COM SUCESSO!")
        else:
            print("\n❌ DEBUG FALHOU")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Erro no debug: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
