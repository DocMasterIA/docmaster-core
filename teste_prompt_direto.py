#!/usr/bin/env python3
"""
Teste direto com prompt simples para verificar se a IA está funcionando
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

def teste_prompt_direto():
    """Teste com prompt direto e simples."""
    
    print("🎯 TESTE COM PROMPT DIRETO")
    print("=" * 50)
    
    # Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Template: {template.name}")
    
    # Teste 1: Alterar valor monetário
    print("\n🔬 TESTE 1: Alterar valor monetário")
    print("-" * 30)
    
    prompt1 = "Altere o valor 'R$ 5.678.659,46' para 'R$ 100.000.000,00'."
    
    try:
        result1 = process_document_with_ai(template.file.path, prompt1)
        
        if result1.get('success'):
            print("✅ Documento processado com sucesso")
            print(f"📊 Mudanças: {result1.get('changes_made', [])}")
            
            # Verificar se o valor foi alterado
            from docx import Document
            doc = Document(result1['output_path'])
            
            valor_alterado = False
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if "R$ 100.000.000,00" in cell.text:
                            valor_alterado = True
                            print("✅ Valor alterado para R$ 100.000.000,00")
                            break
                    if valor_alterado:
                        break
                if valor_alterado:
                    break
            
            if not valor_alterado:
                print("❌ Valor não foi alterado")
                return False
        else:
            print(f"❌ Erro: {result1.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False
    
    # Teste 2: Alterar local
    print("\n🔬 TESTE 2: Alterar local")
    print("-" * 30)
    
    prompt2 = "Mude 'ITAJÁ' para 'SÃO PAULO'."
    
    try:
        result2 = process_document_with_ai(template.file.path, prompt2)
        
        if result2.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar se o local foi alterado
            doc2 = Document(result2['output_path'])
            
            local_alterado = False
            for paragraph in doc2.paragraphs:
                if "SÃO PAULO" in paragraph.text and "ITAJÁ" not in paragraph.text:
                    local_alterado = True
                    print("✅ Local alterado para SÃO PAULO")
                    break
            
            if not local_alterado:
                print("❌ Local não foi alterado")
                return False
        else:
            print(f"❌ Erro: {result2.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Exceção: {e}")
        return False
    
    print("\n🎉 TODOS OS TESTES PASSARAM!")
    print("✅ Sistema funcionando corretamente")
    return True

if __name__ == "__main__":
    try:
        sucesso = teste_prompt_direto()
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
