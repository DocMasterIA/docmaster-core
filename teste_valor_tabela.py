#!/usr/bin/env python3
"""
Teste específico para encontrar valores em tabelas.
"""

import os
import sys
import django

# Configurar Django
sys.path.append('/home/adryan/Downloads/mdlicitatech-system/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mdlicitatech.settings')
django.setup()

from backend.app.services.ia import process_document_with_ai, extract_document_text_simple
from backend.app.models import Template
from docx import Document


def testar_extracao_tabelas():
    """
    Testa se consegue extrair valores das tabelas.
    """
    print("🔍 Testando extração de tabelas")
    print("=" * 60)
    
    # Buscar o template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado")
        return
    
    print(f"📄 Template: {template.name}")
    
    # Carregar documento
    doc = Document(template.file.path)
    
    # Extrair texto
    document_text = extract_document_text_simple(doc)
    
    print(f"📊 Tamanho do texto extraído: {len(document_text)} caracteres")
    print()
    
    # Procurar por valores específicos
    valores_procurados = [
        "PREÇO TOTAL MÉDIO",
        "5.678.659,46",
        "VALOR ESTIMADO",
        "R$"
    ]
    
    print("🔍 Procurando valores no texto extraído:")
    for valor in valores_procurados:
        if valor in document_text:
            print(f"✅ Encontrado: {valor}")
            # Mostrar contexto
            lines = document_text.split('\n')
            for i, line in enumerate(lines):
                if valor in line:
                    print(f"   Linha {i+1}: {line.strip()}")
        else:
            print(f"❌ Não encontrado: {valor}")
    
    print()
    print("📝 Primeiras 500 caracteres do texto:")
    print("-" * 60)
    print(document_text[:500])
    print("-" * 60)
    
    # Procurar especificamente por tabelas
    print("\n📊 Conteúdo das tabelas:")
    for i, table in enumerate(doc.tables):
        print(f"\n--- TABELA {i+1} ---")
        for row in table.rows:
            row_text = " | ".join([cell.text.strip() for cell in row.cells])
            if row_text.strip():
                print(row_text)
                # Procurar por valores específicos nesta linha
                if "PREÇO TOTAL MÉDIO" in row_text or "5.678.659,46" in row_text:
                    print(f"   ⭐ VALOR ENCONTRADO AQUI!")


def testar_alteracao_valor():
    """
    Testa a alteração do valor específico.
    """
    print("\n🧪 Testando alteração do valor")
    print("=" * 60)
    
    template = Template.objects.first()
    if not template:
        return
    
    prompt = "Troque R$ 5.678.659,46 por R$ 2.500.000,00"
    print(f"🔧 Prompt: {prompt}")
    
    try:
        result = process_document_with_ai(template.file.path, prompt)
        
        if result.get('success'):
            print("✅ Processamento bem-sucedido!")
            print(f"📄 Documento salvo em: {result['output_path']}")
            
            # Verificar se o arquivo foi criado
            if os.path.exists(result['output_path']):
                print("\n🔍 Verificando resultado...")
                
                # Ler o documento gerado
                doc = Document(result['output_path'])
                
                # Procurar pelo valor alterado
                found_old = False
                found_new = False
                
                for paragraph in doc.paragraphs:
                    text = paragraph.text
                    if "5.678.659,46" in text:
                        found_old = True
                    if "2.500.000,00" in text:
                        found_new = True
                
                # Procurar também em tabelas
                for table in doc.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            for paragraph in cell.paragraphs:
                                text = paragraph.text
                                if "5.678.659,46" in text:
                                    found_old = True
                                if "2.500.000,00" in text:
                                    found_new = True
                
                if found_new:
                    print("✅ Valor alterado encontrado no documento!")
                elif found_old:
                    print("⚠️ Valor antigo ainda presente")
                else:
                    print("❓ Não foi possível verificar a alteração")
                    
            else:
                print("❌ Arquivo não foi criado")
        else:
            print(f"❌ Erro: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Erro no teste: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    testar_extracao_tabelas()
    testar_alteracao_valor()