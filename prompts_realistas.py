#!/usr/bin/env python3
"""
Prompts realistas baseados no conteúdo real do template.
"""

# Prompts baseados no conteúdo real do documento
PROMPTS_REALISTAS = [
    {
        "nome": "Alteração de Número do Edital",
        "prompt": "Altere o número do edital de 014/2025 para 456/2024"
    },
    {
        "nome": "Alteração de Número do Pregão",
        "prompt": "Mude o número do pregão de 005/2025 para 789/2024"
    },
    {
        "nome": "Alteração de Local",
        "prompt": "Altere todas as referências de ITAJÁ para BRASÍLIA no documento"
    },
    {
        "nome": "Alteração de Data",
        "prompt": "Mude a data de 28 de julho de 2025 para 15 de agosto de 2024"
    },
    {
        "nome": "Alteração de Objeto",
        "prompt": "Altere o objeto de 'Aquisição de Medicamentos' para 'Aquisição de Equipamentos de TI'"
    },
    {
        "nome": "Adição de Cláusula",
        "prompt": "Adicione uma cláusula sobre garantia de execução no valor de 5% do contrato"
    },
    {
        "nome": "Alteração de Prazo",
        "prompt": "Altere o prazo de entrega de 10 dias para 15 dias"
    },
    {
        "nome": "Alteração de Modalidade",
        "prompt": "Mude a modalidade de 'PREGÃO ELETRÔNICO SRP' para 'TOMADA DE PREÇOS'"
    },
    {
        "nome": "Alteração de CNPJ",
        "prompt": "Altere o CNPJ de 02.186.757/0001-47 para 12.345.678/0001-90"
    },
    {
        "nome": "Adição de Penalidade",
        "prompt": "Adicione uma cláusula sobre multa de 0,5% por dia de atraso"
    }
]

def mostrar_prompts():
    """
    Mostra todos os prompts realistas baseados no documento.
    """
    print("🎯 Prompts Realistas Baseados no Template:")
    print("=" * 60)
    
    for i, prompt_info in enumerate(PROMPTS_REALISTAS, 1):
        print(f"{i:2d}. {prompt_info['nome']}")
        print(f"    Prompt: {prompt_info['prompt']}")
        print()
    
    print("💡 Como usar:")
    print("1. Copie qualquer um dos prompts acima")
    print("2. Cole no campo 'Prompt de Inteligência Artificial'")
    print("3. Clique em 'Gerar com IA'")
    print("4. Baixe o documento modificado")

if __name__ == "__main__":
    mostrar_prompts()
