#!/usr/bin/env python3
"""
Debug da resposta da IA
Verifica o que a IA está retornando
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

def debug_ia_response():
    """Debug da resposta da IA."""
    
    print("🔍 DEBUG DA RESPOSTA DA IA")
    print("=" * 40)
    
    # 1. Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Usando template: {template.name}")
    
    # 2. Prompt simples
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
        
        # 4. Verificar se o valor foi alterado
        print("\n🔍 Verificando se o valor foi alterado...")
        from docx import Document
        
        doc = Document(result['output_path'])
        
        # Procurar pelo valor antigo e novo
        valor_antigo_encontrado = False
        valor_novo_encontrado = False
        
        for paragraph in doc.paragraphs:
            if "R$ 5.678.659,46" in paragraph.text:
                valor_antigo_encontrado = True
                print(f"❌ Valor antigo ainda presente: {paragraph.text}")
            if "R$ 7.500.000,00" in paragraph.text:
                valor_novo_encontrado = True
                print(f"✅ Valor novo encontrado: {paragraph.text}")
        
        if not valor_antigo_encontrado and not valor_novo_encontrado:
            print("⚠️ Nenhum valor monetário encontrado")
        
        # Procurar em tabelas
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        if "R$ 5.678.659,46" in paragraph.text:
                            valor_antigo_encontrado = True
                            print(f"❌ Valor antigo ainda presente na tabela: {paragraph.text}")
                        if "R$ 7.500.000,00" in paragraph.text:
                            valor_novo_encontrado = True
                            print(f"✅ Valor novo encontrado na tabela: {paragraph.text}")
        
        # Resultado
        if valor_novo_encontrado:
            print("\n🎉 SUCESSO: Valor alterado!")
        else:
            print("\n❌ PROBLEMA: Valor não foi alterado")
            print("💡 A IA pode não ter encontrado o valor original")
        
        return valor_novo_encontrado
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        sucesso = debug_ia_response()
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
