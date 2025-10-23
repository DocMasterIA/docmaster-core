#!/usr/bin/env python3
"""
Teste focado em posicionamento de cláusulas em diferentes seções do documento
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

def analisar_posicionamento_clausulas(doc, nome_teste):
    """Analisa o posicionamento das cláusulas no documento."""
    
    print(f"\n🔍 ANÁLISE DE POSICIONAMENTO - {nome_teste}")
    print("-" * 50)
    
    # Encontrar todas as cláusulas 3.4.x
    clausulas_3_4 = []
    for i, paragraph in enumerate(doc.paragraphs):
        text = paragraph.text.strip()
        match = re.search(r'(?<!\d)3\.4\.(\d+)', text)
        if match:
            clausulas_3_4.append({
                'linha': i + 1,
                'numero': int(match.group(1)),
                'texto': text[:80] + '...' if len(text) > 80 else text,
                'contem_julgamento': 'julgamento' in text.lower(),
                'contem_garantia': 'garantia' in text.lower(),
                'contem_penalidade': 'penalidade' in text.lower(),
                'contem_desempate': 'desempate' in text.lower()
            })
    
    # Encontrar seções 8.x
    secoes_8_x = []
    for i, paragraph in enumerate(doc.paragraphs):
        text = paragraph.text.strip()
        if re.match(r'8\.\d+', text):
            secoes_8_x.append({
                'linha': i + 1,
                'texto': text[:60] + '...' if len(text) > 60 else text
            })
    
    # Encontrar seções 9.x (recursos)
    secoes_9_x = []
    for i, paragraph in enumerate(doc.paragraphs):
        text = paragraph.text.strip()
        if re.match(r'9\.\d+', text):
            secoes_9_x.append({
                'linha': i + 1,
                'texto': text[:60] + '...' if len(text) > 60 else text
            })
    
    # Encontrar seções 10.x (entrega)
    secoes_10_x = []
    for i, paragraph in enumerate(doc.paragraphs):
        text = paragraph.text.strip()
        if re.match(r'10\.\d+', text):
            secoes_10_x.append({
                'linha': i + 1,
                'texto': text[:60] + '...' if len(text) > 60 else text
            })
    
    print(f"📊 CLÁUSULAS 3.4.x ENCONTRADAS: {len(clausulas_3_4)}")
    for clausula in clausulas_3_4:
        tipo = []
        if clausula['contem_julgamento']: tipo.append("JULGAMENTO")
        if clausula['contem_garantia']: tipo.append("GARANTIA")
        if clausula['contem_penalidade']: tipo.append("PENALIDADE")
        if clausula['contem_desempate']: tipo.append("DESEMPATE")
        
        tipo_str = f" [{', '.join(tipo)}]" if tipo else ""
        print(f"   Linha {clausula['linha']}: 3.4.{clausula['numero']}{tipo_str}")
        print(f"      {clausula['texto']}")
    
    print(f"\n📊 SEÇÕES 8.x ENCONTRADAS: {len(secoes_8_x)}")
    for secao in secoes_8_x:
        print(f"   Linha {secao['linha']}: {secao['texto']}")
    
    print(f"\n📊 SEÇÕES 9.x ENCONTRADAS: {len(secoes_9_x)}")
    for secao in secoes_9_x:
        print(f"   Linha {secao['linha']}: {secao['texto']}")
    
    print(f"\n📊 SEÇÕES 10.x ENCONTRADAS: {len(secoes_10_x)}")
    for secao in secoes_10_x:
        print(f"   Linha {secao['linha']}: {secao['texto']}")
    
    # Verificar se há cláusulas 3.4.x após seções 8.x, 9.x, 10.x
    clausulas_apos_8 = 0
    clausulas_apos_9 = 0
    clausulas_apos_10 = 0
    
    for clausula in clausulas_3_4:
        # Verificar se há seção 8.x antes desta cláusula
        for secao in secoes_8_x:
            if clausula['linha'] > secao['linha']:
                clausulas_apos_8 += 1
                break
        
        # Verificar se há seção 9.x antes desta cláusula
        for secao in secoes_9_x:
            if clausula['linha'] > secao['linha']:
                clausulas_apos_9 += 1
                break
        
        # Verificar se há seção 10.x antes desta cláusula
        for secao in secoes_10_x:
            if clausula['linha'] > secao['linha']:
                clausulas_apos_10 += 1
                break
    
    print(f"\n⚠️ PROBLEMAS DE POSICIONAMENTO:")
    if clausulas_apos_8 > 0:
        print(f"   ❌ {clausulas_apos_8} cláusula(s) 3.4.x após seção 8.x")
    else:
        print(f"   ✅ Nenhuma cláusula 3.4.x após seção 8.x")
    
    if clausulas_apos_9 > 0:
        print(f"   ❌ {clausulas_apos_9} cláusula(s) 3.4.x após seção 9.x")
    else:
        print(f"   ✅ Nenhuma cláusula 3.4.x após seção 9.x")
    
    if clausulas_apos_10 > 0:
        print(f"   ❌ {clausulas_apos_10} cláusula(s) 3.4.x após seção 10.x")
    else:
        print(f"   ✅ Nenhuma cláusula 3.4.x após seção 10.x")
    
    # Verificar sequência das cláusulas 3.4.x
    numeros = [c['numero'] for c in clausulas_3_4]
    numeros_ordenados = sorted(numeros)
    
    if numeros == numeros_ordenados:
        print(f"   ✅ Cláusulas 3.4.x em sequência correta")
    else:
        print(f"   ❌ Cláusulas 3.4.x NÃO em sequência")
        print(f"      Sequência atual: {numeros}")
        print(f"      Sequência esperada: {numeros_ordenados}")
    
    return {
        'clausulas_3_4': len(clausulas_3_4),
        'clausulas_apos_8': clausulas_apos_8,
        'clausulas_apos_9': clausulas_apos_9,
        'clausulas_apos_10': clausulas_apos_10,
        'sequencia_correta': numeros == numeros_ordenados
    }

def testar_posicionamento(prompt, nome_teste):
    """Testa posicionamento de cláusulas com um prompt específico."""
    
    print(f"\n🧪 TESTE: {nome_teste}")
    print(f"📝 Prompt: {prompt}")
    print("=" * 60)
    
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
        output_path = os.path.join(tmpdir, f"posicionamento_{nome_teste}_{int(time.time())}.docx")
        
        render_docx_contextual_intelligent(
            template_path=template.file.path,
            output_path=output_path,
            values=data,
            user_prompt=prompt
        )
        
        # Analisar posicionamento
        doc = Document(output_path)
        resultado = analisar_posicionamento_clausulas(doc, nome_teste)
        
        return resultado
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        return None

def executar_testes_posicionamento():
    """Executa testes focados em posicionamento de cláusulas."""
    
    print("🎯 TESTE AVANÇADO DE POSICIONAMENTO DE CLÁUSULAS")
    print("=" * 70)
    print("Foco: Posicionamento correto de cláusulas em diferentes seções")
    print()
    
    # Prompts específicos para testar posicionamento
    testes = [
        {
            "nome": "CLÁUSULAS_MÚLTIPLAS",
            "prompt": "Aja como um especialista em licitações públicas. Adicione cláusulas de garantia de execução, penalidade por atraso, critério de desempate, prazo de entrega e documentação complementar.",
            "descricao": "Teste com múltiplas cláusulas para verificar sequência"
        },
        {
            "nome": "CLÁUSULA_JULGAMENTO",
            "prompt": "Aja como um especialista em licitações públicas. Adicione uma cláusula de julgamento por técnica e preço com observação prática.",
            "descricao": "Teste específico de cláusula de julgamento"
        },
        {
            "nome": "CLÁUSULAS_ESPECÍFICAS",
            "prompt": "Aja como um especialista em licitações públicas. Inclua cláusulas sobre garantia de fornecimento, penalidade por atraso e critério de desempate.",
            "descricao": "Teste de cláusulas específicas diferentes"
        },
        {
            "nome": "CLÁUSULA_SIMPLES",
            "prompt": "Aja como um especialista em licitações públicas. Adicione apenas uma cláusula de garantia de execução.",
            "descricao": "Teste simples com uma cláusula"
        },
        {
            "nome": "CLÁUSULAS_DIVERSAS",
            "prompt": "Aja como um especialista em licitações públicas. Adicione cláusulas de penalidade por atraso, prazo de entrega e documentação complementar.",
            "descricao": "Teste com cláusulas diversas"
        }
    ]
    
    resultados = []
    
    for teste in testes:
        resultado = testar_posicionamento(teste['prompt'], teste['nome'])
        if resultado:
            resultados.append({
                'nome': teste['nome'],
                'descricao': teste['descricao'],
                **resultado
            })
    
    # Resumo final
    print("\n" + "=" * 70)
    print("📊 RESUMO FINAL - POSICIONAMENTO DE CLÁUSULAS")
    print("=" * 70)
    
    if resultados:
        total_clausulas = sum(r['clausulas_3_4'] for r in resultados)
        total_apos_8 = sum(r['clausulas_apos_8'] for r in resultados)
        total_apos_9 = sum(r['clausulas_apos_9'] for r in resultados)
        total_apos_10 = sum(r['clausulas_apos_10'] for r in resultados)
        sequencias_corretas = sum(1 for r in resultados if r['sequencia_correta'])
        
        print(f"📈 ESTATÍSTICAS GERAIS:")
        print(f"   Total de cláusulas 3.4.x geradas: {total_clausulas}")
        print(f"   Cláusulas após seção 8.x: {total_apos_8}")
        print(f"   Cláusulas após seção 9.x: {total_apos_9}")
        print(f"   Cláusulas após seção 10.x: {total_apos_10}")
        print(f"   Sequências corretas: {sequencias_corretas}/{len(resultados)}")
        print()
        
        print("📋 DETALHES POR TESTE:")
        for resultado in resultados:
            status = "✅" if resultado['clausulas_apos_8'] == 0 and resultado['sequencia_correta'] else "⚠️" if resultado['clausulas_apos_8'] <= 1 else "❌"
            print(f"   {status} {resultado['nome']}: {resultado['clausulas_3_4']} cláusulas, {resultado['clausulas_apos_8']} após 8.x")
        
        # Análise de problemas
        print(f"\n🔍 ANÁLISE DE PROBLEMAS:")
        if total_apos_8 > 0:
            print(f"   ⚠️ {total_apos_8} cláusula(s) inserida(s) após seção 8.x")
        if total_apos_9 > 0:
            print(f"   ⚠️ {total_apos_9} cláusula(s) inserida(s) após seção 9.x")
        if total_apos_10 > 0:
            print(f"   ⚠️ {total_apos_10} cláusula(s) inserida(s) após seção 10.x")
        
        if total_apos_8 == 0 and total_apos_9 == 0 and total_apos_10 == 0:
            print("   ✅ Nenhum problema de posicionamento identificado!")
        
        eficiencia = (sequencias_corretas / len(resultados) * 100) if resultados else 0
        print(f"\n🎉 EFICIÊNCIA DE POSICIONAMENTO: {eficiencia:.1f}%")
    
    else:
        print("❌ Nenhum teste foi executado com sucesso")

if __name__ == "__main__":
    executar_testes_posicionamento()
