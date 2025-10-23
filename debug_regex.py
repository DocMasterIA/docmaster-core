#!/usr/bin/env python3
"""
Debug específico do regex para entender por que ainda detecta 13.4.x
"""

import re

def testar_regex():
    """Testa diferentes padrões de regex."""
    
    print("🔍 DEBUG DO REGEX")
    print("=" * 40)
    
    # Textos de teste
    textos_teste = [
        "3.4.1. A partir do horário previsto no Edital",
        "13.4.1. Para as infrações previstas nos itens",
        "13.4.2. Para as infrações previstas nos itens",
        "3.4.16. Constatando o atendimento das exigências",
        "23.4.5. Algum texto aqui",
        "3.4. ABERTURA DAS PROPOSTAS",
        "9.3.4. o prazo para apresentação das razões"
    ]
    
    # Padrões de regex para testar
    padroes = [
        (r'3\.4\.(\d+)', "Padrão original"),
        (r'(?<!\d)3\.4\.(\d+)', "Padrão com lookbehind"),
        (r'^3\.4\.(\d+)', "Padrão com início de linha"),
        (r'(?<![0-9])3\.4\.(\d+)', "Padrão com lookbehind numérico"),
        (r'\b3\.4\.(\d+)', "Padrão com word boundary"),
        (r'(?<!\d)3\.4\.(\d+)', "Padrão com lookbehind (sem dígito)"),
    ]
    
    for texto in textos_teste:
        print(f"\n📝 Texto: {texto}")
        print("-" * 50)
        
        for padrao, descricao in padroes:
            try:
                match = re.search(padrao, texto)
                if match:
                    print(f"   ✅ {descricao}: {match.group(1)}")
                else:
                    print(f"   ❌ {descricao}: Nenhum match")
            except Exception as e:
                print(f"   ⚠️ {descricao}: Erro - {e}")

if __name__ == "__main__":
    testar_regex()
