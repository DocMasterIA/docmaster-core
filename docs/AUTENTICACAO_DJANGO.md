# Autenticação no sistema Django (DocMaster IA)

Visão geral de como a autenticação está implementada no backend Django e na integração com o frontend Vue.

---

## 1. Configuração base (settings)

| Setting | Valor | Função |
|--------|--------|--------|
| **AUTH_USER_MODEL** | `"app.User"` | Modelo de usuário customizado (email como USERNAME_FIELD, prefeitura, role, etc.). |
| **LOGIN_URL** | `'/login'` | Usado pelo `login_required` do Django para redirect quando não autenticado (views HTML). |
| **Session** | Padrão Django | `SessionMiddleware` + `AuthenticationMiddleware`; sessão em banco (db.sqlite3) por padrão. |
| **CSRF** | `CsrfViewMiddleware` ativo | APIs de login/logout e outras que o frontend chama usam `@csrf_exempt` para aceitar POST sem token CSRF. |

**CORS** está configurado via `django-cors-headers`. Em desenvolvimento (DEBUG=True), as origens `http://localhost:5173` e `http://127.0.0.1:5173` são permitidas. Em produção, defina a variável de ambiente `CORS_ALLOWED_ORIGINS` com as origens separadas por vírgula (ex.: `https://app.exemplo.com`). O frontend usa `credentials: 'include'`, por isso `CORS_ALLOW_CREDENTIALS = True` está ativo.

---

## 2. Modelo de usuário

- **Classe:** `backend.app.models.usuario.User` (herda `AbstractBaseUser`, `PermissionsMixin`).
- **Login:** por **email** (ou username, conforme `LoginForm`).
- **Campos relevantes:** `email`, `password`, `first_name`, `last_name`, `is_active`, `is_staff`, `prefeitura` (FK), `role`, `profile_photo`, etc.
- **Autenticação:** `authenticate(request, username=..., password=...)` — o `username` pode ser o email normalizado ou o próprio username; o `LoginForm` resolve email → username quando o usuário digita email.

---

## 3. APIs de autenticação (uso pelo Vue)

### 3.1 Login — `POST /api/auth/login/`

- **View:** `api_auth_login` em `backend/app/api.py`.
- **Decorators:** `@csrf_exempt` (sem CSRF).
- **Body JSON:** `email_or_username`, `password`, `remember` (opcional).
- **Fluxo:**
  1. Valida presença de `email_or_username` e `password`.
  2. Se já autenticado → retorna `{ "ok": true, "message": "Já autenticado." }`.
  3. Resolve **prefeitura** (por `prefeitura_url` no body ou primeira do banco).
  4. **Proteção contra abuso:** `get_client_ip`, `is_locked(ip_key)` e `is_locked(user_key)` — após **6 tentativas** (por IP ou por usuário), bloqueia por **15 minutos** (`backend/app/utils/utils.py`: `MAX_ATTEMPTS`, `LOCK_MINUTES`, cache).
  5. Valida credenciais com **LoginForm** (email ou username + password, usuário ativo).
  6. Se usuário não é staff/superuser, verifica se `user.prefeitura_id == prefeitura.id`; se não, 403.
  7. Se usuário estava bloqueado, 429; senão limpa contadores de falha.
  8. `auth_login(request, user)` → cria sessão.
  9. Se `remember`: `session.set_expiry(30 dias)`; senão: `session.set_expiry(0)` (sessão ao fechar o navegador).
  10. Resposta: `{ "ok": true, "message": "...", "prefeitura_url": "..." }`.
- **Erros:** 400 (dados inválidos/prefeitura), 401 (credenciais), 403 (usuário de outra prefeitura), 429 (bloqueio ou rate limit), 503 (sem prefeitura).

### 3.2 Logout — `POST /api/auth/logout/`

- **View:** `api_auth_logout`.
- **Decorators:** `@csrf_exempt`.
- **Corpo:** não usado.
- **Ação:** `auth_logout(request)` → invalida sessão.
- **Resposta:** `{ "ok": true, "message": "Logout realizado." }`.

### 3.3 Verificação de sessão / perfil — `GET /api/me/`

- **View:** `api_me` (GET).
- **Proteção:** `@api_login_required` — se não autenticado, retorna **401** com `{ "error": "Não autenticado. Faça login." }`.
- **Resposta (200):** JSON com `id`, `email`, `first_name`, `last_name`, `full_name`, `role`, `date_joined`, `is_staff`, `profile_photo`, `secretaria`, `prefeitura`, etc.
- **Uso no frontend:** router guard chama `GET /api/me/` com `credentials: 'include'`; se 200 → considerado logado; se 401 ou erro → redireciona para `/login?redirect=...`.

---

## 4. Proteção das demais APIs

- **Decorator:** `api_login_required` em `backend/app/api.py`.
- **Comportamento:** antes de executar a view, verifica `request.user.is_authenticated`. Se **False**, responde com **401** e JSON `{ "error": "Não autenticado. Faça login." }` (sem redirect).
- **Views protegidas (exemplos):** upload de template, lista/detalhe de templates, gerar documento, lista_10, preview PDF, `api_me` (GET/POST), `api_me_documents`.

O Django popula `request.user` via **AuthenticationMiddleware** usando o **sessionid** enviado no cookie. Com proxy, o navegador envia o cookie para o mesmo host (Vite); o proxy repassa o cookie para o Django.

---

## 5. Fluxo no frontend Vue

1. **Login:** `POST /api/auth/login/` com `credentials: 'include'` e body JSON → Django define sessão e envia `Set-Cookie` (sessionid) na resposta.
2. **Rotas protegidas:** antes de cada rota não pública, o guard faz `GET /api/me/` com `credentials: 'include'`. Se 200 → segue; se 401 → redireciona para `/login?redirect=...`.
3. **Logout:** botão na topbar chama `POST /api/auth/logout/` com `credentials: 'include'` e em seguida `router.push('/login')`.
4. **Página de login:** ao montar, chama `GET /api/me/`; se 200 → redireciona para home ou `redirect` (já logado).

---

## 6. Login por prefeitura (views HTML legadas)

- **URL:** `/<prefeitura_url>/` → `LoginView` (template `login_portal.html`).
- **Fluxo:** formulário HTML, `LoginForm`, mesma lógica de prefeitura e bloqueio; `auth_login` + `session.set_expiry`; redirect para dashboard da prefeitura.
- **Logout:** `/<prefeitura_url>/logout` → `LogoutView` → `auth_logout` + redirect para login da prefeitura ou `login_global`.

A API de login (`/api/auth/login/`) não exige `prefeitura_url` no body; se não for enviado, usa a primeira prefeitura do banco.

---

## 7. Resumo

| Aspecto | Implementação |
|---------|----------------|
| **Identificação** | Sessão Django (cookie `sessionid`). |
| **Quem pode acessar** | Usuário com sessão válida; APIs protegidas com `@api_login_required` (401 se não autenticado). |
| **Login** | `POST /api/auth/login/` (JSON); validação por email ou username; vínculo com prefeitura; bloqueio por tentativas. |
| **Logout** | `POST /api/auth/logout/`; invalida sessão. |
| **Verificação** | `GET /api/me/` com cookie; frontend usa para guard de rota. |
| **CSRF** | Desabilitado nas views de auth/API usadas pelo Vue (`@csrf_exempt`). |
| **CORS** | Não configurado; depende do proxy em dev; em produção configurar CORS + credenciais. |
