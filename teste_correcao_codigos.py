#!/usr/bin/env python3
"""
Teste para verificar se os códigos [P1], [P2], etc. foram removidos.
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


def testar_correcao_codigos():
    """
    Testa se os códigos [P1], [P2], etc. foram removidos.
    """
    print("🧪 Testando correção dos códigos [P1], [P2], etc.")
    print("=" * 60)
    
    # Buscar o template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return
    
    print(f"📄 Template: {template.name}")
    print()
    
    # Teste simples
    prompt = "Altere o valor de R$ 150.000,00 para R$ 200.000,00"
    print(f"🔧 Prompt: {prompt}")
    
    try:
        result = process_document_with_ai(template.file.path, prompt)
        
        if result.get('success'):
            print("✅ Processamento bem-sucedido!")
            print(f"📄 Documento salvo em: {result['output_path']}")
            print(f"📝 Mudanças: {result['changes_made']}")
            
            # Verificar se o arquivo foi criado
            if os.path.exists(result['output_path']):
                print("\n🔍 Verificando conteúdo do documento gerado...")
                
                # Ler o documento gerado para verificar se tem códigos
                from docx import Document
                doc = Document(result['output_path'])
                
                has_codes = False
                for paragraph in doc.paragraphs[:10]:  # Verificar primeiros 10 parágrafos
                    text = paragraph.text
                    if '[P' in text or '[TABELA' in text:
                        has_codes = True
                        print(f"❌ Código encontrado: {text[:100]}...")
                        break
                
                if not has_codes:
                    print("✅ Nenhum código [P1], [P2], etc. encontrado!")
                    print("✅ Documento limpo e editável!")
                else:
                    print("❌ Ainda há códigos no documento!")
                    
            else:
                print("❌ Arquivo não foi criado")
        else:
            print(f"❌ Erro: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Erro no teste: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    testar_correcao_codigos()
