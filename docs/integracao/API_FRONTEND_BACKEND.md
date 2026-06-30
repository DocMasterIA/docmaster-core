# Conexão APIs Backend ↔ Frontend (Vue)

Referência das rotas de API do backend e onde são usadas no frontend Vue.

## Proxy (Vite)

- `/api` → `http://127.0.0.1:8000`
- `/media` → `http://127.0.0.1:8000` (fotos de perfil, previews, PDFs, documentos)

Com `VITE_API_URL` vazio, o frontend usa URLs relativas (`/api/...`, `/media/...`) e o proxy encaminha para o Django.

---

## Endpoints e uso no frontend

| Backend (Django) | Método | Frontend (Vue) | Observação |
|------------------|--------|----------------|------------|
| `api/auth/login/` | POST | `Login.vue` | JSON: email_or_username, password, remember. Resposta: ok, message |
| `api/auth/logout/` | POST | `App.vue` (botão Sair) | Sem body. Resposta: ok, message |
| `api/me/` | GET | `router/index.js` (guard), `Login.vue`, `AreaDoUsuario.vue` | Verifica sessão. Resposta: id, email, first_name, last_name, full_name, profile_photo, etc. |
| `api/me/` | POST | `AreaDoUsuario.vue` | FormData: first_name, last_name, profile_photo. Resposta: ok, message ou errors |
| `api/me/documents/` | GET | `AreaDoUsuario.vue` | Query: page, q. Resposta: results, count, num_pages, page, has_previous, has_next, start_index, end_index |
| `api/documentos_modelos/` | GET | `TemplateList.vue`, `DocumentGenerator.vue` | Sem query = lista; ?id= = detalhe. Resposta: templates[] ou template (id, name, preview_image) |
| `api/documentos_modelos/lista_10` | GET | `DocumentGenerator.vue` | Query: q. Resposta: templates[] (id, name) |
| `api/documentos_modelos/enviar` | POST | `DocumentGenerator.vue` | FormData: template_file, name. Resposta: ok, template_id, schema |
| `api/documentos_modelos/gerar` | POST | `DocumentGenerator.vue` | JSON: template_id, values: { prompt }, output: 'docx'|'pdf'. Resposta: arquivo binário (blob) |
| `api/documentos_modelos/<uuid>/pdf/` | GET | `DocumentGenerator.vue`, `TemplateList.vue` | Resposta: ok, pdf_url (ou error) |
| `api/llm/<path>` | GET/POST | (uso futuro) | **Proxy LLM**: exige sessão Django; repassa para FastAPI (planner, section, generate, health). Ex.: `api/llm/health`, `api/llm/generate` |

---

## Proxy LLM (FastAPI + IA)

- O frontend chama **Django** em `/api/llm/...` (mesmo cookie de sessão).
- O Django valida a sessão (`@api_login_required`) e repassa a requisição ao serviço FastAPI (`LLM_API_BASE_URL`, ex.: `http://127.0.0.1:8002`).
- Assim o uso do FastAPI+IA fica restrito a usuários autenticados; o FastAPI não precisa implementar autenticação.
- Configuração: `LLM_API_BASE_URL` em `settings.py` ou variável de ambiente.

---

## URLs de mídia

- Backend retorna URLs relativas (ex.: `/media/profile_photos/xxx.jpg`, `/media/previews/xxx.png`).
- Frontend usa `API_BASE + url` (com `API_BASE` vazio em dev, fica `/media/...`).
- O proxy `/media` no Vite encaminha para o Django; imagens e arquivos carregam na mesma origem (5173).

---

## Autenticação

- APIs protegidas usam `@api_login_required` e retornam **401** com `{"error": "Não autenticado. Faça login."}` quando não há sessão.
- O router Vue chama `GET /api/me/` antes de rotas não públicas; se 401, redireciona para `/login?redirect=...`.
