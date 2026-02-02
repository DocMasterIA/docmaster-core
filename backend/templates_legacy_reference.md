# Backend templates – legacy reference

This file records **page context, JavaScript, partials, and integration points** of the Django templates under `backend/templates/`, for reuse when rebuilding the UI (e.g. in the Vue.js frontend). Design/CSS is not preserved.

---

## Template layout

```
backend/templates/
├── login_portal.html       # Login (multi-tenant by prefeitura)
├── register_portal.html    # User registration
├── dashboard.html          # Post-login dashboard
├── area_do_usuario.html    # User area (profile + documents list)
├── document_generator.html # Document wizard + template picker + IA prompt
├── template_list.html     # Biblioteca de templates (filter + grid + PDF modal)
├── password_reset.html    # (empty in repo)
├── test.html              # (empty in repo)
├── partials/
│   └── history_docs_ajax.html  # Fragment for AJAX doc list + pagination
└── admin/
    └── index.html         # Custom admin dashboard (Chart.js)
```

---

## 1. `login_portal.html`

**Purpose:** Tenant-scoped login. Rendered for a given `prefeitura` (URL slug).

**Django context (expected):**
- `prefeitura` – object with at least `url` (slug) and possibly `nome_municipio`
- `form` – Django form with: `email_or_username`, `password`, `remember`; `non_field_errors`; field errors

**URLs / forms:**
- Form `action`: `{% url 'login_panel' prefeitura_url=prefeitura.url %}`
- Link “Cadastre-se”: `{% url 'registro_panel' %}`
- Link “Precisa de ajuda?”: `{% url 'dashboard' prefeitura_url=prefeitura.url %}`

**Static:** `{% static 'logo_licita.png' %}`, `{% static 'css/main.css' %}`

**Key HTML structure:**
- Form id: `loginForm`
- Inputs: `email_or_username`, `password`; optional `remember`
- Button: submit “Entrar na Plataforma”
- Optional: commented block for Django `messages` (success/error)

**JavaScript (inline):**

```js
function togglePassword(id, btn) {
    const input = document.getElementById(id);
    if (input.type === "password") {
        input.type = "text";
    } else {
        input.type = "password";
    }
}

document.addEventListener('DOMContentLoaded', function() {
  const inputs = document.querySelectorAll('.form-input');
  inputs.forEach(input => {
    if (input.value && input.value.trim() !== '') {
      input.parentElement.classList?.add('focused');
    }
    input.addEventListener('focus', () => input.parentElement.classList?.add('focused'));
    input.addEventListener('blur', () => {
      if (!input.value || input.value.trim() === '') {
        input.parentElement.classList?.remove('focused');
      }
    });
  });

  const form = document.getElementById('loginForm');
  form.addEventListener('submit', function(e) {
    form.classList.remove('loading');
  });
});

document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('loginForm');
  const inputs = document.querySelectorAll('.form-input');

  inputs.forEach(input => {
    input.addEventListener('focus', function () { this.parentElement.classList.add('focused'); });
    input.addEventListener('blur', function () {
      if (!this.value) this.parentElement.classList.remove('focused');
    });
    if (input.value) input.parentElement.classList.add('focused');
  });

  form.addEventListener('submit', function (e) {
    const emailOrUser = document.getElementById('email_or_username').value.trim();
    const password = document.getElementById('password').value.trim();
    if (!emailOrUser || !password) {
      e.preventDefault();
      alert('Por favor, preencha todos os campos.');
      return;
    }
    const button = form.querySelector('.login-button');
    if (button) {
      button.disabled = true;
      form.classList.add('loading');
      button.innerHTML = '<div class="spinner"></div>Entrando...';
    }
  });

  window.addEventListener('scroll', function () {
    const scrolled = window.pageYOffset;
    const parallax = scrolled * 0.5;
    const bg = document.querySelector('.bg-animation');
    if (bg) bg.style.transform = `translateY(${parallax}px)`;
  });

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  }
});
```

**Notes:** Real POST to Django (no AJAX). Toggle password by id: `togglePassword('password')`. Eye button is next to `#password`.

---

## 2. `register_portal.html`

