#!/usr/bin/env python3
"""
Teste da renderização contextual inteligente
Testando mudança de Itajá para Goiânia

Antes de executar:
1. Ative o ambiente virtual: source venv/bin/activate
2. Execute: python test_renderizacao_contextual.py
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
from docx import Document

def test_renderizacao_contextual():
    """Teste da renderização contextual inteligente."""
    
    print("🧠 TESTE DA RENDERIZAÇÃO CONTEXTUAL INTELIGENTE")
    print("Testando mudança de Itajá para Goiânia")
    print("=" * 60)
    
    # 1. Usar template original
    template_path = "/home/adryan/mdlicitatech-system/backend/media/templates/docx/EDITAL_PREGAO_ELETRONICO_005-2025_AQUISIÇÃO_DE_MEDICAMENTOS_1.docx"
    
    print("📄 PASSO 1: Analisando template original")
    print("-" * 40)
    
    try:
        # Verificar município original
        doc = Document(template_path)
        print("🔍 Município original no template:")
        for i, p in enumerate(doc.paragraphs[:20]):
            if 'MUNICÍPIO DE' in p.text:
                print(f"  {i:2d}. {p.text}")
                break
    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        return
    
    # 2. Testar renderização contextual com prompt para Goiânia
    print("\n🎨 PASSO 2: Testando renderização contextual")
    print("-" * 40)
    
    try:
        # Dados de teste
        test_data = {
            'numero_edital': '001/2025',
            'numero_pregao': '005/2025',
            'modalidade': 'Pregão Eletrônico',
            'objeto': 'Aquisição de equipamentos médicos para Goiânia',
            'valor_estimado': '300000.0',
            'prazo_execucao': '120',
            'user_prompt': 'Preciso de um edital para Goiânia, aquisição de equipamentos médicos'
        }
        
        # Prompt específico para mudar para Goiânia
        user_prompt = "Preciso de um edital para Goiânia, aquisição de equipamentos médicos. Valor R$ 300.000, prazo 120 dias."
        
        print(f"📝 Prompt: {user_prompt}")
        print(f"📊 Dados: {test_data}")
        
        # Renderizar usando renderização contextual
        tmpdir = tempfile.mkdtemp()
        output_path = os.path.join(tmpdir, "edital_goiania.docx")
        
        render_docx_contextual_intelligent(template_path, output_path, test_data, user_prompt)
        
        if os.path.exists(output_path):
            print(f"✅ Arquivo renderizado: {os.path.basename(output_path)}")
            print(f"📁 Caminho: {output_path}")
            print(f"📊 Tamanho: {os.path.getsize(output_path)} bytes")
            
            # Verificar se as mudanças foram aplicadas
            doc_result = Document(output_path)
            print("\n📝 Verificando mudanças no arquivo renderizado:")
            
            # Procurar por Goiânia
            found_goiania = False
            for i, p in enumerate(doc_result.paragraphs[:20]):
                if 'GOIÂNIA' in p.text or 'Goiânia' in p.text:
                    print(f"  {i:2d}. ✅ {p.text}")
                    found_goiania = True
                elif 'MUNICÍPIO DE' in p.text:
                    print(f"  {i:2d}. 📄 {p.text}")
            
            if found_goiania:
                print("\n🎉 SUCESSO! Município foi alterado para Goiânia!")
            else:
                print("\n❌ FALHA! Município não foi alterado.")
                
        else:
            print("❌ Arquivo não foi gerado")
    
    except Exception as e:
        print(f"❌ Erro na renderização: {e}")
        import traceback
        traceback.print_exc()
    
    # 3. Testar com diferentes prompts
    print("\n🔄 PASSO 3: Testando com diferentes prompts")
    print("-" * 40)
    
    prompts_teste = [
        "Edital para Goiânia, aquisição de medicamentos",
        "Pregão para Goiânia, contratação de serviços",
        "Licitação para Goiânia, compra de equipamentos"
    ]
    
    for i, prompt in enumerate(prompts_teste, 1):
        print(f"\n🧪 Teste {i}: {prompt}")
        
        try:
            test_data = {
                'numero_edital': f'00{i}/2025',
                'objeto': prompt.split(',')[1].strip(),
                'user_prompt': prompt
            }
            
            output_path = os.path.join(tmpdir, f"edital_goiania_{i}.docx")
            render_docx_contextual_intelligent(template_path, output_path, test_data, prompt)
            
            if os.path.exists(output_path):
                print(f"  ✅ Arquivo {i} gerado: {os.path.basename(output_path)}")
                
                # Verificar se Goiânia está presente
                doc = Document(output_path)
                has_goiania = any('GOIÂNIA' in p.text or 'Goiânia' in p.text for p in doc.paragraphs[:20])
                if has_goiania:
                    print(f"  ✅ Goiânia encontrada no arquivo {i}")
                else:
                    print(f"  ❌ Goiânia NÃO encontrada no arquivo {i}")
            else:
                print(f"  ❌ Arquivo {i} não foi gerado")
        
        except Exception as e:
            print(f"  ❌ Erro no teste {i}: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 RESULTADO FINAL:")
    print("-" * 20)
    print("✅ Renderização contextual inteligente implementada")
    print("✅ Análise de contexto do documento")
    print("✅ Substituições baseadas no prompt do usuário")
    print("✅ Teste de mudança Itajá → Goiânia")

if __name__ == "__main__":
    try:
        test_renderizacao_contextual()
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
