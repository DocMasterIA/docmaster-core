#!/usr/bin/env python3
"""
Teste da renderização corrigida usando estratégia de índice

Antes de executar:
1. Ative o ambiente virtual: source venv/bin/activate
2. Execute: python test_renderizacao_corrigida.py
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

from backend.app.services.ia import call_llm_for_mapping, generate_document_data_from_prompt
from backend.app.services.services import extract_docx_structure, validate_mapping_response, save_template_schema
from backend.app.services.render import render_docx_by_index
from backend.app.models import Template, DocumentInstance, User
from django.core.files import File
from django.core.files.uploadedfile import SimpleUploadedFile

def test_renderizacao_corrigida():
    """Teste da renderização corrigida."""
    
    print("🔧 TESTE DA RENDERIZAÇÃO CORRIGIDA")
    print("Usando estratégia de índice para substituir texto")
    print("=" * 60)
    
    # 1. Usar template real
    template_path = "/home/adryan/mdlicitatech-system/backend/media/templates/docx/EDITAL_PREGAO_ELETRONICO_005-2025_AQUISIÇÃO_DE_MEDICAMENTOS_1.docx"
    
    print("📄 PASSO 1: Analisando template")
    print("-" * 40)
    
    try:
        # Extrair estrutura
        doc_structure = extract_docx_structure(template_path)
        print(f"✅ Estrutura extraída: {doc_structure['n_blocks']} blocos")
        
        # IA analisa e identifica campos
        mapping = call_llm_for_mapping(
            doc_structure=doc_structure,
            user_instructions="Analise este edital e identifique campos de preenchimento",
            llm_api_key=None
        )
        
        print(f"✅ IA analisou: {len(mapping.get('fields', []))} campos detectados")
        
        # Mostrar campos identificados
        if mapping.get('fields'):
            print("\n🔍 Campos identificados:")
            for i, field in enumerate(mapping['fields'], 1):
                print(f"  {i:2d}. {field.get('key', 'N/A'):20s} - Blocos: {field.get('block_indices', [])}")
                print(f"      Texto atual: {field.get('text', 'N/A')[:60]}...")
        
    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        return
    
    # 2. Gerar dados com IA
    print("\n🤖 PASSO 2: Gerando dados com IA")
    print("-" * 40)
    
    try:
        # Criar template object
        class MockTemplate:
            def __init__(self, name, mapping_result):
                self.name = name
                self.schema = type('obj', (object,), {
                    'schema': {
                        'fields': mapping_result.get('fields', [])
                    }
                })()
        
        template_obj = MockTemplate("Template Teste", mapping)
        
        # Prompt do usuário
        user_prompt = "Preciso de um edital de pregão eletrônico para aquisição de medicamentos básicos. Valor R$ 150.000, prazo 90 dias."
        
        # Gerar dados
        generated_data = generate_document_data_from_prompt(
            template=template_obj,
            user_prompt=user_prompt,
            llm_api_key=None
        )
        
        if "error" in generated_data:
            print(f"❌ Erro na geração: {generated_data['error']}")
            return
        
        print(f"✅ Dados gerados: {len(generated_data)} campos")
        print("\n📊 Dados principais:")
        for key, value in list(generated_data.items())[:6]:
            print(f"  • {key}: {value}")
    
    except Exception as e:
        print(f"❌ Erro na geração: {e}")
        return
    
    # 3. Testar renderização com estratégia de índice
    print("\n🎨 PASSO 3: Testando renderização com estratégia de índice")
    print("-" * 40)
    
    try:
        # Preparar dados para renderização
        render_data = {}
        for field in mapping.get('fields', []):
            key = field['key']
            if key in generated_data:
                render_data[key] = generated_data[key]
            else:
                render_data[key] = f"[{key.upper()}]"  # Placeholder se não tiver dados
        
        print("📊 Dados para renderização:")
        for key, value in render_data.items():
            print(f"  • {key}: {value}")
        
        # Renderizar usando estratégia de índice
        tmpdir = tempfile.mkdtemp()
        output_path = os.path.join(tmpdir, "edital_renderizado.docx")
        
        print(f"\n🔧 Renderizando com estratégia de índice...")
        render_docx_by_index(template_path, output_path, mapping, render_data)
        
        if os.path.exists(output_path):
            print(f"✅ Arquivo renderizado: {os.path.basename(output_path)}")
            print(f"📁 Caminho: {output_path}")
            print(f"📊 Tamanho: {os.path.getsize(output_path)} bytes")
            
            # Verificar se as substituições foram feitas
            from docx import Document
            doc = Document(output_path)
            
            print("\n📝 Verificando substituições:")
            for i, p in enumerate(doc.paragraphs[:15]):
                if p.text.strip():
                    # Verificar se contém dados substituídos
                    text = p.text
                    if any(key in text for key in render_data.keys()):
                        print(f"  {i:2d}. ✅ {text[:80]}...")
                    else:
                        print(f"  {i:2d}. 📄 {text[:80]}...")
        else:
            print("❌ Arquivo não foi gerado")
    
    except Exception as e:
        print(f"❌ Erro na renderização: {e}")
        import traceback
        traceback.print_exc()
    
    # 4. Testar renderização melhorada
    print("\n🔧 PASSO 4: Testando renderização melhorada")
    print("-" * 40)
    
    try:
        # Criar função de renderização melhorada
        def render_docx_improved(template_path, output_path, mapping, values):
            """Renderização melhorada que substitui texto baseado em padrões."""
            from docx import Document
            import re
            
            doc = Document(template_path)
            
            # Mapear campos para valores
            field_map = {}
            for field in mapping.get('fields', []):
                key = field['key']
                if key in values:
                    field_map[key] = values[key]
            
            print(f"📊 Mapeamento de campos: {field_map}")
            
            # Substituir em todos os parágrafos
            for p in doc.paragraphs:
                original_text = p.text
                new_text = original_text
                
                # Padrões de substituição baseados no conteúdo
                if "N. 014/2025" in original_text or "N.º 014/2025" in original_text:
                    new_text = original_text.replace("014/2025", str(field_map.get('numero_edital', '014/2025')))
                elif "N. 005/2025" in original_text or "N.º 005/2025" in original_text:
                    new_text = original_text.replace("005/2025", str(field_map.get('numero_pregao', '005/2025')))
                elif "PREGÃO ELETRÔNICO" in original_text:
                    new_text = original_text.replace("PREGÃO ELETRÔNICO", str(field_map.get('modalidade', 'PREGÃO ELETRÔNICO')))
                elif "Aquisição de Medicamentos" in original_text:
                    new_text = original_text.replace("Aquisição de Medicamentos", str(field_map.get('objeto', 'Aquisição de Medicamentos')))
                
                if new_text != original_text:
                    print(f"  🔄 Substituído: {original_text[:50]}... -> {new_text[:50]}...")
                    # Limpar runs e adicionar novo texto
                    for r in list(p.runs):
                        p._p.remove(r._r)
                    p.add_run(new_text)
            
            doc.save(output_path)
            return output_path
        
        # Testar renderização melhorada
        tmpdir = tempfile.mkdtemp()
        output_path = os.path.join(tmpdir, "edital_melhorado.docx")
        
        render_docx_improved(template_path, output_path, mapping, render_data)
        
        if os.path.exists(output_path):
            print(f"✅ Arquivo melhorado: {os.path.basename(output_path)}")
            print(f"📁 Caminho: {output_path}")
            print(f"📊 Tamanho: {os.path.getsize(output_path)} bytes")
        else:
            print("❌ Arquivo melhorado não foi gerado")
    
    except Exception as e:
        print(f"❌ Erro na renderização melhorada: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🎯 CONCLUSÕES:")
    print("-" * 20)
    print("1. Template não tem tokens {{ }} - precisa de renderização manual")
    print("2. Estratégia de índice pode funcionar se os blocos estiverem corretos")
    print("3. Renderização melhorada baseada em padrões de texto é necessária")
    print("4. Precisa mapear campos para padrões específicos no template")

if __name__ == "__main__":
    try:
        test_renderizacao_corrigida()
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
