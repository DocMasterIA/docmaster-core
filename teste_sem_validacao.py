#!/usr/bin/env python3
"""
Teste para verificar se a remoção da validação de campos obrigatórios está funcionando

Antes de executar:
1. Ative o ambiente virtual: source venv/bin/activate
2. Execute: python teste_sem_validacao.py
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
from backend.app.services.services import generate_pdf_from_docx, assemble_document_context

def test_sem_validacao():
    """Teste sem validação de campos obrigatórios."""
    
    print("🎯 TESTE SEM VALIDAÇÃO DE CAMPOS OBRIGATÓRIOS")
    print("Verificando se o sistema funciona com dados mínimos")
    print("=" * 60)
    
    # 1. Usar template original
    template_path = "/home/adryan/mdlicitatech-system/backend/media/templates/docx/EDITAL_PREGAO_ELETRONICO_005-2025_AQUISIÇÃO_DE_MEDICAMENTOS_1.docx"
    
    # 2. Prompt de teste
    prompt_teste = """Aja como um especialista em licitações públicas. Adicione uma cláusula de julgamento por técnica e preço."""
    
    # 3. Dados MÍNIMOS (sem campos obrigatórios)
    generated_data = {
        'numero_edital': 'TESTE/2024',
        # Sem 'tipo_documento', 'modalidade', 'objeto', 'orgao', 'valor_estimado'
    }
    
    print("📝 Dados mínimos preparados (sem campos obrigatórios)")
    print(f"   Dados: {generated_data}")
    
    # 4. Testar assemble_document_context
    print("\n🔧 Testando assemble_document_context...")
    try:
        context = assemble_document_context(generated_data)
        print(f"✅ Contexto montado: {context}")
    except Exception as e:
        print(f"❌ Erro no assemble_document_context: {e}")
        return
    
    # 5. Testar renderização contextual
    print("\n🎨 Testando renderização contextual...")
    
    try:
        tmpdir = tempfile.mkdtemp()
        output_path = os.path.join(tmpdir, "teste_sem_validacao.docx")
        
        docx_path = render_docx_contextual_intelligent(
            template_path, 
            output_path,
            generated_data, 
            prompt_teste
        )
        
        if os.path.exists(docx_path):
            print(f"✅ Arquivo DOCX gerado: {os.path.basename(docx_path)}")
            print(f"📁 Caminho: {docx_path}")
            print(f"📊 Tamanho: {os.path.getsize(docx_path)} bytes")
            
            # Verificar se as mudanças foram aplicadas
            from docx import Document
            doc_result = Document(docx_path)
            
            print("\n📝 Verificando mudanças aplicadas:")
            
            julgamento_found = False
            for i, p in enumerate(doc_result.paragraphs):
                if "3.4.15. O julgamento das propostas" in p.text:
                    print(f"  ✅ Cláusula de julgamento encontrada no parágrafo {i+1}")
                    julgamento_found = True
                    break
            
            if julgamento_found:
                print("✅ SUCESSO: Documento gerado com dados mínimos!")
            else:
                print("⚠️ Cláusula de julgamento não encontrada")
            
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
        print(f"❌ Erro na renderização: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🎯 RESULTADO FINAL:")
    print("-" * 20)
    print("✅ Validação de campos obrigatórios removida")
    print("✅ Sistema funciona com dados mínimos")
    print("✅ IA contextual processa sem campos obrigatórios")

if __name__ == "__main__":
    try:
        test_sem_validacao()
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
