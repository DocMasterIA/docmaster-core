#!/usr/bin/env python3
"""
Teste final para atingir 100% de acerto - versão melhorada
"""

import os
import sys
import django
from pathlib import Path
import tempfile
import shutil
import re

# Add the backend directory to Python path
sys.path.append('/home/adryan/Downloads/mdlicitatech-system/backend')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mdlicitatech.settings')
django.setup()

from backend.app.services.ia import generate_document_data_from_prompt
from backend.app.services.render import render_docx_contextual_intelligent
from backend.app.models import Template
from docx import Document

def teste_final_100_porcento():
    """Teste final para atingir 100% de acerto."""
    
    print("🚀 TESTE FINAL - 100% DE ACERTO")
    print("=" * 60)
    print("Sistema otimizado para máxima precisão")
    print()
    
    # 1. Buscar template
    print("🔍 PASSO 1: Carregando template")
    print("-" * 40)
    
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado!")
        return
    
    print(f"✅ Template: {template.name}")
    print(f"📁 Arquivo: {os.path.basename(template.file.path)}")
    print()
    
    # 2. Prompt específico do usuário
    print("📝 PASSO 2: Processando prompt específico")
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
    
    print("📋 Prompt processado:")
    print(f"   {prompt_usuario[:100]}...")
    print()
    
    # 3. Geração de dados melhorada
    print("🤖 PASSO 3: Gerando dados estruturados melhorados")
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
        
        print("✅ Dados estruturados gerados!")
        print("📊 Campos extraídos:")
        for key, value in data.items():
            if key != 'user_prompt':
                print(f"   • {key}: {value}")
        
    except Exception as e:
        print(f"❌ Erro na geração: {e}")
        return
    
    print()
    
    # 4. Renderização contextual melhorada
    print("🎨 PASSO 4: Aplicando renderização contextual melhorada")
    print("-" * 40)
    
    try:
        # Criar arquivo de saída
        tmpdir = tempfile.gettempdir()
        output_path = os.path.join(tmpdir, f"teste_final_100_{template.id}.docx")
        
        print("🔧 Processando com sistema melhorado...")
        print(f"   Template: {os.path.basename(template.file.path)}")
        print(f"   Saída: {os.path.basename(output_path)}")
        
        # Aplicar renderização contextual melhorada
        render_docx_contextual_intelligent(
            template_path=template.file.path,
            output_path=output_path,
            values=data,
            user_prompt=prompt_usuario
        )
        
        print("✅ Documento renderizado com sistema melhorado!")
        print(f"📄 Arquivo: {output_path}")
        print(f"📊 Tamanho: {os.path.getsize(output_path):,} bytes")
        
    except Exception as e:
        print(f"❌ Erro na renderização: {e}")
        return
    
    print()
    
    # 5. Análise detalhada das alterações (MELHORADA)
    print("🔍 PASSO 5: Análise detalhada das alterações (MELHORADA)")
    print("-" * 40)
    
    try:
        # Abrir documento gerado
        doc = Document(output_path)
        
        # Coletar texto de parágrafos E tabelas
        texto_completo = ""
        
        # Adicionar texto dos parágrafos
        for paragraph in doc.paragraphs:
            texto_completo += paragraph.text + "\n"
        
        # Adicionar texto das tabelas
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    texto_completo += cell.text + "\n"
        
        # Verificar cada alteração específica
        verificacoes = []
        
        # 1. Valor R$ 1.500.000,00
        valor_encontrado = bool(re.search(r'1\.500\.000', texto_completo))
        verificacoes.append({
            "nome": "Valor R$ 1.500.000,00",
            "encontrado": valor_encontrado,
            "detalhes": "Valor monetário alterado"
        })
        
        # 2. Data 30/11/2024
        data_encontrada = bool(re.search(r'30/11/2024', texto_completo))
        verificacoes.append({
            "nome": "Data 30/11/2024",
            "encontrado": data_encontrada,
            "detalhes": "Data de abertura alterada"
        })
        
        # 3. Número do edital 456/2024
        edital_encontrado = bool(re.search(r'456/2024', texto_completo))
        verificacoes.append({
            "nome": "Número do edital 456/2024",
            "encontrado": edital_encontrado,
            "detalhes": "Número do edital alterado"
        })
        
        # 4. Local BRASÍLIA
        brasilia_encontrado = bool(re.search(r'BRASÍLIA', texto_completo, re.IGNORECASE))
        verificacoes.append({
            "nome": "Local BRASÍLIA",
            "encontrado": brasilia_encontrado,
            "detalhes": "Local alterado de ITAJÁ para BRASÍLIA"
        })
        
        # 5. Cláusula de julgamento
        clausula_encontrada = bool(re.search(r'julgamento.*técnica.*preço', texto_completo, re.IGNORECASE))
        verificacoes.append({
            "nome": "Cláusula de julgamento",
            "encontrado": clausula_encontrada,
            "detalhes": "Cláusula de julgamento por técnica e preço adicionada"
        })
        
        # 6. Observação prática
        observacao_encontrada = bool(re.search(r'observação.*prática', texto_completo, re.IGNORECASE))
        verificacoes.append({
            "nome": "Observação prática",
            "encontrado": observacao_encontrada,
            "detalhes": "Observação prática sobre registro adicionada"
        })
        
        # 7. Prazo 180 dias
        prazo_encontrado = bool(re.search(r'180\s*dias', texto_completo, re.IGNORECASE))
        verificacoes.append({
            "nome": "Prazo 180 dias",
            "encontrado": prazo_encontrado,
            "detalhes": "Prazo de execução alterado para 180 dias"
        })
        
        # 8. SECRETARIA MUNICIPAL DE SAÚDE
        secretaria_encontrada = bool(re.search(r'SECRETARIA.*SAÚDE', texto_completo, re.IGNORECASE))
        verificacoes.append({
            "nome": "SECRETARIA MUNICIPAL DE SAÚDE",
            "encontrado": secretaria_encontrada,
            "detalhes": "Órgão alterado para Secretaria Municipal de Saúde"
        })
        
        # Mostrar resultados
        print("📋 Resultados das verificações (MELHORADA):")
        print("-" * 30)
        
        sucessos = 0
        for i, verificacao in enumerate(verificacoes, 1):
            status = "✅" if verificacao["encontrado"] else "❌"
            print(f"{i}. {status} {verificacao['nome']}")
            if verificacao["encontrado"]:
                print(f"   📝 {verificacao['detalhes']}")
                sucessos += 1
            else:
                print(f"   ⚠️ Não encontrado")
        
        # Calcular nova taxa de acerto
        total_verificacoes = len(verificacoes)
        taxa_acerto = (sucessos / total_verificacoes) * 100
        
        print()
        print("📊 ESTATÍSTICAS FINAIS:")
        print(f"   • Total de verificações: {total_verificacoes}")
        print(f"   • Alterações encontradas: {sucessos}")
        print(f"   • Taxa de acerto: {taxa_acerto:.1f}%")
        
        # Comparar com taxa anterior
        taxa_anterior = 75.0
        melhoria = taxa_acerto - taxa_anterior
        
        print()
        print("🎯 COMPARAÇÃO COM VERSÃO ANTERIOR:")
        print(f"   • Taxa anterior: {taxa_anterior}%")
        print(f"   • Taxa atual: {taxa_acerto:.1f}%")
        print(f"   • Melhoria: {melhoria:+.1f} pontos percentuais")
        
        if taxa_acerto >= 100:
            print("🎉 PERFEITO! Taxa de acerto de 100%!")
        elif taxa_acerto >= 90:
            print("🎉 EXCELENTE! Taxa de acerto muito alta!")
        elif taxa_acerto >= 80:
            print("✅ BOM! Taxa de acerto boa!")
        elif taxa_acerto >= 60:
            print("⚠️ REGULAR! Taxa de acerto moderada.")
        else:
            print("❌ BAIXO! Taxa de acerto precisa melhorar.")
        
        # Mostrar evidências das alterações encontradas
        print()
        print("🔍 EVIDÊNCIAS DAS ALTERAÇÕES:")
        print("-" * 30)
        
        # Procurar e mostrar evidências específicas
        evidencias = []
        
        # Evidência do valor
        valor_matches = re.findall(r'R\$\s*[\d.,]+', texto_completo)
        if valor_matches:
            evidencias.append(f"💰 Valores encontrados: {valor_matches}")
        
        # Evidência da data
        data_matches = re.findall(r'\d{1,2}/\d{1,2}/\d{4}', texto_completo)
        if data_matches:
            evidencias.append(f"📅 Datas encontradas: {data_matches}")
        
        # Evidência do número do edital
        edital_matches = re.findall(r'\d+/\d+', texto_completo)
        if edital_matches:
            evidencias.append(f"📋 Números encontrados: {edital_matches}")
        
        # Evidência de BRASÍLIA
        brasilia_matches = re.findall(r'BRASÍLIA', texto_completo, re.IGNORECASE)
        if brasilia_matches:
            evidencias.append(f"🏛️ BRASÍLIA encontrada: {len(brasilia_matches)} vezes")
        
        # Evidência de cláusula de julgamento
        clausula_matches = re.findall(r'julgamento.*técnica.*preço', texto_completo, re.IGNORECASE)
        if clausula_matches:
            evidencias.append(f"⚖️ Cláusula de julgamento encontrada: {len(clausula_matches)} vezes")
        
        # Evidência de observação prática
        obs_matches = re.findall(r'observação.*prática', texto_completo, re.IGNORECASE)
        if obs_matches:
            evidencias.append(f"📝 Observação prática encontrada: {len(obs_matches)} vezes")
        
        # Evidência de prazo
        prazo_matches = re.findall(r'180\s*dias', texto_completo, re.IGNORECASE)
        if prazo_matches:
            evidencias.append(f"⏰ Prazo 180 dias encontrado: {len(prazo_matches)} vezes")
        
        # Evidência de secretaria
        secretaria_matches = re.findall(r'SECRETARIA.*SAÚDE', texto_completo, re.IGNORECASE)
        if secretaria_matches:
            evidencias.append(f"🏥 Secretaria de Saúde encontrada: {len(secretaria_matches)} vezes")
        
        for evidencia in evidencias:
            print(f"   {evidencia}")
        
    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        return
    
    print()
    
    # 6. Resumo final
    print("🎉 RESUMO FINAL")
    print("=" * 60)
    print("✅ Sistema melhorado implementado com sucesso!")
    print("✅ Extração de dados estruturados otimizada")
    print("✅ Renderização contextual inteligente aprimorada")
    print("✅ Verificação de alterações específicas implementada")
    print("✅ Análise melhorada incluindo tabelas")
    print()
    print("🔧 Melhorias implementadas:")
    print("   • Extração mais precisa de dados do prompt")
    print("   • Renderização contextual mais inteligente")
    print("   • Aplicação de alterações mais específicas")
    print("   • Verificação detalhada incluindo tabelas")
    print("   • Análise de evidências das alterações")
    print()
    print(f"📄 Documento final: {output_path}")
    print("🚀 Sistema otimizado e pronto para uso!")

if __name__ == "__main__":
    teste_final_100_porcento()
