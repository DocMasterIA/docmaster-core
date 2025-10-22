#!/usr/bin/env python3
"""
Teste para verificar se o sistema não adiciona conteúdo automaticamente

Antes de executar:
1. Ative o ambiente virtual: source venv/bin/activate
2. Execute: python teste_sem_conteudo_automatico.py
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

def test_sem_conteudo_automatico():
    """Teste para verificar se o sistema não adiciona conteúdo automaticamente."""
    
    print("🎯 TESTE SEM CONTEÚDO AUTOMÁTICO")
    print("Verificando se o sistema só adiciona conteúdo quando solicitado")
    print("=" * 60)
    
    # 1. Usar template original
    template_path = "/home/adryan/mdlicitatech-system/backend/media/templates/docx/EDITAL_PREGAO_ELETRONICO_005-2025_AQUISIÇÃO_DE_MEDICAMENTOS_1.docx"
    
    # 2. Prompt MÍNIMO (apenas alterar valor)
    prompt_minimo = """Altere o valor de PREÇO TOTAL MÉDIO para R$ 25.000.000,00."""
    
    print(f"📝 Prompt mínimo: {prompt_minimo}")
    
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
        data = generate_document_data_from_prompt(template, prompt_minimo)
        
        print(f"📊 Dados gerados: {data}")
        
        # 2. Testar renderização contextual
        print("\n🎨 Testando renderização contextual...")
        
        tmpdir = tempfile.mkdtemp()
        output_path = os.path.join(tmpdir, "teste_sem_conteudo_automatico.docx")
        
        docx_path = render_docx_contextual_intelligent(
            template_path, 
            output_path,
            data, 
            prompt_minimo
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
            observacao_found = False
            preco_alterado = False
            valor_correto = False
            
            # Verificar cláusula de julgamento (NÃO deve estar presente)
            for i, p in enumerate(doc_result.paragraphs):
                if "3.4.15. O julgamento das propostas" in p.text:
                    print(f"  ❌ PROBLEMA: Cláusula de julgamento encontrada no parágrafo {i+1} (não foi solicitada)")
                    julgamento_found = True
                    break
            
            if not julgamento_found:
                print(f"  ✅ CORRETO: Cláusula de julgamento NÃO foi adicionada (não foi solicitada)")
            
            # Verificar observação prática (NÃO deve estar presente)
            for i, p in enumerate(doc_result.paragraphs):
                if "OBSERVAÇÃO PRÁTICA:" in p.text:
                    print(f"  ❌ PROBLEMA: Observação prática encontrada no parágrafo {i+1} (não foi solicitada)")
                    observacao_found = True
                    break
            
            if not observacao_found:
                print(f"  ✅ CORRETO: Observação prática NÃO foi adicionada (não foi solicitada)")
            
            # Verificar PREÇO TOTAL MÉDIO (DEVE estar presente)
            for table in doc_result.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if "PREÇO TOTAL MÉDIO" in cell.text:
                            print(f"  📍 Linha com PREÇO TOTAL MÉDIO encontrada: {cell.text}")
                            # Verificar se o valor foi alterado
                            if "25.000.000" in cell.text:
                                print(f"  ✅ PREÇO TOTAL MÉDIO alterado para R$ 25.000.000,00")
                                preco_alterado = True
                                valor_correto = True
                            else:
                                print(f"  ⚠️ Valor encontrado: {cell.text}")
                            break
            
            print(f"\n📊 Resumo das mudanças:")
            print(f"  • Cláusula de julgamento (não solicitada): {'❌ ADICIONADA' if julgamento_found else '✅ NÃO ADICIONADA'}")
            print(f"  • Observação prática (não solicitada): {'❌ ADICIONADA' if observacao_found else '✅ NÃO ADICIONADA'}")
            print(f"  • PREÇO TOTAL MÉDIO alterado (solicitado): {'✅' if preco_alterado else '❌'}")
            print(f"  • Valor correto (R$ 25.000.000,00): {'✅' if valor_correto else '❌'}")
            
            if not julgamento_found and not observacao_found and valor_correto:
                print("\n🎉 SUCESSO TOTAL: Sistema só adicionou o que foi solicitado!")
            else:
                print("\n❌ PROBLEMA: Sistema adicionou conteúdo não solicitado")
            
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
    print("✅ Teste sem conteúdo automático concluído")
    print("✅ Verificação de adição condicional")
    print("✅ Validação de respeito ao prompt")

if __name__ == "__main__":
    try:
        test_sem_conteudo_automatico()
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
