#!/usr/bin/env python3
"""
Debug para investigar duplicação de cláusulas e posicionamento incorreto
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

from backend.app.services.ia import generate_document_data_from_prompt
from backend.app.services.render import render_docx_contextual_intelligent
from backend.app.models import Template
from docx import Document

def debug_duplicacao_clausulas():
    """Debug para investigar duplicação e posicionamento incorreto."""
    
    print("🔍 DEBUG: DUPLICAÇÃO E POSICIONAMENTO DE CLÁUSULAS")
    print("=" * 70)
    
    # Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado!")
        return
    
    # Prompt simples para testar
    prompt = "Aja como um especialista em licitações públicas. Adicione uma cláusula de julgamento por técnica e preço."
    
    print(f"📝 Prompt: {prompt}")
    print()
    
    try:
        # Gerar dados
        data = generate_document_data_from_prompt(template, prompt)
        
        print(f"📊 Dados gerados:")
        print(f"   - Cláusulas específicas: {len(data.get('clausulas_especificas', []))}")
        print(f"   - Adicionar cláusula julgamento: {data.get('adicionar_clausula_julgamento', False)}")
        print(f"   - Adicionar observação prática: {data.get('adicionar_observacao_pratica', False)}")
        
        # Renderizar documento
        tmpdir = tempfile.gettempdir()
        output_path = os.path.join(tmpdir, f"debug_duplicacao_{template.id}.docx")
        
        print(f"\n🔄 Renderizando documento...")
        render_docx_contextual_intelligent(
            template_path=template.file.path,
            output_path=output_path,
            values=data,
            user_prompt=prompt
        )
        
        print(f"✅ Documento renderizado: {output_path}")
        
        # Analisar duplicações e posicionamento
        doc = Document(output_path)
        print(f"\n📋 Análise detalhada:")
        
        # Contar cláusulas 3.4.16
        clausulas_3_4_16 = []
        for i, paragraph in enumerate(doc.paragraphs):
            text = paragraph.text.strip()
            if "3.4.16" in text and "adjudicado" in text.lower():
                clausulas_3_4_16.append({
                    'linha': i + 1,
                    'texto': text[:100] + '...' if len(text) > 100 else text
                })
        
        print(f"\n📊 Cláusulas 3.4.16 encontradas: {len(clausulas_3_4_16)}")
        for i, clausula in enumerate(clausulas_3_4_16):
            print(f"   [{i+1}] Linha {clausula['linha']}: {clausula['texto']}")
        
        # Contar cláusulas 3.4.15
        clausulas_3_4_15 = []
        for i, paragraph in enumerate(doc.paragraphs):
            text = paragraph.text.strip()
            if "3.4.15" in text and "julgamento" in text.lower():
                clausulas_3_4_15.append({
                    'linha': i + 1,
                    'texto': text[:100] + '...' if len(text) > 100 else text
                })
        
        print(f"\n📊 Cláusulas 3.4.15 encontradas: {len(clausulas_3_4_15)}")
        for i, clausula in enumerate(clausulas_3_4_15):
            print(f"   [{i+1}] Linha {clausula['linha']}: {clausula['texto']}")
        
        # Verificar se 3.4.15 está após 8.1
        clausulas_8_1 = []
        for i, paragraph in enumerate(doc.paragraphs):
            text = paragraph.text.strip()
            if "8.1" in text and "julgamento" in text.lower():
                clausulas_8_1.append({
                    'linha': i + 1,
                    'texto': text[:100] + '...' if len(text) > 100 else text
                })
        
        print(f"\n📊 Cláusulas 8.1 encontradas: {len(clausulas_8_1)}")
        for i, clausula in enumerate(clausulas_8_1):
            print(f"   [{i+1}] Linha {clausula['linha']}: {clausula['texto']}")
        
        # Verificar posicionamento relativo
        print(f"\n🔍 Análise de posicionamento:")
        
        # Encontrar todas as cláusulas 3.4.x
        todas_clausulas_3_4 = []
        for i, paragraph in enumerate(doc.paragraphs):
            text = paragraph.text.strip()
            match = re.search(r'3\.4\.(\d+)', text)
            if match:
                todas_clausulas_3_4.append({
                    'linha': i + 1,
                    'numero': int(match.group(1)),
                    'texto': text[:50] + '...' if len(text) > 50 else text
                })
        
        print(f"   Total de cláusulas 3.4.x: {len(todas_clausulas_3_4)}")
        
        # Verificar se há cláusulas após 8.1
        clausulas_apos_8_1 = []
        for clausula in todas_clausulas_3_4:
            # Verificar se há 8.1 antes desta cláusula
            for i in range(clausula['linha'] - 1):
                if "8.1" in doc.paragraphs[i].text and "julgamento" in doc.paragraphs[i].text.lower():
                    clausulas_apos_8_1.append(clausula)
                    break
        
        if clausulas_apos_8_1:
            print(f"   ❌ Cláusulas 3.4.x encontradas após 8.1: {len(clausulas_apos_8_1)}")
            for clausula in clausulas_apos_8_1:
                print(f"      - Linha {clausula['linha']}: 3.4.{clausula['numero']} - {clausula['texto']}")
        else:
            print(f"   ✅ Nenhuma cláusula 3.4.x encontrada após 8.1")
        
        # Verificar duplicações
        numeros_clausulas = [c['numero'] for c in todas_clausulas_3_4]
        duplicacoes = {}
        for num in numeros_clausulas:
            if numeros_clausulas.count(num) > 1:
                duplicacoes[num] = numeros_clausulas.count(num)
        
        if duplicacoes:
            print(f"\n❌ Duplicações encontradas:")
            for num, count in duplicacoes.items():
                print(f"   - 3.4.{num}: {count} ocorrências")
        else:
            print(f"\n✅ Nenhuma duplicação encontrada")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_duplicacao_clausulas()
