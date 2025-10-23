#!/usr/bin/env python3
"""
Teste com prompts realistas para verificar o funcionamento geral do sistema
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

def teste_prompts_realistas():
    """Teste com prompts realistas para verificar funcionamento geral."""
    
    print("🎯 TESTE COM PROMPTS REALISTAS")
    print("=" * 60)
    print("Verificando funcionamento geral com cenários realistas")
    print()
    
    # Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado!")
        return
    
    print(f"✅ Template: {template.name}")
    print()
    
    # Prompts realistas para testar
    prompts_teste = [
        {
            "nome": "Mudança Mínima - Apenas Data",
            "prompt": "Aja como um especialista em licitações públicas. Altere apenas a data de abertura para 15/12/2024.",
            "esperado": {
                "data_abertura": "15/12/2024",
                "outros_preservados": True
            }
        },
        {
            "nome": "Mudança Específica - Valor e Local",
            "prompt": "Aja como um especialista em licitações públicas. Altere o valor estimado para R$ 2.000.000,00 e mude o local de ITAJÁ para GOIÂNIA.",
            "esperado": {
                "valor_estimado": "2000000.00",
                "local_orgao": "GOIÂNIA",
                "outros_preservados": True
            }
        },
        {
            "nome": "Mudança de Número - Edital Específico",
            "prompt": "Aja como um especialista em licitações públicas. Altere o número do edital para 789/2024.",
            "esperado": {
                "numero_edital": "789/2024",
                "outros_preservados": True
            }
        },
        {
            "nome": "Mudança de Órgão - Secretaria Específica",
            "prompt": "Aja como um especialista em licitações públicas. Mude o órgão para SECRETARIA MUNICIPAL DE EDUCAÇÃO.",
            "esperado": {
                "orgao": "SECRETARIA MUNICIPAL DE EDUCAÇÃO",
                "outros_preservados": True
            }
        },
        {
            "nome": "Mudança Múltipla - Poucas Alterações",
            "prompt": "Aja como um especialista em licitações públicas. Altere a data para 20/01/2025, o valor para R$ 800.000,00 e o prazo de execução para 120 dias.",
            "esperado": {
                "data_abertura": "20/01/2025",
                "valor_estimado": "800000.00",
                "prazo_execucao": "120",
                "outros_preservados": True
            }
        },
        {
            "nome": "Mudança com Adição - Cláusula Específica",
            "prompt": "Aja como um especialista em licitações públicas. Altere o valor para R$ 1.200.000,00 e adicione uma cláusula sobre garantia de execução.",
            "esperado": {
                "valor_estimado": "1200000.00",
                "adicionar_clausula": True,
                "outros_preservados": True
            }
        },
        {
            "nome": "Mudança Zero - Apenas Confirmação",
            "prompt": "Aja como um especialista em licitações públicas. Confirme se o documento está adequado para licitação de medicamentos.",
            "esperado": {
                "nenhuma_mudanca": True,
                "outros_preservados": True
            }
        }
    ]
    
    resultados = []
    
    for i, teste in enumerate(prompts_teste, 1):
        print(f"🧪 TESTE {i}: {teste['nome']}")
        print("-" * 50)
        
        try:
            # Gerar dados
            data = generate_document_data_from_prompt(template, teste['prompt'])
            
            # Renderizar documento
            tmpdir = tempfile.gettempdir()
            output_path = os.path.join(tmpdir, f"teste_prompt_{i}_{template.id}.docx")
            
            render_docx_contextual_intelligent(
                template_path=template.file.path,
                output_path=output_path,
                values=data,
                user_prompt=teste['prompt']
            )
            
            # Analisar resultado
            doc = Document(output_path)
            texto_completo = ""
            for paragraph in doc.paragraphs:
                texto_completo += paragraph.text + "\n"
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        texto_completo += cell.text + "\n"
            
            # Verificar se as mudanças esperadas foram aplicadas
            mudancas_aplicadas = 0
            total_mudancas = 0
            
            if 'data_abertura' in teste['esperado']:
                total_mudancas += 1
                if re.search(teste['esperado']['data_abertura'], texto_completo):
                    mudancas_aplicadas += 1
                    print(f"   ✅ Data {teste['esperado']['data_abertura']} aplicada")
                else:
                    print(f"   ❌ Data {teste['esperado']['data_abertura']} não aplicada")
            
            if 'valor_estimado' in teste['esperado']:
                total_mudancas += 1
                valor_esperado = teste['esperado']['valor_estimado']
                if re.search(r'1\.200\.000' if '1200000' in valor_esperado else r'2\.000\.000' if '2000000' in valor_esperado else r'800\.000', texto_completo):
                    mudancas_aplicadas += 1
                    print(f"   ✅ Valor R$ {valor_esperado} aplicado")
                else:
                    print(f"   ❌ Valor R$ {valor_esperado} não aplicado")
            
            if 'numero_edital' in teste['esperado']:
                total_mudancas += 1
                if re.search(teste['esperado']['numero_edital'], texto_completo):
                    mudancas_aplicadas += 1
                    print(f"   ✅ Número do edital {teste['esperado']['numero_edital']} aplicado")
                else:
                    print(f"   ❌ Número do edital {teste['esperado']['numero_edital']} não aplicado")
            
            if 'local_orgao' in teste['esperado']:
                total_mudancas += 1
                if re.search(teste['esperado']['local_orgao'], texto_completo):
                    mudancas_aplicadas += 1
                    print(f"   ✅ Local {teste['esperado']['local_orgao']} aplicado")
                else:
                    print(f"   ❌ Local {teste['esperado']['local_orgao']} não aplicado")
            
            if 'orgao' in teste['esperado']:
                total_mudancas += 1
                if re.search(teste['esperado']['orgao'], texto_completo):
                    mudancas_aplicadas += 1
                    print(f"   ✅ Órgão {teste['esperado']['orgao']} aplicado")
                else:
                    print(f"   ❌ Órgão {teste['esperado']['orgao']} não aplicado")
            
            if 'prazo_execucao' in teste['esperado']:
                total_mudancas += 1
                if re.search(teste['esperado']['prazo_execucao'] + r'\s*dias', texto_completo):
                    mudancas_aplicadas += 1
                    print(f"   ✅ Prazo {teste['esperado']['prazo_execucao']} dias aplicado")
                else:
                    print(f"   ❌ Prazo {teste['esperado']['prazo_execucao']} dias não aplicado")
            
            if 'adicionar_clausula' in teste['esperado']:
                total_mudancas += 1
                if re.search(r'garantia.*execução', texto_completo, re.IGNORECASE):
                    mudancas_aplicadas += 1
                    print(f"   ✅ Cláusula de garantia adicionada")
                else:
                    print(f"   ❌ Cláusula de garantia não adicionada")
            
            if 'nenhuma_mudanca' in teste['esperado']:
                # Verificar se não houve mudanças desnecessárias
                mudancas_nao_esperadas = 0
                if re.search(r'456/2024', texto_completo):
                    mudancas_nao_esperadas += 1
                if re.search(r'30/11/2024', texto_completo):
                    mudancas_nao_esperadas += 1
                if re.search(r'1\.500\.000', texto_completo):
                    mudancas_nao_esperadas += 1
                
                if mudancas_nao_esperadas == 0:
                    mudancas_aplicadas += 1
                    print(f"   ✅ Nenhuma mudança desnecessária aplicada")
                else:
                    print(f"   ❌ {mudancas_nao_esperadas} mudanças desnecessárias aplicadas")
                total_mudancas = 1
            
            # Verificar se referências legais foram preservadas
            referencias_preservadas = True
            if re.search(r'Lei\s+14\.456/2024', texto_completo):
                referencias_preservadas = False
                print(f"   ❌ Referência legal alterada incorretamente")
            
            if referencias_preservadas:
                print(f"   ✅ Referências legais preservadas")
            
            # Calcular score
            score = (mudancas_aplicadas / total_mudancas * 100) if total_mudancas > 0 else 100
            score_final = score if referencias_preservadas else score * 0.8  # Penalizar se referências foram alteradas
            
            print(f"   📊 Score: {score_final:.1f}%")
            
            resultados.append({
                'nome': teste['nome'],
                'score': score_final,
                'mudancas_aplicadas': mudancas_aplicadas,
                'total_mudancas': total_mudancas,
                'referencias_preservadas': referencias_preservadas
            })
            
        except Exception as e:
            print(f"   ❌ Erro: {e}")
            resultados.append({
                'nome': teste['nome'],
                'score': 0,
                'mudancas_aplicadas': 0,
                'total_mudancas': 1,
                'referencias_preservadas': False
            })
        
        print()
    
    # Resumo final
    print("📊 RESUMO FINAL DOS TESTES")
    print("=" * 60)
    
    scores = [r['score'] for r in resultados]
    score_medio = sum(scores) / len(scores)
    
    print(f"🎯 Score médio: {score_medio:.1f}%")
    print()
    
    for resultado in resultados:
        status = "✅" if resultado['score'] >= 80 else "⚠️" if resultado['score'] >= 60 else "❌"
        print(f"   {status} {resultado['nome']}: {resultado['score']:.1f}%")
    
    print()
    
    if score_medio >= 90:
        print("🎉 EXCELENTE! Sistema funcionando perfeitamente!")
    elif score_medio >= 80:
        print("✅ BOM! Sistema funcionando bem!")
    elif score_medio >= 70:
        print("⚠️ REGULAR! Sistema precisa de ajustes.")
    else:
        print("❌ RUIM! Sistema precisa de melhorias significativas.")
    
    print(f"\n📄 Documentos gerados em: {tmpdir}")
    print("🚀 Teste concluído!")

if __name__ == "__main__":
    teste_prompts_realistas()
