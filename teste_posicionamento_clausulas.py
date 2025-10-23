#!/usr/bin/env python3
"""
Teste específico para verificar o posicionamento correto das cláusulas
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

def teste_posicionamento_clausulas():
    """Teste específico para verificar o posicionamento das cláusulas."""
    
    print("🎯 TESTE DE POSICIONAMENTO DE CLÁUSULAS")
    print("=" * 60)
    print("Verificando se as cláusulas são inseridas na sequência correta 3.4.x")
    print()
    
    # Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado!")
        return
    
    # Prompt com múltiplas cláusulas
    prompt = "Aja como um especialista em licitações públicas e na Lei 14.133/21. Adicione cláusulas de garantia de execução, penalidade por atraso e critério de desempate."
    
    print(f"📝 Prompt: {prompt}")
    print()
    
    try:
        # Gerar dados
        data = generate_document_data_from_prompt(template, prompt)
        
        print(f"📊 Cláusulas detectadas: {len(data.get('clausulas_especificas', []))}")
        for i, clausula in enumerate(data.get('clausulas_especificas', [])):
            print(f"   [{i}] {clausula['tipo']}: {clausula['descricao']}")
        
        # Renderizar documento
        tmpdir = tempfile.gettempdir()
        output_path = os.path.join(tmpdir, f"teste_posicionamento_{template.id}.docx")
        
        print(f"\n🔄 Renderizando documento...")
        render_docx_contextual_intelligent(
            template_path=template.file.path,
            output_path=output_path,
            values=data,
            user_prompt=prompt
        )
        
        print(f"✅ Documento renderizado: {output_path}")
        
        # Analisar posicionamento das cláusulas
        doc = Document(output_path)
        print(f"\n📋 Análise do posicionamento das cláusulas:")
        
        clausulas_encontradas = []
        for i, paragraph in enumerate(doc.paragraphs):
            text = paragraph.text.strip()
            if re.search(r'3\.4\.\d+', text) and any(keyword in text.lower() for keyword in ['garantia', 'penalidade', 'critério', 'desempate']):
                clausulas_encontradas.append({
                    'linha': i + 1,
                    'texto': text[:100] + '...' if len(text) > 100 else text,
                    'numero': re.search(r'3\.4\.(\d+)', text).group(1) if re.search(r'3\.4\.(\d+)', text) else 'N/A'
                })
        
        print(f"\n📊 Cláusulas encontradas no documento:")
        for clausula in clausulas_encontradas:
            print(f"   Linha {clausula['linha']}: 3.4.{clausula['numero']} - {clausula['texto']}")
        
        # Verificar se estão na sequência correta
        numeros = [int(c['numero']) for c in clausulas_encontradas if c['numero'] != 'N/A']
        if numeros:
            numeros_ordenados = sorted(numeros)
            if numeros == numeros_ordenados:
                print(f"\n✅ Cláusulas estão na sequência correta!")
            else:
                print(f"\n❌ Cláusulas NÃO estão na sequência correta!")
                print(f"   Sequência atual: {numeros}")
                print(f"   Sequência esperada: {numeros_ordenados}")
        else:
            print(f"\n⚠️ Não foi possível verificar a sequência (números não encontrados)")
        
        # Verificar se contém base legal
        texto_completo = ""
        for paragraph in doc.paragraphs:
            texto_completo += paragraph.text + "\n"
        
        base_legal_count = len(re.findall(r'Lei\s+14\.133/2021', texto_completo))
        print(f"\n📚 Base legal Lei 14.133/2021 encontrada {base_legal_count} vezes")
        
        if base_legal_count > 0:
            print("✅ Base legal presente nas cláusulas!")
        else:
            print("❌ Base legal não encontrada!")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    teste_posicionamento_clausulas()
