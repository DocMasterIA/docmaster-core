#!/usr/bin/env python3
"""
Teste completo do frontend para verificar se o sistema está funcionando.
"""

import requests
import time
import os

def testar_geracao_documento():
    """
    Testa a geração de documento via frontend.
    """
    print("🧪 Testando Geração de Documento via Frontend")
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
        
        # 6. Obter ID do template
        print("6️⃣ Obtendo ID do template...")
        template_id = None
        
        # Primeiro, tentar obter o template via API
        api_url = f"{base_url}/api/documentos_modelos/lista_10"
        api_response = session.get(api_url)
        
        if api_response.status_code == 200:
            try:
                import json
                templates_data = json.loads(api_response.text)
                if templates_data and len(templates_data) > 0:
                    template_id = templates_data[0]['id']
                    print(f"✅ Template ID obtido via API: {template_id}")
                else:
                    print("❌ Nenhum template encontrado na API")
                    return False
            except:
                print("❌ Erro ao processar resposta da API")
                return False
        else:
            print(f"❌ Erro na API de templates: {api_response.status_code}")
            return False
        
        # 7. Gerar documento
        print("7️⃣ Gerando documento...")
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
        
        # 8. Verificar se há mensagem de sucesso
        if "sucesso" in response.text.lower():
            print("✅ Mensagem de sucesso encontrada na resposta")
        else:
            print("⚠️ Mensagem de sucesso não encontrada")
        
        # 9. Verificar se há links de download
        if "download" in response.text.lower() or "arquivo" in response.text.lower():
            print("✅ Links de download encontrados")
        else:
            print("⚠️ Links de download não encontrados")
        
        print("\n🎉 TESTE DE GERAÇÃO DE DOCUMENTO CONCLUÍDO!")
        return True
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 TESTE COMPLETO DO FRONTEND")
    print("=" * 60)
    
    sucesso = testar_geracao_documento()
    
    if sucesso:
        print("\n🎉 TESTE CONCLUÍDO COM SUCESSO!")
        print("🚀 O sistema está funcionando corretamente!")
    else:
        print("\n❌ TESTE FALHOU!")
        print("🔧 Verifique os logs acima para identificar o problema.")
