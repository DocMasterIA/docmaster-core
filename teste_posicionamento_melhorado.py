#!/usr/bin/env python3
"""
Teste específico para verificar o posicionamento correto das cláusulas
com foco na cláusula 3.4.15 que estava aparecendo após 8.1
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

def teste_posicionamento_melhorado():
    """Teste específico para verificar o posicionamento correto das cláusulas."""
    
    print("🎯 TESTE DE POSICIONAMENTO MELHORADO")
    print("=" * 60)
    print("Verificando se as cláusulas são inseridas na seção 3.4.x correta")
    print("e NÃO na seção 8.1 ou outras seções")
    print()
    
    # Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado!")
        return
    
    # Prompt com cláusula de julgamento específica
    prompt = "Aja como um especialista em licitações públicas e na Lei 14.133/21. Adicione uma cláusula de julgamento por técnica e preço."
    
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
        output_path = os.path.join(tmpdir, f"teste_posicionamento_melhorado_{template.id}.docx")
        
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
        print(f"\n📋 Análise detalhada do posicionamento:")
        
        # Encontrar todas as cláusulas 3.4.x
        clausulas_3_4 = []
        for i, paragraph in enumerate(doc.paragraphs):
            text = paragraph.text.strip()
            match = re.search(r'3\.4\.(\d+)', text)
            if match:
                clausulas_3_4.append({
                    'linha': i + 1,
                    'numero': int(match.group(1)),
                    'texto': text[:100] + '...' if len(text) > 100 else text,
                    'contem_julgamento': 'julgamento' in text.lower()
                })
        
        # Encontrar cláusulas 8.x (onde NÃO deveria estar)
        clausulas_8_x = []
        for i, paragraph in enumerate(doc.paragraphs):
            text = paragraph.text.strip()
            match = re.search(r'8\.(\d+)', text)
            if match:
                clausulas_8_x.append({
                    'linha': i + 1,
                    'numero': int(match.group(1)),
                    'texto': text[:100] + '...' if len(text) > 100 else text
                })
        
        print(f"\n📊 Cláusulas 3.4.x encontradas ({len(clausulas_3_4)}):")
        for clausula in clausulas_3_4:
            status = "🎯 JULGAMENTO" if clausula['contem_julgamento'] else "📋 Normal"
            print(f"   Linha {clausula['linha']}: 3.4.{clausula['numero']} - {status}")
            print(f"      {clausula['texto']}")
        
        print(f"\n📊 Cláusulas 8.x encontradas ({len(clausulas_8_x)}):")
        for clausula in clausulas_8_x:
            print(f"   Linha {clausula['linha']}: 8.{clausula['numero']} - {clausula['texto']}")
        
        # Verificar se há cláusulas de julgamento na seção 3.4.x
        clausulas_julgamento_3_4 = [c for c in clausulas_3_4 if c['contem_julgamento']]
        
        if clausulas_julgamento_3_4:
            print(f"\n✅ Encontradas {len(clausulas_julgamento_3_4)} cláusula(s) de julgamento na seção 3.4.x")
            for clausula in clausulas_julgamento_3_4:
                print(f"   ✅ 3.4.{clausula['numero']} - Linha {clausula['linha']}")
        else:
            print(f"\n❌ Nenhuma cláusula de julgamento encontrada na seção 3.4.x")
        
        # Verificar se há cláusulas de julgamento na seção 8.x (erro)
        clausulas_julgamento_8_x = []
        for i, paragraph in enumerate(doc.paragraphs):
            text = paragraph.text.strip()
            if (re.search(r'8\.\d+', text) and 
                'julgamento' in text.lower() and 
                'proposta' in text.lower()):
                clausulas_julgamento_8_x.append({
                    'linha': i + 1,
                    'texto': text[:100] + '...' if len(text) > 100 else text
                })
        
        if clausulas_julgamento_8_x:
            print(f"\n❌ ERRO: Encontradas {len(clausulas_julgamento_8_x)} cláusula(s) de julgamento na seção 8.x")
            for clausula in clausulas_julgamento_8_x:
                print(f"   ❌ Linha {clausula['linha']}: {clausula['texto']}")
        else:
            print(f"\n✅ Nenhuma cláusula de julgamento encontrada na seção 8.x (correto)")
        
        # Verificar sequência das cláusulas 3.4.x
        if clausulas_3_4:
            numeros = [c['numero'] for c in clausulas_3_4]
            numeros_ordenados = sorted(numeros)
            
            if numeros == numeros_ordenados:
                print(f"\n✅ Cláusulas 3.4.x estão em sequência correta!")
            else:
                print(f"\n⚠️ Cláusulas 3.4.x NÃO estão em sequência:")
                print(f"   Sequência atual: {numeros}")
                print(f"   Sequência esperada: {numeros_ordenados}")
        
        # Verificar base legal
        texto_completo = ""
        for paragraph in doc.paragraphs:
            texto_completo += paragraph.text + "\n"
        
        base_legal_count = len(re.findall(r'Lei\s+14\.133/2021', texto_completo))
        print(f"\n📚 Base legal Lei 14.133/2021 encontrada {base_legal_count} vezes")
        
        if base_legal_count > 0:
            print("✅ Base legal presente nas cláusulas!")
        else:
            print("❌ Base legal não encontrada!")
        
        # Resultado final
        print(f"\n🎯 RESULTADO FINAL:")
        if clausulas_julgamento_3_4 and not clausulas_julgamento_8_x:
            print("✅ SUCESSO: Cláusulas de julgamento estão na seção 3.4.x correta!")
        elif clausulas_julgamento_8_x:
            print("❌ FALHA: Cláusulas de julgamento estão na seção 8.x incorreta!")
        else:
            print("⚠️ PARCIAL: Cláusulas de julgamento não encontradas ou em local inesperado")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    teste_posicionamento_melhorado()
