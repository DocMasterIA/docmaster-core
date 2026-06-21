<template>
  <div class="area-usuario">
    <header class="gov-page-header">
      <h1 class="gov-page-title">Minha Conta</h1>
      <p class="gov-page-subtitle">
        Gerencie seus dados pessoais e acesse seus documentos e histórico.
      </p>
    </header>

    <div class="area-usuario__grid">
      <div class="area-usuario__left">
      <!-- Coluna esquerda: Perfil -->
      <section class="gov-surface area-usuario__profile">
        <div class="gov-surface__header">
          <div>
            <h2 class="gov-surface__title">Dados Pessoais</h2>
            <p class="gov-surface__subtitle">Atualize seu nome, sobrenome e foto.</p>
          </div>
        </div>

        <div class="area-usuario__profile-body">
          <!-- Avatar -->
          <div class="area-usuario__avatar-row">
            <div class="area-usuario__avatar-wrap">
              <img
                :src="avatarPreviewUrl"
                alt="Avatar"
                class="area-usuario__avatar-img"
              />
              <label for="photo" class="area-usuario__avatar-upload" title="Alterar foto">
                <svg class="area-usuario__avatar-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"/>
                </svg>
              </label>
            </div>
            <div>
              <p class="area-usuario__avatar-name">{{ profile.full_name }}</p>
              <p class="gov-text-soft gov-text-sm">Formatos: JPG ou PNG. Até 5MB.</p>
              <p class="gov-text-soft gov-text-xs">Use uma imagem quadrada para melhor resultado.</p>
            </div>
          </div>

          <form id="profileForm" class="area-usuario__form" @submit.prevent="submitProfile">
            <input
              id="photo"
              ref="photoInput"
              type="file"
              accept="image/*"
              class="area-usuario__file-hidden"
              @change="onPhotoChange"
            />

            <div class="gov-field">
              <label class="gov-label" for="first_name">Nome</label>
              <input
                id="first_name"
                v-model="form.first_name"
                type="text"
                class="gov-input"
                placeholder="Seu nome"
                required
              />
            </div>
            <div class="gov-field">
              <label class="gov-label" for="last_name">Sobrenome</label>
              <input
                id="last_name"
                v-model="form.last_name"
                type="text"
                class="gov-input"
                placeholder="Seu sobrenome"
                required
              />
            </div>
            <div class="gov-field">
              <label class="gov-label" for="email">Email</label>
              <input
                id="email"
                :value="profile.email"
                type="email"
                class="gov-input gov-input--readonly"
                readonly
              />
            </div>

            <div class="area-usuario__meta">
              <div class="area-usuario__meta-item">
                <span class="area-usuario__meta-label">Nome e Sobrenome</span>
                <span class="area-usuario__meta-value">{{ profile.full_name }}</span>
              </div>
              <div class="area-usuario__meta-item">
                <span class="area-usuario__meta-label">Secretaria</span>
                <span class="area-usuario__meta-value">{{ profile.secretaria || '—' }}</span>
              </div>
              <div class="area-usuario__meta-item">
                <span class="area-usuario__meta-label">Prefeitura</span>
                <span class="area-usuario__meta-value">{{ profile.prefeitura || '—' }}</span>
              </div>
              <div class="area-usuario__meta-item">
                <span class="area-usuario__meta-label">Conta criada em</span>
                <span class="area-usuario__meta-value">{{ profile.date_joined }}</span>
              </div>
              <div class="area-usuario__meta-item">
                <span class="area-usuario__meta-label">Acesso</span>
                <span class="area-usuario__meta-value">{{ profile.is_staff ? 'Admin' : 'Usuário' }}</span>
              </div>
            </div>
            <p class="gov-text-soft gov-text-sm">
              *Precisa de alguma informação ou ajuste? <a href="#" class="gov-link" @click.prevent>Entre em contato.</a>
            </p>

            <p v-if="profileError" class="area-usuario__msg area-usuario__msg--error">{{ profileError }}</p>
            <p v-if="profileSuccess" class="area-usuario__msg area-usuario__msg--success">{{ profileSuccess }}</p>
            <div class="area-usuario__form-actions">
              <button type="button" class="gov-btn gov-btn--outline" @click="resetForm">Cancelar</button>
              <button type="submit" class="gov-btn gov-btn--primary" :disabled="profileSaving">
                {{ profileSaving ? 'Salvando...' : 'Salvar' }}
              </button>
            </div>
          </form>
        </div>
      </section>

      <!-- Segurança: alterar senha -->
      <section class="gov-surface area-usuario__security">
        <div class="gov-surface__header">
          <div>
            <h2 class="gov-surface__title">Segurança</h2>
            <p class="gov-surface__subtitle">Altere sua senha de acesso à plataforma.</p>
          </div>
        </div>

        <div v-if="!showPasswordForm" class="area-usuario__security-intro">
          <p class="gov-text-soft gov-text-sm">
            Para sua segurança, confirme a senha atual antes de definir uma nova.
          </p>
          <button type="button" class="gov-btn gov-btn--outline" @click="openPasswordForm">
            Alterar senha
          </button>
        </div>

        <form
          v-else
          id="passwordForm"
          class="area-usuario__form area-usuario__password-form"
          @submit.prevent="submitPasswordChange"
        >
          <div class="gov-field">
            <label class="gov-label" for="current_password">Senha atual</label>
            <input
              id="current_password"
              v-model="passwordForm.current_password"
              type="password"
              class="gov-input"
              autocomplete="current-password"
              required
            />
          </div>
          <div class="gov-field">
            <label class="gov-label" for="new_password">Nova senha</label>
            <input
              id="new_password"
              v-model="passwordForm.new_password"
              type="password"
              class="gov-input"
              autocomplete="new-password"
              minlength="8"
              required
            />
            <p class="gov-text-soft gov-text-xs area-usuario__hint">Mínimo 8 caracteres.</p>
          </div>
          <div class="gov-field">
            <label class="gov-label" for="confirm_password">Confirmar nova senha</label>
            <input
              id="confirm_password"
              v-model="passwordForm.confirm_password"
              type="password"
              class="gov-input"
              autocomplete="new-password"
              minlength="8"
              required
            />
          </div>

          <p v-if="passwordError" class="area-usuario__msg area-usuario__msg--error">{{ passwordError }}</p>
          <p v-if="passwordSuccess" class="area-usuario__msg area-usuario__msg--success">{{ passwordSuccess }}</p>

          <div class="area-usuario__form-actions">
            <button type="button" class="gov-btn gov-btn--outline" @click="cancelPasswordForm">Cancelar</button>
            <button type="submit" class="gov-btn gov-btn--primary" :disabled="passwordSaving">
              {{ passwordSaving ? 'Alterando...' : 'Alterar senha' }}
            </button>
          </div>
        </form>
      </section>
      </div>

      <!-- Coluna direita: Meus Documentos -->
      <section class="gov-surface area-usuario__docs">
        <div class="area-usuario__docs-header">
          <span class="area-usuario__tab area-usuario__tab--active">Meus Documentos</span>
          <form class="area-usuario__search-form" @submit.prevent="searchDocs">
            <input
              v-model="docSearchQuery"
              type="text"
              class="gov-input area-usuario__search-input"
              placeholder="Buscar por título..."
              @input="debouncedSearch"
            />
            <button type="submit" class="gov-btn gov-btn--outline gov-btn--sm">Buscar</button>
          </form>
        </div>

        <div class="area-usuario__docs-list">
          <template v-for="doc in documents.results" :key="doc.id">
            <div class="area-usuario__doc-row">
              <div class="area-usuario__doc-info">
                <p class="area-usuario__doc-title">{{ doc.template_name }}</p>
                <p class="gov-text-soft gov-text-xs">
                  Atualizado em {{ doc.updated_at }} • Status:
                  <span :class="doc.status === 'draft' ? 'area-usuario__status--draft' : 'area-usuario__status--final'">
                    {{ doc.status_display }}
                  </span>
                </p>
              </div>
              <div class="area-usuario__doc-actions">
                <a
                  v-if="doc.file_docx_url"
                  :href="docUrl(doc.file_docx_url)"
                  target="_blank"
                  class="gov-btn gov-btn--outline gov-btn--sm"
                >
                  Abrir DOCX
                </a>
                <a
                  v-if="doc.file_pdf_url"
                  :href="docUrl(doc.file_pdf_url)"
                  download
                  class="gov-btn gov-btn--outline gov-btn--sm"
                >
                  Exportar PDF
                </a>
              </div>
            </div>
          </template>
        </div>

        <p v-if="documents.results.length === 0 && !docsLoading" class="gov-text-soft gov-text-sm area-usuario__empty">
          Nenhum documento encontrado.
        </p>

        <!-- Paginação -->
        <div v-if="documents.count > 0" class="area-usuario__pagination">
          <p class="gov-text-soft gov-text-sm">
            Mostrando {{ documents.start_index }}–{{ documents.end_index }} de {{ documents.count }}
          </p>
          <div class="area-usuario__pagination-btns">
            <button
              type="button"
              class="gov-btn gov-btn--outline gov-btn--sm"
              :disabled="!documents.has_previous"
              @click="goToPage(documents.page - 1)"
            >
              Anterior
            </button>
            <button
              type="button"
              class="gov-btn gov-btn--outline gov-btn--sm"
              :disabled="!documents.has_next"
              @click="goToPage(documents.page + 1)"
            >
              Próximo
            </button>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { changePassword } from '../services/userAccount.js';

