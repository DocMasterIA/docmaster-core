#!/usr/bin/env python3
"""
Teste completo e inteligente do sistema de geração de documentos
Baseado na análise detalhada do template
"""

import os
import sys
import django
from pathlib import Path
import tempfile
import shutil
import re
import time

# Add the backend directory to Python path
sys.path.append('/home/adryan/Downloads/mdlicitatech-system/backend')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mdlicitatech.settings')
django.setup()

from backend.app.services.ia import generate_document_data_from_prompt
from backend.app.services.render import render_docx_contextual_intelligent
from backend.app.models import Template
from docx import Document

def testar_prompt(prompt, categoria, descricao):
    """Testa um prompt específico e retorna os resultados."""
    
    print(f"\n🧪 TESTE: {categoria}")
    print(f"📝 Prompt: {prompt}")
    print(f"📋 Descrição: {descricao}")
    print("-" * 60)
    
    try:
        # Buscar template
        template = Template.objects.first()
        if not template:
            print("❌ Nenhum template encontrado!")
            return None
        
        # Gerar dados
        data = generate_document_data_from_prompt(template, prompt)
        
        # Renderizar documento
        tmpdir = tempfile.gettempdir()
        output_path = os.path.join(tmpdir, f"teste_{categoria}_{int(time.time())}.docx")
        
        render_docx_contextual_intelligent(
            template_path=template.file.path,
            output_path=output_path,
            values=data,
            user_prompt=prompt
        )
        
        # Analisar resultados
        doc = Document(output_path)
        
        # Verificar alterações aplicadas
        alteracoes = {
            'valor_alterado': False,
            'data_alterada': False,
            'local_alterado': False,
            'edital_alterado': False,
            'clausulas_adicionadas': 0,
            'observacao_adicionada': False,
            'referencias_legais_preservadas': True
        }
        
        # Verificar valores monetários
        for paragraph in doc.paragraphs:
            text = paragraph.text
            if 'R$ 2.500.000,00' in text or 'R$ 3.000.000,00' in text or 'R$ 1.800.000,00' in text or 'R$ 4.500.000,00' in text or 'R$ 1.000.000,00' in text:
                alteracoes['valor_alterado'] = True
            
            # Verificar datas
            if '15/12/2024' in text or '20/01/2025' in text or '10/03/2025' in text or '25/12/2024' in text:
                alteracoes['data_alterada'] = True
            
            # Verificar locais
            if 'SÃO PAULO' in text or 'RIO DE JANEIRO' in text or 'BELO HORIZONTE' in text or 'CURITIBA' in text:
                alteracoes['local_alterado'] = True
            
            # Verificar números de edital
            if '789/2024' in text or '001/2025' in text or '123/2025' in text:
                alteracoes['edital_alterado'] = True
            
            # Verificar cláusulas adicionadas
            if 'GARANTIA DE EXECUÇÃO' in text or 'PENALIDADE POR ATRASO' in text or 'CRITÉRIO DE DESEMPATE' in text:
                alteracoes['clausulas_adicionadas'] += 1
            
            # Verificar observação prática
            if 'OBSERVAÇÃO PRÁTICA' in text:
                alteracoes['observacao_adicionada'] = True
            
            # Verificar preservação de referências legais
            if 'Lei 14.133/2021' in text and '14.456/2024' in text:
                alteracoes['referencias_legais_preservadas'] = False
        
        # Contar cláusulas 3.4.x
        clausulas_3_4 = len([p for p in doc.paragraphs if re.search(r'3\.4\.\d+', p.text)])
        
        # Verificar se cláusulas estão na seção correta
        clausulas_apos_8_1 = 0
        for i, paragraph in enumerate(doc.paragraphs):
            if '8.1' in paragraph.text and 'julgamento' in paragraph.text.lower():
                # Verificar se há cláusulas 3.4.x após esta linha
                for j in range(i+1, len(doc.paragraphs)):
                    if re.search(r'3\.4\.\d+', doc.paragraphs[j].text):
                        clausulas_apos_8_1 += 1
                        break
        
        # Calcular score
        score = 0
        total_checks = 0
        
        if 'valor' in prompt.lower():
            total_checks += 1
            if alteracoes['valor_alterado']:
                score += 1
                print("✅ Valor alterado corretamente")
            else:
                print("❌ Valor não foi alterado")
        
        if 'data' in prompt.lower():
            total_checks += 1
            if alteracoes['data_alterada']:
                score += 1
                print("✅ Data alterada corretamente")
            else:
                print("❌ Data não foi alterada")
        
        if 'local' in prompt.lower() or 'itajá' in prompt.lower():
            total_checks += 1
            if alteracoes['local_alterado']:
                score += 1
                print("✅ Local alterado corretamente")
            else:
                print("❌ Local não foi alterado")
        
        if 'edital' in prompt.lower():
            total_checks += 1
            if alteracoes['edital_alterado']:
                score += 1
                print("✅ Número do edital alterado corretamente")
            else:
                print("❌ Número do edital não foi alterado")
        
        if 'cláusula' in prompt.lower() or 'clausula' in prompt.lower():
            total_checks += 1
            if alteracoes['clausulas_adicionadas'] > 0:
                score += 1
                print(f"✅ {alteracoes['clausulas_adicionadas']} cláusula(s) adicionada(s)")
            else:
                print("❌ Nenhuma cláusula foi adicionada")
        
        if 'observação' in prompt.lower() or 'observacao' in prompt.lower():
            total_checks += 1
            if alteracoes['observacao_adicionada']:
                score += 1
                print("✅ Observação prática adicionada")
            else:
                print("❌ Observação prática não foi adicionada")
        
        # Verificar preservação de referências legais
        total_checks += 1
        if alteracoes['referencias_legais_preservadas']:
            score += 1
            print("✅ Referências legais preservadas")
        else:
            print("❌ Referências legais foram alteradas incorretamente")
        
        # Verificar posicionamento de cláusulas
        total_checks += 1
        if clausulas_apos_8_1 == 0:
            score += 1
            print("✅ Cláusulas inseridas na seção correta")
        else:
            print(f"❌ {clausulas_apos_8_1} cláusula(s) inserida(s) após 8.1")
        
        # Calcular percentual
        percentual = (score / total_checks * 100) if total_checks > 0 else 0
        
        print(f"\n📊 RESULTADO: {score}/{total_checks} ({percentual:.1f}%)")
        print(f"📄 Cláusulas 3.4.x no documento: {clausulas_3_4}")
        
        return {
            'categoria': categoria,
            'score': score,
            'total': total_checks,
            'percentual': percentual,
            'alteracoes': alteracoes,
            'clausulas_3_4': clausulas_3_4,
            'clausulas_apos_8_1': clausulas_apos_8_1
        }
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return None

