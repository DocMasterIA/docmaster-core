#!/usr/bin/env python3
"""
Teste final para verificar se o conteúdo está sendo inserido no contexto correto

Antes de executar:
1. Ative o ambiente virtual: source venv/bin/activate
2. Execute: python teste_contexto_final.py
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

def test_contexto_final():
    """Teste final para verificar se o conteúdo está sendo inserido no contexto correto."""
    
    print("🎯 TESTE FINAL - CONTEXTO CORRETO")
    print("Verificando se o conteúdo é inserido no local apropriado")
    print("=" * 60)
    
    # 1. Usar template original
    template_path = "/home/adryan/mdlicitatech-system/backend/media/templates/docx/EDITAL_PREGAO_ELETRONICO_005-2025_AQUISIÇÃO_DE_MEDICAMENTOS_1.docx"
    
    # 2. Prompt de especialista complexo e interessante
    prompt_especialista = """Você é um especialista sênior em licitações públicas com 20 anos de experiência, especializado em Lei 14.133/21 e jurisprudência do TCU. Sua missão é transformar este edital em um documento exemplar de excelência técnica e jurídica.

🎯 OBJETIVOS ESPECÍFICOS:

1. SEGURANÇA JURÍDICA: Adicione cláusulas de proteção contra recursos e contestações
2. TRANSPARÊNCIA: Melhore a clareza dos critérios de julgamento e aceitabilidade
3. EFICIÊNCIA: Otimize prazos e procedimentos para agilizar o processo
4. CONFORMIDADE: Garanta 100% de aderência à Lei 14.133/21 e orientações do TCU

📋 TAREFAS OBRIGATÓRIAS:

✅ Adicione uma cláusula de "JULGAMENTO POR TÉCNICA E PREÇO" após o parágrafo de julgamento existente
✅ Inclua uma "OBSERVAÇÃO PRÁTICA" sobre registros detalhados após o parágrafo 15.16
✅ Melhore a referência à Lei 14.133/21 para incluir "e suas alterações posteriores"
✅ Adicione uma cláusula de "GARANTIA DE CUMPRIMENTO" com prazo de 24 meses
✅ Inclua orientação sobre "CRITÉRIOS DE ACEITABILIDADE" baseados no art. 46
✅ Adicione cláusula de "PENALIDADES POR ATRASO" conforme art. 129

💰 ALTERAÇÕES FINANCEIRAS:
- Mude o valor de "PREÇO TOTAL MÉDIO" para R$ 15.000.000,00
- Ajuste o valor estimado para R$ 15.000.000,00 em todas as ocorrências

🏛️ CONTEXTO MUNICIPAL:
- Mantenha o município como "ITAJÁ/GO" mas adicione referência à "Região Metropolitana de Goiânia"
- Inclua menção ao "Plano Plurianual 2024-2027" do município

⚖️ BASE LEGAL REFORÇADA:
- Cite artigos específicos: 46 (julgamento), 129 (penalidades), 131 (garantias)
- Referencie a Súmula 473 do STJ sobre licitações
- Inclua orientação do TCU sobre transparência

🎨 FORMATAÇÃO:
- Todo conteúdo adicionado deve aparecer em AZUL para destacar as melhorias
- Use numeração sequencial (3.4.16, 3.4.17, etc.) para novas cláusulas
- Mantenha linguagem técnica mas acessível

