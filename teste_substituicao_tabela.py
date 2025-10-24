#!/usr/bin/env python3
"""
Teste específico da substituição em tabelas
"""

import os
import sys
import django
from pathlib import Path
import tempfile

# Add the backend directory to Python path
sys.path.append('/home/adryan/mdlicitatech-system/backend')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mdlicitatech.settings')
django.setup()

from backend.app.models import Template
from docx import Document
from docx.shared import RGBColor

def teste_substituicao_tabela():
    """Teste específico da substituição em tabelas."""
    
    print("🔍 TESTE DE SUBSTITUIÇÃO EM TABELAS")
    print("=" * 50)
    
    # 1. Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return False
    
    print(f"📄 Usando template: {template.name}")
    
    # 2. Carregar documento
    doc = Document(template.file.path)
    
    # 3. Procurar por "PREÇO TOTAL MÉDIO" e substituir valor
    print("\n🔍 Procurando por PREÇO TOTAL MÉDIO...")
    found = False
    
    for table in doc.tables:
        for row in table.rows:
            for cell_idx, cell in enumerate(row.cells):
                for paragraph in cell.paragraphs:
                    if "PREÇO TOTAL MÉDIO" in paragraph.text:
                        print(f"✅ Encontrado PREÇO TOTAL MÉDIO na célula [{cell_idx}]")
                        
                        # Procurar na célula adjacente por valor monetário
                        if cell_idx + 1 < len(row.cells):
                            next_cell = row.cells[cell_idx + 1]
                            print(f"🔍 Verificando célula adjacente...")
                            
                            for next_paragraph in next_cell.paragraphs:
                                if "R$" in next_paragraph.text and "5.678.659,46" in next_paragraph.text:
                                    print(f"✅ Encontrado valor na célula adjacente: {next_paragraph.text}")
                                    
                                    # Substituir o valor
                                    for run in next_paragraph.runs:
                                        if "5.678.659,46" in run.text:
                                            old_text = run.text
                                            run.text = run.text.replace("5.678.659,46", "7.500.000,00")
                                            run.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                                            print(f"✅ Substituído: {old_text} -> {run.text}")
                                            found = True
                                            break
                                    
                                    if found:
                                        break
                        break
                if found:
                    break
            if found:
                break
        if found:
            break
    
    if found:
        print("\n🎉 SUCESSO: Substituição em tabela funcionou!")
        
        # Salvar documento modificado
        output_path = "/tmp/teste_substituicao_tabela.docx"
        doc.save(output_path)
        print(f"📁 Documento salvo em: {output_path}")
        
        # Verificar se a substituição funcionou
        print("\n🔍 Verificando se a substituição funcionou...")
        doc_verificacao = Document(output_path)
        
        for table in doc_verificacao.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        if "7.500.000,00" in paragraph.text:
                            print(f"✅ Valor alterado confirmado: {paragraph.text}")
                            return True
        
        print("❌ Valor não foi alterado")
        return False
    else:
        print("❌ PREÇO TOTAL MÉDIO não encontrado")
        return False

if __name__ == "__main__":
    try:
        sucesso = teste_substituicao_tabela()
        if sucesso:
            print("\n🎉 TESTE CONCLUÍDO COM SUCESSO!")
        else:
            print("\n❌ TESTE FALHOU")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
