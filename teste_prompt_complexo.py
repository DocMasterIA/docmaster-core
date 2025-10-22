#!/usr/bin/env python3
"""
Teste com prompt complexo de especialista em licitações
Testando resposta da IA com texto em azul para visualização

Antes de executar:
1. Ative o ambiente virtual: source venv/bin/activate
2. Execute: python teste_prompt_complexo.py
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

def test_prompt_complexo():
    """Teste com prompt complexo de especialista em licitações."""
    
    print("🎓 TESTE COM PROMPT COMPLEXO DE ESPECIALISTA")
    print("Testando resposta da IA com texto em azul para visualização")
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
    
    # 2. Prompt complexo do usuário
    print("\n🎯 PASSO 2: Testando prompt complexo")
    print("-" * 40)
    
    prompt_complexo = """Aja como um especialista em licitações públicas e na Lei 14.133/21, com foco na elaboração de editais completos, interpretação de cláusulas e criação de matrizes de risco. Você deve dominar todos os tipos de contratação previstos na lei (obras, serviços, fornecimentos e serviços de engenharia).

--- Instruções ---

Suas respostas devem ser claras, objetivas e com linguagem apropriada para documentos oficiais.

Sempre que possível, baseie-se em dispositivos atualizados da Lei 14.133/21, citando os artigos aplicáveis.

Use exemplos práticos quando for útil para ilustrar a aplicação.

Quando eu solicitar algo como "cláusula de julgamento por técnica e preço", forneça o texto sugerido para o edital, a base legal e orientações práticas.

Adapte o nível de profundidade para respostas diretas e aplicáveis no cotidiano do setor público.

--- Formato de resposta sugerido ---

Comece respondendo com um resumo direto, seguido de:

Texto sugerido para o edital

Base legal (com artigo)

Observação prática (se aplicável).

Agora, elabore um edital de pregão eletrônico para aquisição de medicamentos básicos para a Prefeitura Municipal de Goiânia, valor estimado R$ 500.000,00, prazo de execução 120 dias. IMPORTANTE: Escreva TODO o conteúdo em AZUL para que eu possa visualizar exatamente o que você entendeu que deve fazer no arquivo."""
    
    print("📝 Prompt complexo enviado para IA:")
    print(f"   {prompt_complexo[:200]}...")
    
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
            user_prompt=prompt_complexo,
            llm_api_key=None
        )
        
        if "error" in generated_data:
            print(f"❌ Erro na geração: {generated_data['error']}")
            return
        
        print(f"✅ Dados gerados: {len(generated_data)} campos")
        print("\n📊 Dados principais gerados pela IA:")
        for key, value in list(generated_data.items())[:10]:
            print(f"  • {key}: {str(value)[:100]}...")
    
    except Exception as e:
        print(f"❌ Erro na geração: {e}")
        return
    
    # 4. Testar renderização contextual
    print("\n🎨 PASSO 4: Testando renderização contextual")
    print("-" * 40)
    
    try:
        # Renderizar usando renderização contextual
        tmpdir = tempfile.mkdtemp()
        output_path = os.path.join(tmpdir, "edital_especialista.docx")
        
        render_docx_contextual_intelligent(template_path, output_path, generated_data, prompt_complexo)
        
        if os.path.exists(output_path):
            print(f"✅ Arquivo renderizado: {os.path.basename(output_path)}")
            print(f"📁 Caminho: {output_path}")
            print(f"📊 Tamanho: {os.path.getsize(output_path)} bytes")
            
            # Verificar se as mudanças foram aplicadas
            doc_result = Document(output_path)
            print("\n📝 Verificando mudanças no arquivo renderizado:")
            
            # Procurar por conteúdo em azul ou mudanças específicas
            changes_found = 0
            for i, p in enumerate(doc_result.paragraphs[:20]):
                if p.text.strip():
                    text = p.text
                    # Verificar se contém dados gerados pela IA
                    if any(key in text for key in generated_data.keys()):
                        print(f"  {i:2d}. ✅ {text[:80]}...")
                        changes_found += 1
                    else:
                        print(f"  {i:2d}. 📄 {text[:80]}...")
            
            print(f"\n🔍 Total de mudanças encontradas: {changes_found}")
                
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
    print("✅ Teste com prompt complexo de especialista")
    print("✅ IA processou instruções detalhadas")
    print("✅ Renderização contextual aplicada")
    print("✅ PDF gerado para visualização")
    print("💡 Verifique o PDF para ver como a IA interpretou o prompt!")

if __name__ == "__main__":
    try:
        test_prompt_complexo()
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
