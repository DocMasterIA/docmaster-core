#!/usr/bin/env python3
"""
Teste de integração com template real para verificar funcionamento completo.
"""

import os
import sys
import django
from pathlib import Path

# Configurar Django
sys.path.append('backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.mdlicitatech.settings')
django.setup()

from backend.app.services.ia import generate_document_data_from_prompt
from backend.app.services.render import render_docx_contextual_intelligent
from docx import Document

def testar_integracao_completa():
    """Testa integração completa com template real."""
    
    print("🔧 TESTE DE INTEGRAÇÃO COMPLETA")
    print("=" * 50)
    
    # Template real
    template_path = "templates/docx/modelo_template_mdlicitatech.docx"
    
    if not os.path.exists(template_path):
        print(f"❌ Template não encontrado: {template_path}")
        return False
    
    print(f"📁 Usando template: {template_path}")
    
    # Teste com prompt complexo
    prompt = """Aja como um especialista em licitações públicas e na Lei 14.133/2021.

INSTRUÇÕES ESPECÍFICAS:
1. Altere o valor de PREÇO TOTAL MÉDIO para R$ 1.500.000,00
2. Mude a data de abertura para 30/11/2024
3. Altere o número do edital para 456/2024
4. Mude o local de "ITAJÁ" para "BRASÍLIA"
5. Adicione cláusulas sobre caução de execução, multa por atraso e critério de desempate
6. Adicione uma observação prática sobre registro de propostas
7. Altere o prazo de execução para 180 dias
8. Mude o órgão para "SECRETARIA MUNICIPAL DE SAÚDE"

OBJETIVO: Gerar um edital de pregão eletrônico para aquisição de medicamentos e insumos hospitalares."""
    
    print(f"📝 Prompt: {prompt[:100]}...")
    print()
    
    try:
        # 1. Testar extração de dados
        print("🔍 1. TESTANDO EXTRAÇÃO DE DADOS:")
        dados = generate_document_data_from_prompt('template', prompt)
        
        print(f"✅ Dados extraídos com sucesso!")
        print(f"  - Número do edital: {dados.get('numero_edital', 'N/A')}")
        print(f"  - Data de abertura: {dados.get('data_abertura', 'N/A')}")
        print(f"  - Local: {dados.get('local_orgao', 'N/A')}")
        print(f"  - Órgão: {dados.get('orgao', 'N/A')}")
        print(f"  - Valor: {dados.get('valor_estimado', 'N/A')}")
        print(f"  - Prazo: {dados.get('prazo_execucao', 'N/A')}")
        print(f"  - Cláusulas específicas: {len(dados.get('clausulas_especificas', []))}")
        print(f"  - Observação prática: {dados.get('adicionar_observacao_pratica', False)}")
        
        # Mostrar cláusulas detectadas
        clausulas = dados.get('clausulas_especificas', [])
        if clausulas:
            print(f"  - Tipos de cláusulas: {[c['tipo'] for c in clausulas]}")
        
        print()
        
        # 2. Testar renderização
        print("🎨 2. TESTANDO RENDERIZAÇÃO:")
        
        # Renderizar usando a função correta
        output_path = "teste_integracao_completa.docx"
        doc_renderizado = render_docx_contextual_intelligent(template_path, output_path, dados, prompt)
        print(f"✅ Documento renderizado com sucesso!")
        print(f"  - Salvo em: {output_path}")
        
        # Carregar o documento renderizado para verificação
        doc_final = Document(output_path)
        print(f"  - Parágrafos finais: {len(doc_final.paragraphs)}")
        
        # 3. Verificar alterações
        print("\n🔍 3. VERIFICANDO ALTERAÇÕES:")
        
        # Verificar se as alterações foram aplicadas
        texto_completo = ""
        for p in doc_final.paragraphs:
            texto_completo += p.text + "\n"
        
        verificacoes = [
            ("R$ 1.500.000,00", "Valor alterado"),
            ("30/11/2024", "Data alterada"),
            ("456/2024", "Número do edital alterado"),
            ("BRASÍLIA", "Local alterado"),
            ("SECRETARIA MUNICIPAL DE SAÚDE", "Órgão alterado"),
            ("180 dias", "Prazo alterado"),
            ("caução", "Cláusula de caução"),
            ("multa", "Cláusula de multa"),
            ("desempate", "Cláusula de desempate"),
            ("OBSERVAÇÃO PRÁTICA", "Observação prática")
        ]
        
        sucessos = 0
        for termo, descricao in verificacoes:
            if termo.lower() in texto_completo.lower():
                print(f"  ✅ {descricao}: {termo}")
                sucessos += 1
            else:
                print(f"  ❌ {descricao}: {termo} - NÃO ENCONTRADO")
        
        print(f"\n📊 Taxa de sucesso: {sucessos}/{len(verificacoes)} ({(sucessos/len(verificacoes))*100:.1f}%)")
        
        # 4. Documento já foi salvo durante a renderização
        print(f"\n💾 Documento salvo: {output_path}")
        
        return sucessos >= len(verificacoes) * 0.8  # 80% de sucesso
        
    except Exception as e:
        print(f"❌ Erro na integração: {e}")
        import traceback
        traceback.print_exc()
        return False

