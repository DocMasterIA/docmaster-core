#!/usr/bin/env python3
"""
Debug específico para entender o problema de posicionamento de cláusulas
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

from backend.app.models import Template
from docx import Document

def debug_posicionamento():
    """Debug detalhado do posicionamento de cláusulas."""
    
    print("🔍 DEBUG DETALHADO - POSICIONAMENTO DE CLÁUSULAS")
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
        
        print("📊 ANÁLISE DETALHADA DAS SEÇÕES:")
        print("-" * 40)
        
        # Encontrar todas as seções numeradas
        secoes_encontradas = {}
        
        for i, paragraph in enumerate(doc.paragraphs):
            text = paragraph.text.strip()
            if not text:
                continue
            
            # Detectar seções principais
            if re.match(r'^\d+\.', text):
                secao = text.split('.')[0]
                if secao not in secoes_encontradas:
                    secoes_encontradas[secao] = []
                secoes_encontradas[secao].append({
                    'linha': i + 1,
                    'texto': text[:80] + '...' if len(text) > 80 else text
                })
        
        # Mostrar seções em ordem
        for secao in sorted(secoes_encontradas.keys(), key=int):
            itens = secoes_encontradas[secao]
            print(f"\n📌 SEÇÃO {secao}: {len(itens)} itens")
            for item in itens[:3]:  # Mostrar apenas os primeiros 3
                print(f"   Linha {item['linha']}: {item['texto']}")
            if len(itens) > 3:
                print(f"   ... e mais {len(itens) - 3} itens")
        
        # Análise específica das cláusulas 3.4.x
        print(f"\n🔍 ANÁLISE ESPECÍFICA DAS CLÁUSULAS 3.4.x:")
        print("-" * 50)
        
        clausulas_3_4 = []
        for i, paragraph in enumerate(doc.paragraphs):
            text = paragraph.text.strip()
            match = re.search(r'3\.4\.(\d+)', text)
            if match:
                clausulas_3_4.append({
                    'linha': i + 1,
                    'numero': int(match.group(1)),
                    'texto': text[:60] + '...' if len(text) > 60 else text
                })
        
        print(f"📊 Total de cláusulas 3.4.x encontradas: {len(clausulas_3_4)}")
        for clausula in clausulas_3_4:
            print(f"   Linha {clausula['linha']}: 3.4.{clausula['numero']} - {clausula['texto']}")
        
        # Encontrar seções 8.x, 9.x, 10.x
        secoes_8 = []
        secoes_9 = []
        secoes_10 = []
        
        for i, paragraph in enumerate(doc.paragraphs):
            text = paragraph.text.strip()
            if re.match(r'^8\.', text):
                secoes_8.append({'linha': i + 1, 'texto': text[:60] + '...' if len(text) > 60 else text})
            elif re.match(r'^9\.', text):
                secoes_9.append({'linha': i + 1, 'texto': text[:60] + '...' if len(text) > 60 else text})
            elif re.match(r'^10\.', text):
                secoes_10.append({'linha': i + 1, 'texto': text[:60] + '...' if len(text) > 60 else text})
        
        print(f"\n📊 SEÇÕES 8.x: {len(secoes_8)} itens")
        for secao in secoes_8:
            print(f"   Linha {secao['linha']}: {secao['texto']}")
        
        print(f"\n📊 SEÇÕES 9.x: {len(secoes_9)} itens")
        for secao in secoes_9:
            print(f"   Linha {secao['linha']}: {secao['texto']}")
        
        print(f"\n📊 SEÇÕES 10.x: {len(secoes_10)} itens")
        for secao in secoes_10:
            print(f"   Linha {secao['linha']}: {secao['texto']}")
        
        # Verificar onde estão as cláusulas 3.4.x em relação às outras seções
        print(f"\n🔍 ANÁLISE DE POSICIONAMENTO:")
        print("-" * 40)
        
        if secoes_8:
            primeira_8 = min(s['linha'] for s in secoes_8)
            clausulas_apos_8 = [c for c in clausulas_3_4 if c['linha'] > primeira_8]
            print(f"   Cláusulas 3.4.x após seção 8.x: {len(clausulas_apos_8)}")
            for c in clausulas_apos_8:
                print(f"      Linha {c['linha']}: 3.4.{c['numero']}")
        
        if secoes_9:
            primeira_9 = min(s['linha'] for s in secoes_9)
            clausulas_apos_9 = [c for c in clausulas_3_4 if c['linha'] > primeira_9]
            print(f"   Cláusulas 3.4.x após seção 9.x: {len(clausulas_apos_9)}")
            for c in clausulas_apos_9:
                print(f"      Linha {c['linha']}: 3.4.{c['numero']}")
        
        if secoes_10:
            primeira_10 = min(s['linha'] for s in secoes_10)
            clausulas_apos_10 = [c for c in clausulas_3_4 if c['linha'] > primeira_10]
            print(f"   Cláusulas 3.4.x após seção 10.x: {len(clausulas_apos_10)}")
            for c in clausulas_apos_10:
                print(f"      Linha {c['linha']}: 3.4.{c['numero']}")
        
        # Verificar se há cláusulas 13.4.x (que podem estar sendo confundidas)
        clausulas_13_4 = []
        for i, paragraph in enumerate(doc.paragraphs):
            text = paragraph.text.strip()
            match = re.search(r'13\.4\.(\d+)', text)
            if match:
                clausulas_13_4.append({
                    'linha': i + 1,
                    'numero': int(match.group(1)),
                    'texto': text[:60] + '...' if len(text) > 60 else text
                })
        
        print(f"\n📊 CLÁUSULAS 13.4.x (PENALIDADES): {len(clausulas_13_4)}")
        for clausula in clausulas_13_4:
            print(f"   Linha {clausula['linha']}: 13.4.{clausula['numero']} - {clausula['texto']}")
        
        # Verificar se o problema está na detecção de cláusulas 3.4.x
        print(f"\n🔍 VERIFICAÇÃO DE DETECÇÃO:")
        print("-" * 30)
        
        # Procurar por padrões que podem estar sendo confundidos
        for i, paragraph in enumerate(doc.paragraphs):
            text = paragraph.text.strip()
            if '3.4.' in text and not re.search(r'3\.4\.\d+', text):
                print(f"   Linha {i+1}: Texto com '3.4.' mas sem padrão: {text[:50]}...")
        
        # Verificar se há cláusulas 3.4.x que estão sendo detectadas incorretamente
        print(f"\n🔍 VERIFICAÇÃO DE PADRÕES:")
        print("-" * 30)
        
        for i, paragraph in enumerate(doc.paragraphs):
            text = paragraph.text.strip()
            if re.search(r'3\.4\.\d+', text):
                match = re.search(r'3\.4\.(\d+)', text)
                numero = int(match.group(1))
                print(f"   Linha {i+1}: 3.4.{numero} - {text[:50]}...")
        
    except Exception as e:
        print(f"❌ Erro ao analisar template: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_posicionamento()