const API_BASE = import.meta.env.DEV ? '' : (import.meta.env.VITE_API_URL || 'https://api.docmasteria.com.br');

const profile = reactive({
  id: '',
  email: '',
  first_name: '',
  last_name: '',
  full_name: '',
  role: '',
  date_joined: '',
  is_staff: false,
  profile_photo: null,
  secretaria: null,
  prefeitura: null,
});

const form = reactive({
  first_name: '',
  last_name: '',
});

const photoFile = ref(null);
const avatarPreviewUrl = ref('');
const profileSaving = ref(false);
const profileError = ref('');
const profileSuccess = ref('');

const showPasswordForm = ref(false);
const passwordSaving = ref(false);
const passwordError = ref('');
const passwordSuccess = ref('');
const passwordForm = reactive({
  current_password: '',
  new_password: '',
  confirm_password: '',
});

const docSearchQuery = ref('');
const docSearchDebounce = ref(null);
const documents = reactive({
  results: [],
  count: 0,
  num_pages: 0,
  page: 1,
  has_previous: false,
  has_next: false,
  start_index: 0,
  end_index: 0,
});
const docsLoading = ref(false);

const photoInput = ref(null);

function docUrl(url) {
  if (!url) return '#';
  return url.startsWith('http') ? url : `${API_BASE}${url}`;
}

