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
        <span v-if="user" class="gov-topbar__meta-uf">
          <img
            v-if="ufFlagUrl"
            :src="ufFlagUrl"
            :alt="`Bandeira do estado ${user.prefeitura_uf}`"
            class="gov-topbar__uf-flag"
          />
          UF: {{ user.prefeitura_uf || '—' }} • Órgão: Prefeitura de {{ user.prefeitura_nome || '—' }}
        </span>
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
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';

const API_BASE = import.meta.env.VITE_API_URL || '';
const router = useRouter();

const user = ref(null);

const UF_FLAGS = {
  AC: new URL('./assets/estados/02-acre-full.svg', import.meta.url).href,
  AL: new URL('./assets/estados/03-alagoas-full.svg', import.meta.url).href,
  AP: new URL('./assets/estados/04-amapa-full.svg', import.meta.url).href,
  AM: new URL('./assets/estados/05-amazonas-full.svg', import.meta.url).href,
  BA: new URL('./assets/estados/06-bahia-full.svg', import.meta.url).href,
  CE: new URL('./assets/estados/07-ceara-full.svg', import.meta.url).href,
  DF: new URL('./assets/estados/08-distrito-federal-full.svg', import.meta.url).href,
  ES: new URL('./assets/estados/09-espirito-santo-full.svg', import.meta.url).href,
  GO: new URL('./assets/estados/10-goias-full.svg', import.meta.url).href,
  MA: new URL('./assets/estados/11-maranhao-full.svg', import.meta.url).href,
  MT: new URL('./assets/estados/12-mato-grosso-full.svg', import.meta.url).href,
  MS: new URL('./assets/estados/13-mato-grosso-do-sul-full.svg', import.meta.url).href,
  MG: new URL('./assets/estados/14-minas-gerais-full.svg', import.meta.url).href,
  PA: new URL('./assets/estados/15-para-full.svg', import.meta.url).href,
  PB: new URL('./assets/estados/16-paraiba-full.svg', import.meta.url).href,
  PR: new URL('./assets/estados/17-parana-full.svg', import.meta.url).href,
  PE: new URL('./assets/estados/18-pernambuco-full.svg', import.meta.url).href,
  PI: new URL('./assets/estados/19-piaui-full.svg', import.meta.url).href,
  RJ: new URL('./assets/estados/20-rio-de-janeiro-full.svg', import.meta.url).href,
  RN: new URL('./assets/estados/21-rio-grande-do-norte-full.svg', import.meta.url).href,
  RS: new URL('./assets/estados/22-rio-grande-do-sul-full.svg', import.meta.url).href,
  RO: new URL('./assets/estados/23-rondonia-full.svg', import.meta.url).href,
  RR: new URL('./assets/estados/24-roraima-full.svg', import.meta.url).href,
  SC: new URL('./assets/estados/25-santa-catarina-full.svg', import.meta.url).href,
  SP: new URL('./assets/estados/26-sao-paulo-full.svg', import.meta.url).href,
  SE: new URL('./assets/estados/27-sergipe-full.svg', import.meta.url).href,
  TO: new URL('./assets/estados/28-tocantins-full.svg', import.meta.url).href,
};

const BR_FLAG = new URL('./assets/estados/01-brasil-full.svg', import.meta.url).href;

const ufFlagUrl = computed(() => {
  const uf = user.value?.prefeitura_uf;
  if (!uf) return '';
  return UF_FLAGS[uf] || BR_FLAG;
});

async function fetchMe() {
  try {
    const res = await fetch(`${API_BASE}/api/me/`, { credentials: 'include' });
    if (!res.ok) return;
    const data = await res.json();
    user.value = data;
  } catch (e) {
    console.warn('fetchMe failed', e);
  }
}

async function logout() {
  try {
    await fetch(`${API_BASE}/api/auth/logout/`, { method: 'POST', credentials: 'include' });
  } catch (e) {
    console.warn('logout request failed', e);
  }
  user.value = null;
  router.push('/login');
}

onMounted(() => {
  fetchMe();
});
</script>

<style scoped>
.gov-topbar__meta-uf {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.gov-topbar__uf-flag {
  width: 28px;
  height: 20px;
  object-fit: cover;
  border-radius: 2px;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.4);
}

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