**Purpose:** New user registration (no tenant in URL; `registro_panel`).

**Django context:**
- `form` – fields: `first_name`, `last_name`, `email`, `password1`, `password2`, `role`, `organization`; plus field errors

**URLs / forms:**
- Form `action`: `{% url 'registro_panel' %}`

**Static:** `{% static 'logo_licita.png' %}` (and same Netflix-style CSS as login in `<style>`)

**Key HTML structure:**
- Form id: `registerForm`
- Fields: first_name, last_name, email, password1, password2 (each with optional eye toggle), role (select: SERVIDOR, EMPRESA), organization
- Submit: “Criar Conta”

**JavaScript (inline):**

```js
function togglePassword(id, btn) {
    const input = document.getElementById(id);
    if (input.type === "password") input.type = "text";
    else input.type = "password";
}

document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('loginForm');   // BUG: should be registerForm
  const inputs = document.querySelectorAll('.form-input');
  // ... same floating-label and submit logic as login (validation + loading state)
});
```

**Note:** Script references `loginForm` but form id is `registerForm`; fix when reimplementing (e.g. use `registerForm` and avoid duplicate submit logic).

---

## 3. `dashboard.html`

**Purpose:** Post-login dashboard for authenticated user (tenant = prefeitura).

**Django context (expected):**
- `user` – request.user (full_name, profile_photo.url, role, prefeitura)
- `prefeitura` – tenant object with `url`

**URLs / links:**
- Nav: `{% url 'dashboard' prefeitura_url=prefeitura.url %}`, `{% url 'gerador_de_documentos' prefeitura_url=prefeitura.url %}`, `{% url 'area_do_usuario' prefeitura_url=prefeitura.url %}`
- Logout: `POST {% url 'logout' prefeitura_url=prefeitura.url %}`
- Admin: `/admin` (shown if `request.user.is_staff` or `is_superuser`)
- “Novo Documento”: hardcoded `/gerador_documentos`; “Ver todos”: `project_workspace.html` (static)

**Static:** `{% static 'css/main.css' %}`, `{% static 'logo_licita.png' %}`

**JavaScript:** None material (only optional `dhws-data-injector.js` at bottom). Content is static cards and lists (projects, deadlines).

**Notes:** No API calls. Dashboard is server-rendered only. Profile photo uses `user.profile_photo.url` with `onerror` fallback to Unsplash.

---

## 4. `area_do_usuario.html`

**Purpose:** User profile + “Meus Documentos” list with search and pagination.

**Django context (expected):**
- `user` – full_name, profile_photo, email, role, secretaria, prefeitura, date_joined; is_staff
- `form` – profile form: `first_name`, `last_name` (and possibly profile_photo)
- `page_obj` – paginator page for user’s documents (DocumentInstance)
- `query` – search query string for documents

**URLs / forms:**
- Profile form: POST to same view (assumed) with `enctype="multipart/form-data"`
- Document search: GET with `?q=...&page=...`
- Links: dashboard, gerador_de_documentos, area_do_usuario, logout (same pattern as dashboard)
- Document links: `doc.file_docx.url`, `doc.file_pdf.url` (download)

**Key HTML structure:**
- `#profileForm` – first_name, last_name, email (readonly), hidden file input `#photo`, avatar preview `#avatarPreview`
- `#tab-documents` – list of docs (from `page_obj`); pagination with `page_obj.has_previous/next`, `previous_page_number`, `next_page_number`
- Search: `input[name="q"]` in a GET form

**JavaScript (inline):**

