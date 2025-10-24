#!/usr/bin/env python3
"""
Teste para verificar se a substituição de cidades foi melhorada
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

def teste_cidade_melhorada():
    """Teste para verificar se a substituição de cidades foi melhorada."""
    
    print("🏙️ TESTE: MELHORIA NA SUBSTITUIÇÃO DE CIDADES")
    print("=" * 60)
    
    # Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Template: {template.name}")
    
    # Teste: Prompt simples sem especificar maiúsculo
    print("\n🔍 TESTE: Prompt simples sem especificar maiúsculo")
    print("-" * 50)
    
    prompt = "Modifique o documento para uma licitação em Belo Horizonte e o valor R$ 200.000.000,00 e adicione cláusulas de penalidades por atraso."
    
    print(f"Prompt: {prompt}")
    
    try:
        result = process_document_with_ai(template.file.path, prompt)
        
        if result.get('success'):
            print("✅ Documento processado com sucesso")
            
            # Verificar se TODAS as ocorrências de ITAJÁ foram alteradas
            from docx import Document
            doc = Document(result['output_path'])
            
            # Contar ocorrências
            itaja_count = 0
            belo_horizonte_count = 0
            
            for paragraph in doc.paragraphs:
                text = paragraph.text.upper()
                itaja_count += text.count('ITAJÁ')
                belo_horizonte_count += text.count('BELO HORIZONTE')
            
            # Verificar em tabelas também
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        text = cell.text.upper()
                        itaja_count += text.count('ITAJÁ')
                        belo_horizonte_count += text.count('BELO HORIZONTE')
            
            print(f"📊 Ocorrências de 'ITAJÁ' restantes: {itaja_count}")
            print(f"📊 Ocorrências de 'BELO HORIZONTE' encontradas: {belo_horizonte_count}")
            
            # Verificar valor monetário
            valor_ok = False
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if "R$ 200.000.000,00" in cell.text:
                            valor_ok = True
                            print("✅ Valor alterado para R$ 200.000.000,00")
                            break
                    if valor_ok:
                        break
                if valor_ok:
                    break
            
            # Verificar cláusulas de penalidades
            clausulas_ok = False
            for paragraph in doc.paragraphs:
                if "PENALIDADES" in paragraph.text.upper() or "MULTAS" in paragraph.text.upper():
                    clausulas_ok = True
                    print("✅ Cláusulas de penalidades adicionadas")
                    break
            
            # Resultado
            if itaja_count == 0 and belo_horizonte_count > 0 and valor_ok:
                print("✅ TESTE: PASSOU - Todas as ocorrências de ITAJÁ foram alteradas")
                if clausulas_ok:
                    print("✅ BONUS: Cláusulas de penalidades também foram adicionadas")
                return True
            else:
                print("❌ TESTE: FALHOU - Ainda há ocorrências de ITAJÁ não alteradas")
                return False
        else:
            print(f"❌ TESTE: Erro - {result.get('error')}")
            return False
    except Exception as e:
        print(f"❌ TESTE: Exceção - {e}")
        return False

if __name__ == "__main__":
    try:
        sucesso = teste_cidade_melhorada()
        if sucesso:
            print("\n🎉 TESTE CONCLUÍDO COM SUCESSO!")
            print("✅ A substituição de cidades foi melhorada")
            print("✅ Agora funciona sem especificar maiúsculo no prompt")
        else:
            print("\n❌ TESTE FALHOU")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
