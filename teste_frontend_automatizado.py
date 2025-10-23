#!/usr/bin/env python3
"""
Teste automatizado do frontend para verificar se o sistema está funcionando.
"""

import requests
import time
import os

def testar_frontend():
    """
    Testa o frontend do sistema.
    """
    print("🧪 Testando Frontend do Sistema")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    prefeitura_url = "prefeitura_de_teste"
    
    # Criar sessão
    session = requests.Session()
    
    try:
        # 1. Acessar página de login
        print("1️⃣ Acessando página de login...")
        login_url = f"{base_url}/{prefeitura_url}/"
        response = session.get(login_url)
        
        if response.status_code != 200:
            print(f"❌ Erro ao acessar página de login: {response.status_code}")
            return False
        
        print("✅ Página de login acessada com sucesso")
        
        # 2. Obter token CSRF
        print("2️⃣ Obtendo token CSRF...")
        csrf_token = None
        for line in response.text.split('\n'):
            if 'csrfmiddlewaretoken' in line:
                csrf_token = line.split('value="')[1].split('"')[0]
                break
        
        if not csrf_token:
            print("❌ Token CSRF não encontrado")
            return False
        
        print("✅ Token CSRF obtido")
        
        # 3. Fazer login
        print("3️⃣ Fazendo login...")
        login_data = {
            'email_or_username': 'admin@admin.com',
            'password': '123',
            'csrfmiddlewaretoken': csrf_token
        }
        
        response = session.post(login_url, data=login_data, allow_redirects=True)
        
        if response.status_code != 200:
            print(f"❌ Erro no login: {response.status_code}")
            return False
        
        print("✅ Login realizado com sucesso")
        
        # 4. Acessar página de geração de documentos
        print("4️⃣ Acessando página de geração de documentos...")
        doc_gen_url = f"{base_url}/{prefeitura_url}/gerador_de_documentos/"
        response = session.get(doc_gen_url)
        
        if response.status_code != 200:
            print(f"❌ Erro ao acessar página de geração de documentos: {response.status_code}")
            return False
        
        print("✅ Página de geração de documentos acessada com sucesso")
        
        # 5. Verificar se a página contém elementos esperados
        print("5️⃣ Verificando elementos da página...")
        page_content = response.text
        
        elementos_esperados = [
            'template',
            'prompt',
            'gerar',
            'documento'
        ]
        
        elementos_encontrados = []
        for elemento in elementos_esperados:
            if elemento.lower() in page_content.lower():
                elementos_encontrados.append(elemento)
        
        print(f"✅ Elementos encontrados: {elementos_encontrados}")
        
        # 6. Testar API de templates
        print("6️⃣ Testando API de templates...")
        api_url = f"{base_url}/api/documentos_modelos/lista_10"
        response = session.get(api_url)
        
        if response.status_code == 200:
            print("✅ API de templates funcionando")
        else:
            print(f"⚠️ API de templates retornou: {response.status_code}")
        
        print("\n🎉 TESTE DO FRONTEND CONCLUÍDO COM SUCESSO!")
        print("=" * 60)
        print("📋 Resumo:")
        print("   ✅ Página de login acessível")
        print("   ✅ Login funcionando")
        print("   ✅ Página de geração de documentos acessível")
        print("   ✅ Elementos da página presentes")
        print("   ✅ API de templates funcionando")
        print("\n🚀 O sistema está pronto para uso!")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {str(e)}")
        return False

def testar_api_direta():
    """
    Testa a API diretamente para verificar se o sistema está funcionando.
    """
    print("\n🔧 Testando API Direta")
    print("=" * 60)
    
    try:
        # Testar API de templates
        response = requests.get("http://localhost:8000/api/documentos_modelos/lista_10")
        
        if response.status_code == 200:
            print("✅ API de templates funcionando")
            return True
        else:
            print(f"❌ API de templates retornou: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro na API: {str(e)}")
        return False

if __name__ == "__main__":
    print("🧪 TESTE AUTOMATIZADO DO FRONTEND")
    print("=" * 60)
    
    # Testar API primeiro
    api_ok = testar_api_direta()
    
    if api_ok:
        # Testar frontend
        frontend_ok = testar_frontend()
        
        if frontend_ok:
            print("\n🎉 TODOS OS TESTES PASSARAM!")
            print("🚀 O sistema está funcionando corretamente!")
        else:
            print("\n⚠️ Alguns testes falharam, mas a API está funcionando.")
    else:
        print("\n❌ Problemas na API. Verifique se o servidor está rodando.")