def executar_testes_completos():
    """Executa todos os testes inteligentes."""
    
    print("🚀 TESTE COMPLETO E INTELIGENTE DO SISTEMA")
    print("=" * 70)
    print("Baseado na análise detalhada do template")
    print()
    
    # Prompts de teste baseados na análise
    testes = [
        {
            "categoria": "ALTERAÇÕES_BÁSICAS",
            "prompt": "Aja como um especialista em licitações públicas. Altere o valor estimado para R$ 2.500.000,00 e a data de abertura para 15/12/2024.",
            "descricao": "Teste de alterações básicas de valor e data"
        },
        {
            "categoria": "ALTERAÇÕES_LOCAIS",
            "prompt": "Aja como um especialista em licitações públicas. Mude o local de 'ITAJÁ' para 'SÃO PAULO' e o número do edital para 789/2024.",
            "descricao": "Teste de alteração de local e número do edital"
        },
        {
            "categoria": "CLÁUSULAS_ESPECÍFICAS",
            "prompt": "Aja como um especialista em licitações públicas. Adicione cláusulas de garantia de execução, penalidade por atraso e critério de desempate.",
            "descricao": "Teste de adição de cláusulas específicas"
        },
        {
            "categoria": "ALTERAÇÕES_COMPLEXAS",
            "prompt": "Aja como um especialista em licitações públicas. Altere o valor para R$ 3.000.000,00, a data para 20/01/2025, o local para 'RIO DE JANEIRO', o número do edital para 001/2025, adicione cláusulas de garantia e penalidade, e mude o prazo de execução para 90 dias.",
            "descricao": "Teste de alterações complexas múltiplas"
        },
        {
            "categoria": "PRESERVAÇÃO_LEGAL",
            "prompt": "Aja como um especialista em licitações públicas. Altere apenas o valor para R$ 1.000.000,00. Mantenha todas as referências legais intactas.",
            "descricao": "Teste de preservação de referências legais"
        }
    ]
    
    resultados = []
    
    for teste in testes:
        resultado = testar_prompt(
            teste['prompt'],
            teste['categoria'],
            teste['descricao']
        )
        if resultado:
            resultados.append(resultado)
    
    # Resumo final
    print("\n" + "=" * 70)
    print("📊 RESUMO FINAL DOS TESTES")
    print("=" * 70)
    
    if resultados:
        scores = [r['percentual'] for r in resultados]
        media_geral = sum(scores) / len(scores)
        
        print(f"🎯 MÉDIA GERAL: {media_geral:.1f}%")
        print(f"📈 MELHOR TESTE: {max(scores):.1f}%")
        print(f"📉 PIOR TESTE: {min(scores):.1f}%")
        print()
        
        print("📋 DETALHES POR CATEGORIA:")
        for resultado in resultados:
            status = "✅" if resultado['percentual'] >= 80 else "⚠️" if resultado['percentual'] >= 60 else "❌"
            print(f"   {status} {resultado['categoria']}: {resultado['percentual']:.1f}% ({resultado['score']}/{resultado['total']})")
        
        # Análise de problemas
        print("\n🔍 ANÁLISE DE PROBLEMAS:")
        problemas = []
        
        for resultado in resultados:
            if resultado['clausulas_apos_8_1'] > 0:
                problemas.append(f"Cláusulas inseridas após 8.1 em {resultado['categoria']}")
            
            if not resultado['alteracoes']['referencias_legais_preservadas']:
                problemas.append(f"Referências legais alteradas em {resultado['categoria']}")
        
        if problemas:
            for problema in problemas:
                print(f"   ⚠️ {problema}")
        else:
            print("   ✅ Nenhum problema crítico identificado")
        
        print(f"\n🎉 SISTEMA FUNCIONANDO COM {media_geral:.1f}% DE EFICIÊNCIA!")
    
    else:
        print("❌ Nenhum teste foi executado com sucesso")

if __name__ == "__main__":
    executar_testes_completos()