```js
document.getElementById('photo').addEventListener('change', function(event){
  const [file] = event.target.files;
  if (file) {
    const preview = document.getElementById('avatarPreview');
    preview.src = URL.createObjectURL(file);
  }
});

// Duplicate block: more complete validation
const input = document.getElementById('photo');
const avatar = document.getElementById('avatarPreview');
const navAvatar = document.getElementById('navAvatar');
if (input) {
  input.addEventListener('change', (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) return alert('Selecione uma imagem válida.');
    if (file.size > 5 * 1024 * 1024) return alert('Imagem acima de 5MB.');
    const reader = new FileReader();
    reader.onload = (ev) => {
      avatar.src = ev.target.result;
      if (navAvatar) navAvatar.src = ev.target.result;
    };
    reader.readAsDataURL(file);
  });
}

// Tabs (tab-documents, tab-history) – panels keyed by data-tab
const tabs = document.querySelectorAll('.tab-btn');
const panels = { documents: document.getElementById('tab-documents'), history: document.getElementById('tab-history') };
tabs.forEach((btn) => {
  btn.addEventListener('click', () => {
    tabs.forEach(b => b.className = 'tab-btn px-4 py-2 rounded-xl text-sm font-medium bg-white text-slate-700 border border-slate-300 hover:bg-slate-50');
    Object.values(panels).forEach(p => p.classList.add('hidden'));
    btn.className = 'tab-btn px-4 py-2 rounded-xl text-sm font-medium bg-blue-50 text-blue-700 border border-blue-200';
    const key = btn.getAttribute('data-tab');
    panels[key]?.classList.remove('hidden');
  });
});

document.getElementById('profileForm')?.addEventListener('submit', (e) => {
  const firstName = document.getElementById('first_name').value.trim();
  const lastName = document.getElementById('last_name').value.trim();
  if (!firstName || !lastName) {
    e.preventDefault();
    alert('Preencha todos os campos obrigatórios.');
    return;
  }
});
```

**Note:** `tab-history` and `.tab-btn` are referenced but not present in the snippet; likely intended for a “histórico” tab. Pagination is server-side (links with `?q=&page=`).

---

## 5. `partials/history_docs_ajax.html`

**Purpose:** HTML fragment returned by an AJAX endpoint for “Meus Documentos” list (and optionally pagination).

**Django context:**
- `page_obj` – page of document instances (same as area_do_usuario list item structure)

**Structure:** No full HTML document; only a loop and optional script.
- Loop: `{% for doc in page_obj %}` → card with `doc.template.name`, `doc.updated_at`, `doc.get_status_display`, links to `doc.file_docx.url`, `doc.file_pdf.url`
- `{% empty %}`: “Nenhum documento encontrado.”

**JavaScript (in partial):**

```js
document.addEventListener("DOMContentLoaded", function() {
  const container = document.getElementById("tab-documents");
  const searchInput = document.querySelector('input[placeholder="Buscar por título..."]');

  function fetchDocuments(page=1, query="") {
    fetch(`/area_do_usuario/docs/ajax/?page=${page}&q=${encodeURIComponent(query)}`)
      .then(res => res.json())
      .then(data => {
        container.innerHTML = data.html;
        attachPageButtons();
      });
  }

  searchInput?.addEventListener("input", () => fetchDocuments(1, searchInput.value));

  function attachPageButtons() {
    document.querySelectorAll(".page-btn").forEach(btn => {
      btn.addEventListener("click", () => fetchDocuments(btn.dataset.page, searchInput.value));
    });
  }
  attachPageButtons();
});
```

**API:** `GET /area_do_usuario/docs/ajax/?page=1&q=...` → JSON with `{ html: "..." }` (rendered partial). Backend must render `partials/history_docs_ajax.html` with `page_obj` and return JSON.

**Note:** If the main area_do_usuario page doesn’t include this script and the partial is loaded via AJAX, the script in the partial may run in a different context (e.g. innerHTML doesn’t run scripts). Reimplement as a single-page flow or inject script in the main page that calls the same endpoint.

---

## 6. `document_generator.html`

**Purpose:** Wizard to choose a template, (optionally) preview PDF, and submit an “IA prompt” to generate a document.

**Django context (expected):**
- `user`, `prefeitura` (for nav and URLs)
- `selected_template` – optional Template object (id, name) when opening with `?template_id=`
- `form_data` – optional `ia_prompt` for repopulation
- `document_ready` – boolean
- `document_docx_url`, `document_pdf_url` – download links when ready
- `document_instance` – optional (status, created_at)

**URLs / forms:**
- Form: POST to same view (generate action); `action="generate"` button
- Links: dashboard, gerador_de_documentos, area_do_usuario, logout, `biblioteca_documentos`, `biblioteca_documentos` (library)