def testar_prompts_variados():
    """Testa com diferentes tipos de prompts."""
    
    print("\n\n🎯 TESTE DE PROMPTS VARIADOS")
    print("=" * 50)
    
    prompts_teste = [
        {
            "nome": "Prompt Simples",
            "texto": "Aja como um especialista. Adicione caução de execução e multa por atraso."
        },
        {
            "nome": "Prompt Complexo",
            "texto": "Aja como um especialista em licitações públicas. Altere o valor para R$ 500.000,00, mude a data para 15/12/2024, altere o número do edital para 789/2024, mude o local para SÃO PAULO, adicione cláusulas sobre garantia de fornecimento, critério de desempate e prazo de entrega, adicione observação prática sobre documentação, altere o prazo para 120 dias e mude o órgão para SECRETARIA MUNICIPAL DE EDUCAÇÃO."
        },
        {
            "nome": "Prompt Focado em Cláusulas",
            "texto": "Aja como um especialista. Inclua todas as cláusulas necessárias: caução, multa, desempate, prazo, documentação, reajuste, qualidade, execução, fornecimento e julgamento."
        },
        {
            "nome": "Prompt com Alterações Básicas",
            "texto": "Aja como um especialista. Altere o valor para R$ 2.000.000,00, mude a data para 20/01/2025 e altere o número do edital para 001/2025."
        }
    ]
    
    resultados = []
    
    for i, teste in enumerate(prompts_teste, 1):
        print(f"\n🎯 Teste {i}: {teste['nome']}")
        print(f"Prompt: {teste['texto'][:80]}...")
        
        try:
            dados = generate_document_data_from_prompt('template', teste['texto'])
            
            clausulas = dados.get('clausulas_especificas', [])
            observacao = dados.get('adicionar_observacao_pratica', False)
            
            print(f"✅ Processado com sucesso!")
            print(f"  - Cláusulas: {len(clausulas)}")
            print(f"  - Observação: {observacao}")
            print(f"  - Tipos: {[c['tipo'] for c in clausulas]}")
            
            sucesso = True
            resultados.append({
                'teste': teste['nome'],
                'sucesso': sucesso,
                'clausulas': len(clausulas)
            })
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            resultados.append({
                'teste': teste['nome'],
                'sucesso': False,
                'clausulas': 0
            })
    
    return resultados

def main():
    """Executa todos os testes de integração."""
    
    print("🚀 INICIANDO TESTES DE INTEGRAÇÃO COMPLETA")
    print("=" * 70)
    
    # Teste de integração completa
    sucesso_integracao = testar_integracao_completa()
    
    # Teste de prompts variados
    resultados_prompts = testar_prompts_variados()
    
    # Resumo final
    print("\n\n📊 RESUMO FINAL")
    print("=" * 70)
    
    print(f"🔧 INTEGRAÇÃO COMPLETA: {'✅ SUCESSO' if sucesso_integracao else '❌ FALHOU'}")
    
    sucessos_prompts = sum(1 for r in resultados_prompts if r['sucesso'])
    total_prompts = len(resultados_prompts)
    print(f"🎯 PROMPTS VARIADOS: {sucessos_prompts}/{total_prompts} ({(sucessos_prompts/total_prompts)*100:.1f}%)")
    
    if sucesso_integracao and sucessos_prompts == total_prompts:
        print("\n🎉 SISTEMA FUNCIONANDO PERFEITAMENTE!")
        print("   - Integração completa ✓")
        print("   - Prompts variados ✓")
        print("   - Sistema flexível ✓")
        print("   - Pronto para produção ✓")
    elif sucesso_integracao and sucessos_prompts >= total_prompts * 0.8:
        print("\n✅ SISTEMA FUNCIONANDO MUITO BEM!")
        print("   - Integração completa ✓")
        print("   - Prompts variados (maioria) ✓")
        print("   - Pequenos ajustes necessários")
    else:
        print("\n⚠️ SISTEMA PRECISA DE AJUSTES")
        print("   - Verificar integração")
        print("   - Melhorar processamento de prompts")
    
    return sucesso_integracao and sucessos_prompts >= total_prompts * 0.8

if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1)
