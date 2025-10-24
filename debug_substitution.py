#!/usr/bin/env python3
"""
Debug da substituição
Verifica se a substituição está funcionando
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

from backend.app.services.pure_ai_processor import apply_substitution
from backend.app.models import Template
from docx import Document

def debug_substitution():
    """Debug da substituição."""
    
    print("🔍 DEBUG DA SUBSTITUIÇÃO")
    print("=" * 40)
    
    # 1. Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Usando template: {template.name}")
    
    # 2. Carregar documento
    doc = Document(template.file.path)
    
    # 3. Testar substituição
    old_text = "PREÇO TOTAL MÉDIO: | R$ 5.678.659,46"
    new_text = "PREÇO TOTAL MÉDIO: | R$ 7.500.000,00"
    
    print(f"\n🎯 Testando substituição:")
    print(f"  Antigo: {old_text}")
    print(f"  Novo: {new_text}")
    
    # 4. Verificar se o texto antigo existe
    print("\n🔍 Verificando se o texto antigo existe...")
    found_old = False
    for paragraph in doc.paragraphs:
        if old_text in paragraph.text:
            found_old = True
            print(f"✅ Texto antigo encontrado em parágrafo: {paragraph.text}")
            break
    
    if not found_old:
        print("❌ Texto antigo não encontrado em parágrafos")
        
        # Procurar em tabelas
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        if old_text in paragraph.text:
                            found_old = True
                            print(f"✅ Texto antigo encontrado em tabela: {paragraph.text}")
                            break
                    if found_old:
                        break
                if found_old:
                    break
            if found_old:
                break
    
    if not found_old:
        print("❌ Texto antigo não encontrado em lugar nenhum")
        return False
    
    # 5. Aplicar substituição
    print("\n🔧 Aplicando substituição...")
    result = apply_substitution(doc, old_text, new_text)
    
    if result:
        print("✅ Substituição aplicada com sucesso!")
        
        # 6. Verificar se a substituição funcionou
        print("\n🔍 Verificando se a substituição funcionou...")
        found_new = False
        for paragraph in doc.paragraphs:
            if "R$ 7.500.000,00" in paragraph.text:
                found_new = True
                print(f"✅ Texto novo encontrado em parágrafo: {paragraph.text}")
                break
        
        if not found_new:
            print("❌ Texto novo não encontrado em parágrafos")
            
            # Procurar em tabelas
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            if "R$ 7.500.000,00" in paragraph.text:
                                found_new = True
                                print(f"✅ Texto novo encontrado em tabela: {paragraph.text}")
                                break
                        if found_new:
                            break
                    if found_new:
                        break
                if found_new:
                    break
        
        if found_new:
            print("\n🎉 SUCESSO: Substituição funcionou!")
        else:
            print("\n❌ PROBLEMA: Substituição não funcionou")
        
        return found_new
    else:
        print("❌ Substituição falhou")
        return False

if __name__ == "__main__":
    try:
        sucesso = debug_substitution()
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
