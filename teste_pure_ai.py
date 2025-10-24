#!/usr/bin/env python3
"""
Teste do sistema 100% baseado em IA
Sem regras fixas, sem regex, sem contexto pré-definido
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

def teste_pure_ai():
    """Teste do sistema 100% baseado em IA."""
    
    print("🤖 TESTE DO SISTEMA 100% BASEADO EM IA")
    print("Sem regras fixas, sem regex, sem contexto pré-definido")
    print("A IA decide tudo baseada no documento e no prompt")
    print("=" * 70)
    
    # 1. Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Usando template: {template.name}")
    print(f"📁 Arquivo: {template.file.path}")
    
    # 2. Prompt livre - sem referências específicas
    prompt_livre = """
    Adicione uma cláusula de julgamento por técnica e preço no local apropriado.
    Adicione uma observação prática onde fizer sentido no documento.
    Altere o valor de PREÇO TOTAL MÉDIO para R$ 3.000.000,00.
    Mude o município de ITAJÁ para BRASÍLIA.
    
    IMPORTANTE: Analise o documento e decida onde fazer cada mudança baseado no contexto.
    """
    
    print(f"\n🎯 Prompt livre (sem regras fixas):")
    print("-" * 60)
    print(prompt_livre)
    print("-" * 60)
    
    # 3. Processar documento
    print("\n🤖 Processando documento com IA pura...")
    try:
        result = process_document_with_ai(template.file.path, prompt_livre)
        
        if not result.get('success'):
            print(f"❌ Erro na IA: {result.get('error')}")
            return False
        
        print("✅ Documento processado com IA pura!")
        print(f"📊 Mudanças aplicadas: {result.get('changes_made', [])}")
        print(f"📁 Arquivo gerado: {result.get('output_path')}")
        
        # 4. Analisar o documento gerado
        print("\n🔍 Analisando documento gerado pela IA...")
        from docx import Document
        
        doc = Document(result['output_path'])
        
        # Verificar se as mudanças foram aplicadas
        mudancas_verificadas = []
        
        # Verificar valor alterado
        valor_encontrado = False
        for paragraph in doc.paragraphs:
            if "R$ 3.000.000,00" in paragraph.text:
                valor_encontrado = True
                mudancas_verificadas.append("✅ Valor alterado para R$ 3.000.000,00")
                break
        
        if not valor_encontrado:
            mudancas_verificadas.append("❌ Valor não alterado")
        
        # Verificar local alterado
        local_encontrado = False
        for paragraph in doc.paragraphs:
            if "BRASÍLIA" in paragraph.text and "ITAJÁ" not in paragraph.text:
                local_encontrado = True
                mudancas_verificadas.append("✅ Local alterado de ITAJÁ para BRASÍLIA")
                break
        
        if not local_encontrado:
            mudancas_verificadas.append("❌ Local não alterado")
        
        # Verificar cláusula de julgamento adicionada
        clausula_encontrada = False
        for paragraph in doc.paragraphs:
            if "julgamento das propostas" in paragraph.text.lower():
                clausula_encontrada = True
                mudancas_verificadas.append("✅ Cláusula de julgamento adicionada")
                break
        
        if not clausula_encontrada:
            mudancas_verificadas.append("❌ Cláusula de julgamento não encontrada")
        
        # Verificar observação prática adicionada
        obs_encontrada = False
        for paragraph in doc.paragraphs:
            if "OBSERVAÇÃO PRÁTICA" in paragraph.text:
                obs_encontrada = True
                mudancas_verificadas.append("✅ Observação prática adicionada")
                break
        
        if not obs_encontrada:
            mudancas_verificadas.append("❌ Observação prática não encontrada")
        
        # Mostrar resultados
        print("\n📊 RESULTADOS DAS MUDANÇAS:")
        print("-" * 50)
        for mudanca in mudancas_verificadas:
            print(mudanca)
        
        # Contar sucessos
        sucessos = sum(1 for m in mudancas_verificadas if m.startswith("✅"))
        total = len(mudancas_verificadas)
        
        print(f"\n📈 TAXA DE SUCESSO: {sucessos}/{total} ({sucessos/total*100:.1f}%)")
        
        # Verificar se a IA está funcionando
        if sucessos >= 3:  # Pelo menos 3 das 4 mudanças
            print("\n🎉 SUCESSO: Sistema 100% baseado em IA funcionando!")
            print("✅ IA decidindo onde fazer mudanças baseada no contexto")
            print("✅ Sem regras fixas, sem regex, sem contexto pré-definido")
            return True
        else:
            print("\n⚠️ PARCIAL: IA funcionando parcialmente")
            print("💡 Verifique se a IA está analisando o documento corretamente")
            return False
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        sucesso = teste_pure_ai()
        if sucesso:
            print("\n🎉 TESTE CONCLUÍDO COM SUCESSO!")
            print("✅ Sistema 100% baseado em IA funcionando")
            print("✅ Exatamente como o ChatGPT - sem regras fixas")
        else:
            print("\n❌ TESTE FALHOU - IA precisa melhorar análise")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
