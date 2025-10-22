#!/usr/bin/env python3
"""
Debug da renderização de documentos - investigar problema

Antes de executar:
1. Ative o ambiente virtual: source venv/bin/activate
2. Execute: python debug_renderizacao.py
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

from backend.app.services.services import extract_docx_structure
from backend.app.services.render import render_docx_from_template, render_docx_by_index, render_docx_with_tokens
from docx import Document

def debug_renderizacao():
    """Debug da renderização de documentos."""
    
    print("🔍 DEBUG DA RENDERIZAÇÃO DE DOCUMENTOS")
    print("=" * 60)
    
    # 1. Analisar template original
    template_path = "/home/adryan/mdlicitatech-system/backend/media/templates/docx/EDITAL_PREGAO_ELETRONICO_005-2025_AQUISIÇÃO_DE_MEDICAMENTOS_1.docx"
    
    print("📄 PASSO 1: Analisando template original")
    print("-" * 40)
    
    try:
        # Extrair estrutura
        doc_structure = extract_docx_structure(template_path)
        print(f"✅ Estrutura extraída: {doc_structure['n_blocks']} blocos")
        
        # Mostrar blocos com possíveis campos
        print("\n🔍 Blocos com possíveis campos de preenchimento:")
        for i, block in enumerate(doc_structure['blocks'][:15]):
            text = block['text']
            if any(marker in text for marker in ['{{', '}}', '____', 'N.º', 'Nº', 'N°']):
                print(f"  {i:3d}. [{block['type']:8s}] {text[:80]}...")
        
    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        return
    
    # 2. Testar diferentes métodos de renderização
    print("\n🎨 PASSO 2: Testando métodos de renderização")
    print("-" * 40)
    
    # Dados de teste
    test_data = {
        "numero_edital": "014/2025",
        "numero_pregao": "005/2025", 
        "objeto": "Aquisição de medicamentos básicos para farmácia municipal",
        "modalidade": "Pregão Eletrônico",
        "tipo_julgamento": "Menor Preço por Item",
        "data_abertura": "15/03/2025",
        "orgao": "Prefeitura Municipal de Exemplo",
        "base_legal": "Lei Federal nº 14.133/2021"
    }
    
    print("📊 Dados de teste:")
    for key, value in test_data.items():
        print(f"  • {key}: {value}")
    
    # Teste 1: render_docx_from_template (docxtpl)
    print("\n🧪 Teste 1: render_docx_from_template (docxtpl)")
    try:
        tmpdir = tempfile.mkdtemp()
        output_path = render_docx_from_template(template_path, test_data, dest_dir=tmpdir)
        
        if os.path.exists(output_path):
            print(f"✅ Arquivo gerado: {os.path.basename(output_path)}")
            print(f"📁 Caminho: {output_path}")
            print(f"📊 Tamanho: {os.path.getsize(output_path)} bytes")
            
            # Verificar se o conteúdo foi alterado
            doc = Document(output_path)
            print("\n📝 Primeiros parágrafos do arquivo gerado:")
            for i, p in enumerate(doc.paragraphs[:10]):
                if p.text.strip():
                    print(f"  {i:2d}. {p.text[:80]}...")
        else:
            print("❌ Arquivo não foi gerado")
    
    except Exception as e:
        print(f"❌ Erro no teste 1: {e}")
        import traceback
        traceback.print_exc()
    
    # Teste 2: render_docx_with_tokens (docxtpl com tokens)
    print("\n🧪 Teste 2: render_docx_with_tokens (docxtpl com tokens)")
    try:
        tmpdir = tempfile.mkdtemp()
        output_path = os.path.join(tmpdir, "teste_tokens.docx")
        render_docx_with_tokens(template_path, output_path, test_data)
        
        if os.path.exists(output_path):
            print(f"✅ Arquivo gerado: {os.path.basename(output_path)}")
            print(f"📁 Caminho: {output_path}")
            print(f"📊 Tamanho: {os.path.getsize(output_path)} bytes")
            
            # Verificar se o conteúdo foi alterado
            doc = Document(output_path)
            print("\n📝 Primeiros parágrafos do arquivo gerado:")
            for i, p in enumerate(doc.paragraphs[:10]):
                if p.text.strip():
                    print(f"  {i:2d}. {p.text[:80]}...")
        else:
            print("❌ Arquivo não foi gerado")
    
    except Exception as e:
        print(f"❌ Erro no teste 2: {e}")
        import traceback
        traceback.print_exc()
    
    # Teste 3: Verificar se o template tem tokens {{ }}
    print("\n🔍 Teste 3: Verificando tokens no template original")
    try:
        doc = Document(template_path)
        print("📝 Procurando por tokens {{ }} no template:")
        
        found_tokens = False
        for i, p in enumerate(doc.paragraphs[:20]):
            if '{{' in p.text and '}}' in p.text:
                print(f"  {i:2d}. {p.text}")
                found_tokens = True
        
        if not found_tokens:
            print("  ❌ Nenhum token {{ }} encontrado no template")
            print("  💡 O template pode não estar preparado para renderização com docxtpl")
        else:
            print("  ✅ Tokens encontrados - template compatível com docxtpl")
    
    except Exception as e:
        print(f"❌ Erro no teste 3: {e}")
    
    # Teste 4: Verificar se há campos com ____ ou espaços para preenchimento
    print("\n🔍 Teste 4: Verificando campos com ____ no template")
    try:
        doc = Document(template_path)
        print("📝 Procurando por campos com ____ no template:")
        
        found_underscores = False
        for i, p in enumerate(doc.paragraphs[:20]):
            if '____' in p.text or 'N.º' in p.text or 'Nº' in p.text:
                print(f"  {i:2d}. {p.text}")
                found_underscores = True
        
        if not found_underscores:
            print("  ❌ Nenhum campo com ____ encontrado")
        else:
            print("  ✅ Campos com ____ encontrados - pode precisar de renderização manual")
    
    except Exception as e:
        print(f"❌ Erro no teste 4: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 DIAGNÓSTICO:")
    print("-" * 20)
    print("1. Verificar se o template tem tokens {{ }}")
    print("2. Verificar se o template tem campos com ____")
    print("3. Testar diferentes métodos de renderização")
    print("4. Identificar o método correto para este template")

if __name__ == "__main__":
    try:
        debug_renderizacao()
    except Exception as e:
        print(f"❌ Erro no debug: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