**APIs used (JavaScript):**
- `GET /api/documentos_modelos/?q=...` – list templates (autocomplete); response: `{ templates: [ { id, name }, ... ] }`
- `GET /api/documentos_modelos/?id=<id>` – single template (id, name, preview_image, etc.)
- `GET /api/documentos_modelos/<id>/pdf/` – JSON `{ ok, pdf_url }` for preview PDF

**Key HTML structure:**
- `#docForm` – csrf, `#template-search`, `#template-results` (dropdown), `#template-id` (hidden), `textarea[name="ia_prompt"]`, submit button “Gerar com IA Contextual”
- `#generateBtn`, `#btnText`, `#btnLoading` – loading state on submit
- Preview card: `#previewHeading`, `#previewSub`, `#previewExcerpt`, `#previewBtn` (calls `openPdfModalWithTemplate(templateId, templateName)`)
- PDF modal: `#pdfModal`, `#pdfCanvas`, `#pageNum`, `#pageCount`, `#prevPage`, `#nextPage`, `#gotoInput`, `#gotoBtn`, `#thumbnails`, `#pdfModalTitle`, `#pdfMeta`, `#btnClosePdf`

**JavaScript (summary):**
- **Template search:** Debounced input, fetch `/api/documentos_modelos/?q=`, render list; keyboard (ArrowDown/Up, Enter); click item → `onTemplateSelected(id, name)`.
- **onTemplateSelected:** Set `#template-search`, `#template-id`; fetch `/api/documentos_modelos/?id=`; call `updatePreviewCard(template)` (heading, sub, excerpt, preview image; show/hide preview button).
- **Form submit:** Disable button, show “Processando com IA...”.
- **PDF modal:** pdf.js (CDN 3.9.179), worker from same CDN. `openPdfModalWithTemplate(templateId, templateName)` → `loadTemplatePreviewPdf(templateId)` → GET `.../pdf/` → `loadPdf(pdf_url)` → render page on canvas, thumbnails; prev/next/goto; close clears state. Exposed globally: `openPdfModalWithTemplate`, `closePdfModal`, `loadTemplatePreviewPdf`, `renderPage`.
- Stubs at top of page: `loadTemplatePreviewPdf`, `renderPage` (warn if called before ready).

**Note:** There is a typo in one place: `window.closePdfModal = closePdfModal;7` (trailing `7`). Duplicate `onTemplateSelected` and duplicate assignment of `openPdfModalWithTemplate`/`closePdfModal` appear; keep a single implementation when reusing.

---

## 7. `template_list.html`

**Purpose:** “Biblioteca de Templates” – filters (estado, prefeitura, subtopico), search box, grid of template cards, each with “Pré-visualizar” opening the same PDF modal; “Usar como base” redirects to document generator with template_id.

**Django context (expected):**
- `templates` – list of template objects (id, name, preview_image)
- `estados`, `prefeituras`, `subtopicos` – for filter dropdowns
- `selected_estado`, `selected_prefeitura`, `selected_subtopico` – current filter values
- `user`, `prefeitura` (for header/nav/logout)

**URLs / forms:**
- Filter form: GET with `estado`, `prefeitura`, `subtopico`
- “Pré-visualizar”: `onclick="openPdfModalWithTemplate('{{ tpl.id }}', '{{ tpl.name|escapejs }}')"`
- “Usar como base”: in modal, `#btnUseTemplate` → `window.location.href = /gerador_de_documentos/?template_id=${currentTemplateId}`

**JavaScript (summary):**
- **PDF modal:** Same pattern as document_generator (pdf.js, worker, loadTemplatePreviewPdf, loadPdf, renderPage, thumbnails, prev/next/goto). `openPdfModalWithTemplate` / `closePdfModal`; `btnUseTemplate` stores `currentTemplateId` and redirects to gerador with `template_id`.
- **Local search:** `#templateSearch` filters `.template-card` by `data-name` (lowercase); show/hide `#noMatchMessage`.

