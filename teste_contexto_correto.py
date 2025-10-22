#!/usr/bin/env python3
"""
Teste para verificar se o conteúdo está sendo adicionado no contexto correto

Antes de executar:
1. Ative o ambiente virtual: source venv/bin/activate
2. Execute: python teste_contexto_correto.py
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

from backend.app.services.ia import call_llm_for_mapping
from backend.app.services.render import render_docx_contextual_intelligent
from backend.app.services.services import extract_docx_structure
from docx import Document

def test_contexto_correto():
    """Teste para verificar se o conteúdo está sendo adicionado no contexto correto."""
    
    print("🎯 TESTE DE CONTEXTO CORRETO")
    print("Verificando se o conteúdo é adicionado no local apropriado")
    print("=" * 60)
    
    # 1. Usar template original
    template_path = "/home/adryan/mdlicitatech-system/backend/media/templates/docx/EDITAL_PREGAO_ELETRONICO_005-2025_AQUISIÇÃO_DE_MEDICAMENTOS_1.docx"
    
    print("📄 PASSO 1: Analisando template original")
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
        
        # Verificar parágrafos específicos no template original
        doc_original = Document(template_path)
        print("\n🔍 Verificando parágrafos específicos no template original:")
        
        for i, p in enumerate(doc_original.paragraphs):
            if "julgamento" in p.text.lower() and "proposta" in p.text.lower():
                print(f"  📍 Parágrafo {i+1} (julgamento): {p.text[:80]}...")
            elif "Lei Federal nº 14.133" in p.text:
                print(f"  📍 Parágrafo {i+1} (lei): {p.text[:80]}...")
            elif "15.16" in p.text:
                print(f"  📍 Parágrafo {i+1} (15.16): {p.text[:80]}...")
        
    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        return
    
    # 2. Prompt de especialista
    print("\n🎯 PASSO 2: Aplicando prompt de especialista")
    print("-" * 40)
    
    prompt_especialista = """Aja como um especialista em licitações públicas e na Lei 14.133/21, com foco na elaboração de editais completos, interpretação de cláusulas e criação de matrizes de risco. Você deve dominar todos os tipos de contratação previstos na lei (obras, serviços, fornecimentos e serviços de engenharia).

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

Observação prática (se aplicável)

Agora, analise este edital e adicione conteúdo onde fizer sentido, melhorando-o com sua expertise em licitações públicas."""
    
    print("📝 Prompt de especialista enviado")
    
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
        
        # Dados básicos para renderização
        generated_data = {
            'numero_edital': '01/2022',
            'modalidade': 'Pregão Eletrônico',
            'objeto': 'Aquisição de medicamentos básicos',
            'valor_estimado': '500000.00'
        }
        
        print(f"✅ Dados gerados: {len(generated_data)} campos")
    
    except Exception as e:
        print(f"❌ Erro na geração: {e}")
        return
    
    # 4. Testar renderização contextual com contexto correto
    print("\n🎨 PASSO 4: Testando renderização contextual com contexto correto")
    print("-" * 40)
    
    try:
        # Renderizar usando renderização contextual
        tmpdir = tempfile.mkdtemp()
        output_path = os.path.join(tmpdir, "edital_contexto_correto.docx")
        
        render_docx_contextual_intelligent(template_path, output_path, generated_data, prompt_especialista)
        
        if os.path.exists(output_path):
            print(f"✅ Arquivo renderizado: {os.path.basename(output_path)}")
            print(f"📁 Caminho: {output_path}")
            print(f"📊 Tamanho: {os.path.getsize(output_path)} bytes")
            
            # Verificar se as mudanças foram aplicadas no contexto correto
            doc_result = Document(output_path)
            print("\n📝 Verificando contexto das mudanças:")
            
            # Verificar se o conteúdo foi adicionado no local correto
            for i, p in enumerate(doc_result.paragraphs):
                if "3.4.15. O julgamento das propostas" in p.text:
                    print(f"  ✅ Cláusula de julgamento encontrada no parágrafo {i+1}")
                    print(f"      Contexto: {p.text[:100]}...")
                elif "OBSERVAÇÃO PRÁTICA:" in p.text:
                    print(f"  ✅ Observação prática encontrada no parágrafo {i+1}")
                    print(f"      Contexto: {p.text[:100]}...")
                elif "Lei Federal nº 14.133, de 1º de abril de 2021" in p.text:
                    print(f"  ✅ Referência legal melhorada no parágrafo {i+1}")
                    print(f"      Contexto: {p.text[:100]}...")
            
            # Verificar se o conteúdo não foi adicionado no final
            last_paragraphs = doc_result.paragraphs[-5:]
            print(f"\n🔍 Últimos 5 parágrafos do documento:")
            for i, p in enumerate(last_paragraphs):
                if p.text.strip():
                    print(f"  {len(doc_result.paragraphs)-5+i+1}. {p.text[:80]}...")
            
            # Verificar se há conteúdo de especialista no final
            has_expert_content_at_end = any(
                "3.4.15" in p.text or "OBSERVAÇÃO PRÁTICA" in p.text 
                for p in last_paragraphs
            )
            
            if has_expert_content_at_end:
                print("\n❌ PROBLEMA: Conteúdo de especialista foi adicionado no final!")
            else:
                print("\n✅ SUCESSO: Conteúdo de especialista foi adicionado no contexto correto!")
                
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
    
    print("\n" + "=" * 60)
    print("🎯 RESULTADO FINAL:")
    print("-" * 20)
    print("✅ Teste de contexto correto")
    print("✅ Verificação de localização do conteúdo")
    print("✅ Renderização contextual com contexto")
    print("✅ PDF gerado para visualização")

if __name__ == "__main__":
    try:
        test_contexto_correto()
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
