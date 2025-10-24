#!/usr/bin/env python3
"""
Teste para verificar se o vício no valor 7.500.000,00 foi corrigido
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

def teste_vicio_corrigido():
    """Teste para verificar se o vício foi corrigido."""
    
    print("🔧 TESTE: CORREÇÃO DO VÍCIO NO VALOR 7.500.000,00")
    print("=" * 60)
    
    # Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Template: {template.name}")
    
    # Teste 1: Prompt que especifica "PREÇO TOTAL MÉDIO" (deve funcionar)
    print("\n✅ TESTE 1: Com 'PREÇO TOTAL MÉDIO' especificado")
    print("-" * 50)
    
    prompt1 = "Modifique o documento para uma licitação em Belo Horizonte e mude PREÇO TOTAL MÉDIO para 'R$ 200.000.000,00' e adicione cláusulas de penalidades por atraso."
    
    try:
        result1 = process_document_with_ai(template.file.path, prompt1)
        
        if result1.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar se o valor correto foi aplicado
            from docx import Document
            doc1 = Document(result1['output_path'])
            
            valor_correto = False
            valor_viciado = False
            
            for table in doc1.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if "R$ 200.000.000,00" in cell.text:
                            valor_correto = True
                            print("✅ Valor correto aplicado: R$ 200.000.000,00")
                        if "R$ 7.500.000,00" in cell.text:
                            valor_viciado = True
                            print("❌ Valor viciado encontrado: R$ 7.500.000,00")
            
            if valor_correto and not valor_viciado:
                print("✅ TESTE 1: PASSOU - Valor correto aplicado")
            else:
                print("❌ TESTE 1: FALHOU")
                return False
        else:
            print(f"❌ TESTE 1: Erro - {result1.get('error')}")
            return False
    except Exception as e:
        print(f"❌ TESTE 1: Exceção - {e}")
        return False
    
    # Teste 2: Prompt que NÃO especifica "PREÇO TOTAL MÉDIO" (deve funcionar agora)
    print("\n🔍 TESTE 2: Sem 'PREÇO TOTAL MÉDIO' especificado")
    print("-" * 50)
    
    prompt2 = "Modifique o documento para uma licitação em Belo Horizonte e o valor R$ 200.000.000,00 e adicione cláusulas de penalidades por atraso."
    
    try:
        result2 = process_document_with_ai(template.file.path, prompt2)
        
        if result2.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar se o valor correto foi aplicado
            doc2 = Document(result2['output_path'])
            
            valor_correto = False
            valor_viciado = False
            
            for table in doc2.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if "R$ 200.000.000,00" in cell.text:
                            valor_correto = True
                            print("✅ Valor correto aplicado: R$ 200.000.000,00")
                        if "R$ 7.500.000,00" in cell.text:
                            valor_viciado = True
                            print("❌ Valor viciado encontrado: R$ 7.500.000,00")
            
            if valor_correto and not valor_viciado:
                print("✅ TESTE 2: PASSOU - Valor correto aplicado sem vício")
            else:
                print("❌ TESTE 2: FALHOU - Ainda há vício no valor")
                return False
        else:
            print(f"❌ TESTE 2: Erro - {result2.get('error')}")
            return False
    except Exception as e:
        print(f"❌ TESTE 2: Exceção - {e}")
        return False
    
    # Teste 3: Verificar se Belo Horizonte foi aplicado
    print("\n🏙️ TESTE 3: Verificar mudança de local")
    print("-" * 50)
    
    local_ok = False
    for paragraph in doc2.paragraphs:
        if "BELO HORIZONTE" in paragraph.text.upper() and "ITAJÁ" not in paragraph.text.upper():
            local_ok = True
            print("✅ Local alterado para BELO HORIZONTE")
            break
    
    if local_ok:
        print("✅ TESTE 3: PASSOU - Local alterado corretamente")
    else:
        print("❌ TESTE 3: FALHOU - Local não foi alterado")
        return False
    
    print("\n🎉 RESULTADO FINAL")
    print("=" * 60)
    print("✅ TESTE 1: Com 'PREÇO TOTAL MÉDIO' - PASSOU")
    print("✅ TESTE 2: Sem 'PREÇO TOTAL MÉDIO' - PASSOU")
    print("✅ TESTE 3: Mudança de local - PASSOU")
    print("\n🎉 VÍCIO NO VALOR 7.500.000,00 CORRIGIDO!")
    print("✅ Sistema agora funciona independente da especificação")
    
    return True

if __name__ == "__main__":
    try:
        sucesso = teste_vicio_corrigido()
        if sucesso:
            print("\n🎉 TESTE CONCLUÍDO COM SUCESSO!")
            print("✅ O vício no valor 7.500.000,00 foi corrigido")
        else:
            print("\n❌ TESTE FALHOU")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
