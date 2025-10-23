#!/usr/bin/env python3
"""
Debug para investigar por que valor e data não estão sendo detectados
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

def debug_valor_data():
    """Debug para investigar problemas com valor e data."""
    
    print("🔍 DEBUG - VALOR E DATA")
    print("=" * 50)
    
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
    print("🤖 Gerando dados estruturados...")
    data = generate_document_data_from_prompt(template, prompt)
    
    print("📊 Dados extraídos:")
    for key, value in data.items():
        if key != 'user_prompt':
            print(f"   • {key}: {value}")
    print()
    
    # 4. Renderizar documento
    print("🎨 Renderizando documento...")
    tmpdir = tempfile.gettempdir()
    output_path = os.path.join(tmpdir, f"debug_valor_data_{template.id}.docx")
    
    render_docx_contextual_intelligent(
        template_path=template.file.path,
        output_path=output_path,
        values=data,
        user_prompt=prompt
    )
    
    print(f"✅ Documento gerado: {output_path}")
    print()
    
    # 5. Análise detalhada do documento
    print("🔍 Análise detalhada do documento...")
    doc = Document(output_path)
    
    # Coletar todo o texto
    texto_completo = ""
    for paragraph in doc.paragraphs:
        texto_completo += paragraph.text + "\n"
    
    # Procurar por valores monetários
    print("💰 Procurando valores monetários:")
    valor_patterns = [
        r'R\$\s*[\d.,]+',
        r'1\.500\.000',
        r'1,500,000',
        r'1500000',
        r'R\$\s*1\.500\.000,00',
        r'R\$\s*1,500,000.00'
    ]
    
    for i, pattern in enumerate(valor_patterns, 1):
        matches = re.findall(pattern, texto_completo)
        print(f"   {i}. Padrão '{pattern}': {len(matches)} encontrados")
        if matches:
            for match in matches[:3]:  # Mostrar apenas os primeiros 3
                print(f"      - {match}")
    
    print()
    
    # Procurar por datas
    print("📅 Procurando datas:")
    data_patterns = [
        r'\d{1,2}/\d{1,2}/\d{4}',
        r'30/11/2024',
        r'30/11',
        r'novembro.*2024',
        r'30.*novembro.*2024'
    ]
    
    for i, pattern in enumerate(data_patterns, 1):
        matches = re.findall(pattern, texto_completo, re.IGNORECASE)
        print(f"   {i}. Padrão '{pattern}': {len(matches)} encontrados")
        if matches:
            for match in matches[:3]:  # Mostrar apenas os primeiros 3
                print(f"      - {match}")
    
    print()
    
    # Procurar por valores em tabelas
    print("📊 Procurando valores em tabelas:")
    for table_idx, table in enumerate(doc.tables):
        print(f"   Tabela {table_idx}:")
        for row_idx, row in enumerate(table.rows):
            for cell_idx, cell in enumerate(row.cells):
                cell_text = cell.text
                if 'R$' in cell_text or any(char.isdigit() for char in cell_text):
                    print(f"      Linha {row_idx}, Célula {cell_idx}: {cell_text}")
    
    print()
    
    # Procurar por datas em tabelas
    print("📅 Procurando datas em tabelas:")
    for table_idx, table in enumerate(doc.tables):
        print(f"   Tabela {table_idx}:")
        for row_idx, row in enumerate(table.rows):
            for cell_idx, cell in enumerate(row.cells):
                cell_text = cell.text
                if re.search(r'\d{1,2}/\d{1,2}/\d{4}', cell_text):
                    print(f"      Linha {row_idx}, Célula {cell_idx}: {cell_text}")
    
    print()
    
    # Mostrar trechos relevantes do texto
    print("📝 Trechos relevantes do documento:")
    linhas = texto_completo.split('\n')
    for i, linha in enumerate(linhas):
        if 'R$' in linha or '30/11' in linha or '1.500' in linha:
            print(f"   Linha {i+1}: {linha.strip()}")

if __name__ == "__main__":
    debug_valor_data()
