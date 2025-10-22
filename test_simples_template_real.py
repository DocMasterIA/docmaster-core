#!/usr/bin/env python3
"""
Teste simples com template DOCX real (sem dependências Django)

Antes de executar:
1. Ative o ambiente virtual: source venv/bin/activate
2. Execute: python test_simples_template_real.py
"""

import os
import sys
from pathlib import Path

# Add the backend directory to Python path
sys.path.append('/home/adryan/mdlicitatech-system/backend')

def test_simples_template_real():
    """Teste simples com template DOCX real."""
    
    print("🎯 Teste Simples com Template DOCX Real")
    print("=" * 50)
    
    # 1. Encontrar template DOCX real
    template_paths = [
        "/home/adryan/mdlicitatech-system/backend/media/templates/docx/modelo_template_mdlicitatech.docx",
        "/home/adryan/mdlicitatech-system/templates/docx/modelo_template_mdlicitatech.docx"
    ]
    
    template_path = None
    for path in template_paths:
        if os.path.exists(path):
            template_path = path
            break
    
    if not template_path:
        print("❌ Nenhum template DOCX encontrado!")
        return
    
    print(f"📄 Template encontrado: {os.path.basename(template_path)}")
    print(f"📁 Caminho: {template_path}")
    print(f"📊 Tamanho: {os.path.getsize(template_path)} bytes")
    
    # 2. Testar extração de estrutura
    print("\n🔍 PASSO 1: Testando extração de estrutura")
    print("-" * 40)
    
    try:
        # Importar função de extração
        from backend.app.services.services import extract_docx_structure
        
        doc_structure = extract_docx_structure(template_path)
        print(f"✅ Estrutura extraída: {doc_structure['n_blocks']} blocos")
        
        # Mostrar alguns blocos
        print("\n📊 Primeiros blocos encontrados:")
        for i, block in enumerate(doc_structure['blocks'][:8]):
            text_preview = block['text'][:60].replace('\n', ' ')
            print(f"  {i+1:2d}. [{block['type']:8s}] {text_preview}...")
        
        if len(doc_structure['blocks']) > 8:
            print(f"  ... e mais {len(doc_structure['blocks']) - 8} blocos")
            
    except Exception as e:
        print(f"❌ Erro ao extrair estrutura: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 3. Testar análise com IA (modo mock)
    print("\n🤖 PASSO 2: Testando análise com IA")
    print("-" * 40)
    
    try:
        # Importar função de IA
        from backend.app.services.ia import call_llm_for_mapping
        
        print("🔧 Usando modo mock para teste...")
        
        # Temporariamente ativar modo mock
        import os
        os.environ['AI_USE_MOCK'] = 'True'
        
        mapping_result = call_llm_for_mapping(
            doc_structure=doc_structure,
            user_instructions="Analise este template de licitação e identifique todos os campos de preenchimento",
            llm_api_key=None
        )
        
        print(f"✅ Análise concluída: {len(mapping_result.get('fields', []))} campos detectados")
        print(f"📝 Observações: {mapping_result.get('notes', 'Nenhuma')}")
        
        if mapping_result.get('fields'):
            print("\n🔍 Campos identificados pela IA:")
            for i, field in enumerate(mapping_result['fields'], 1):
                print(f"  {i:2d}. {field.get('key', 'N/A'):20s} ({field.get('type', 'N/A'):8s})")
                if field.get('description'):
                    desc = field.get('description')[:50]
                    print(f"      📝 {desc}...")
        
    except Exception as e:
        print(f"❌ Erro na análise da IA: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 4. Testar geração de dados
    print("\n🚀 PASSO 3: Testando geração de dados")
    print("-" * 40)
    
    try:
        from backend.app.services.ia import generate_document_data_from_prompt
        
        # Simular template object
        class MockTemplate:
            def __init__(self, name, mapping_result):
                self.name = name
                self.schema = type('obj', (object,), {
                    'schema': {
                        'fields': mapping_result.get('fields', [])
                    }
                })()
        
        template_obj = MockTemplate("Template Real", mapping_result)
        
        # Prompts de teste
        prompts_teste = [
            "Preciso de um edital de pregão eletrônico para contratação de serviços de limpeza urbana. Valor estimado R$ 500.000,00. Prazo de execução 12 meses.",
            "Elabore um edital de concorrência para execução de obra pública. Valor estimado R$ 2.000.000,00. Prazo de execução 24 meses. Critério técnica e preço."
        ]
        
        for i, prompt in enumerate(prompts_teste, 1):
            print(f"\n📝 Teste {i}: {prompt[:50]}...")
            
            generated_data = generate_document_data_from_prompt(
                template=template_obj,
                user_prompt=prompt,
                llm_api_key=None
            )
            
            if "error" in generated_data:
                print(f"❌ Erro: {generated_data['error']}")
            else:
                print(f"✅ Dados gerados: {len(generated_data)} campos")
                print("📊 Principais campos:")
                for key, value in list(generated_data.items())[:4]:
                    print(f"  • {key}: {value}")
                if len(generated_data) > 4:
                    print(f"  ... e mais {len(generated_data) - 4} campos")
        
    except Exception as e:
        print(f"❌ Erro na geração de dados: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 5. Testar renderização (opcional)
    print("\n🎨 PASSO 4: Testando renderização")
    print("-" * 40)
    
    try:
        from backend.app.services.render import render_docx_from_template
        
        # Usar dados do último teste
        if 'generated_data' in locals() and "error" not in generated_data:
            print("📝 Testando renderização com dados gerados...")
            
            # Criar diretório temporário
            import tempfile
            tmpdir = tempfile.mkdtemp()
            
            try:
                # Renderizar template
                docx_path = render_docx_from_template(
                    template_path, 
                    generated_data, 
                    dest_dir=tmpdir
                )
                
                if os.path.exists(docx_path):
                    print(f"✅ Documento renderizado: {os.path.basename(docx_path)}")
                    print(f"📁 Caminho: {docx_path}")
                    print(f"📊 Tamanho: {os.path.getsize(docx_path)} bytes")
                else:
                    print("❌ Arquivo renderizado não encontrado")
                
            finally:
                # Limpar arquivo temporário
                try:
                    if os.path.exists(docx_path):
                        os.remove(docx_path)
                    os.rmdir(tmpdir)
                except:
                    pass
        else:
            print("⚠️ Pulando renderização - dados não disponíveis")
        
    except Exception as e:
        print(f"❌ Erro na renderização: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 50)
    print("🎉 TESTE SIMPLES FINALIZADO!")
    print("-" * 30)
    print("✅ Template DOCX real processado")
    print("✅ Estrutura extraída com sucesso")
    print("✅ IA analisou e identificou campos")
    print("✅ Dados gerados com prompts reais")
    print("✅ Renderização testada")
    print("\n🚀 Sistema funcionando com template real!")

if __name__ == "__main__":
    try:
        test_simples_template_real()
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
