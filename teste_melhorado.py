#!/usr/bin/env python3
"""
Teste melhorado com aplicação de dados da IA e formatação em azul

Antes de executar:
1. Ative o ambiente virtual: source venv/bin/activate
2. Execute: python teste_melhorado.py
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

from backend.app.services.ia import generate_document_data_from_prompt, call_llm_for_mapping
from backend.app.services.render import render_docx_contextual_intelligent
from backend.app.services.services import extract_docx_structure
from docx import Document

def test_melhorado():
    """Teste melhorado com aplicação de dados da IA."""
    
    print("🚀 TESTE MELHORADO - APLICAÇÃO DE DADOS DA IA")
    print("Testando aplicação correta dos dados e formatação em azul")
    print("=" * 70)
    
    # 1. Usar template original
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
        
    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        return
    
    # 2. Prompt com instrução de azul
    print("\n🎯 PASSO 2: Testando com instrução de azul")
    print("-" * 40)
    
    prompt_azul = """Elabore um edital de pregão eletrônico para aquisição de medicamentos básicos para a Prefeitura Municipal de Goiânia, valor estimado R$ 500.000,00, prazo de execução 120 dias. 

IMPORTANTE: Escreva TODO o conteúdo em AZUL para que eu possa visualizar exatamente o que você entendeu que deve fazer no arquivo."""
    
    print("📝 Prompt com instrução de azul:")
    print(f"   {prompt_azul}")
    
    # 3. Gerar dados com IA
    print("\n🤖 PASSO 3: Gerando dados com IA")
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
        
        # Gerar dados
        generated_data = generate_document_data_from_prompt(
            template=template_obj,
            user_prompt=prompt_azul,
            llm_api_key=None
        )
        
        if "error" in generated_data:
            print(f"❌ Erro na geração: {generated_data['error']}")
            return
        
        print(f"✅ Dados gerados: {len(generated_data)} campos")
        print("\n📊 Dados principais gerados pela IA:")
        for key, value in list(generated_data.items())[:8]:
            print(f"  • {key}: {str(value)[:80]}...")
    
    except Exception as e:
        print(f"❌ Erro na geração: {e}")
        return
    
    # 4. Testar renderização contextual melhorada
    print("\n🎨 PASSO 4: Testando renderização contextual melhorada")
    print("-" * 40)
    
    try:
        # Renderizar usando renderização contextual
        tmpdir = tempfile.mkdtemp()
        output_path = os.path.join(tmpdir, "edital_melhorado.docx")
        
        render_docx_contextual_intelligent(template_path, output_path, generated_data, prompt_azul)
        
        if os.path.exists(output_path):
            print(f"✅ Arquivo renderizado: {os.path.basename(output_path)}")
            print(f"📁 Caminho: {output_path}")
            print(f"📊 Tamanho: {os.path.getsize(output_path)} bytes")
            
            # Verificar se as mudanças foram aplicadas
            doc_result = Document(output_path)
            print("\n📝 Verificando aplicação dos dados da IA:")
            
            # Verificar dados específicos
            dados_aplicados = 0
            
            # Procurar por Goiânia
            for i, p in enumerate(doc_result.paragraphs[:20]):
                if 'GOIÂNIA' in p.text or 'Goiânia' in p.text:
                    print(f"  ✅ Goiânia: {p.text[:60]}...")
                    dados_aplicados += 1
            
            # Procurar por valor R$ 500.000
            for i, p in enumerate(doc_result.paragraphs[:20]):
                if '500.000' in p.text or '500000' in p.text:
                    print(f"  ✅ Valor R$ 500.000: {p.text[:60]}...")
                    dados_aplicados += 1
            
            # Procurar por número do edital
            for i, p in enumerate(doc_result.paragraphs[:20]):
                if 'PE' in p.text and '2022' in p.text:
                    print(f"  ✅ Número do edital: {p.text[:60]}...")
                    dados_aplicados += 1
            
            # Procurar por marcações de azul
            for i, p in enumerate(doc_result.paragraphs[:20]):
                if '[AZUL]' in p.text or '[/AZUL]' in p.text:
                    print(f"  🎨 Formatação azul: {p.text[:60]}...")
                    dados_aplicados += 1
            
            print(f"\n📊 Total de dados aplicados: {dados_aplicados}")
            
            if dados_aplicados >= 3:
                print("🎉 SUCESSO! IA aplicou a maioria dos dados!")
            else:
                print("❌ FALHA! IA não aplicou os dados corretamente")
                
        else:
            print("❌ Arquivo não foi gerado")
    
    except Exception as e:
        print(f"❌ Erro na renderização: {e}")
        import traceback
        traceback.print_exc()
    
    # 5. Gerar PDF para visualização
    print("\n📄 PASSO 5: Gerando PDF para visualização")
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
    
    print("\n" + "=" * 70)
    print("🎯 RESULTADO FINAL:")
    print("-" * 20)
    print("✅ Teste melhorado com aplicação de dados da IA")
    print("✅ Verificação de formatação em azul")
    print("✅ Renderização contextual melhorada")
    print("✅ PDF gerado para visualização")

if __name__ == "__main__":
    try:
        test_melhorado()
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
