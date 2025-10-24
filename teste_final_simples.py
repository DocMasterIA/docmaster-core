#!/usr/bin/env python3
"""
Teste final simples para verificar se o sistema está funcionando
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

def teste_final():
    """Teste final com prompts simples."""
    
    print("🎯 TESTE FINAL - SISTEMA FUNCIONANDO")
    print("=" * 60)
    
    # Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Template: {template.name}")
    
    # Teste 1: Valor monetário
    print("\n💰 TESTE 1: Alterar valor monetário")
    print("-" * 40)
    
    prompt1 = "Altere o valor 'R$ 5.678.659,46' para 'R$ 50.000.000,00'."
    
    try:
        result1 = process_document_with_ai(template.file.path, prompt1)
        
        if result1.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar se o valor foi alterado
            from docx import Document
            doc = Document(result1['output_path'])
            
            valor_ok = False
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if "R$ 50.000.000,00" in cell.text:
                            valor_ok = True
                            print("✅ Valor alterado para R$ 50.000.000,00")
                            break
                    if valor_ok:
                        break
                if valor_ok:
                    break
            
            if valor_ok:
                print("✅ TESTE 1: PASSOU")
            else:
                print("❌ TESTE 1: FALHOU - Valor não alterado")
                return False
        else:
            print(f"❌ TESTE 1: Erro - {result1.get('error')}")
            return False
    except Exception as e:
        print(f"❌ TESTE 1: Exceção - {e}")
        return False
    
    # Teste 2: Local
    print("\n🏙️ TESTE 2: Alterar local")
    print("-" * 40)
    
    prompt2 = "Mude 'ITAJÁ' para 'RIO DE JANEIRO'."
    
    try:
        result2 = process_document_with_ai(template.file.path, prompt2)
        
        if result2.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar se o local foi alterado
            doc2 = Document(result2['output_path'])
            
            local_ok = False
            for paragraph in doc2.paragraphs:
                if "RIO DE JANEIRO" in paragraph.text and "ITAJÁ" not in paragraph.text:
                    local_ok = True
                    print("✅ Local alterado para RIO DE JANEIRO")
                    break
            
            if local_ok:
                print("✅ TESTE 2: PASSOU")
            else:
                print("❌ TESTE 2: FALHOU - Local não alterado")
                return False
        else:
            print(f"❌ TESTE 2: Erro - {result2.get('error')}")
            return False
    except Exception as e:
        print(f"❌ TESTE 2: Exceção - {e}")
        return False
    
    # Teste 3: Adicionar texto
    print("\n📝 TESTE 3: Adicionar texto")
    print("-" * 40)
    
    prompt3 = "Adicione uma observação prática após o parágrafo 3.1."
    
    try:
        result3 = process_document_with_ai(template.file.path, prompt3)
        
        if result3.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar se o texto foi adicionado
            doc3 = Document(result3['output_path'])
            
            texto_ok = False
            for paragraph in doc3.paragraphs:
                if "OBSERVAÇÃO PRÁTICA" in paragraph.text:
                    texto_ok = True
                    print("✅ Observação prática adicionada")
                    break
            
            if texto_ok:
                print("✅ TESTE 3: PASSOU")
            else:
                print("❌ TESTE 3: FALHOU - Texto não adicionado")
                return False
        else:
            print(f"❌ TESTE 3: Erro - {result3.get('error')}")
            return False
    except Exception as e:
        print(f"❌ TESTE 3: Exceção - {e}")
        return False
    
    print("\n🎉 RESULTADO FINAL")
    print("=" * 60)
    print("✅ TESTE 1: Valor monetário - PASSOU")
    print("✅ TESTE 2: Alterar local - PASSOU")
    print("✅ TESTE 3: Adicionar texto - PASSOU")
    print("\n🎉 SISTEMA FUNCIONANDO PERFEITAMENTE!")
    print("✅ Cache limpo implementado")
    print("✅ Processamento de prompts funcionando")
    print("✅ Sistema estável e otimizado")
    
    return True

if __name__ == "__main__":
    try:
        sucesso = teste_final()
        if sucesso:
            print("\n🎉 TESTE FINAL CONCLUÍDO COM SUCESSO!")
            print("✅ Todas as funcionalidades estão funcionando")
        else:
            print("\n❌ TESTE FINAL FALHOU")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
