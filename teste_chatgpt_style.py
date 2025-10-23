#!/usr/bin/env python3
"""
Teste da nova abordagem estilo ChatGPT - simples e direta.
"""

import os
import sys
import django

# Configurar Django
sys.path.append('/home/adryan/Downloads/mdlicitatech-system/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mdlicitatech.settings')
django.setup()

from backend.app.services.ia import process_document_with_ai
from backend.app.models import Template


def testar_estilo_chatgpt():
    """
    Testa a nova abordagem estilo ChatGPT.
    """
    print("🤖 Testando abordagem ESTILO CHATGPT")
    print("=" * 60)
    
    # Buscar o template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return
    
    print(f"📄 Template: {template.name}")
    print()
    
    # Teste com o prompt que você mencionou
    prompt = "Troque R$ 5.678.659,46 por R$ 2.500.000,00"
    print(f"🔧 Prompt: {prompt}")
    print()
    
    try:
        print("🚀 Processando documento...")
        result = process_document_with_ai(template.file.path, prompt)
        
        if result.get('success'):
            print("✅ Processamento bem-sucedido!")
            print(f"📄 Documento salvo em: {result['output_path']}")
            print(f"📝 Mudanças: {result['changes_made']}")
            
            # Verificar se o arquivo foi criado
            if os.path.exists(result['output_path']):
                print("\n🔍 Verificando resultado...")
                
                # Ler o documento gerado
                from docx import Document
                doc = Document(result['output_path'])
                
                # Verificar se ainda tem estrutura
                total_paragraphs = len(doc.paragraphs)
                total_tables = len(doc.tables)
                
                print(f"📊 Estrutura do documento:")
                print(f"   - Parágrafos: {total_paragraphs}")
                print(f"   - Tabelas: {total_tables}")
                
                # Procurar pelo valor alterado
                found_old = False
                found_new = False
                
                for paragraph in doc.paragraphs:
                    text = paragraph.text
                    if "5.678.659,46" in text:
                        found_old = True
                    if "2.500.000,00" in text:
                        found_new = True
                
                if found_new:
                    print("✅ Valor alterado encontrado no documento!")
                elif found_old:
                    print("⚠️ Valor antigo ainda presente")
                else:
                    print("❓ Não foi possível verificar a alteração")
                    
            else:
                print("❌ Arquivo não foi criado")
        else:
            print(f"❌ Erro: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Erro no teste: {str(e)}")
        import traceback
        traceback.print_exc()


def testar_prompts_simples():
    """
    Testa com prompts mais simples.
    """
    print("\n🧪 Testando com prompts simples")
    print("=" * 60)
    
    template = Template.objects.first()
    if not template:
        return
    
    prompts_simples = [
        "Altere o número do edital de 005/2025 para 456/2024",
        "Mude o número do pregão de 005/2025 para 789/2024",
        "Altere todas as referências de ITAJÁ para BRASÍLIA"
    ]
    
    for i, prompt in enumerate(prompts_simples, 1):
        print(f"\n🔧 Teste {i}: {prompt}")
        
        try:
            result = process_document_with_ai(template.file.path, prompt)
            
            if result.get('success'):
                print("✅ Sucesso!")
                print(f"📝 Mudanças: {result['changes_made']}")
            else:
                print(f"❌ Erro: {result.get('error')}")
                
        except Exception as e:
            print(f"❌ Erro: {str(e)}")


if __name__ == "__main__":
    testar_estilo_chatgpt()
    testar_prompts_simples()