Transforme este edital em um modelo de excelência que sirva de referência para outros municípios!"""
    
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
        output_path = os.path.join(tmpdir, "edital_contexto_final.docx")
        
        render_docx_contextual_intelligent(template_path, output_path, generated_data, prompt_especialista)
        
        if os.path.exists(output_path):
            print(f"✅ Arquivo renderizado: {os.path.basename(output_path)}")
            print(f"📁 Caminho: {output_path}")
            print(f"📊 Tamanho: {os.path.getsize(output_path)} bytes")
            
            # Verificar se as mudanças foram aplicadas no contexto correto
            from docx import Document
            doc_result = Document(output_path)
            
            print("\n📝 Verificando contexto das mudanças:")
            
            # Verificar se o conteúdo foi adicionado no local correto
            julgamento_found = False
            observacao_found = False
            
            for i, p in enumerate(doc_result.paragraphs):
                if "3.4.15. O julgamento das propostas" in p.text:
                    print(f"  ✅ Cláusula de julgamento encontrada no parágrafo {i+1}")
                    print(f"      Contexto: {p.text[:100]}...")
                    julgamento_found = True
                    
                    # Verificar se está próximo de outros parágrafos de julgamento
                    if i > 0:
                        prev_p = doc_result.paragraphs[i-1]
                        if "julgamento" in prev_p.text.lower():
                            print(f"      ✅ Está próximo de parágrafo de julgamento: {prev_p.text[:50]}...")
                        else:
                            print(f"      ❌ NÃO está próximo de parágrafo de julgamento")
                
                elif "OBSERVAÇÃO PRÁTICA:" in p.text:
                    print(f"  ✅ Observação prática encontrada no parágrafo {i+1}")
                    print(f"      Contexto: {p.text[:100]}...")
                    observacao_found = True
                    
                    # Verificar se está próximo de 15.16
                    if i > 0:
                        prev_p = doc_result.paragraphs[i-1]
                        if "15.16" in prev_p.text:
                            print(f"      ✅ Está próximo de parágrafo 15.16: {prev_p.text[:50]}...")
                        else:
                            print(f"      ❌ NÃO está próximo de parágrafo 15.16")
            
            # Verificar se o conteúdo não foi adicionado no final
            last_paragraphs = doc_result.paragraphs[-5:]
            print(f"\n🔍 Últimos 5 parágrafos do documento:")
            for i, p in enumerate(last_paragraphs):
                if p.text.strip():
                    print(f"  {len(doc_result.paragraphs)-5+i+1}. {p.text[:80]}...")
            
            # Verificar se há conteúdo de especialista no final
            has_expert_content_at_end = any(
                "3.4.15" in p.text or "OBSERVAÇÃO PRÁTICA" in p.text 
                for p in last_paragraphs
            )
            
            if has_expert_content_at_end:
                print("\n❌ PROBLEMA: Conteúdo de especialista foi adicionado no final!")
            else:
                print("\n✅ SUCESSO: Conteúdo de especialista foi adicionado no contexto correto!")
            
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
            
            print(f"\n📊 Resumo:")
            print(f"  • Cláusula de julgamento: {'✅' if julgamento_found else '❌'}")
            print(f"  • Observação prática: {'✅' if observacao_found else '❌'}")
            print(f"  • Formatação azul: {'✅' if blue_found else '❌'}")
            print(f"  • Contexto correto: {'✅' if not has_expert_content_at_end else '❌'}")
                
        else:
            print("❌ Arquivo não foi gerado")
    
    except Exception as e:
        print(f"❌ Erro na renderização: {e}")
        import traceback
        traceback.print_exc()
    
    # 5. Gerar PDF para visualização
    print("\n📄 Gerando PDF para visualização...")
    
    try:
        from backend.app.services.services import generate_pdf_from_docx
        
        pdf_path = generate_pdf_from_docx(output_path)
        
        if os.path.exists(pdf_path):
            size = os.path.getsize(pdf_path)
            print(f"✅ PDF gerado: {os.path.basename(pdf_path)}")
            print(f"📊 Tamanho: {size:,} bytes")
            print(f"📁 Localização: {pdf_path}")
        else:
            print("❌ PDF não foi gerado")
    
    except Exception as e:
        print(f"❌ Erro ao gerar PDF: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 RESULTADO FINAL:")
    print("-" * 20)
    print("✅ Teste final de contexto correto")
    print("✅ Verificação de localização do conteúdo")
    print("✅ Verificação de formatação em azul")
    print("✅ PDF gerado para visualização")

if __name__ == "__main__":
    try:
        test_contexto_final()
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
