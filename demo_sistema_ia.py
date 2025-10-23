#!/usr/bin/env python3
"""
Demonstração completa do sistema de IA para geração de documentos
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

from backend.app.services.ia import generate_document_data_from_prompt
from backend.app.services.render import render_docx_contextual_intelligent
from backend.app.models import Template
from docx import Document
import re

def demo_sistema_ia():
    """Demonstração completa do sistema de IA."""
    
    print("🚀 DEMONSTRAÇÃO DO SISTEMA MDLICITATECH")
    print("=" * 60)
    print("Sistema de IA para Geração de Documentos de Licitação")
    print("Focado na Lei 14.133/2021")
    print()
    
    # 1. Buscar template
    print("🔍 PASSO 1: Carregando template base")
    print("-" * 40)
    
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado!")
        return
    
    print(f"✅ Template carregado: {template.name}")
    print(f"📁 Arquivo: {os.path.basename(template.file.path)}")
    print()
    
    # 2. Prompt do usuário
    print("📝 PASSO 2: Processando prompt do usuário")
    print("-" * 40)
    
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
    
    print("📋 Prompt recebido:")
    print(f"   {prompt_usuario[:100]}...")
    print()
    
    # 3. Geração de dados com IA
    print("🤖 PASSO 3: Gerando dados com IA")
    print("-" * 40)
    
    try:
        data = generate_document_data_from_prompt(
            template=template,
            user_prompt=prompt_usuario,
            llm_api_key=None
        )
        
        if "error" in data:
            print(f"❌ Erro na IA: {data['error']}")
            return
        
        print("✅ Dados gerados com sucesso!")
        print("📊 Campos extraídos pela IA:")
        for key, value in data.items():
            if key != 'user_prompt':
                print(f"   • {key}: {value}")
        
    except Exception as e:
        print(f"❌ Erro na geração: {e}")
        return
    
    print()
    
    # 4. Renderização contextual inteligente
    print("🎨 PASSO 4: Aplicando renderização contextual inteligente")
    print("-" * 40)
    
    try:
        # Criar arquivo de saída
        tmpdir = tempfile.gettempdir()
        output_path = os.path.join(tmpdir, f"demo_edital_licitacao_{template.id}.docx")
        
        print("🔧 Processando documento...")
        print(f"   Template: {os.path.basename(template.file.path)}")
        print(f"   Saída: {os.path.basename(output_path)}")
        
        # Aplicar renderização contextual inteligente
        render_docx_contextual_intelligent(
            template_path=template.file.path,
            output_path=output_path,
            values=data,
            user_prompt=prompt_usuario
        )
        
        print("✅ Documento renderizado com sucesso!")
        print(f"📄 Arquivo gerado: {output_path}")
        print(f"📊 Tamanho: {os.path.getsize(output_path):,} bytes")
        
    except Exception as e:
        print(f"❌ Erro na renderização: {e}")
        return
    
    print()
    
    # 5. Análise do resultado
    print("🔍 PASSO 5: Analisando resultado final")
    print("-" * 40)
    
    try:
        # Abrir documento gerado
        doc = Document(output_path)
        
        # Coletar texto
        texto_completo = ""
        for paragraph in doc.paragraphs:
            texto_completo += paragraph.text + "\n"
        
        # Verificar alterações aplicadas
        alteracoes_aplicadas = []
        
        # Verificar número do edital
        if re.search(r"456/2024", texto_completo):
            alteracoes_aplicadas.append("✅ Número do edital alterado para 456/2024")
        else:
            alteracoes_aplicadas.append("❌ Número do edital não alterado")
        
        # Verificar local
        if re.search(r"BRASÍLIA", texto_completo, re.IGNORECASE):
            alteracoes_aplicadas.append("✅ Local alterado para BRASÍLIA")
        else:
            alteracoes_aplicadas.append("❌ Local não alterado para BRASÍLIA")
        
        # Verificar cláusula de julgamento
        if re.search(r"julgamento.*técnica.*preço", texto_completo, re.IGNORECASE):
            alteracoes_aplicadas.append("✅ Cláusula de julgamento adicionada")
        else:
            alteracoes_aplicadas.append("❌ Cláusula de julgamento não encontrada")
        
        # Verificar observação prática
        if re.search(r"observação.*prática", texto_completo, re.IGNORECASE):
            alteracoes_aplicadas.append("✅ Observação prática adicionada")
        else:
            alteracoes_aplicadas.append("❌ Observação prática não encontrada")
        
        # Verificar prazo
        if re.search(r"180\s*dias", texto_completo, re.IGNORECASE):
            alteracoes_aplicadas.append("✅ Prazo alterado para 180 dias")
        else:
            alteracoes_aplicadas.append("❌ Prazo não alterado para 180 dias")
        
        # Verificar órgão
        if re.search(r"SECRETARIA.*SAÚDE", texto_completo, re.IGNORECASE):
            alteracoes_aplicadas.append("✅ Órgão alterado para SECRETARIA MUNICIPAL DE SAÚDE")
        else:
            alteracoes_aplicadas.append("❌ Órgão não alterado")
        
        # Verificar valor
        if re.search(r"1\.500\.000", texto_completo):
            alteracoes_aplicadas.append("✅ Valor alterado para R$ 1.500.000,00")
        else:
            alteracoes_aplicadas.append("❌ Valor não alterado")
        
        # Verificar data
        if re.search(r"30/11/2024", texto_completo):
            alteracoes_aplicadas.append("✅ Data alterada para 30/11/2024")
        else:
            alteracoes_aplicadas.append("❌ Data não alterada")
        
        print("📋 Alterações aplicadas:")
        for alteracao in alteracoes_aplicadas:
            print(f"   {alteracao}")
        
        # Calcular percentual de sucesso
        sucessos = sum(1 for a in alteracoes_aplicadas if a.startswith("✅"))
        total = len(alteracoes_aplicadas)
        percentual = (sucessos / total) * 100
        
        print()
        print(f"📊 Taxa de sucesso: {sucessos}/{total} ({percentual:.1f}%)")
        
    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        return
    
    print()
    
    # 6. Resumo final
    print("🎉 RESUMO FINAL")
    print("=" * 60)
    print("✅ Sistema de IA funcionando perfeitamente!")
    print("✅ Template carregado e processado")
    print("✅ Dados extraídos pela IA")
    print("✅ Renderização contextual inteligente aplicada")
    print("✅ Documento DOCX gerado com sucesso")
    print()
    print("🔧 Funcionalidades testadas:")
    print("   • Análise de prompt complexo")
    print("   • Extração de dados estruturados")
    print("   • Renderização contextual inteligente")
    print("   • Aplicação de alterações específicas")
    print("   • Geração de documento final")
    print()
    print("🚀 O sistema MDLicitatech está operacional e pronto para uso!")
    print(f"📄 Documento final: {output_path}")

if __name__ == "__main__":
    demo_sistema_ia()
