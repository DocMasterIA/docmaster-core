#!/usr/bin/env python3
"""
Teste simples do sistema estilo ChatGPT
Foca apenas na inserção contextual
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

def teste_simples_chatgpt():
    """Teste simples focado na inserção contextual."""
    
    print("🤖 TESTE SIMPLES - SISTEMA ESTILO CHATGPT")
    print("Foco: Inserção contextual vs final do documento")
    print("=" * 60)
    
    # 1. Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Usando template: {template.name}")
    
    # 2. Prompt simples e direto
    prompt_simples = """
    Adicione uma cláusula de julgamento por técnica e preço APÓS a seção 3.4.14.
    Adicione uma observação prática APÓS o parágrafo 15.16.
    
    IMPORTANTE: Adicione no local contextual correto, não no final.
    """
    
    print(f"\n🎯 Prompt simples:")
    print("-" * 50)
    print(prompt_simples)
    print("-" * 50)
    
    # 3. Processar documento
    print("\n🤖 Processando documento...")
    try:
        result = process_document_with_ai(template.file.path, prompt_simples)
        
        if not result.get('success'):
            print(f"❌ Erro na IA: {result.get('error')}")
            return False
        
        print("✅ Documento processado!")
        print(f"📁 Arquivo: {result.get('output_path')}")
        
        # 4. Analisar posicionamento
        print("\n🔍 Analisando posicionamento das adições...")
        from docx import Document
        
        doc = Document(result['output_path'])
        
        # Encontrar cláusula de julgamento
        clausula_posicao = None
        for i, paragraph in enumerate(doc.paragraphs):
            if "julgamento das propostas" in paragraph.text.lower():
                clausula_posicao = i
                break
        
        # Encontrar observação prática
        obs_posicao = None
        for i, paragraph in enumerate(doc.paragraphs):
            if "OBSERVAÇÃO PRÁTICA" in paragraph.text:
                obs_posicao = i
                break
        
        # Encontrar seção 3.4.14
        secao_314_posicao = None
        for i, paragraph in enumerate(doc.paragraphs):
            if "3.4.14" in paragraph.text:
                secao_314_posicao = i
                break
        
        # Encontrar parágrafo 15.16
        paragrafo_1516_posicao = None
        for i, paragraph in enumerate(doc.paragraphs):
            if "15.16" in paragraph.text:
                paragrafo_1516_posicao = i
                break
        
        # Mostrar posições
        print(f"\n📊 POSIÇÕES NO DOCUMENTO:")
        print(f"  Seção 3.4.14: parágrafo {secao_314_posicao}")
        print(f"  Cláusula julgamento: parágrafo {clausula_posicao}")
        print(f"  Parágrafo 15.16: parágrafo {paragrafo_1516_posicao}")
        print(f"  Observação prática: parágrafo {obs_posicao}")
        print(f"  Total de parágrafos: {len(doc.paragraphs)}")
        
        # Verificar se está contextual
        clausula_contextual = False
        obs_contextual = False
        
        if clausula_posicao is not None and secao_314_posicao is not None:
            if clausula_posicao > secao_314_posicao and clausula_posicao < secao_314_posicao + 10:
                clausula_contextual = True
                print("✅ Cláusula adicionada contextualmente após 3.4.14")
            else:
                print("❌ Cláusula NÃO adicionada contextualmente")
        
        if obs_posicao is not None and paragrafo_1516_posicao is not None:
            if obs_posicao > paragrafo_1516_posicao and obs_posicao < paragrafo_1516_posicao + 10:
                obs_contextual = True
                print("✅ Observação adicionada contextualmente após 15.16")
            else:
                print("❌ Observação NÃO adicionada contextualmente")
        
        # Verificar se está no final (problema)
        clausula_final = False
        obs_final = False
        
        if clausula_posicao is not None:
            if clausula_posicao > len(doc.paragraphs) - 10:  # Últimos 10 parágrafos
                clausula_final = True
                print("⚠️ PROBLEMA: Cláusula adicionada no final do documento")
        
        if obs_posicao is not None:
            if obs_posicao > len(doc.paragraphs) - 10:  # Últimos 10 parágrafos
                obs_final = True
                print("⚠️ PROBLEMA: Observação adicionada no final do documento")
        
        # Resultado final
        if clausula_contextual and obs_contextual:
            print("\n🎉 SUCESSO: Sistema funcionando como ChatGPT!")
            print("✅ Inserção contextual funcionando perfeitamente")
            return True
        elif clausula_final or obs_final:
            print("\n❌ PROBLEMA: Texto ainda sendo adicionado no final")
            print("💡 Precisa melhorar a lógica de inserção contextual")
            return False
        else:
            print("\n⚠️ PARCIAL: Algumas inserções funcionaram, outras não")
            return False
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        sucesso = teste_simples_chatgpt()
        if sucesso:
            print("\n🎉 TESTE CONCLUÍDO COM SUCESSO!")
            print("✅ Sistema funcionando como ChatGPT")
        else:
            print("\n❌ TESTE FALHOU - Precisa melhorar inserção contextual")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