async function loadProfile() {
  try {
    const res = await fetch(`${API_BASE}/api/me/`, { credentials: 'include' });
    if (!res.ok) return;
    const data = await res.json();
    profile.id = data.id;
    profile.email = data.email || '';
    profile.first_name = data.first_name || '';
    profile.last_name = data.last_name || '';
    profile.full_name = data.full_name || '';
    profile.role = data.role || '';
    profile.date_joined = data.date_joined || '';
    profile.is_staff = !!data.is_staff;
    profile.profile_photo = data.profile_photo || null;
    profile.secretaria = data.secretaria ?? null;
    profile.prefeitura = data.prefeitura ?? null;
    form.first_name = profile.first_name;
    form.last_name = profile.last_name;
    if (profile.profile_photo) {
      avatarPreviewUrl.value = docUrl(profile.profile_photo);
    } else {
      avatarPreviewUrl.value = 'https://images.unsplash.com/photo-1584824486509-112e4181ff6b?q=80&w=2940&auto=format&fit=crop';
    }
  } catch (e) {
    console.warn('loadProfile', e);
  }
}

function onPhotoChange(e) {
  const file = e.target.files?.[0];
  if (!file) return;
  if (!file.type.startsWith('image/')) {
    alert('Selecione uma imagem válida.');
    return;
  }
  if (file.size > 5 * 1024 * 1024) {
    alert('Imagem acima de 5MB.');
    return;
  }
  photoFile.value = file;
  const reader = new FileReader();
  reader.onload = (ev) => {
    avatarPreviewUrl.value = ev.target.result;
  };
  reader.readAsDataURL(file);
}

