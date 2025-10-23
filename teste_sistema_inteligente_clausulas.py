#!/usr/bin/env python3
"""
Teste do novo sistema inteligente de detecção de cláusulas usando IA.
"""

import os
import sys
import django
from pathlib import Path

# Configurar Django
sys.path.append('backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.mdlicitatech.settings')
django.setup()

from backend.app.services.ia import generate_document_data_from_prompt, extrair_clausulas_com_ia

def testar_sistema_inteligente():
    """Testa o novo sistema inteligente de detecção de cláusulas."""
    
    print("🧠 TESTE DO SISTEMA INTELIGENTE DE CLÁUSULAS")
    print("=" * 60)
    
    # Testes com diferentes variações de prompts
    testes = [
        {
            "nome": "Variação 1 - Ordem diferente",
            "prompt": "Aja como um especialista em licitações públicas. Inclua cláusulas sobre garantia de fornecimento e penalidade por atraso, e adicione uma observação prática sobre registro de propostas."
        },
        {
            "nome": "Variação 2 - Sinônimos",
            "prompt": "Aja como um especialista em licitações públicas. Adicione caução de execução, multa por atraso e critério de desempate."
        },
        {
            "nome": "Variação 3 - Linguagem informal",
            "prompt": "Aja como um especialista em licitações públicas. Preciso de cláusulas de garantia de qualidade, prazo de entrega e documentação adicional."
        },
        {
            "nome": "Variação 4 - Múltiplas cláusulas",
            "prompt": "Aja como um especialista em licitações públicas. Inclua cláusulas sobre: garantia de execução, penalidade por atraso, critério de desempate, prazo de entrega, documentação complementar e reajuste de preços."
        },
        {
            "nome": "Variação 5 - Linguagem técnica",
            "prompt": "Aja como um especialista em licitações públicas. Elabore cláusulas contratuais para garantia de fornecimento, penalidade por atraso, critério de desempate e prazo de execução."
        }
    ]
    
    resultados = []
    
    for i, teste in enumerate(testes, 1):
        print(f"\n🔍 TESTE {i}: {teste['nome']}")
        print(f"📝 Prompt: {teste['prompt']}")
        print()
        
        try:
            # Testar detecção direta com IA
            clausulas_detectadas = extrair_clausulas_com_ia(teste['prompt'])
            
            print("🎯 CLÁUSULAS DETECTADAS PELA IA:")
            for j, clausula in enumerate(clausulas_detectadas, 1):
                print(f"  {j}. Tipo: {clausula.get('tipo', 'N/A')}")
                print(f"     Descrição: {clausula.get('descricao', 'N/A')}")
                print(f"     Confiança: {clausula.get('confianca', 'N/A')}")
                print()
            
            # Testar sistema completo
            dados = generate_document_data_from_prompt('template', teste['prompt'])
            clausulas_sistema = dados.get('clausulas_especificas', [])
            
            print("📊 RESULTADO DO SISTEMA COMPLETO:")
            print(f"  - Cláusulas detectadas: {len(clausulas_sistema)}")
            print(f"  - Observação prática: {dados.get('adicionar_observacao_pratica', False)}")
            
            # Verificar se as cláusulas foram detectadas corretamente
            tipos_detectados = [c.get('tipo') for c in clausulas_sistema]
            print(f"  - Tipos detectados: {tipos_detectados}")
            
            sucesso = len(clausulas_sistema) > 0
            resultados.append({
                'teste': teste['nome'],
                'sucesso': sucesso,
                'clausulas': len(clausulas_sistema),
                'tipos': tipos_detectados
            })
            
            if sucesso:
                print("  ✅ SUCESSO")
            else:
                print("  ❌ FALHA")
                
        except Exception as e:
            print(f"  ❌ ERRO: {e}")
            resultados.append({
                'teste': teste['nome'],
                'sucesso': False,
                'clausulas': 0,
                'tipos': [],
                'erro': str(e)
            })
    
    # Resumo final
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS RESULTADOS:")
    print("=" * 60)
    
    sucessos = sum(1 for r in resultados if r['sucesso'])
    total = len(resultados)
    
    for resultado in resultados:
        status = "✅" if resultado['sucesso'] else "❌"
        print(f"{status} {resultado['teste']}: {resultado['clausulas']} cláusulas")
        if resultado['tipos']:
            print(f"    Tipos: {', '.join(resultado['tipos'])}")
        if 'erro' in resultado:
            print(f"    Erro: {resultado['erro']}")
        print()
    
    print(f"🎯 TAXA DE SUCESSO: {sucessos}/{total} ({(sucessos/total)*100:.1f}%)")
    
    if sucessos == total:
        print("🎉 TODOS OS TESTES PASSARAM! Sistema inteligente funcionando perfeitamente!")
    elif sucessos > total * 0.8:
        print("✅ Sistema funcionando bem, com pequenos ajustes necessários.")
    else:
        print("⚠️ Sistema precisa de melhorias significativas.")
    
    return sucessos == total

if __name__ == "__main__":
    print("🚀 INICIANDO TESTE DO SISTEMA INTELIGENTE")
    print()
    
    sucesso = testar_sistema_inteligente()
    
    print("\n" + "=" * 60)
    if sucesso:
        print("🎉 SISTEMA INTELIGENTE FUNCIONANDO PERFEITAMENTE!")
    else:
        print("⚠️ SISTEMA PRECISA DE AJUSTES")
