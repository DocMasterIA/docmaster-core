#!/usr/bin/env python3
"""
Teste do sistema SEM regras fixas
A IA decide tudo baseada no documento e no prompt
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

def teste_sem_regras():
    """Teste do sistema SEM regras fixas."""
    
    print("🤖 TESTE DO SISTEMA SEM REGRAS FIXAS")
    print("A IA decide tudo baseada no documento e no prompt")
    print("=" * 60)
    
    # 1. Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Usando template: {template.name}")
    
    # 2. Prompt livre - sem referências específicas
    prompt_livre = """
    Altere o valor de PREÇO TOTAL MÉDIO para R$ 7.500.000,00.
    Mude o município de ITAJÁ para RIO DE JANEIRO.
    """
    
    print(f"\n🎯 Prompt livre:")
    print("-" * 40)
    print(prompt_livre)
    print("-" * 40)
    
    # 3. Processar documento
    print("\n🤖 Processando documento...")
    try:
        result = process_document_with_ai(template.file.path, prompt_livre)
        
        if not result.get('success'):
            print(f"❌ Erro na IA: {result.get('error')}")
            return False
        
        print("✅ Documento processado!")
        print(f"📊 Mudanças aplicadas: {result.get('changes_made', [])}")
        print(f"📁 Arquivo: {result.get('output_path')}")
        
        # 4. Verificar mudanças
        print("\n🔍 Verificando mudanças...")
        from docx import Document
        
        doc = Document(result['output_path'])
        
        # Verificar valor
        valor_encontrado = False
        
        # Procurar em parágrafos
        for paragraph in doc.paragraphs:
            if "R$ 7.500.000,00" in paragraph.text:
                valor_encontrado = True
                print("✅ Valor alterado para R$ 7.500.000,00")
                break
        
        # Procurar em tabelas
        if not valor_encontrado:
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            if "R$ 7.500.000,00" in paragraph.text:
                                valor_encontrado = True
                                print("✅ Valor alterado para R$ 7.500.000,00")
                                break
                        if valor_encontrado:
                            break
                    if valor_encontrado:
                        break
                if valor_encontrado:
                    break
        
        if not valor_encontrado:
            print("❌ Valor não alterado")
        
        # Verificar local
        local_encontrado = False
        for paragraph in doc.paragraphs:
            if "RIO DE JANEIRO" in paragraph.text and "ITAJÁ" not in paragraph.text:
                local_encontrado = True
                print("✅ Local alterado de ITAJÁ para RIO DE JANEIRO")
                break
        
        if not local_encontrado:
            print("❌ Local não alterado")
        
        # Resultado
        if valor_encontrado and local_encontrado:
            print("\n🎉 SUCESSO: Sistema funcionando sem regras fixas!")
            print("✅ A IA decidiu onde fazer as mudanças")
            return True
        else:
            print("\n⚠️ PARCIAL: Algumas mudanças não foram aplicadas")
            return False
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        sucesso = teste_sem_regras()
        if sucesso:
            print("\n🎉 TESTE CONCLUÍDO COM SUCESSO!")
            print("✅ Sistema funcionando sem regras fixas")
        else:
            print("\n❌ TESTE FALHOU")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
