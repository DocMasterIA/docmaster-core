<template>
  <div v-if="$route.name === 'Login'" class="app-auth-wrap">
    <router-view />
  </div>
  <div v-else class="gov-shell">
    <header class="gov-shell__topbar">
      <div class="gov-topbar__brand">
        <img src="@/assets/logo_branca.png" alt="DocMasterIA" class="gov-topbar__logo" />
        <span>DocMaster IA</span>
      </div>
      <div class="gov-topbar__meta">
        <span>Ambiente Vue.js</span>
        <span>|</span>
        <span>UF: SP • Órgão: Prefeitura Municipal</span>
        <button
          type="button"
          class="gov-topbar__logout"
          title="Sair e ir para o login"
          @click="logout"
        >
          <i class="fa-solid fa-right-from-bracket" aria-hidden="true"></i>
          Sair
        </button>
      </div>
    </header>

    <div class="gov-shell__body">
      <aside class="gov-shell__sidebar">
        <nav>
          <div class="gov-nav__section">
            <div class="gov-nav__section-label">Navegação</div>
            <ul class="gov-nav">
              <li class="gov-nav__item">
                <router-link
                  to="/"
                  class="gov-nav__link"
                  :class="{ 'gov-nav__link--active': $route.name === 'DocumentGenerator' }"
                  active-class="gov-nav__link--active"
                >
                  <i class="gov-nav__link-icon fa-solid fa-file-lines" aria-hidden="true"></i>
                  Geração de Documentos
                </router-link>
              </li>
              <li class="gov-nav__item">
                <router-link
                  to="/biblioteca"
                  class="gov-nav__link"
                  :class="{ 'gov-nav__link--active': $route.name === 'TemplateList' }"
                  active-class="gov-nav__link--active"
                >
                  <i class="gov-nav__link-icon fa-solid fa-book" aria-hidden="true"></i>
                  Biblioteca de Documentos
                </router-link>
              </li>
              <li class="gov-nav__item">
                <router-link
                  to="/analisador"
                  class="gov-nav__link"
                  :class="{ 'gov-nav__link--active': $route.name === 'DocumentAnalyzer' }"
                  active-class="gov-nav__link--active"
                >
                  <i class="gov-nav__link-icon fa-solid fa-magnifying-glass-chart" aria-hidden="true"></i>
                  Analisador de Documentos
                </router-link>
              </li>
              <li class="gov-nav__item">
                <router-link
                  to="/area-do-usuario"
                  class="gov-nav__link"
                  :class="{ 'gov-nav__link--active': $route.name === 'AreaDoUsuario' }"
                  active-class="gov-nav__link--active"
                >
                  <i class="gov-nav__link-icon fa-solid fa-user" aria-hidden="true"></i>
                  Área do Usuário
                </router-link>
              </li>
            </ul>
          </div>
        </nav>
      </aside>

      <main class="gov-shell__content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router';

const API_BASE = import.meta.env.VITE_API_URL || '';
const router = useRouter();

async function logout() {
  try {
    await fetch(`${API_BASE}/api/auth/logout/`, { method: 'POST', credentials: 'include' });
  } catch (e) {
    console.warn('logout request failed', e);
  }
  router.push('/login');
}
</script>

<style scoped>
.gov-topbar__logout {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  margin-left: 8px;
  font-size: 12px;
  font-weight: 500;
  color: #ffffff;
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
}
.gov-topbar__logout:hover {
  background: rgba(255, 255, 255, 0.25);
  border-color: rgba(255, 255, 255, 0.6);
}
</style>
