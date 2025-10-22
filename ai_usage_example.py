#!/usr/bin/env python3
"""
Example of how to use the updated call_llm_for_mapping function.

Before running this example:
1. Set your OpenAI API key: export OPENAI_API_KEY="your-api-key-here"
2. Install dependencies: pip install -r requirements.txt
3. Run: python ai_usage_example.py
"""

import os
import sys
import django

# Add the backend directory to Python path
sys.path.append('/home/adryan/mdlicitatech-system/backend')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mdlicitatech.settings')
django.setup()

from app.services.ia import call_llm_for_mapping

def example_usage():
    """Example of using the AI mapping function."""
    
    # Example document structure (simulating extract_docx_structure output)
    doc_structure = {
        "blocks": [
            {"index": 0, "type": "heading", "style": "Heading 1", "text": "EDITAL DE LICITAÇÃO"},
            {"index": 1, "type": "paragraph", "style": "Normal", "text": "PREFEITURA MUNICIPAL DE EXEMPLO"},
            {"index": 2, "type": "paragraph", "style": "Normal", "text": "Objeto: Contratação de serviços de limpeza urbana"},
            {"index": 3, "type": "paragraph", "style": "Normal", "text": "Valor estimado: R$ 500.000,00"},
            {"index": 4, "type": "paragraph", "style": "Normal", "text": "Data de início: 01/01/2024"},
            {"index": 5, "type": "paragraph", "style": "Normal", "text": "Data final: 31/12/2024"},
            {"index": 6, "type": "paragraph", "style": "Normal", "text": "Modalidade: Pregão Eletrônico"},
            {"index": 7, "type": "paragraph", "style": "Normal", "text": "Responsável técnico: João Silva"},
        ],
        "n_blocks": 8
    }
    
    # User instructions
    user_instructions = "Detecte todos os campos de data, valores e informações do órgão"
    
    print("🤖 Analisando documento com IA...")
    print(f"📄 Documento tem {doc_structure['n_blocks']} blocos")
    print(f"💭 Instruções: {user_instructions}")
    print("-" * 50)
    
    # Call the AI function
    result = call_llm_for_mapping(
        doc_structure=doc_structure,
        user_instructions=user_instructions,
        llm_api_key="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"  # Will use OPENAI_API_KEY from environment
    )
    
    # Display results
    print("📊 Resultado da análise:")
    print(f"✅ Campos detectados: {len(result.get('fields', []))}")
    print(f"📝 Observações: {result.get('notes', 'Nenhuma')}")
    print()
    
    if result.get('fields'):
        print("🔍 Campos identificados:")
        for i, field in enumerate(result['fields'], 1):
            print(f"  {i}. {field.get('key', 'N/A')} ({field.get('type', 'N/A')})")
            print(f"     Label: {field.get('label', 'N/A')}")
            print(f"     Obrigatório: {field.get('required', False)}")
            print(f"     Descrição: {field.get('description', 'N/A')}")
            print(f"     Blocos: {field.get('block_indices', [])}")
            print()
    else:
        print("❌ Nenhum campo foi detectado")

if __name__ == "__main__":
    # Check if API key is set
    """if not os.getenv('OPENAI_API_KEY'):
        print("❌ Erro: OPENAI_API_KEY não configurada")
        print("Configure com: export OPENAI_API_KEY='sua-chave-aqui'")
        sys.exit(1)"""
    
    try:
        example_usage()
    except Exception as e:
        print(f"❌ Erro: {e}")
        sys.exit(1)
