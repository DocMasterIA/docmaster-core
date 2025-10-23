#!/usr/bin/env python3
"""
Análise detalhada do template para criar prompts inteligentes
"""

import os
import sys
import django
from pathlib import Path
import tempfile
import shutil
import re

# Add the backend directory to Python path
sys.path.append('/home/adryan/Downloads/mdlicitatech-system/backend')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mdlicitatech.settings')
django.setup()

from backend.app.models import Template
from docx import Document

def analisar_template():
    """Analisa o template para entender sua estrutura e criar prompts inteligentes."""
    
    print("🔍 ANÁLISE DETALHADA DO TEMPLATE")
    print("=" * 60)
    
    # Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado!")
        return
    
    print(f"📄 Template: {template.name}")
    print(f"📁 Arquivo: {template.file.path}")
    print()
    
    try:
        # Carregar documento
        doc = Document(template.file.path)
        
        print("📋 ESTRUTURA DO DOCUMENTO:")
        print("-" * 40)
        
        # Analisar seções principais
        secoes = {}
        clausulas_por_secao = {}
        
        for i, paragraph in enumerate(doc.paragraphs):
            text = paragraph.text.strip()
            if not text:
                continue
                
            # Detectar seções principais
            if re.match(r'^\d+\.', text):
                secao = text.split('.')[0]
                if secao not in secoes:
                    secoes[secao] = []
                secoes[secao].append({
                    'linha': i + 1,
                    'texto': text[:100] + '...' if len(text) > 100 else text
                })
            
            # Detectar cláusulas 3.4.x
            if re.match(r'3\.4\.\d+', text):
                if '3.4' not in clausulas_por_secao:
                    clausulas_por_secao['3.4'] = []
                clausulas_por_secao['3.4'].append({
                    'linha': i + 1,
                    'texto': text[:80] + '...' if len(text) > 80 else text
                })
        
        # Mostrar seções principais
        print("📊 SEÇÕES PRINCIPAIS ENCONTRADAS:")
        for secao, itens in sorted(secoes.items()):
            print(f"   Seção {secao}: {len(itens)} itens")
            for item in itens[:3]:  # Mostrar apenas os primeiros 3
                print(f"      Linha {item['linha']}: {item['texto']}")
            if len(itens) > 3:
                print(f"      ... e mais {len(itens) - 3} itens")
            print()
        
        # Mostrar cláusulas 3.4.x
        if '3.4' in clausulas_por_secao:
            print("⚖️ CLÁUSULAS 3.4.x (CRITÉRIOS DE JULGAMENTO):")
            for clausula in clausulas_por_secao['3.4']:
                print(f"   Linha {clausula['linha']}: {clausula['texto']}")
            print()
        
        # Analisar tabelas
        print("📊 TABELAS ENCONTRADAS:")
        for i, table in enumerate(doc.tables):
            print(f"   Tabela {i}: {len(table.rows)} linhas x {len(table.columns)} colunas")
            # Mostrar primeira linha da tabela
            if table.rows:
                primeira_linha = []
                for cell in table.rows[0].cells:
                    primeira_linha.append(cell.text.strip()[:30])
                print(f"      Primeira linha: {' | '.join(primeira_linha)}")
        print()
        
        # Analisar valores específicos
        print("💰 VALORES E DATAS ENCONTRADOS:")
        valores_encontrados = []
        datas_encontradas = []
        locais_encontrados = []
        
        for paragraph in doc.paragraphs:
            text = paragraph.text
            
            # Procurar valores monetários
            valores = re.findall(r'R\$\s*[\d.,]+', text)
            for valor in valores:
                if valor not in valores_encontrados:
                    valores_encontrados.append(valor)
            
            # Procurar datas
            datas = re.findall(r'\d{1,2}/\d{1,2}/\d{4}', text)
            for data in datas:
                if data not in datas_encontradas:
                    datas_encontradas.append(data)
            
            # Procurar locais
            if 'ITAJÁ' in text or 'BRASÍLIA' in text or 'GO' in text:
                locais_encontrados.append(text[:50] + '...' if len(text) > 50 else text)
        
        print(f"   Valores: {valores_encontrados}")
        print(f"   Datas: {datas_encontradas}")
        print(f"   Locais: {locais_encontrados[:3]}")  # Primeiros 3
        print()
        
        # Analisar referências legais
        print("📚 REFERÊNCIAS LEGAIS ENCONTRADAS:")
        referencias_legais = []
        for paragraph in doc.paragraphs:
            text = paragraph.text
            # Procurar por leis, decretos, etc.
            leis = re.findall(r'Lei\s+[^.]*', text)
            decretos = re.findall(r'Decreto[^.]*', text)
            artigos = re.findall(r'art\.\s*\d+', text)
            
            for lei in leis:
                if lei not in referencias_legais:
                    referencias_legais.append(lei)
            for decreto in decretos:
                if decreto not in referencias_legais:
                    referencias_legais.append(decreto)
            for artigo in artigos:
                if artigo not in referencias_legais:
                    referencias_legais.append(artigo)
        
        for ref in referencias_legais[:10]:  # Primeiras 10
            print(f"   - {ref}")
        print()
        
        # Criar prompts inteligentes baseados na análise
        print("🎯 PROMPTS INTELIGENTES SUGERIDOS:")
        print("=" * 50)
        
        prompts = [
            {
                "categoria": "Alterações Básicas",
                "prompts": [
                    "Aja como um especialista em licitações públicas. Altere o valor estimado para R$ 2.500.000,00 e a data de abertura para 15/12/2024.",
                    "Aja como um especialista em licitações públicas. Mude o local de 'ITAJÁ' para 'SÃO PAULO' e o número do edital para 789/2024.",
                    "Aja como um especialista em licitações públicas. Altere o prazo de execução para 120 dias e o órgão para 'SECRETARIA MUNICIPAL DE EDUCAÇÃO'."
                ]
            },
            {
                "categoria": "Cláusulas Específicas",
                "prompts": [
                    "Aja como um especialista em licitações públicas. Adicione cláusulas de garantia de execução, penalidade por atraso e critério de desempate.",
                    "Aja como um especialista em licitações públicas. Inclua uma cláusula sobre documentação complementar e prazo de entrega.",
                    "Aja como um especialista em licitações públicas. Adicione uma cláusula de julgamento por técnica e preço com observação prática."
                ]
            },
            {
                "categoria": "Alterações Complexas",
                "prompts": [
                    "Aja como um especialista em licitações públicas. Altere o valor para R$ 3.000.000,00, a data para 20/01/2025, o local para 'RIO DE JANEIRO', o número do edital para 001/2025, adicione cláusulas de garantia e penalidade, e mude o prazo de execução para 90 dias.",
                    "Aja como um especialista em licitações públicas. Mude o órgão para 'SECRETARIA MUNICIPAL DE SAÚDE', altere o valor para R$ 1.800.000,00, adicione cláusula de julgamento por técnica e preço, e inclua observação prática sobre registro de propostas.",
                    "Aja como um especialista em licitações públicas. Altere todos os dados: valor R$ 4.500.000,00, data 10/03/2025, local 'BELO HORIZONTE', edital 123/2025, prazo 150 dias, órgão 'SECRETARIA MUNICIPAL DE OBRAS', e adicione cláusulas de garantia, penalidade e critério de desempate."
                ]
            },
            {
                "categoria": "Testes de Preservação",
                "prompts": [
                    "Aja como um especialista em licitações públicas. Altere apenas o valor para R$ 1.000.000,00. Mantenha todas as referências legais intactas.",
                    "Aja como um especialista em licitações públicas. Mude apenas a data de abertura para 25/12/2024. Preserve todas as cláusulas existentes.",
                    "Aja como um especialista em licitações públicas. Altere o local para 'CURITIBA' e adicione uma cláusula de garantia. Não modifique as referências à Lei 14.133/2021."
                ]
            }
        ]
        
        for categoria in prompts:
            print(f"\n📌 {categoria['categoria'].upper()}:")
            for i, prompt in enumerate(categoria['prompts'], 1):
                print(f"   {i}. {prompt}")
        
        print(f"\n🎯 TOTAL: {sum(len(cat['prompts']) for cat in prompts)} prompts sugeridos")
        
    except Exception as e:
        print(f"❌ Erro ao analisar template: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analisar_template()
