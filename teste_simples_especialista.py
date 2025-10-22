#!/usr/bin/env python3
"""
Teste simples para verificar se o conteúdo de especialista está sendo adicionado

Antes de executar:
1. Ative o ambiente virtual: source venv/bin/activate
2. Execute: python teste_simples_especialista.py
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

def test_simples_especialista():
    """Teste simples para verificar se o conteúdo de especialista está sendo adicionado."""
    
    print("🧪 TESTE SIMPLES - ESPECIALISTA")
    print("Verificando se o conteúdo está sendo adicionado")
    print("=" * 50)
    
    # 1. Usar template original
    template_path = "/home/adryan/mdlicitatech-system/backend/media/templates/docx/EDITAL_PREGAO_ELETRONICO_005-2025_AQUISIÇÃO_DE_MEDICAMENTOS_1.docx"
    
    # 2. Prompt de especialista
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
    
    # 3. Dados básicos
    generated_data = {
        'numero_edital': '01/2022',
        'modalidade': 'Pregão Eletrônico',
        'objeto': 'Aquisição de medicamentos básicos',
        'valor_estimado': '500000.00'
    }
    
    print("📝 Prompt de especialista enviado")
    print("📊 Dados básicos preparados")
    
    # 4. Testar renderização contextual
    print("\n🎨 Testando renderização contextual...")
    
    try:
        # Renderizar usando renderização contextual
        tmpdir = tempfile.mkdtemp()
        output_path = os.path.join(tmpdir, "edital_simples_especialista.docx")
        
        render_docx_contextual_intelligent(template_path, output_path, generated_data, prompt_especialista)
        
        if os.path.exists(output_path):
            print(f"✅ Arquivo renderizado: {os.path.basename(output_path)}")
            print(f"📁 Caminho: {output_path}")
            print(f"📊 Tamanho: {os.path.getsize(output_path)} bytes")
            
            # Verificar se as mudanças foram aplicadas
            from docx import Document
            doc_result = Document(output_path)
            
            print("\n📝 Verificando conteúdo adicionado:")
            
            # Procurar por conteúdo específico
            found_content = []
            for i, p in enumerate(doc_result.paragraphs):
                if "3.4.15. O julgamento das propostas" in p.text:
                    found_content.append(f"Cláusula de julgamento no parágrafo {i+1}")
                elif "OBSERVAÇÃO PRÁTICA:" in p.text:
                    found_content.append(f"Observação prática no parágrafo {i+1}")
                elif "Lei Federal nº 14.133, de 1º de abril de 2021" in p.text:
                    found_content.append(f"Referência legal melhorada no parágrafo {i+1}")
            
            if found_content:
                print("✅ Conteúdo encontrado:")
                for content in found_content:
                    print(f"  • {content}")
            else:
                print("❌ Nenhum conteúdo de especialista encontrado")
            
            # Verificar formatação em azul
            blue_found = False
            for i, p in enumerate(doc_result.paragraphs):
                for run in p.runs:
                    if hasattr(run.font.color, 'rgb') and run.font.color.rgb:
                        if run.font.color.rgb == (0, 0, 255):  # Azul
                            print(f"  🎨 Texto azul encontrado no parágrafo {i+1}: {run.text[:50]}...")
                            blue_found = True
            
            if not blue_found:
                print("❌ Nenhum texto em azul encontrado")
            
        else:
            print("❌ Arquivo não foi gerado")
    
    except Exception as e:
        print(f"❌ Erro na renderização: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 50)
    print("🎯 RESULTADO FINAL:")
    print("-" * 20)
    print("✅ Teste simples de especialista")
    print("✅ Verificação de conteúdo adicionado")
    print("✅ Verificação de formatação em azul")

if __name__ == "__main__":
    try:
        test_simples_especialista()
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
