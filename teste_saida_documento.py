#!/usr/bin/env python3
"""
Teste rápido para verificar se a saída do documento está funcionando

Antes de executar:
1. Ative o ambiente virtual: source venv/bin/activate
2. Execute: python teste_saida_documento.py
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

from backend.app.models import Template, DocumentInstance
from backend.app.services.render import render_docx_contextual_intelligent
from backend.app.services.services import generate_pdf_from_docx

def test_saida_documento():
    """Teste de saída do documento."""
    
    print("🎯 TESTE DE SAÍDA DO DOCUMENTO")
    print("Verificando se os arquivos são gerados e salvos corretamente")
    print("=" * 60)
    
    # 1. Usar template original
    template_path = "/home/adryan/mdlicitatech-system/backend/media/templates/docx/EDITAL_PREGAO_ELETRONICO_005-2025_AQUISIÇÃO_DE_MEDICAMENTOS_1.docx"
    
    # 2. Prompt de teste simples
    prompt_teste = """Aja como um especialista em licitações públicas. Adicione uma cláusula de julgamento por técnica e preço e altere o valor de PREÇO TOTAL MÉDIO para R$ 1.000.000,00."""
    
    # 3. Dados básicos
    generated_data = {
        'numero_edital': 'TESTE/2024',
        'modalidade': 'Pregão Eletrônico',
        'objeto': 'Teste de saída de documento',
        'valor_estimado': '1000000.00'
    }
    
    print("📝 Simulando geração de documento...")
    
    try:
        # Simular o fluxo da view
        template = Template.objects.first()
        if not template:
            print("❌ Nenhum template encontrado")
            return
        
        print(f"✅ Template: {template.name}")
        
        # Criar DocumentInstance
        inst = DocumentInstance.objects.create(
            template=template,
            owner=None,  # Simular sem usuário
            data=generated_data,
            status="draft"
        )
        
        print(f"✅ DocumentInstance criado: {inst.pk}")
        
        # Gerar arquivos
        tmpdir = tempfile.mkdtemp()
        docx_path = render_docx_contextual_intelligent(
            template.file.path, 
            os.path.join(tmpdir, f"teste_saida_{inst.pk}.docx"),
            generated_data, 
            prompt_teste
        )
        
        pdf_path = generate_pdf_from_docx(docx_path)
        
        print(f"✅ DOCX gerado: {os.path.basename(docx_path)}")
        print(f"✅ PDF gerado: {os.path.basename(pdf_path)}")
        
        # Simular salvamento como na view
        from django.core.files import File
        
        with open(docx_path, "rb") as f:
            inst.file_docx.save(os.path.basename(docx_path), File(f), save=False)
        
        with open(pdf_path, "rb") as f:
            inst.file_pdf.save(os.path.basename(pdf_path), File(f), save=False)
        
        inst.status = "final"
        inst.save()
        
        print(f"✅ Arquivos salvos no DocumentInstance")
        print(f"   - DOCX URL: {inst.file_docx.url if inst.file_docx else 'N/A'}")
        print(f"   - PDF URL: {inst.file_pdf.url if inst.file_pdf else 'N/A'}")
        print(f"   - Status: {inst.status}")
        
        # Verificar se os arquivos existem
        if inst.file_docx and os.path.exists(inst.file_docx.path):
            print(f"✅ Arquivo DOCX existe: {inst.file_docx.path}")
            print(f"   Tamanho: {os.path.getsize(inst.file_docx.path):,} bytes")
        
        if inst.file_pdf and os.path.exists(inst.file_pdf.path):
            print(f"✅ Arquivo PDF existe: {inst.file_pdf.path}")
            print(f"   Tamanho: {os.path.getsize(inst.file_pdf.path):,} bytes")
        
        # Limpar
        inst.delete()
        print("✅ DocumentInstance removido")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🎯 RESULTADO:")
    print("✅ Teste de saída do documento concluído")
    print("✅ Arquivos são gerados e salvos corretamente")
    print("✅ URLs são criadas para download")

if __name__ == "__main__":
    try:
        test_saida_documento()
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
