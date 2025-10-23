#!/usr/bin/env python3
"""
Debug específico da detecção de cláusulas no render.py
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

def debug_deteccao_clausulas():
    """Debug específico da detecção de cláusulas."""
    
    print("🔍 DEBUG DETECÇÃO DE CLÁUSULAS")
    print("=" * 50)
    
    # Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado!")
        return
    
    try:
        # Carregar documento
        doc = Document(template.file.path)
        
        print("📊 TESTANDO DIFERENTES PADRÕES DE REGEX:")
        print("-" * 50)
        
        # Padrões para testar
        padroes = [
            (r'3\.4\.(\d+)', "Padrão original"),
            (r'(?<!\d)3\.4\.(\d+)', "Padrão com lookbehind"),
            (r'^3\.4\.(\d+)', "Padrão com início de linha"),
            (r'(?<![0-9])3\.4\.(\d+)', "Padrão com lookbehind numérico"),
            (r'\b3\.4\.(\d+)', "Padrão com word boundary"),
        ]
        
        for padrao, descricao in padroes:
            print(f"\n🔍 {descricao}:")
            clausulas_encontradas = []
            
            for i, paragraph in enumerate(doc.paragraphs):
                text = paragraph.text.strip()
                match = re.search(padrao, text)
                if match:
                    clausulas_encontradas.append({
                        'linha': i + 1,
                        'numero': int(match.group(1)),
                        'texto': text[:60] + '...' if len(text) > 60 else text
                    })
            
            print(f"   Total encontrado: {len(clausulas_encontradas)}")
            
            # Mostrar apenas as primeiras 5
            for clausula in clausulas_encontradas[:5]:
                print(f"   Linha {clausula['linha']}: 3.4.{clausula['numero']} - {clausula['texto']}")
            
            if len(clausulas_encontradas) > 5:
                print(f"   ... e mais {len(clausulas_encontradas) - 5} cláusulas")
        
        # Verificar especificamente as cláusulas 13.4.x
        print(f"\n🔍 VERIFICAÇÃO ESPECÍFICA DAS CLÁUSULAS 13.4.x:")
        print("-" * 50)
        
        clausulas_13_4 = []
        for i, paragraph in enumerate(doc.paragraphs):
            text = paragraph.text.strip()
            if '13.4.' in text:
                clausulas_13_4.append({
                    'linha': i + 1,
                    'texto': text[:80] + '...' if len(text) > 80 else text
                })
        
        print(f"📊 Cláusulas com '13.4.' encontradas: {len(clausulas_13_4)}")
        for clausula in clausulas_13_4:
            print(f"   Linha {clausula['linha']}: {clausula['texto']}")
        
        # Testar o regex específico nas cláusulas 13.4.x
        print(f"\n🔍 TESTE DO REGEX NAS CLÁUSULAS 13.4.x:")
        print("-" * 50)
        
        for clausula in clausulas_13_4:
            texto = clausula['texto']
            match = re.search(r'(?<!\d)3\.4\.(\d+)', texto)
            if match:
                print(f"   ❌ ERRO: Linha {clausula['linha']} - {texto[:50]}...")
                print(f"      Regex detectou: 3.4.{match.group(1)}")
            else:
                print(f"   ✅ OK: Linha {clausula['linha']} - {texto[:50]}...")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_deteccao_clausulas()
