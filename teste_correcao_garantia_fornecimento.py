#!/usr/bin/env python3
"""
Teste para verificar se a correção da detecção de 'garantia de fornecimento' está funcionando.
"""

import os
import sys
import django
from pathlib import Path

# Configurar Django
sys.path.append('backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.mdlicitatech.settings')
django.setup()

from backend.app.services.ia import generate_document_data_from_prompt, gerar_clausula_especifica
from backend.app.services.render import render_docx_contextual_intelligent

def testar_deteccao_garantia_fornecimento():
    """Testa se 'garantia de fornecimento' é detectada corretamente."""
    
    print("🔍 TESTE DE DETECÇÃO: GARANTIA DE FORNECIMENTO")
    print("=" * 60)
    
    # Prompt que estava falhando
    prompt = "Aja como um especialista em licitações públicas. Inclua cláusulas sobre garantia de fornecimento e penalidade por atraso, e adicione uma observação prática sobre registro de propostas."
    
    print(f"📝 Prompt: {prompt}")
    print()
    
    # Extrair dados do prompt
    dados = generate_document_data_from_prompt('template', prompt)
    
    # Verificar cláusulas específicas
    clausulas_especificas = dados.get('clausulas_especificas', [])
    
    print("🎯 CLÁUSULAS DETECTADAS:")
    for i, clausula in enumerate(clausulas_especificas, 1):
        print(f"{i}. Tipo: {clausula.get('tipo', 'N/A')}")
        print(f"   Descrição: {clausula.get('descricao', 'N/A')}")
        print()
    
    # Verificar se ambas as cláusulas foram detectadas
    tipos_detectados = [c.get('tipo') for c in clausulas_especificas]
    
    print("✅ VERIFICAÇÕES:")
    print(f"- Penalidade por atraso detectada: {'penalidade_atraso' in tipos_detectados}")
    print(f"- Garantia de fornecimento detectada: {'fornecimento_garantia' in tipos_detectados}")
    print(f"- Observação prática detectada: {dados.get('adicionar_observacao_pratica', False)}")
    print()
    
    # Testar geração de cláusulas
    print("🔧 TESTANDO GERAÇÃO DE CLÁUSULAS:")
    for clausula in clausulas_especificas:
        tipo = clausula.get('tipo', '')
        descricao = clausula.get('descricao', '')
        
        clausula_gerada = gerar_clausula_especifica(tipo, descricao)
        
        print(f"📋 {tipo.upper()}:")
        print(f"   Texto: {clausula_gerada.get('texto', 'N/A')[:80]}...")
        print(f"   Base legal: {clausula_gerada.get('base_legal', 'N/A')}")
        print(f"   Observação: {clausula_gerada.get('observacao', 'N/A')}")
        print()
    
    # Resultado final
    sucesso = (
        'penalidade_atraso' in tipos_detectados and 
        'fornecimento_garantia' in tipos_detectados and
        dados.get('adicionar_observacao_pratica', False)
    )
    
    print("🎯 RESULTADO FINAL:")
    if sucesso:
        print("✅ SUCESSO: Todas as cláusulas foram detectadas e geradas corretamente!")
        print("   - Penalidade por atraso: ✓")
        print("   - Garantia de fornecimento: ✓") 
        print("   - Observação prática: ✓")
    else:
        print("❌ FALHA: Algumas cláusulas não foram detectadas corretamente.")
        print(f"   - Penalidade por atraso: {'✓' if 'penalidade_atraso' in tipos_detectados else '✗'}")
        print(f"   - Garantia de fornecimento: {'✓' if 'fornecimento_garantia' in tipos_detectados else '✗'}")
        print(f"   - Observação prática: {'✓' if dados.get('adicionar_observacao_pratica', False) else '✗'}")
    
    return sucesso

if __name__ == "__main__":
    print("🚀 INICIANDO TESTE DE CORREÇÃO")
    print()
    
    sucesso = testar_deteccao_garantia_fornecimento()
    
    print()
    print("=" * 60)
    if sucesso:
        print("🎉 TESTE CONCLUÍDO COM SUCESSO!")
        print("   O sistema agora detecta corretamente 'garantia de fornecimento'")
    else:
        print("⚠️  TESTE FALHOU!")
        print("   Verifique os padrões de detecção no código")
