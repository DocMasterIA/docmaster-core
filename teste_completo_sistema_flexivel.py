#!/usr/bin/env python3
"""
Teste completo do sistema flexível de IA para diferentes tipos de documentos e prompts.
"""

import os
import sys
import django
from pathlib import Path

# Configurar Django
sys.path.append('backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.mdlicitatech.settings')
django.setup()

from backend.app.services.ia import generate_document_data_from_prompt, extrair_clausulas_com_ia, analisar_documento_e_posicionar_clausulas_com_ia
from docx import Document

def testar_deteccao_clausulas():
    """Testa detecção de cláusulas com diferentes variações."""
    
    print("🔍 TESTE 1: DETECÇÃO DE CLÁUSULAS")
    print("=" * 50)
    
    testes_deteccao = [
        {
            "nome": "Variações de caução",
            "prompt": "Aja como um especialista. Adicione caução, caução de execução, caução contratual e calção."
        },
        {
            "nome": "Sinônimos de penalidade",
            "prompt": "Aja como um especialista. Inclua multa por atraso, penalidade por atraso e penalidade."
        },
        {
            "nome": "Garantias variadas",
            "prompt": "Aja como um especialista. Adicione garantia de fornecimento, garantia de qualidade e garantia de execução."
        },
        {
            "nome": "Linguagem informal",
            "prompt": "Aja como um especialista. Preciso de critério de desempate, prazo de entrega e documentação adicional."
        },
        {
            "nome": "Múltiplas cláusulas",
            "prompt": "Aja como um especialista. Inclua: caução de execução, multa por atraso, critério de desempate, prazo de entrega, documentação complementar e reajuste de preços."
        }
    ]
    
    resultados = []
    
    for i, teste in enumerate(testes_deteccao, 1):
        print(f"\n📝 Teste {i}: {teste['nome']}")
        print(f"Prompt: {teste['prompt']}")
        
        try:
            clausulas = extrair_clausulas_com_ia(teste['prompt'])
            
            print(f"✅ Cláusulas detectadas: {len(clausulas)}")
            for j, clausula in enumerate(clausulas, 1):
                print(f"  {j}. {clausula['tipo']}: {clausula['descricao']} (confiança: {clausula['confianca']})")
            
            sucesso = len(clausulas) > 0
            resultados.append({
                'teste': teste['nome'],
                'sucesso': sucesso,
                'clausulas': len(clausulas),
                'tipos': [c['tipo'] for c in clausulas]
            })
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            resultados.append({
                'teste': teste['nome'],
                'sucesso': False,
                'clausulas': 0,
                'tipos': []
            })
    
    return resultados

def testar_analise_documento():
    """Testa análise de documento com diferentes estruturas."""
    
    print("\n\n📄 TESTE 2: ANÁLISE DE DOCUMENTO")
    print("=" * 50)
    
    # Criar documentos com estruturas diferentes
    documentos_teste = [
        {
            "nome": "Edital Padrão",
            "estrutura": [
                "1. OBJETO",
                "1.1. Aquisição de medicamentos...",
                "2. MODALIDADE", 
                "2.1. Pregão Eletrônico...",
                "3. CONDIÇÕES DE PARTICIPAÇÃO",
                "3.1. Habilitação jurídica...",
                "3.4.1. Garantia de execução...",
                "3.4.2. Penalidade por atraso...",
                "4. JULGAMENTO",
                "4.1. Critérios de julgamento..."
            ]
        },
        {
            "nome": "Edital com Seção 5",
            "estrutura": [
                "1. OBJETO",
                "2. MODALIDADE",
                "3. CONDIÇÕES",
                "4. JULGAMENTO",
                "5. CONTRATAÇÃO",
                "5.1. Garantias contratuais...",
                "5.2. Prazos de execução...",
                "6. PENALIDADES",
                "6.1. Multa por atraso..."
            ]
        },
        {
            "nome": "Edital Simples",
            "estrutura": [
                "1. OBJETO",
                "2. MODALIDADE",
                "3. CONDIÇÕES",
                "4. JULGAMENTO"
            ]
        }
    ]
    
    clausulas_teste = [
        {'tipo': 'garantia_execucao', 'descricao': 'caução de execução'},
        {'tipo': 'penalidade_atraso', 'descricao': 'multa por atraso'},
        {'tipo': 'criterio_desempate', 'descricao': 'critério de desempate'}
    ]
    
    resultados = []
    
    for i, doc_teste in enumerate(documentos_teste, 1):
        print(f"\n📄 Teste {i}: {doc_teste['nome']}")
        
        # Criar documento
        doc = Document()
        for paragrafo in doc_teste['estrutura']:
            doc.add_paragraph(paragrafo)
        
        try:
            posicionamento = analisar_documento_e_posicionar_clausulas_com_ia(
                doc, clausulas_teste, "Adicione caução, multa e desempate"
            )
            
            print(f"✅ Análise concluída!")
            print(f"  Estratégia: {posicionamento.get('estrategia', 'N/A')}")
            print(f"  Seção alvo: {posicionamento.get('secao_alvo', 'N/A')}")
            
            if 'clausulas_posicionadas' in posicionamento:
                print(f"  Cláusulas posicionadas: {len(posicionamento['clausulas_posicionadas'])}")
                for clausula in posicionamento['clausulas_posicionadas']:
                    print(f"    - {clausula.get('tipo', 'N/A')}: {clausula.get('posicao', 'N/A')}")
            
            sucesso = True
            resultados.append({
                'documento': doc_teste['nome'],
                'sucesso': sucesso,
                'estrategia': posicionamento.get('estrategia', 'N/A')
            })
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            resultados.append({
                'documento': doc_teste['nome'],
                'sucesso': False,
                'estrategia': 'N/A'
            })
    
    return resultados

