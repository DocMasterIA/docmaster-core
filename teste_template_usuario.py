#!/usr/bin/env python3
"""
Teste do sistema refatorado com o template cadastrado do usuário.
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


def testar_template_usuario():
    """
    Testa o sistema com o template cadastrado do usuário.
    """
    print("🧪 Testando sistema refatorado com template do usuário")
    print("=" * 60)
    
    # Buscar o template cadastrado
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado no banco de dados")
        return
    
    print(f"📄 Template encontrado:")
    print(f"   ID: {template.id}")
    print(f"   Nome: {template.name}")
    print(f"   Arquivo: {template.file.path}")
    print(f"   Criado em: {template.created_at}")
    print()
    
    # Testes com prompts realistas
    testes = [
        {
            "nome": "Alteração de Valor",
            "prompt": "Altere o valor estimado de R$ 150.000,00 para R$ 250.000,00 em todo o documento"
        },
        {
            "nome": "Alteração de Data",
            "prompt": "Mude a data de abertura de 15/03/2025 para 22/04/2025"
        },
        {
            "nome": "Alteração de Local",
            "prompt": "Altere todas as referências de ITAJÁ para BRASÍLIA no documento"
        },
        {
            "nome": "Adição de Cláusula",
            "prompt": "Adicione uma cláusula sobre garantia de execução no valor de 5% do contrato"
        },
        {
            "nome": "Alteração de Número do Edital",
            "prompt": "Altere o número do edital de 005/2025 para 456/2024"
        }
    ]
    
    resultados = []
    
    for i, teste in enumerate(testes, 1):
        print(f"🔧 Teste {i}: {teste['nome']}")
        print(f"Prompt: {teste['prompt']}")
        
        try:
            # Processar documento com IA
            result = process_document_with_ai(template.file.path, teste['prompt'])
            
            if result.get('success'):
                print("✅ Teste passou!")
                print(f"📄 Documento salvo em: {result['output_path']}")
                print(f"📝 Mudanças aplicadas: {result['changes_made']}")
                
                resultados.append({
                    "teste": teste['nome'],
                    "status": "✅ PASSOU",
                    "mudanças": result['changes_made']
                })
            else:
                print(f"❌ Teste falhou: {result.get('error')}")
                resultados.append({
                    "teste": teste['nome'],
                    "status": "❌ FALHOU",
                    "erro": result.get('error')
                })
                
        except Exception as e:
            print(f"❌ Erro no teste: {str(e)}")
            resultados.append({
                "teste": teste['nome'],
                "status": "❌ ERRO",
                "erro": str(e)
            })
        
        print("-" * 50)
        print()
    
    # Resumo dos resultados
    print("📊 RESUMO DOS TESTES")
    print("=" * 60)
    
    passou = 0
    falhou = 0
    
    for resultado in resultados:
        status = resultado['status']
        if "✅" in status:
            passou += 1
        else:
            falhou += 1
        
        print(f"{status} {resultado['teste']}")
        if 'mudanças' in resultado:
            for mudança in resultado['mudanças']:
                print(f"    📝 {mudança}")
        elif 'erro' in resultado:
            print(f"    ❌ {resultado['erro']}")
        print()
    
    print(f"🎯 RESULTADO FINAL:")
    print(f"   ✅ Testes que passaram: {passou}")
    print(f"   ❌ Testes que falharam: {falhou}")
    print(f"   📊 Taxa de sucesso: {(passou / len(testes) * 100):.1f}%")
    
    if passou == len(testes):
        print("\n🎉 TODOS OS TESTES PASSARAM! Sistema funcionando perfeitamente!")
    elif passou > 0:
        print(f"\n⚠️ Sistema funcionando parcialmente ({passou}/{len(testes)} testes passaram)")
    else:
        print("\n❌ Sistema com problemas - nenhum teste passou")


if __name__ == "__main__":
    testar_template_usuario()
