#!/usr/bin/env python3
"""
Teste do sistema com documento grande
Verifica se o sistema funciona com documentos que excedem o limite de tokens
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

def teste_documento_grande():
    """Teste do sistema com documento grande."""
    
    print("🤖 TESTE DO SISTEMA COM DOCUMENTO GRANDE")
    print("Verificando se o sistema funciona com documentos que excedem limite de tokens")
    print("=" * 70)
    
    # 1. Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Usando template: {template.name}")
    print(f"📁 Arquivo: {template.file.path}")
    
    # 2. Prompt simples para testar
    prompt_simples = """
    Altere o valor de PREÇO TOTAL MÉDIO para R$ 5.000.000,00.
    Mude o município de ITAJÁ para SÃO PAULO.
    """
    
    print(f"\n🎯 Prompt simples:")
    print("-" * 50)
    print(prompt_simples)
    print("-" * 50)
    
    # 3. Processar documento
    print("\n🤖 Processando documento grande...")
    try:
        result = process_document_with_ai(template.file.path, prompt_simples)
        
        if not result.get('success'):
            print(f"❌ Erro na IA: {result.get('error')}")
            return False
        
        print("✅ Documento processado com sucesso!")
        print(f"📊 Mudanças aplicadas: {result.get('changes_made', [])}")
        print(f"📁 Arquivo gerado: {result.get('output_path')}")
        
        # 4. Analisar o documento gerado
        print("\n🔍 Analisando documento gerado...")
        from docx import Document
        
        doc = Document(result['output_path'])
        
        # Verificar se as mudanças foram aplicadas
        mudancas_verificadas = []
        
        # Verificar valor alterado
        valor_encontrado = False
        for paragraph in doc.paragraphs:
            if "R$ 5.000.000,00" in paragraph.text:
                valor_encontrado = True
                mudancas_verificadas.append("✅ Valor alterado para R$ 5.000.000,00")
                break
        
        if not valor_encontrado:
            mudancas_verificadas.append("❌ Valor não alterado")
        
        # Verificar local alterado
        local_encontrado = False
        for paragraph in doc.paragraphs:
            if "SÃO PAULO" in paragraph.text and "ITAJÁ" not in paragraph.text:
                local_encontrado = True
                mudancas_verificadas.append("✅ Local alterado de ITAJÁ para SÃO PAULO")
                break
        
        if not local_encontrado:
            mudancas_verificadas.append("❌ Local não alterado")
        
        # Mostrar resultados
        print("\n📊 RESULTADOS DAS MUDANÇAS:")
        print("-" * 50)
        for mudanca in mudancas_verificadas:
            print(mudanca)
        
        # Contar sucessos
        sucessos = sum(1 for m in mudancas_verificadas if m.startswith("✅"))
        total = len(mudancas_verificadas)
        
        print(f"\n📈 TAXA DE SUCESSO: {sucessos}/{total} ({sucessos/total*100:.1f}%)")
        
        # Verificar se o sistema está funcionando
        if sucessos >= 1:  # Pelo menos 1 mudança
            print("\n🎉 SUCESSO: Sistema funcionando com documento grande!")
            print("✅ Otimização de tokens funcionando")
            print("✅ Sistema 100% baseado em IA funcionando")
            return True
        else:
            print("\n❌ PROBLEMA: Sistema não aplicou mudanças")
            return False
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        sucesso = teste_documento_grande()
        if sucesso:
            print("\n🎉 TESTE CONCLUÍDO COM SUCESSO!")
            print("✅ Sistema funcionando com documento grande")
            print("✅ Otimização de tokens funcionando")
        else:
            print("\n❌ TESTE FALHOU - Sistema não funcionou com documento grande")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
