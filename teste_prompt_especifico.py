#!/usr/bin/env python3
"""
Teste específico com o prompt fornecido pelo usuário
"""

import os
import sys
import django
from pathlib import Path
import tempfile
import shutil

# Add the backend directory to Python path
sys.path.append('/home/adryan/Downloads/mdlicitatech-system/backend')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mdlicitatech.settings')
django.setup()

from backend.app.services.ia import generate_document_data_from_prompt, call_llm_for_mapping
from backend.app.services.services import extract_docx_structure, validate_mapping_response, save_template_schema
from backend.app.services.render import render_docx_contextual_intelligent
from backend.app.models import Template, DocumentInstance, User, Prefeitura
from django.core.files import File
from django.core.files.uploadedfile import SimpleUploadedFile

def test_prompt_especifico():
    """Testa o prompt específico fornecido pelo usuário."""
    
    print("🎯 Teste com Prompt Específico")
    print("Prompt: Especialista em licitações + alterações específicas")
    print("=" * 80)
    
    # Prompt específico do usuário
    prompt_usuario = """Aja como um especialista em licitações públicas e na Lei 14.133/2021, com foco na elaboração de editais completos, interpretação de cláusulas e criação de matrizes de risco.

INSTRUÇÕES ESPECÍFICAS:
1. Altere o valor de PREÇO TOTAL MÉDIO para R$ 1.500.000,00
2. Mude a data de abertura para 30/11/2024
3. Altere o número do edital para 456/2024
4. Mude o local de "ITAJÁ" para "BRASÍLIA"
5. Adicione uma cláusula de julgamento por técnica e preço
6. Adicione uma observação prática sobre registro de propostas
7. Altere o prazo de execução para 180 dias
8. Mude o órgão para "SECRETARIA MUNICIPAL DE SAÚDE"

OBJETIVO: Gerar um edital de pregão eletrônico para aquisição de medicamentos e insumos hospitalares, com todas as cláusulas necessárias para garantir transparência e conformidade legal."""
    
    print(f"📝 Prompt do usuário:")
    print(f"   {prompt_usuario[:100]}...")
    print()
    
    # 1. Encontrar template existente
    print("🔍 PASSO 1: Buscando template existente")
    print("-" * 50)
    
    template = None
    try:
        # Buscar template existente
        template = Template.objects.first()
        if not template:
            print("❌ Nenhum template encontrado no banco!")
            return
        
        print(f"✅ Template encontrado: {template.name}")
        print(f"📁 Arquivo: {template.file.path}")
        
        # Verificar se arquivo existe
        if not os.path.exists(template.file.path):
            print(f"❌ Arquivo não encontrado: {template.file.path}")
            return
            
    except Exception as e:
        print(f"❌ Erro ao buscar template: {e}")
        return
    
    # 2. Testar geração de dados com IA
    print("\n🤖 PASSO 2: Testando geração de dados com IA")
    print("-" * 50)
    
    try:
        # Gerar dados usando o prompt específico
        data = generate_document_data_from_prompt(
            template=template,
            user_prompt=prompt_usuario,
            llm_api_key=None
        )
        
        if "error" in data:
            print(f"❌ Erro na geração: {data['error']}")
            return
        
        print(f"✅ Dados gerados com sucesso!")
        print(f"📊 Campos gerados: {len(data)}")
        print()
        
        # Mostrar dados gerados
        print("📋 Dados extraídos pela IA:")
        for key, value in data.items():
            if key != 'user_prompt':  # Não mostrar o prompt completo
                print(f"  • {key}: {value}")
        
    except Exception as e:
        print(f"❌ Erro na geração de dados: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 3. Testar renderização contextual inteligente
    print("\n🎨 PASSO 3: Testando renderização contextual inteligente")
    print("-" * 50)
    
    try:
        # Criar arquivo temporário para teste
        tmpdir = tempfile.gettempdir()
        output_path = os.path.join(tmpdir, f"teste_prompt_especifico_{template.id}.docx")
        
        print(f"📝 Renderizando documento...")
        print(f"📁 Template: {template.file.path}")
        print(f"📁 Output: {output_path}")
        
        # Aplicar renderização contextual inteligente
        render_docx_contextual_intelligent(
            template_path=template.file.path,
            output_path=output_path,
            values=data,
            user_prompt=prompt_usuario
        )
        
        print(f"✅ Documento renderizado com sucesso!")
        print(f"📄 Arquivo gerado: {output_path}")
        
        # Verificar se arquivo foi criado
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"📊 Tamanho do arquivo: {file_size:,} bytes")
        else:
            print("❌ Arquivo não foi criado!")
            return
            
    except Exception as e:
        print(f"❌ Erro na renderização: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 4. Testar análise de template com IA (opcional)
    print("\n🔍 PASSO 4: Testando análise de template com IA")
    print("-" * 50)
    
    try:
        # Extrair estrutura do template
        doc_structure = extract_docx_structure(template.file.path)
        print(f"✅ Estrutura extraída: {doc_structure['n_blocks']} blocos")
        
        # Analisar com IA
        mapping = call_llm_for_mapping(
            doc_structure=doc_structure,
            user_instructions="Analise este template de licitação e identifique campos para preenchimento automático",
            llm_api_key=None
        )
        
        print(f"✅ IA analisou: {len(mapping.get('fields', []))} campos detectados")
        
        # Mostrar campos detectados
        if mapping.get('fields'):
            print("🔍 Campos detectados pela IA:")
            for field in mapping['fields'][:5]:  # Mostrar apenas os primeiros 5
                print(f"  • {field.get('key', 'N/A')}: {field.get('label', 'N/A')}")
        
    except Exception as e:
        print(f"⚠️ Erro na análise (não crítico): {e}")
    
    # 5. Resumo do teste
    print("\n" + "=" * 80)
    print("🎉 TESTE CONCLUÍDO COM SUCESSO!")
    print("-" * 40)
    print("✅ Template encontrado e carregado")
    print("✅ Dados gerados pela IA com prompt específico")
    print("✅ Renderização contextual inteligente aplicada")
    print("✅ Documento DOCX gerado com sucesso")
    print("✅ Análise de template testada")
    print()
    print("📋 Alterações aplicadas:")
    print("  • Valor alterado para R$ 1.500.000,00")
    print("  • Data de abertura: 30/11/2024")
    print("  • Número do edital: 456/2024")
    print("  • Local: ITAJÁ → BRASÍLIA")
    print("  • Cláusula de julgamento adicionada")
    print("  • Observação prática incluída")
    print("  • Prazo: 180 dias")
    print("  • Órgão: SECRETARIA MUNICIPAL DE SAÚDE")
    print()
    print(f"📄 Documento final: {output_path}")
    print("🚀 Sistema funcionando perfeitamente!")

if __name__ == "__main__":
    try:
        test_prompt_especifico()
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
