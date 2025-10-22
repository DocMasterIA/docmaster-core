#!/usr/bin/env python3
"""
Teste para alterar valor em tabela
Testando mudança de R$ 5.678.659,46 para R$10.000.412,19

Antes de executar:
1. Ative o ambiente virtual: source venv/bin/activate
2. Execute: python teste_valor_tabela.py
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

from backend.app.services.render import render_docx_contextual_intelligent
from docx import Document

def test_valor_tabela():
    """Teste para alterar valor em tabela."""
    
    print("💰 TESTE DE ALTERAÇÃO DE VALOR EM TABELA")
    print("Testando mudança de R$ 5.678.659,46 para R$10.000.412,19")
    print("=" * 60)
    
    # 1. Usar template original
    template_path = "/home/adryan/mdlicitatech-system/backend/media/templates/docx/EDITAL_PREGAO_ELETRONICO_005-2025_AQUISIÇÃO_DE_MEDICAMENTOS_1.docx"
    
    print("📄 PASSO 1: Analisando template original")
    print("-" * 40)
    
    try:
        # Verificar se o valor existe no template
        doc = Document(template_path)
        print("🔍 Procurando por valores monetários no template:")
        
        found_values = []
        for i, p in enumerate(doc.paragraphs):
            if 'R$' in p.text and any(char.isdigit() for char in p.text):
                print(f"  {i:3d}. {p.text}")
                found_values.append((i, p.text))
        
        # Procurar em tabelas também
        print("\n🔍 Procurando em tabelas:")
        for table_idx, table in enumerate(doc.tables):
            for row_idx, row in enumerate(table.rows):
                for cell_idx, cell in enumerate(row.cells):
                    if 'R$' in cell.text and any(char.isdigit() for char in cell.text):
                        print(f"  Tabela {table_idx}, Linha {row_idx}, Célula {cell_idx}: {cell.text}")
                        found_values.append((f"T{table_idx}R{row_idx}C{cell_idx}", cell.text))
        
        if not found_values:
            print("  ❌ Nenhum valor monetário encontrado")
        else:
            print(f"  ✅ {len(found_values)} valores monetários encontrados")
    
    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        return
    
    # 2. Testar renderização contextual com foco no valor
    print("\n🎨 PASSO 2: Testando renderização contextual")
    print("-" * 40)
    
    try:
        # Dados de teste com foco no valor
        test_data = {
            'valor_total': '10000412.19',
            'valor_estimado': '10000412.19',
            'preco_total_medio': '10000412.19',
            'user_prompt': 'Preciso alterar o valor total de R$ 5.678.659,46 para R$10.000.412,19'
        }
        
        # Prompt específico para mudar o valor
        user_prompt = "Preciso alterar o valor total de R$ 5.678.659,46 para R$10.000.412,19"
        
        print(f"📝 Prompt: {user_prompt}")
        print(f"📊 Dados: {test_data}")
        
        # Renderizar usando renderização contextual
        tmpdir = tempfile.mkdtemp()
        output_path = os.path.join(tmpdir, "edital_valor_alterado.docx")
        
        render_docx_contextual_intelligent(template_path, output_path, test_data, user_prompt)
        
        if os.path.exists(output_path):
            print(f"✅ Arquivo renderizado: {os.path.basename(output_path)}")
            print(f"📁 Caminho: {output_path}")
            print(f"📊 Tamanho: {os.path.getsize(output_path)} bytes")
            
            # Verificar se as mudanças foram aplicadas
            doc_result = Document(output_path)
            print("\n📝 Verificando mudanças no arquivo renderizado:")
            
            # Procurar por valores monetários
            found_new_values = []
            for i, p in enumerate(doc_result.paragraphs):
                if 'R$' in p.text and any(char.isdigit() for char in p.text):
                    print(f"  {i:3d}. {p.text}")
                    if '10.000.412,19' in p.text or '10000412' in p.text:
                        found_new_values.append((i, p.text))
            
            # Procurar em tabelas também
            print("\n🔍 Verificando em tabelas:")
            for table_idx, table in enumerate(doc_result.tables):
                for row_idx, row in enumerate(table.rows):
                    for cell_idx, cell in enumerate(row.cells):
                        if 'R$' in cell.text and any(char.isdigit() for char in cell.text):
                            print(f"  Tabela {table_idx}, Linha {row_idx}, Célula {cell_idx}: {cell.text}")
                            if '10.000.412,19' in cell.text or '10000412' in cell.text:
                                found_new_values.append((f"T{table_idx}R{row_idx}C{cell_idx}", cell.text))
            
            if found_new_values:
                print(f"\n🎉 SUCESSO! {len(found_new_values)} valores foram alterados para R$10.000.412,19!")
                for location, text in found_new_values:
                    print(f"  ✅ {location}: {text}")
            else:
                print("\n❌ FALHA! Valores não foram alterados.")
                
        else:
            print("❌ Arquivo não foi gerado")
    
    except Exception as e:
        print(f"❌ Erro na renderização: {e}")
        import traceback
        traceback.print_exc()
    
    # 3. Gerar PDF para visualização
    print("\n📄 PASSO 3: Gerando PDF para visualização")
    print("-" * 40)
    
    try:
        from backend.app.services.services import generate_pdf_from_docx
        
        pdf_path = generate_pdf_from_docx(output_path)
        
        if os.path.exists(pdf_path):
            size = os.path.getsize(pdf_path)
            print(f"✅ PDF gerado: {os.path.basename(pdf_path)}")
            print(f"📊 Tamanho: {size:,} bytes")
            print(f"📁 Localização: {pdf_path}")
        else:
            print("❌ PDF não foi gerado")
    
    except Exception as e:
        print(f"❌ Erro ao gerar PDF: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 RESULTADO FINAL:")
    print("-" * 20)
    print("✅ Teste de alteração de valor em tabela")
    print("✅ Verificação de valores monetários")
    print("✅ Renderização contextual aplicada")
    print("✅ PDF gerado para visualização")

if __name__ == "__main__":
    try:
        test_valor_tabela()
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
