#!/usr/bin/env python3
"""
Teste específico para cláusulas específicas baseadas no prompt do cliente
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

def teste_clausulas_especificas():
    """Teste específico para cláusulas específicas."""
    
    print("⚖️ TESTE DE CLÁUSULAS ESPECÍFICAS")
    print("=" * 60)
    print("Testando geração de cláusulas baseadas no prompt do cliente")
    print()
    
    # Buscar template
    template = Template.objects.first()
    if not template:
        print("❌ Nenhum template encontrado!")
        return
    
    print(f"✅ Template: {template.name}")
    print()
    
    # Prompts específicos para testar cláusulas
    prompts_teste = [
        {
            "nome": "Cláusula de Garantia de Execução",
            "prompt": "Aja como um especialista em licitações públicas e na Lei 14.133/21. Adicione uma cláusula de garantia de execução.",
            "esperado": "garantia de execução"
        },
        {
            "nome": "Cláusula de Penalidade por Atraso",
            "prompt": "Aja como um especialista em licitações públicas e na Lei 14.133/21. Inclua cláusula de penalidade por atraso.",
            "esperado": "penalidade por atraso"
        },
        {
            "nome": "Cláusula de Critério de Desempate",
            "prompt": "Aja como um especialista em licitações públicas e na Lei 14.133/21. Adicione uma cláusula sobre critério de desempate.",
            "esperado": "critério de desempate"
        },
        {
            "nome": "Cláusula de Prazo de Entrega",
            "prompt": "Aja como um especialista em licitações públicas e na Lei 14.133/21. Inclua cláusula de prazo de entrega.",
            "esperado": "prazo de entrega"
        },
        {
            "nome": "Cláusula Genérica - Qualidade",
            "prompt": "Aja como um especialista em licitações públicas e na Lei 14.133/21. Adicione uma cláusula sobre qualidade dos produtos.",
            "esperado": "qualidade dos produtos"
        },
        {
            "nome": "Múltiplas Cláusulas",
            "prompt": "Aja como um especialista em licitações públicas e na Lei 14.133/21. Adicione cláusulas de garantia de execução e penalidade por atraso.",
            "esperado": ["garantia de execução", "penalidade por atraso"]
        }
    ]
    
    resultados = []
    
    for i, teste in enumerate(prompts_teste, 1):
        print(f"🧪 TESTE {i}: {teste['nome']}")
        print("-" * 50)
        
        try:
            # Gerar dados
            data = generate_document_data_from_prompt(template, teste['prompt'])
            
            print(f"📊 Cláusulas específicas detectadas: {len(data.get('clausulas_especificas', []))}")
            for clausula in data.get('clausulas_especificas', []):
                print(f"   • {clausula['tipo']}: {clausula['descricao']}")
            
            # Renderizar documento
            tmpdir = tempfile.gettempdir()
            output_path = os.path.join(tmpdir, f"teste_clausula_{i}_{template.id}.docx")
            
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
            
            # Verificar se as cláusulas foram adicionadas
            clausulas_encontradas = 0
            total_clausulas = 1 if isinstance(teste['esperado'], str) else len(teste['esperado'])
            
            if isinstance(teste['esperado'], str):
                # Cláusula única
                if re.search(teste['esperado'], texto_completo, re.IGNORECASE):
                    clausulas_encontradas += 1
                    print(f"   ✅ Cláusula '{teste['esperado']}' encontrada")
                else:
                    print(f"   ❌ Cláusula '{teste['esperado']}' não encontrada")
            else:
                # Múltiplas cláusulas
                for clausula_esperada in teste['esperado']:
                    if re.search(clausula_esperada, texto_completo, re.IGNORECASE):
                        clausulas_encontradas += 1
                        print(f"   ✅ Cláusula '{clausula_esperada}' encontrada")
                    else:
                        print(f"   ❌ Cláusula '{clausula_esperada}' não encontrada")
            
            # Verificar se contém base legal
            base_legal_encontrada = bool(re.search(r'Lei\s+14\.133/2021', texto_completo))
            print(f"   {'✅' if base_legal_encontrada else '❌'} Base legal Lei 14.133/2021: {'Encontrada' if base_legal_encontrada else 'Não encontrada'}")
            
            # Calcular score
            score = (clausulas_encontradas / total_clausulas * 100)
            if base_legal_encontrada:
                score = min(score * 1.1, 100)  # Bonus por base legal
            
            print(f"   📊 Score: {score:.1f}%")
            
            resultados.append({
                'nome': teste['nome'],
                'score': score,
                'clausulas_encontradas': clausulas_encontradas,
                'total_clausulas': total_clausulas,
                'base_legal': base_legal_encontrada
            })
            
        except Exception as e:
            print(f"   ❌ Erro: {e}")
            resultados.append({
                'nome': teste['nome'],
                'score': 0,
                'clausulas_encontradas': 0,
                'total_clausulas': 1,
                'base_legal': False
            })
        
        print()
    
    # Resumo final
    print("📊 RESUMO FINAL DOS TESTES DE CLÁUSULAS")
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
        print("🎉 EXCELENTE! Sistema de cláusulas funcionando perfeitamente!")
    elif score_medio >= 80:
        print("✅ BOM! Sistema de cláusulas funcionando bem!")
    elif score_medio >= 70:
        print("⚠️ REGULAR! Sistema de cláusulas precisa de ajustes.")
    else:
        print("❌ RUIM! Sistema de cláusulas precisa de melhorias significativas.")
    
    print(f"\n📄 Documentos gerados em: {tmpdir}")
    print("🚀 Teste de cláusulas concluído!")

if __name__ == "__main__":
    teste_clausulas_especificas()
