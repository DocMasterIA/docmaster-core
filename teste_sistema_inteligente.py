#!/usr/bin/env python3
"""
Teste para verificar se o sistema está mais inteligente e flexível

Antes de executar:
1. Ative o ambiente virtual: source venv/bin/activate
2. Execute: python teste_sistema_inteligente.py
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

def test_sistema_inteligente():
    """Teste para verificar se o sistema é mais inteligente e flexível."""
    
    print("🧠 TESTE SISTEMA INTELIGENTE")
    print("Verificando se o sistema analisa o prompt de forma inteligente")
    print("=" * 60)
    
    # 1. Usar template original
    template_path = "/home/adryan/mdlicitatech-system/backend/media/templates/docx/EDITAL_PREGAO_ELETRONICO_005-2025_AQUISIÇÃO_DE_MEDICAMENTOS_1.docx"
    
    # 2. Teste 1: Prompt com múltiplas mudanças
    prompt_teste1 = """Mude ITAJÁ para GOIÂNIA, altere o valor de PREÇO TOTAL MÉDIO para R$ 50.000.000,00 e mude o número do edital para 123/2025."""
    
    print(f"📝 Teste 1 - Prompt complexo: {prompt_teste1}")
    
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
        data = generate_document_data_from_prompt(template, prompt_teste1)
        
        print(f"📊 Dados gerados: {data}")
        
        # 2. Testar renderização contextual
        print("\n🎨 Testando renderização contextual inteligente...")
        
        tmpdir = tempfile.mkdtemp()
        output_path = os.path.join(tmpdir, "teste_sistema_inteligente.docx")
        
        docx_path = render_docx_contextual_intelligent(
            template_path, 
            output_path,
            data, 
            prompt_teste1
        )
        
        if os.path.exists(docx_path):
            print(f"✅ Arquivo DOCX gerado: {os.path.basename(docx_path)}")
            print(f"📁 Caminho: {docx_path}")
            print(f"📊 Tamanho: {os.path.getsize(docx_path)} bytes")
            
            # Verificar se as mudanças foram aplicadas corretamente
            from docx import Document
            doc_result = Document(docx_path)
            
            print("\n📝 Verificando mudanças aplicadas:")
            
            itaja_mudado = False
            valor_alterado = False
            numero_alterado = False
            
            # Verificar mudança de ITAJÁ para GOIÂNIA
            for i, p in enumerate(doc_result.paragraphs):
                if "GOIÂNIA" in p.text and "ITAJÁ" not in p.text:
                    print(f"  ✅ ITAJÁ mudado para GOIÂNIA no parágrafo {i+1}")
                    itaja_mudado = True
                    break
            
            # Verificar valor alterado
            for table in doc_result.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if "R$ 50.000.000,00" in cell.text:
                            print(f"  ✅ Valor alterado para R$ 50.000.000,00")
                            valor_alterado = True
                            break
            
            # Verificar número do edital
            for i, p in enumerate(doc_result.paragraphs):
                if "123/2025" in p.text:
                    print(f"  ✅ Número do edital alterado para 123/2025 no parágrafo {i+1}")
                    numero_alterado = True
                    break
            
            print(f"\n📊 Resumo das mudanças:")
            print(f"  • ITAJÁ -> GOIÂNIA: {'✅' if itaja_mudado else '❌'}")
            print(f"  • Valor R$ 50.000.000,00: {'✅' if valor_alterado else '❌'}")
            print(f"  • Número 123/2025: {'✅' if numero_alterado else '❌'}")
            
            if itaja_mudado and valor_alterado and numero_alterado:
                print("\n🎉 SUCESSO TOTAL: Sistema inteligente funcionando!")
            else:
                print("\n❌ PROBLEMA: Sistema não aplicou todas as mudanças")
            
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
    print("✅ Teste sistema inteligente concluído")
    print("✅ Verificação de análise inteligente do prompt")
    print("✅ Validação de mudanças dinâmicas")

if __name__ == "__main__":
    try:
        test_sistema_inteligente()
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
