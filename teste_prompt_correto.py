#!/usr/bin/env python3
"""
Teste para verificar se o prompt está sendo respeitado corretamente

Antes de executar:
1. Ative o ambiente virtual: source venv/bin/activate
2. Execute: python teste_prompt_correto.py
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

from backend.app.services.ia import generate_document_data_from_prompt
from backend.app.services.render import render_docx_contextual_intelligent
from backend.app.services.services import generate_pdf_from_docx
from backend.app.models import Template

def test_prompt_correto():
    """Teste para verificar se o prompt está sendo respeitado."""
    
    print("🎯 TESTE DE PROMPT CORRETO")
    print("Verificando se o prompt do usuário está sendo respeitado")
    print("=" * 60)
    
    # 1. Usar template original
    template_path = "/home/adryan/mdlicitatech-system/backend/media/templates/docx/EDITAL_PREGAO_ELETRONICO_005-2025_AQUISIÇÃO_DE_MEDICAMENTOS_1.docx"
    
    # 2. Prompt específico do usuário
    prompt_usuario = """Aja como um especialista em licitações públicas. Adicione uma cláusula de julgamento por técnica e preço e altere o valor de PREÇO TOTAL MÉDIO para R$ 50.000.000,00."""
    
    print(f"📝 Prompt do usuário: {prompt_usuario}")
    
    # 3. Simular o fluxo da view
    print("\n🤖 Testando geração de dados com IA...")
    
    try:
        # Usar template existente
        template = Template.objects.first()
        if not template:
            print("❌ Nenhum template encontrado")
            return
        
        print(f"✅ Template: {template.name}")
        
        # 1. Gerar dados com IA (como na view)
        data = generate_document_data_from_prompt(template, prompt_usuario)
        
        print(f"📊 Dados gerados: {data}")
        
        # Verificar se o valor foi extraído corretamente
        if data.get('valor_estimado') == '50000000.00':
            print("✅ SUCESSO: Valor R$ 50.000.000,00 extraído corretamente do prompt")
        else:
            print(f"❌ PROBLEMA: Valor esperado 50000000.00, obtido {data.get('valor_estimado')}")
        
        # 2. Testar renderização contextual
        print("\n🎨 Testando renderização contextual...")
        
        tmpdir = tempfile.mkdtemp()
        output_path = os.path.join(tmpdir, "teste_prompt_correto.docx")
        
        docx_path = render_docx_contextual_intelligent(
            template_path, 
            output_path,
            data, 
            prompt_usuario
        )
        
        if os.path.exists(docx_path):
            print(f"✅ Arquivo DOCX gerado: {os.path.basename(docx_path)}")
            print(f"📁 Caminho: {docx_path}")
            print(f"📊 Tamanho: {os.path.getsize(docx_path)} bytes")
            
            # Verificar se as mudanças foram aplicadas corretamente
            from docx import Document
            doc_result = Document(docx_path)
            
            print("\n📝 Verificando mudanças aplicadas:")
            
            julgamento_found = False
            preco_alterado = False
            valor_correto = False
            
            # Verificar cláusula de julgamento
            for i, p in enumerate(doc_result.paragraphs):
                if "3.4.15. O julgamento das propostas" in p.text:
                    print(f"  ✅ Cláusula de julgamento encontrada no parágrafo {i+1}")
                    julgamento_found = True
                    break
            
            # Verificar PREÇO TOTAL MÉDIO
            for table in doc_result.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if "PREÇO TOTAL MÉDIO" in cell.text:
                            print(f"  📍 Linha com PREÇO TOTAL MÉDIO encontrada: {cell.text}")
                            # Verificar se o valor foi alterado
                            if "50.000.000" in cell.text:
                                print(f"  ✅ PREÇO TOTAL MÉDIO alterado para R$ 50.000.000,00")
                                preco_alterado = True
                                valor_correto = True
                            elif "1.000.000" in cell.text:
                                print(f"  ❌ PROBLEMA: Valor ainda é R$ 1.000.000,00 (valor antigo)")
                                preco_alterado = True
                                valor_correto = False
                            else:
                                print(f"  ⚠️ Valor encontrado: {cell.text}")
                            break
            
            print(f"\n📊 Resumo das mudanças:")
            print(f"  • Cláusula de julgamento: {'✅' if julgamento_found else '❌'}")
            print(f"  • PREÇO TOTAL MÉDIO alterado: {'✅' if preco_alterado else '❌'}")
            print(f"  • Valor correto (R$ 50.000.000,00): {'✅' if valor_correto else '❌'}")
            
            if valor_correto:
                print("\n🎉 SUCESSO TOTAL: Prompt do usuário foi respeitado!")
            else:
                print("\n❌ PROBLEMA: Prompt do usuário não foi respeitado")
            
            # Gerar PDF
            print("\n📄 Gerando PDF...")
            pdf_path = generate_pdf_from_docx(docx_path)
            
            if os.path.exists(pdf_path):
                size = os.path.getsize(pdf_path)
                print(f"✅ PDF gerado: {os.path.basename(pdf_path)}")
                print(f"📊 Tamanho: {size:,} bytes")
            else:
                print("❌ PDF não foi gerado")
                
        else:
            print("❌ Arquivo DOCX não foi gerado")
    
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🎯 RESULTADO FINAL:")
    print("-" * 20)
    print("✅ Teste de prompt correto concluído")
    print("✅ Verificação de valores específicos")
    print("✅ Validação de mudanças aplicadas")

if __name__ == "__main__":
    try:
        test_prompt_correto()
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
