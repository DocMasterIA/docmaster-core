#!/usr/bin/env python3
"""
Teste do sistema estilo ChatGPT
Verifica se o texto é adicionado contextualmente, não no final

Antes de executar:
1. Ative o ambiente virtual: source venv/bin/activate
2. Execute: python teste_chatgpt_style.py
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

def teste_chatgpt_style():
    """Teste do sistema estilo ChatGPT."""
    
    print("🤖 TESTE DO SISTEMA ESTILO CHATGPT")
    print("Verificando se o texto é adicionado contextualmente")
    print("=" * 60)
    
    # 1. Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Usando template: {template.name}")
    print(f"📁 Arquivo: {template.file.path}")
    
    # 2. Prompt de teste específico
    prompt_teste = """
    Aja como um especialista em licitações públicas.
    
    INSTRUÇÕES ESPECÍFICAS:
    1. Altere o valor de PREÇO TOTAL MÉDIO para R$ 2.500.000,00
    2. Mude ITAJÁ para BRASÍLIA
    3. Adicione uma cláusula de julgamento por técnica e preço APÓS a seção 3.4.14
    4. Adicione uma observação prática APÓS o parágrafo 15.16
    5. Altere o número do edital para 456/2024
    
    IMPORTANTE: Adicione o conteúdo no local contextual correto, não no final do documento.
    """
    
    print(f"\n🎯 Prompt de teste:")
    print("-" * 50)
    print(prompt_teste)
    print("-" * 50)
    
    # 3. Processar documento
    print("\n🤖 Processando documento com IA estilo ChatGPT...")
    try:
        result = process_document_with_ai(template.file.path, prompt_teste)
        
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
        
        # Verificar se as mudanças foram aplicadas contextualmente
        mudancas_verificadas = []
        
        # Verificar valor alterado
        valor_encontrado = False
        for paragraph in doc.paragraphs:
            if "R$ 2.500.000,00" in paragraph.text:
                valor_encontrado = True
                mudancas_verificadas.append("✅ Valor alterado para R$ 2.500.000,00")
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
        
        # Verificar cláusula de julgamento adicionada contextualmente
        clausula_contextual = False
        clausula_final = False
        
        for i, paragraph in enumerate(doc.paragraphs):
            if "3.4.15. O julgamento das propostas" in paragraph.text:
                # Verificar se está após 3.4.14 (contextual)
                for j in range(max(0, i-5), i):
                    if "3.4.14" in doc.paragraphs[j].text:
                        clausula_contextual = True
                        mudancas_verificadas.append("✅ Cláusula de julgamento adicionada contextualmente após 3.4.14")
                        break
                
                # Verificar se está no final (problema)
                if i > len(doc.paragraphs) - 10:  # Últimos 10 parágrafos
                    clausula_final = True
        
        if clausula_final and not clausula_contextual:
            mudancas_verificadas.append("❌ PROBLEMA: Cláusula adicionada no final, não contextualmente")
        elif not clausula_contextual and not clausula_final:
            mudancas_verificadas.append("❌ Cláusula de julgamento não encontrada")
        
        # Verificar observação prática adicionada contextualmente
        obs_contextual = False
        obs_final = False
        
        for i, paragraph in enumerate(doc.paragraphs):
            if "OBSERVAÇÃO PRÁTICA" in paragraph.text:
                # Verificar se está após 15.16 (contextual)
                for j in range(max(0, i-5), i):
                    if "15.16" in doc.paragraphs[j].text:
                        obs_contextual = True
                        mudancas_verificadas.append("✅ Observação prática adicionada contextualmente após 15.16")
                        break
                
                # Verificar se está no final (problema)
                if i > len(doc.paragraphs) - 10:  # Últimos 10 parágrafos
                    obs_final = True
        
        if obs_final and not obs_contextual:
            mudancas_verificadas.append("❌ PROBLEMA: Observação adicionada no final, não contextualmente")
        elif not obs_contextual and not obs_final:
            mudancas_verificadas.append("❌ Observação prática não encontrada")
        
        # Verificar número do edital
        edital_encontrado = False
        for paragraph in doc.paragraphs:
            if "456/2024" in paragraph.text:
                edital_encontrado = True
                mudancas_verificadas.append("✅ Número do edital alterado para 456/2024")
                break
        
        if not edital_encontrado:
            mudancas_verificadas.append("❌ Número do edital não alterado")
        
        # Mostrar resultados
        print("\n📊 RESULTADOS DAS MUDANÇAS:")
        print("-" * 50)
        for mudanca in mudancas_verificadas:
            print(mudanca)
        
        # Contar sucessos
        sucessos = sum(1 for m in mudancas_verificadas if m.startswith("✅"))
        total = len(mudancas_verificadas)
        
        print(f"\n📈 TAXA DE SUCESSO: {sucessos}/{total} ({sucessos/total*100:.1f}%)")
        
        # Verificar se o problema do final foi resolvido
        if clausula_contextual and obs_contextual:
            print("\n🎉 SUCESSO: Sistema funcionando como ChatGPT!")
            print("✅ Texto adicionado contextualmente, não no final")
            return True
        else:
            print("\n⚠️ PROBLEMA: Ainda há texto sendo adicionado no final")
            return False
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        sucesso = teste_chatgpt_style()
        if sucesso:
            print("\n🎉 TESTE CONCLUÍDO COM SUCESSO!")
            print("✅ Sistema funcionando como ChatGPT")
            print("✅ Inserção contextual funcionando")
        else:
            print("\n❌ TESTE FALHOU - Ainda há problemas")
            print("💡 Verifique se o texto está sendo adicionado no local correto")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)