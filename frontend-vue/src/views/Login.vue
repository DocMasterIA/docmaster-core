<template>
  <div class="login-page">
    <div class="login-page__bg"></div>
    <header class="login-page__header">
      <div class="login-page__brand">
        <img src="@/assets/logo_branca.png" alt="DocMasterIA" class="login-page__logo" />
        <span class="login-page__name">DocMasterIA</span>
      </div>
      <div class="login-page__badge">
        <i class="fa-solid fa-lock" aria-hidden="true"></i>
        Conexão segura
      </div>
    </header>

    <main class="login-page__main">
      <div class="login-page__card gov-surface">
        <h1 class="login-page__title">Entrar</h1>
        <p class="login-page__subtitle">Acesso à plataforma de geração de documentos com IA</p>

        <form id="loginForm" class="login-page__form" @submit.prevent="onSubmit">
          <p v-if="error" class="login-page__error">{{ error }}</p>
          <div class="gov-field">
            <label class="gov-label" for="email_or_username">E-mail ou usuário</label>
            <input
              id="email_or_username"
              v-model="emailOrUsername"
              type="text"
              class="gov-input login-page__input"
              placeholder="seu@email.com"
              autocomplete="username"
              required
            />
          </div>
          <div class="gov-field">
            <label class="gov-label" for="password">Senha</label>
            <div class="login-page__password-wrap">
              <input
                id="password"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                class="gov-input login-page__input"
                placeholder="••••••••"
                autocomplete="current-password"
                required
              />
              <button
                type="button"
                class="login-page__eye"
                :aria-label="showPassword ? 'Ocultar senha' : 'Mostrar senha'"
                @click="showPassword = !showPassword"
              >
                <i :class="showPassword ? 'fa-solid fa-eye-slash' : 'fa-solid fa-eye'" aria-hidden="true"></i>
              </button>
            </div>
          </div>
          <div class="login-page__options">
            <label class="login-page__remember">
              <input v-model="remember" type="checkbox" class="login-page__checkbox" />
              <span>Lembrar de mim</span>
            </label>
            <router-link to="/" class="login-page__link">Precisa de ajuda?</router-link>
          </div>
          <button
            type="submit"
            class="gov-btn gov-btn--primary login-page__submit"
            :disabled="loading"
          >
            <template v-if="loading">
              <i class="fa-solid fa-spinner fa-spin" aria-hidden="true"></i>
              Entrando...
            </template>
            <template v-else>
              <i class="fa-solid fa-right-to-bracket" aria-hidden="true"></i>
              Entrar na plataforma
            </template>
          </button>
        </form>

      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useSessionUser } from '@/composables/useSessionUser.js';

const API_BASE = import.meta.env.DEV ? '' : (import.meta.env.VITE_API_URL || 'https://api.docmasteria.com.br');
const router = useRouter();
const route = useRoute();
const { clearUser, fetchMe } = useSessionUser();

const emailOrUsername = ref('');
const password = ref('');
const remember = ref(false);
const showPassword = ref(false);
const loading = ref(false);
const error = ref('');

async function onSubmit() {
  error.value = '';
  if (!emailOrUsername.value.trim() || !password.value) {
    error.value = 'Preencha e-mail/usuário e senha.';
    return;
  }
  loading.value = true;
  try {
    const res = await fetch(`${API_BASE}/api/auth/login/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        email_or_username: emailOrUsername.value.trim(),
        password: password.value,
        remember: remember.value,
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      error.value = data.error || 'E-mail/usuário ou senha inválidos.';
      return;
    }
    if (data.ok) {
      clearUser();
      await fetchMe({ force: true });
      const r = route.query.redirect && String(route.query.redirect);
      router.replace(r && r.startsWith('/') ? r : '/');
    } else {
      error.value = data.error || 'Erro ao entrar.';
    }
  } catch (e) {
    error.value = 'Erro de conexão. Tente novamente.';
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  document.body.classList.add('login-page-body');
  const res = await fetch(`${API_BASE}/api/me/`, { credentials: 'include' });
  if (res.ok) {
    const r = route.query.redirect && String(route.query.redirect);
    router.replace(r && r.startsWith('/') ? r : '/');
  }
});
onUnmounted(() => {
  document.body.classList.remove('login-page-body');
});
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  position: relative;
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, var(--color-primary-dark) 0%, #0e3459 50%, #1b2433 100%);
}
.login-page-body {
  margin: 0;
  background: transparent;
}
.login-page__bg {
  position: fixed;
  inset: 0;
  background: radial-gradient(ellipse at 20% 20%, rgba(61, 186, 231, 0.15) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 80%, rgba(21, 78, 135, 0.2) 0%, transparent 50%);
  pointer-events: none;
}
.login-page__header {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 32px;
  z-index: 10;
}
.login-page__brand {
  display: flex;
  align-items: center;
  gap: 12px;
}
.login-page__logo {
  height: 40px;
  width: auto;
  display: block;
}
.login-page__name {
  font-size: 22px;
  font-weight: 700;
  color: #fff;
  letter-spacing: 0.02em;
}
.login-page__badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 999px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.15);
}
.login-page__main {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  position: relative;
  z-index: 5;
}
.login-page__card {
  width: 100%;
  max-width: 420px;
  padding: 40px 36px;
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.97);
}
.login-page__title {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text);
  margin: 0 0 8px;
}
.login-page__subtitle {
  font-size: 14px;
  color: var(--color-text-soft);
  margin: 0 0 24px;
}
.login-page__form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.login-page__error {
  margin: 0;
  padding: 10px 12px;
  background: #f6e0de;
  border: 1px solid var(--color-danger);
  border-radius: var(--radius-md);
  color: var(--color-danger);
  font-size: 13px;
}
.login-page__input {
  width: 100%;
  padding: 10px 12px;
  height: 44px;
}
.login-page__password-wrap {
  position: relative;
}
.login-page__password-wrap .gov-input {
  padding-right: 44px;
}
.login-page__eye {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  color: var(--color-text-soft);
  cursor: pointer;
  border-radius: var(--radius-sm);
}
.login-page__eye:hover {
  color: var(--color-text);
  background: var(--color-bg-soft);
}
.login-page__options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}
.login-page__remember {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--color-text-soft);
  cursor: pointer;
}
.login-page__checkbox {
  width: 16px;
  height: 16px;
  accent-color: var(--color-primary-dark);
}
.login-page__link {
  font-size: 13px;
}
.login-page__submit {
  margin-top: 8px;
  height: 48px;
  font-size: 15px;
  gap: 10px;
}
</style>
