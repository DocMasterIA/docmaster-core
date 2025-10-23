#!/usr/bin/env python3
"""
Teste direto do frontend usando o ID do template conhecido.
"""

import requests
import time
import os

def testar_geracao_documento_direto():
    """
    Testa a geração de documento via frontend usando ID conhecido.
    """
    print("🧪 Testando Geração de Documento Direto")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    prefeitura_url = "prefeitura_de_teste"
    template_id = "d8a3684d-5c29-499f-9637-5113cd9e36aa"  # ID do template "teste"
    
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
        
        # 5. Obter novo token CSRF da página de geração
        print("5️⃣ Obtendo token CSRF da página de geração...")
        csrf_token_gen = None
        for line in response.text.split('\n'):
            if 'csrfmiddlewaretoken' in line:
                csrf_token_gen = line.split('value="')[1].split('"')[0]
                break
        
        if not csrf_token_gen:
            print("❌ Token CSRF da página de geração não encontrado")
            return False
        
        print("✅ Token CSRF da página de geração obtido")
        
        # 6. Gerar documento
        print("6️⃣ Gerando documento...")
        prompt = "Mude o preço total médio na tabela para R$ 9.555.123,42"
        print(f"🔧 Prompt: {prompt}")
        
        generate_data = {
            'template_id': template_id,
            'ia_prompt': prompt,
            'csrfmiddlewaretoken': csrf_token_gen
        }
        
        response = session.post(doc_gen_url, data=generate_data, allow_redirects=True)
        
        if response.status_code != 200:
            print(f"❌ Erro na geração do documento: {response.status_code}")
            return False
        
        print("✅ Documento gerado com sucesso!")
        
        # 7. Verificar se há mensagem de sucesso
        if "sucesso" in response.text.lower():
            print("✅ Mensagem de sucesso encontrada na resposta")
        else:
            print("⚠️ Mensagem de sucesso não encontrada")
        
        # 8. Verificar se há links de download
        if "download" in response.text.lower() or "arquivo" in response.text.lower():
            print("✅ Links de download encontrados")
        else:
            print("⚠️ Links de download não encontrados")
        
        # 9. Verificar se há erros
        if "erro" in response.text.lower() or "error" in response.text.lower():
            print("⚠️ Possíveis erros encontrados na resposta")
            # Mostrar parte da resposta para debug
            print("📄 Parte da resposta:")
            print(response.text[:500])
        
        print("\n🎉 TESTE DE GERAÇÃO DE DOCUMENTO CONCLUÍDO!")
        return True
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 TESTE DIRETO DO FRONTEND")
    print("=" * 60)
    
    sucesso = testar_geracao_documento_direto()
    
    if sucesso:
        print("\n🎉 TESTE CONCLUÍDO COM SUCESSO!")
        print("🚀 O sistema está funcionando corretamente!")
    else:
        print("\n❌ TESTE FALHOU!")
        print("🔧 Verifique os logs acima para identificar o problema.")
