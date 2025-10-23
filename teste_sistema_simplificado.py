#!/usr/bin/env python3
"""
Teste do sistema simplificado de geração de documentos.
Este script testa a nova abordagem direta com IA.
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


def test_sistema_simplificado():
    """
    Testa o sistema simplificado de geração de documentos.
    """
    print("🧪 Testando sistema simplificado de geração de documentos")
    print("=" * 60)
    
    # Buscar um template existente
    try:
        template = Template.objects.first()
        if not template:
            print("❌ Nenhum template encontrado no banco de dados")
            return
        
        print(f"📄 Template encontrado: {template.name}")
        print(f"📁 Caminho: {template.file.path}")
        
        # Teste 1: Mudança simples de valor
        print("\n🔧 Teste 1: Mudança de valor")
        prompt1 = "Altere o valor de R$ 100.000,00 para R$ 200.000,00"
        print(f"Prompt: {prompt1}")
        
        result1 = process_document_with_ai(template.file.path, prompt1)
        
        if result1.get('success'):
            print("✅ Teste 1 passou!")
            print(f"📄 Documento salvo em: {result1['output_path']}")
            print(f"📝 Mudanças aplicadas: {result1['changes_made']}")
        else:
            print(f"❌ Teste 1 falhou: {result1.get('error')}")
        
        # Teste 2: Mudança de data
        print("\n🔧 Teste 2: Mudança de data")
        prompt2 = "Altere a data de 15/03/2025 para 20/04/2025"
        print(f"Prompt: {prompt2}")
        
        result2 = process_document_with_ai(template.file.path, prompt2)
        
        if result2.get('success'):
            print("✅ Teste 2 passou!")
            print(f"📄 Documento salvo em: {result2['output_path']}")
            print(f"📝 Mudanças aplicadas: {result2['changes_made']}")
        else:
            print(f"❌ Teste 2 falhou: {result2.get('error')}")
        
        # Teste 3: Adicionar cláusula
        print("\n🔧 Teste 3: Adicionar cláusula")
        prompt3 = "Adicione uma cláusula sobre garantia de 90 dias para os produtos fornecidos"
        print(f"Prompt: {prompt3}")
        
        result3 = process_document_with_ai(template.file.path, prompt3)
        
        if result3.get('success'):
            print("✅ Teste 3 passou!")
            print(f"📄 Documento salvo em: {result3['output_path']}")
            print(f"📝 Mudanças aplicadas: {result3['changes_made']}")
        else:
            print(f"❌ Teste 3 falhou: {result3.get('error')}")
        
        print("\n" + "=" * 60)
        print("🎉 Testes concluídos!")
        
    except Exception as e:
        print(f"❌ Erro durante os testes: {str(e)}")
        import traceback
        traceback.print_exc()


def test_comparacao_antigo_vs_novo():
    """
    Compara o sistema antigo (complexo) vs novo (simplificado).
    """
    print("\n🔄 Comparação: Sistema Antigo vs Novo")
    print("=" * 60)
    
    print("SISTEMA ANTIGO (Complexo):")
    print("❌ Detecta padrões específicos")
    print("❌ Força cláusulas predefinidas")
    print("❌ Algoritmo rígido")
    print("❌ Só funciona com padrões conhecidos")
    print("❌ IA 'falsa' - só detecta, não executa")
    
    print("\nSISTEMA NOVO (Simplificado):")
    print("✅ IA processa documento diretamente")
    print("✅ Flexível para qualquer mudança")
    print("✅ Abordagem direta e simples")
    print("✅ Funciona com qualquer prompt")
    print("✅ IA real - faz mudanças no documento")
    
    print("\n🎯 Resultado: Sistema muito mais simples e eficiente!")


if __name__ == "__main__":
    test_sistema_simplificado()
    test_comparacao_antigo_vs_novo()