**Note:** Modal markup is duplicated at bottom of page (`#pdfModal`, `#pdfCanvas`, etc.). Same IDs as in document_generator; only one such modal should exist per page.

---

## 8. `admin/index.html`

**Purpose:** Custom Django Admin dashboard (Unfold); date filter and Chart.js bar charts.

**Django context (expected):**
- `cards` – list of `{ title, value, bg, chart }` for top cards
- `template_names` – JSON array of template names (for chart labels)
- `documents_per_template` – JSON array of counts
- `top_users_names` – JSON array of user names
- `top_users_docs` – JSON array of document counts
- `request.GET.start_date`, `request.GET.end_date` – filter

**URLs / forms:**
- Form: GET with `start_date`, `end_date` (submit “Filtrar”)

**JavaScript:**
- Chart.js from CDN.
- Bar chart “Documentos por Documento Base”: `#chartDocsByTemplate`, labels = `template_names`, data = `documents_per_template`.
- Horizontal bar “Top 5 Usuários”: `#chartTopUsers`, labels = `top_users_names`, data = `top_users_docs`.
- Uses CSS variables `--primary-600`, `--unfold-text-*` for colors.

**Note:** Extends `admin/base.html` and Unfold; `{% include "unfold/helpers/site_branding.html" %}`.

---

## 9. `password_reset.html` and `test.html`

**Status:** Empty in the repo. No context or JS to preserve.

---

## API and URL summary (for Vue or new frontend)

| Endpoint / usage | Method | Purpose |
|------------------|--------|--------|
| `/<prefeitura_slug>/login/` (login_panel) | POST | Login (email_or_username, password, remember) |
| `/registro/` (registro_panel) | GET/POST | Register (first_name, last_name, email, password1, password2, role, organization) |
| `/<prefeitura_slug>/logout/` | POST | Logout (CSRF) |
| `/<prefeitura_slug>/dashboard/` | GET | Dashboard |
| `/<prefeitura_slug>/area_do_usuario/` | GET/POST | Profile + document list (q, page) |
| `/<prefeitura_slug>/area_do_usuario/docs/ajax/` | GET | JSON `{ html }` for document list fragment (page, q) |
| `/<prefeitura_slug>/gerador_de_documentos/` | GET/POST | Document generator (template_id, ia_prompt, action=generate) |
| `/<prefeitura_slug>/biblioteca_documentos/` (biblioteca_documentos) | GET | Template library (estado, prefeitura, subtopico) |
| `/api/documentos_modelos/?q=` | GET | Template search; response `{ templates: [{ id, name }, ...] }` |
| `/api/documentos_modelos/?id=` | GET | Single template (id, name, preview_image, …) |
| `/api/documentos_modelos/<id>/pdf/` | GET | JSON `{ ok, pdf_url }` for template preview PDF |

**Static assets:** `{% static 'css/main.css' %}`, `{% static 'logo_licita.png' %}`. External: Rocket.new script, pdf.js 3.9.179 + worker, Chart.js (admin), Google Fonts Inter.

---

## Reuse checklist (Vue or other frontend)

- [ ] Login: POST to login_panel with CSRF; handle redirect and validation errors; optional “remember” and password toggle.
- [ ] Register: POST to registro_panel; fix registerForm vs loginForm in script; role = SERVIDOR | EMPRESA.
- [ ] Dashboard: Load tenant from URL; show user and prefeitura; links to gerador, area_do_usuario, logout, admin.
- [ ] Area do usuário: Profile form (first_name, last_name, photo); document list with search (q) and pagination (page); optional AJAX refresh using docs/ajax endpoint and partial HTML or JSON.
- [ ] Document generator: Template autocomplete (API list + single); IA prompt textarea; POST generate; show doc links when ready; PDF preview modal (pdf.js) for template preview.
- [ ] Template library: Filters (estado, prefeitura, subtopico); local or server search; grid of templates; same PDF modal; “Usar como base” → redirect to gerador with template_id.
- [ ] Admin dashboard: Date filter; cards and Chart.js data from backend (template_names, documents_per_template, top_users_names, top_users_docs).

This file is the single reference for backend template behavior; the Vue.js frontend is not modified by this document.
