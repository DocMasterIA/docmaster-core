#!/usr/bin/env python3
"""
Teste simples para cláusulas
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

def teste_clausulas_simples():
    """Teste simples para cláusulas."""
    
    print("⚖️ TESTE SIMPLES DE CLÁUSULAS")
    print("=" * 50)
    
    # Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado!")
        return
    
    # Prompt simples
    prompt = "Aja como um especialista em licitações públicas e na Lei 14.133/21. Adicione uma cláusula de garantia de execução."
    
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
        output_path = os.path.join(tmpdir, f"teste_clausula_simples_{template.id}.docx")
        
        print(f"\n🔄 Renderizando documento...")
        render_docx_contextual_intelligent(
            template_path=template.file.path,
            output_path=output_path,
            values=data,
            user_prompt=prompt
        )
        
        print(f"✅ Documento renderizado: {output_path}")
        
        # Verificar se a cláusula foi adicionada
        doc = Document(output_path)
        texto_completo = ""
        for paragraph in doc.paragraphs:
            texto_completo += paragraph.text + "\n"
        
        if "GARANTIA DE EXECUÇÃO" in texto_completo:
            print("✅ Cláusula de garantia de execução encontrada no documento!")
        else:
            print("❌ Cláusula de garantia de execução NÃO encontrada no documento!")
        
        if "Lei 14.133/2021" in texto_completo:
            print("✅ Base legal Lei 14.133/2021 encontrada!")
        else:
            print("❌ Base legal Lei 14.133/2021 NÃO encontrada!")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    teste_clausulas_simples()
