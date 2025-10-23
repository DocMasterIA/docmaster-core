#!/usr/bin/env python3
"""
Debug específico para investigar os problemas restantes
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

def debug_especifico():
    """Debug específico para investigar problemas."""
    
    print("🔍 DEBUG ESPECÍFICO - INVESTIGAÇÃO DETALHADA")
    print("=" * 60)
    
    # 1. Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado!")
        return
    
    print(f"✅ Template: {template.name}")
    print()
    
    # 2. Prompt específico
    prompt = """Aja como um especialista em licitações públicas e na Lei 14.133/2021, com foco na elaboração de editais completos, interpretação de cláusulas e criação de matrizes de risco.

INSTRUÇÕES ESPECÍFICAS:
1. Altere o valor de PREÇO TOTAL MÉDIO para R$ 1.500.000,00
2. Mude a data de abertura para 30/11/2024
3. Altere o número do edital para 456/2024
4. Mude o local de "ITAJÁ" para "BRASÍLIA"
5. Adicione uma cláusula de julgamento por técnica e preço
6. Adicione uma observação prática sobre registro de propostas
7. Altere o prazo de execução para 180 dias
8. Mude o órgão para "SECRETARIA MUNICIPAL DE SAÚDE"

OBJETIVO: Gerar um edital de pregão eletrônico para aquisição de medicamentos e insumos hospitalares, com todas as cláusulas necessárias para garantir transparência e conformidade legal."""
    
    # 3. Gerar dados
    print("🤖 Gerando dados...")
    data = generate_document_data_from_prompt(template, prompt)
    print(f"📊 Número do edital: {data.get('numero_edital')}")
    print()
    
    # 4. Renderizar documento
    print("🎨 Renderizando documento...")
    tmpdir = tempfile.gettempdir()
    output_path = os.path.join(tmpdir, f"debug_especifico_{template.id}.docx")
    
    render_docx_contextual_intelligent(
        template_path=template.file.path,
        output_path=output_path,
        values=data,
        user_prompt=prompt
    )
    
    print(f"✅ Documento gerado: {output_path}")
    print()
    
    # 5. Análise detalhada
    print("🔍 Análise detalhada do documento...")
    doc = Document(output_path)
    
    # Coletar todo o texto
    texto_completo = ""
    for paragraph in doc.paragraphs:
        texto_completo += paragraph.text + "\n"
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                texto_completo += cell.text + "\n"
    
    # Procurar por padrões específicos
    print("🔍 Procurando por padrões específicos:")
    print("-" * 40)
    
    # Padrões de referências legais
    padroes_legais = [
        (r'Lei\s+14\.133/2021', 'Lei 14.133/2021'),
        (r'Decreto\s+10\.024/19', 'Decreto 10.024/19'),
        (r'Lei\s+Complementar\s+123/2006', 'Lei Complementar 123/2006'),
        (r'art\.\s+156', 'art. 156'),
        (r'§5º', '§5º'),
    ]
    
    print("📋 Referências legais encontradas:")
    for pattern, nome in padroes_legais:
        matches = re.findall(pattern, texto_completo, re.IGNORECASE)
        status = "✅" if matches else "❌"
        print(f"   {status} {nome}: {len(matches)} encontradas")
        if matches:
            for match in matches[:2]:  # Mostrar apenas os primeiros 2
                print(f"      - {match}")
    
    print()
    
    # Padrões de alterações corretas
    padroes_alteracoes = [
        (r'456/2024', 'Número do edital 456/2024'),
        (r'30/11/2024', 'Data 30/11/2024'),
        (r'1\.500\.000', 'Valor 1.500.000'),
        (r'BRASÍLIA', 'Local BRASÍLIA'),
    ]
    
    print("📋 Alterações corretas encontradas:")
    for pattern, nome in padroes_alteracoes:
        matches = re.findall(pattern, texto_completo, re.IGNORECASE)
        status = "✅" if matches else "❌"
        print(f"   {status} {nome}: {len(matches)} encontradas")
        if matches:
            for match in matches[:2]:  # Mostrar apenas os primeiros 2
                print(f"      - {match}")
    
    print()
    
    # Padrões de substituições incorretas
    padroes_incorretos = [
        (r'Lei\s+14\.456/2024', 'Lei 14.456/2024 (INCORRETO)'),
        (r'Decreto\s+10\.456/2024', 'Decreto 10.456/2024 (INCORRETO)'),
        (r'Lei\s+Complementar\s+456/2024', 'Lei Complementar 456/2024 (INCORRETO)'),
        (r'art\.\s+456', 'art. 456 (INCORRETO)'),
    ]
    
    print("📋 Substituições incorretas encontradas:")
    for pattern, nome in padroes_incorretos:
        matches = re.findall(pattern, texto_completo, re.IGNORECASE)
        status = "❌" if matches else "✅"
        print(f"   {status} {nome}: {len(matches)} encontradas")
        if matches:
            for match in matches[:2]:  # Mostrar apenas os primeiros 2
                print(f"      - {match}")
    
    print()
    
    # Procurar por trechos específicos que podem ter problemas
    print("🔍 Trechos específicos que podem ter problemas:")
    print("-" * 40)
    
    linhas = texto_completo.split('\n')
    for i, linha in enumerate(linhas):
        if any(palavra in linha for palavra in ['Lei', 'Decreto', 'art.', '456', '133']):
            print(f"   Linha {i+1}: {linha.strip()[:100]}...")

if __name__ == "__main__":
    debug_especifico()
