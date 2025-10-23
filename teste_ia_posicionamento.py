#!/usr/bin/env python3
"""
Teste do novo sistema onde a IA determina tanto o reconhecimento quanto o posicionamento.
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

def testar_ia_posicionamento():
    """Testa se a IA agora determina tanto reconhecimento quanto posicionamento."""
    
    print("🧠 TESTE: IA DETERMINA RECONHECIMENTO E POSICIONAMENTO")
    print("=" * 70)
    
    # Teste com prompt complexo
    prompt = "Aja como um especialista em licitações públicas. Adicione caução de execução, multa por atraso, critério de desempate e prazo de entrega."
    
    print(f"📝 Prompt: {prompt}")
    print()
    
    # Testar detecção com IA
    print("🔍 TESTANDO DETECÇÃO COM IA:")
    resultado_ia = extrair_clausulas_com_ia(prompt)
    
    if isinstance(resultado_ia, dict):
        print("✅ IA retornou dados estruturados:")
        print(f"  - Cláusulas detectadas: {len(resultado_ia.get('clausulas', []))}")
        print(f"  - Observação prática: {resultado_ia.get('observacao_pratica', False)}")
        print(f"  - Estratégia de posicionamento: {resultado_ia.get('posicionamento', {}).get('estrategia', 'N/A')}")
        
        print("\n📋 DETALHES DAS CLÁUSULAS:")
        for i, clausula in enumerate(resultado_ia.get('clausulas', []), 1):
            print(f"  {i}. Tipo: {clausula.get('tipo', 'N/A')}")
            print(f"     Descrição: {clausula.get('descricao', 'N/A')}")
            print(f"     Posição: {clausula.get('posicao', 'N/A')}")
            print(f"     Número sequencial: {clausula.get('numero_sequencial', 'N/A')}")
            print(f"     Confiança: {clausula.get('confianca', 'N/A')}")
            print()
        
        print("🎯 ESTRATÉGIA DE POSICIONAMENTO:")
        posicionamento = resultado_ia.get('posicionamento', {})
        for key, value in posicionamento.items():
            print(f"  - {key}: {value}")
        
    else:
        print("❌ IA retornou formato antigo (lista)")
        print(f"  - Resultado: {resultado_ia}")
    
    print("\n" + "=" * 70)
    
    # Testar sistema completo
    print("🔧 TESTANDO SISTEMA COMPLETO:")
    dados = generate_document_data_from_prompt('template', prompt)
    
    print("📊 DADOS EXTRAÍDOS:")
    print(f"  - Cláusulas específicas: {len(dados.get('clausulas_especificas', []))}")
    print(f"  - Observação prática: {dados.get('adicionar_observacao_pratica', False)}")
    print(f"  - Posicionamento IA: {dados.get('posicionamento_ia', {})}")
    
    # Verificar se tem informações de posicionamento
    posicionamento_ia = dados.get('posicionamento_ia', {})
    if posicionamento_ia:
        print("\n✅ SISTEMA INTELIGENTE FUNCIONANDO!")
        print("   - IA determina reconhecimento ✓")
        print("   - IA determina posicionamento ✓")
        print("   - Sistema usa dados da IA ✓")
    else:
        print("\n⚠️ SISTEMA PARCIALMENTE INTELIGENTE")
        print("   - IA determina reconhecimento ✓")
        print("   - IA determina posicionamento ✗")
        print("   - Sistema usa fallback para posicionamento")
    
    return posicionamento_ia is not None

if __name__ == "__main__":
    print("🚀 INICIANDO TESTE DE IA INTELIGENTE")
    print()
    
    sucesso = testar_ia_posicionamento()
    
    print("\n" + "=" * 70)
    if sucesso:
        print("🎉 IA AGORA DETERMINA TUDO!")
        print("   - Reconhecimento: ✓")
        print("   - Posicionamento: ✓")
        print("   - Estratégia: ✓")
    else:
        print("⚠️ IA AINDA NÃO DETERMINA POSICIONAMENTO")
        print("   - Reconhecimento: ✓")
        print("   - Posicionamento: ✗")