def testar_sistema_completo():
    """Testa o sistema completo com diferentes prompts."""
    
    print("\n\n🔧 TESTE 3: SISTEMA COMPLETO")
    print("=" * 50)
    
    prompts_teste = [
        "Aja como um especialista em licitações públicas. Adicione caução de execução e multa por atraso.",
        "Aja como um especialista. Inclua garantia de fornecimento, critério de desempate e prazo de entrega.",
        "Aja como um especialista. Preciso de documentação complementar, reajuste de preços e garantia de qualidade.",
        "Aja como um especialista. Adicione todas as cláusulas necessárias para um edital completo.",
        "Aja como um especialista. Inclua caução, multa, desempate, prazo, documentação e reajuste."
    ]
    
    resultados = []
    
    for i, prompt in enumerate(prompts_teste, 1):
        print(f"\n🔧 Teste {i}: {prompt[:50]}...")
        
        try:
            dados = generate_document_data_from_prompt('template', prompt)
            
            clausulas = dados.get('clausulas_especificas', [])
            observacao = dados.get('adicionar_observacao_pratica', False)
            
            print(f"✅ Sistema processou com sucesso!")
            print(f"  Cláusulas: {len(clausulas)}")
            print(f"  Observação: {observacao}")
            print(f"  Tipos: {[c['tipo'] for c in clausulas]}")
            
            sucesso = len(clausulas) > 0
            resultados.append({
                'prompt': prompt[:30] + "...",
                'sucesso': sucesso,
                'clausulas': len(clausulas),
                'observacao': observacao
            })
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            resultados.append({
                'prompt': prompt[:30] + "...",
                'sucesso': False,
                'clausulas': 0,
                'observacao': False
            })
    
    return resultados