function resetForm() {
  form.first_name = profile.first_name;
  form.last_name = profile.last_name;
  photoFile.value = null;
  if (profile.profile_photo) {
    avatarPreviewUrl.value = docUrl(profile.profile_photo);
  }
  if (photoInput.value) photoInput.value.value = '';
}

async function submitProfile() {
  if (!form.first_name?.trim() || !form.last_name?.trim()) {
    alert('Preencha todos os campos obrigatórios.');
    return;
  }
  profileSaving.value = true;
  profileError.value = '';
  profileSuccess.value = '';
  try {
    const body = new FormData();
    body.append('first_name', form.first_name.trim());
    body.append('last_name', form.last_name.trim());
    if (photoFile.value) body.append('profile_photo', photoFile.value);
    const res = await fetch(`${API_BASE}/api/me/`, {
      method: 'POST',
      credentials: 'include',
      body,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      profileError.value = data.errors ? Object.values(data.errors).flat().join(' ') : 'Erro ao atualizar.';
      return;
    }
    profileSuccess.value = data.message || 'Dados atualizados com sucesso!';
    profileError.value = '';
    photoFile.value = null;
    await loadProfile();
    setTimeout(() => { profileSuccess.value = ''; }, 4000);
  } catch (e) {
    profileError.value = e.message || 'Erro ao atualizar.';
  } finally {
    profileSaving.value = false;
  }
}

function resetPasswordForm() {
  passwordForm.current_password = '';
  passwordForm.new_password = '';
  passwordForm.confirm_password = '';
}

function openPasswordForm() {
  passwordError.value = '';
  passwordSuccess.value = '';
  resetPasswordForm();
  showPasswordForm.value = true;
}

function cancelPasswordForm() {
  showPasswordForm.value = false;
  passwordError.value = '';
  passwordSuccess.value = '';
  resetPasswordForm();
}

async function submitPasswordChange() {
  passwordError.value = '';
  passwordSuccess.value = '';

  if (!passwordForm.current_password || !passwordForm.new_password || !passwordForm.confirm_password) {
    passwordError.value = 'Preencha todos os campos.';
    return;
  }
  if (passwordForm.new_password !== passwordForm.confirm_password) {
    passwordError.value = 'A confirmação não confere com a nova senha.';
    return;
  }
  if (passwordForm.new_password.length < 8) {
    passwordError.value = 'A nova senha deve ter pelo menos 8 caracteres.';
    return;
  }

  passwordSaving.value = true;
  try {
    const data = await changePassword({
      currentPassword: passwordForm.current_password,
      newPassword: passwordForm.new_password,
      confirmPassword: passwordForm.confirm_password,
    });
    passwordSuccess.value = data.message || 'Senha alterada com sucesso!';
    resetPasswordForm();
    setTimeout(() => {
      passwordSuccess.value = '';
      showPasswordForm.value = false;
    }, 3000);
  } catch (e) {
    passwordError.value = e.message || 'Erro ao alterar senha.';
  } finally {
    passwordSaving.value = false;
  }
}

async function loadDocuments() {
  docsLoading.value = true;
  try {
    const params = new URLSearchParams();
    params.set('page', String(documents.page));
    if (docSearchQuery.value.trim()) params.set('q', docSearchQuery.value.trim());
    const res = await fetch(`${API_BASE}/api/me/documents/?${params}`, { credentials: 'include' });
    if (!res.ok) {
      documents.results = [];
      documents.count = 0;
      documents.num_pages = 0;
      documents.page = 1;
      documents.has_previous = false;
      documents.has_next = false;
      documents.start_index = 0;
      documents.end_index = 0;
      return;
    }
    const data = await res.json();
    documents.results = data.results || [];
    documents.count = data.count || 0;
    documents.num_pages = data.num_pages || 0;
    documents.page = data.page || 1;
    documents.has_previous = !!data.has_previous;
    documents.has_next = !!data.has_next;
    documents.start_index = data.start_index ?? 0;
    documents.end_index = data.end_index ?? 0;
  } catch (e) {
    console.warn('loadDocuments', e);
    documents.results = [];
    documents.count = 0;
    documents.num_pages = 0;
    documents.page = 1;
    documents.has_previous = false;
    documents.has_next = false;
    documents.start_index = 0;
    documents.end_index = 0;
  } finally {
    docsLoading.value = false;
  }
}

function searchDocs() {
  documents.page = 1;
  loadDocuments();
}

function debouncedSearch() {
  clearTimeout(docSearchDebounce.value);
  docSearchDebounce.value = setTimeout(() => {
    documents.page = 1;
    loadDocuments();
  }, 300);
}

function goToPage(page) {
  documents.page = page;
  loadDocuments();
}

onMounted(() => {
  loadProfile();
  loadDocuments();
});
</script>

<style scoped>
.area-usuario {
  color: #0f172a;
}

:deep(.gov-surface) {
  border-radius: 24px;
  border: 1px solid #e2e8f0;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 14px 36px rgba(15, 23, 42, 0.045);
}

:deep(.gov-surface__title) {
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

:deep(.gov-surface__subtitle) {
  color: #64748b;
}

:deep(.gov-input) {
  border-radius: 16px;
  border: 1px solid #cbd5e1;
  background: #fff;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

:deep(.gov-input:focus) {
  border-color: #254e78;
  box-shadow: 0 0 0 4px rgba(37, 78, 120, 0.1);
}

:deep(.gov-btn) {
  border-radius: 999px;
  font-weight: 700;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

:deep(.gov-btn:hover) {
  transform: translateY(-1px);
}

:deep(.gov-btn--primary) {
  background: #254e78;
  border-color: #254e78;
  color: #fff;
  box-shadow: 0 16px 34px rgba(37, 78, 120, 0.24);
}

:deep(.gov-btn--primary:hover) {
  background: #1f4468;
  border-color: #1f4468;
}

:deep(.gov-btn--outline) {
  border-color: #cbd5e1;
}

.area-usuario__grid {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 24px;
}
.area-usuario__left {
  display: flex;
  flex-direction: column;
  gap: 24px;
}
@media (max-width: 960px) {
  .area-usuario__grid {
    grid-template-columns: 1fr;
  }
}
.area-usuario__profile {
  padding: 20px 24px;
}
.area-usuario__security {
  padding: 20px 24px;
}
.area-usuario__security-intro {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 12px;
  margin-top: 8px;
}
.area-usuario__password-form {
  margin-top: 8px;
}
.area-usuario__hint {
  margin: 6px 0 0;
}
.area-usuario__profile-body {
  margin-top: 8px;
}
.area-usuario__avatar-row {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 20px;
}
.area-usuario__avatar-wrap {
  position: relative;
  flex-shrink: 0;
}
.area-usuario__avatar-img {
  width: 80px;
  height: 80px;
  border-radius: var(--radius-lg);
  object-fit: cover;
  border: 2px solid var(--color-primary);
}
.area-usuario__avatar-upload {
  position: absolute;
  bottom: 0;
  right: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.area-usuario__avatar-upload:hover {
  background: #e6ecf3;
}
.area-usuario__avatar-icon {
  width: 14px;
  height: 14px;
}
.area-usuario__avatar-name {
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 4px;
  font-size: 13px;
}
.area-usuario__file-hidden {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  pointer-events: none;
}
.area-usuario__form {
  margin-top: 8px;
}
.area-usuario__meta {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px 16px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--color-border);
}
.area-usuario__meta-label {
  display: block;
  font-size: 11px;
  color: var(--color-text-soft);
  margin-bottom: 2px;
}
.area-usuario__meta-value {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
}
.gov-input--readonly {
  background: var(--color-bg-soft);
  color: var(--color-text-soft);
}
.gov-text-sm { font-size: 12px; }
.gov-text-xs { font-size: 11px; }
.area-usuario__form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
  padding-top: 16px;
}
.area-usuario__docs {
  padding: 0;
  overflow: hidden;
}
.area-usuario__docs-header {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  padding: 16px 24px;
  border-bottom: 1px solid var(--color-border);
}
.area-usuario__tab {
  padding: 8px 16px;
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 500;
  background: var(--color-bg);
  color: var(--color-text-soft);
  border: 1px solid var(--color-border);
}
.area-usuario__tab--active {
  background: #e5f3fa;
  color: var(--color-primary-dark);
  border-color: var(--color-primary);
}
.area-usuario__search-form {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
}
.area-usuario__search-input {
  width: 220px;
  padding: 8px 12px;
}
.area-usuario__docs-list {
  padding: 16px 24px;
  display: flex;
  flex-direction: column;
  gap: 0;
  border-bottom: 1px solid var(--color-border);
}
.area-usuario__doc-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  padding: 16px 0;
  border-bottom: 1px solid var(--color-border);
}
.area-usuario__doc-row:last-child {
  border-bottom: none;
}
.area-usuario__doc-title {
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 4px;
  font-size: 13px;
}
.area-usuario__doc-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.area-usuario__status--draft {
  color: #b45309;
}
.area-usuario__status--final {
  color: var(--color-success);
}
.area-usuario__empty {
  padding: 24px;
  margin: 0;
}
.area-usuario__pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  padding: 16px 24px;
}
.area-usuario__pagination-btns {
  display: flex;
  gap: 8px;
}
.area-usuario__msg {
  margin: 0 0 12px;
  font-size: 13px;
}
.area-usuario__msg--error {
  color: var(--color-danger);
}
.area-usuario__msg--success {
  color: var(--color-success);
}

:global(.dm-dark) .area-usuario {
  color: #e2e8f0;
}

:global(.dm-dark) .area-usuario :deep(.gov-surface) {
  border-color: #1e293b;
  background: rgba(15, 23, 42, 0.74);
  box-shadow: 0 16px 36px rgba(2, 6, 23, 0.3);
}

:global(.dm-dark) .area-usuario :deep(.gov-surface__title) {
  color: #f8fafc;
}

:global(.dm-dark) .area-usuario :deep(.gov-surface__subtitle),
:global(.dm-dark) .area-usuario :deep(.gov-text-soft) {
  color: #94a3b8;
}

:global(.dm-dark) .area-usuario :deep(.gov-input) {
  border-color: #334155;
  background: #0f172a;
  color: #e2e8f0;
}

:global(.dm-dark) .area-usuario :deep(.gov-input--readonly) {
  background: #111827;
  color: #94a3b8;
}

:global(.dm-dark) .area-usuario :deep(.gov-btn--outline) {
  border-color: #475569;
  color: #e2e8f0;
  background: #0f172a;
}

:global(.dm-dark) .area-usuario :deep(.gov-btn--outline:hover) {
  background: #1e293b;
}

:global(.dm-dark) .area-usuario .area-usuario__docs-header,
:global(.dm-dark) .area-usuario .area-usuario__doc-row,
:global(.dm-dark) .area-usuario .area-usuario__docs-list,
:global(.dm-dark) .area-usuario .area-usuario__meta {
  border-color: #334155;
}

:global(.dm-dark) .area-usuario .area-usuario__meta-value,
:global(.dm-dark) .area-usuario .area-usuario__doc-title {
  color: #f8fafc;
}
</style>