def testar_robustez():
    """Testa robustez com prompts problemáticos."""
    
    print("\n\n🛡️ TESTE 4: ROBUSTEZ")
    print("=" * 50)
    
    prompts_problematicos = [
        "Adicione caução",  # Muito simples
        "Aja como um especialista. Inclua cláusulas sobre garantia de execução, penalidade por atraso, critério de desempate, prazo de entrega, documentação complementar, reajuste de preços, garantia de qualidade, prazo de execução, garantia de fornecimento e critério de julgamento.",  # Muito longo
        "Aja como um especialista. Adicione cláusula de caução de execução contratual e multa por atraso na entrega.",  # Linguagem complexa
        "Aja como um especialista. Preciso de caução, multa, desempate, prazo, documentação, reajuste, qualidade, execução, fornecimento e julgamento.",  # Muitas cláusulas
        "Aja como um especialista. Inclua cláusulas sobre garantia de execução, penalidade por atraso, critério de desempate, prazo de entrega, documentação complementar, reajuste de preços, garantia de qualidade, prazo de execução, garantia de fornecimento, critério de julgamento, garantia de execução, penalidade por atraso, critério de desempate, prazo de entrega, documentação complementar, reajuste de preços, garantia de qualidade, prazo de execução, garantia de fornecimento e critério de julgamento."  # Repetitivo
    ]
    
    resultados = []
    
    for i, prompt in enumerate(prompts_problematicos, 1):
        print(f"\n🛡️ Teste {i}: {prompt[:50]}...")
        
        try:
            clausulas = extrair_clausulas_com_ia(prompt)
            
            print(f"✅ Processado com sucesso!")
            print(f"  Cláusulas detectadas: {len(clausulas)}")
            print(f"  Tipos únicos: {len(set(c['tipo'] for c in clausulas))}")
            
            sucesso = len(clausulas) > 0
            resultados.append({
                'teste': f"Robustez {i}",
                'sucesso': sucesso,
                'clausulas': len(clausulas),
                'tipos_unicos': len(set(c['tipo'] for c in clausulas))
            })
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            resultados.append({
                'teste': f"Robustez {i}",
                'sucesso': False,
                'clausulas': 0,
                'tipos_unicos': 0
            })
    
    return resultados

def main():
    """Executa todos os testes."""
    
    print("🚀 INICIANDO TESTES COMPLETOS DO SISTEMA FLEXÍVEL")
    print("=" * 70)
    
    # Executar todos os testes
    resultados_deteccao = testar_deteccao_clausulas()
    resultados_documento = testar_analise_documento()
    resultados_completo = testar_sistema_completo()
    resultados_robustez = testar_robustez()
    
    # Resumo final
    print("\n\n📊 RESUMO FINAL DOS TESTES")
    print("=" * 70)
    
    # Estatísticas de detecção
    sucessos_deteccao = sum(1 for r in resultados_deteccao if r['sucesso'])
    total_deteccao = len(resultados_deteccao)
    print(f"🔍 DETECÇÃO DE CLÁUSULAS: {sucessos_deteccao}/{total_deteccao} ({(sucessos_deteccao/total_deteccao)*100:.1f}%)")
    
    # Estatísticas de documento
    sucessos_documento = sum(1 for r in resultados_documento if r['sucesso'])
    total_documento = len(resultados_documento)
    print(f"📄 ANÁLISE DE DOCUMENTO: {sucessos_documento}/{total_documento} ({(sucessos_documento/total_documento)*100:.1f}%)")
    
    # Estatísticas de sistema completo
    sucessos_completo = sum(1 for r in resultados_completo if r['sucesso'])
    total_completo = len(resultados_completo)
    print(f"🔧 SISTEMA COMPLETO: {sucessos_completo}/{total_completo} ({(sucessos_completo/total_completo)*100:.1f}%)")
    
    # Estatísticas de robustez
    sucessos_robustez = sum(1 for r in resultados_robustez if r['sucesso'])
    total_robustez = len(resultados_robustez)
    print(f"🛡️ ROBUSTEZ: {sucessos_robustez}/{total_robustez} ({(sucessos_robustez/total_robustez)*100:.1f}%)")
    
    # Estatística geral
    total_sucessos = sucessos_deteccao + sucessos_documento + sucessos_completo + sucessos_robustez
    total_testes = total_deteccao + total_documento + total_completo + total_robustez
    print(f"\n🎯 TAXA GERAL DE SUCESSO: {total_sucessos}/{total_testes} ({(total_sucessos/total_testes)*100:.1f}%)")
    
    if total_sucessos == total_testes:
        print("\n🎉 TODOS OS TESTES PASSARAM! Sistema flexível funcionando perfeitamente!")
    elif total_sucessos >= total_testes * 0.9:
        print("\n✅ Sistema funcionando muito bem, com pequenos ajustes necessários.")
    elif total_sucessos >= total_testes * 0.7:
        print("\n⚠️ Sistema funcionando bem, mas precisa de melhorias.")
    else:
        print("\n❌ Sistema precisa de melhorias significativas.")
    
    return total_sucessos == total_testes

if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1)
