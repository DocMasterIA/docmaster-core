<template>
  <div v-if="$route.name === 'Login'" class="app-auth-wrap">
    <router-view />
  </div>
  <div v-else class="dm-layout-bg" :class="{ 'dm-dark': darkMode }">
    <div class="dm-layout-wrap">
      <div class="dm-shell">
        <header class="dm-topbar">
          <div class="dm-topbar-main">
            <div class="dm-brand">
              <div class="dm-brand-logo-wrap">
                <img src="@/assets/logo_branca.png" alt="DocMasterIA" class="dm-brand-logo" />
              </div>
              <div class="dm-brand-text">
                <h1>DocMaster IA</h1>
                <span>Gestão Documental</span>
              </div>
            </div>
            <div class="dm-topbar-actions">
              <span v-if="user" class="dm-topbar-meta">
                <img v-if="ufFlagUrl" :src="ufFlagUrl" :alt="`Bandeira ${user.prefeitura_uf}`" class="dm-uf-flag" />
                UF {{ user.prefeitura_uf || '—' }}
              </span>
              <button type="button" class="dm-chip-btn" @click="toggleDarkMode">
                <i class="fa-solid" :class="darkMode ? 'fa-sun' : 'fa-moon'" aria-hidden="true"></i>
                {{ darkMode ? 'Claro' : 'Escuro' }}
              </button>
              <button type="button" class="dm-chip-btn" title="Sair e ir para o login" @click="logout">
                <i class="fa-solid fa-right-from-bracket" aria-hidden="true"></i>
                Sair
              </button>
            </div>
          </div>
          <div class="dm-top-tabs">
            <button
              v-for="tab in mainTabs"
              :key="tab.key"
              type="button"
              class="dm-top-tab"
              :class="{ 'dm-top-tab--active': isMainTabActive(tab.key) }"
              @click="onMainTabClick(tab)"
            >
              <i class="fa-solid" :class="tab.icon" aria-hidden="true"></i>
              <span>{{ tab.label }}</span>
            </button>
          </div>
        </header>

        <div class="dm-body">
          <aside class="dm-sidebar">
            <div class="dm-sidebar-head">
              <div class="dm-sidebar-kicker">Navegação da seção</div>
              <div class="dm-sidebar-title">{{ activeSectionLabel }}</div>
              <p>Selecione uma opção para avançar no fluxo.</p>
            </div>
            <nav class="dm-sidebar-nav">
              <template v-if="activeMainTabKey === 'geracao'">
                <button
                  type="button"
                  class="dm-nav-item dm-nav-item--expandable"
                  :class="{ 'dm-nav-item--active': isGenerationSectionActive }"
                  @click="generationMenuOpen = !generationMenuOpen"
                >
                  <span><i class="fa-solid fa-file-lines" aria-hidden="true"></i>Geração de Documentos</span>
                  <i class="fa-solid" :class="generationMenuOpen ? 'fa-chevron-up' : 'fa-chevron-down'" aria-hidden="true"></i>
                </button>

                <div v-if="generationMenuOpen" class="dm-subnav">
                  <div v-for="page in generationPages" :key="page.name" class="dm-subnav-item">
                    <button
                      type="button"
                      class="dm-subnav-btn"
                      :class="{ 'dm-subnav-btn--active': isGroupActive(page) }"
                      @click="toggleGroup(page.name)"
                    >
                      <span><i class="fa-solid" :class="page.icon" aria-hidden="true"></i>{{ page.label }}</span>
                      <i class="fa-solid" :class="isGroupOpen(page.name) ? 'fa-chevron-up' : 'fa-chevron-down'" aria-hidden="true"></i>
                    </button>
                    <div v-if="isGroupOpen(page.name) && page.children?.length" class="dm-subsubnav">
                      <router-link
                        v-for="child in page.children"
                        :key="child.name"
                        :to="child.to"
                        class="dm-subsubnav-link"
                        :class="{ 'dm-subsubnav-link--active': isRouteActive(child.name) }"
                      >
                        <i class="fa-solid" :class="child.icon" aria-hidden="true"></i>
                        {{ child.label }}
                      </router-link>
                    </div>
                  </div>
                </div>
              </template>

              <template v-else-if="activeMainTabKey === 'biblioteca'">
                <router-link to="/biblioteca" class="dm-nav-item dm-nav-item--active">
                  <i class="fa-solid fa-book" aria-hidden="true"></i>
                  Biblioteca de Documentos
                </router-link>
              </template>

              <template v-else-if="activeMainTabKey === 'analisador'">
                <router-link to="/analisador" class="dm-nav-item dm-nav-item--active">
                  <i class="fa-solid fa-magnifying-glass-chart" aria-hidden="true"></i>
                  Analisador de Documentos
                </router-link>
              </template>

              <template v-else-if="activeMainTabKey === 'pncp'">
                <router-link to="/pesquisador-pncp" class="dm-nav-item dm-nav-item--active">
                  <i class="fa-solid fa-database" aria-hidden="true"></i>
                  Pesquisador de Dados PNCP
                </router-link>
              </template>

              <template v-else-if="activeMainTabKey === 'usuario'">
                <router-link to="/area-do-usuario" class="dm-nav-item dm-nav-item--active">
                  <i class="fa-solid fa-user" aria-hidden="true"></i>
                  Área do Usuário
                </router-link>
              </template>
            </nav>
          </aside>

          <main class="dm-content">
            <router-view />
          </main>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';

const API_BASE = import.meta.env.VITE_API_URL || 'https://api.docmasteria.com.br';
const DARK_MODE_KEY = 'docmaster.ui.darkmode';
const router = useRouter();
const route = useRoute();

const user = ref(null);
const darkMode = ref(false);
const generationMenuOpen = ref(false);
const groupOpenState = ref({
  DispensaArt75I: false,
  DispensaArt75II: false,
  InexigibilidadeArt74I: false,
  EtpLivreGroup: false,
});

const generationPages = [
  {
    name: 'DispensaArt75I',
    label: 'Dispensa - Art. 75, I',
    icon: 'fa-gavel',
    children: [
      {
        name: 'DispensaArt75IObrasEngenharia',
        label: 'Obras e serviços de engenharia',
        icon: 'fa-compass-drafting',
        to: '/geracao/dispensa-art-75-i/obras-servicos-engenharia',
      },
      {
        name: 'DispensaArt75IManutencaoVeiculos',
        label: 'Manutenção de veículos',
        icon: 'fa-car-side',
        to: '/geracao/dispensa-art-75-i/manutencao-veiculos',
      },
    ],
  },
  {
    name: 'DispensaArt75II',
    label: 'Dispensa - Art. 75, II',
    icon: 'fa-scale-balanced',
    children: [
      {
        name: 'DispensaArt75IICompras',
        label: 'Compras',
        icon: 'fa-cart-shopping',
        to: '/geracao/dispensa-art-75-ii/compras',
      },
      {
        name: 'DispensaArt75IIServicos',
        label: 'Serviços',
        icon: 'fa-screwdriver-wrench',
        to: '/geracao/dispensa-art-75-ii/servicos',
      },
      {
        name: 'DispensaArt75IIComprasServicosInclusos',
        label: 'Compras com serviços inclusos',
        icon: 'fa-boxes-stacked',
        to: '/geracao/dispensa-art-75-ii/compras-servicos-inclusos',
      },
    ],
  },
  {
    name: 'InexigibilidadeArt74I',
    label: 'Inexigibilidade - Art. 74, I',
    icon: 'fa-file-circle-check',
    children: [
      {
        name: 'InexigibilidadeArt74IShowArtistico',
        label: 'Show artístico',
        icon: 'fa-music',
        to: '/geracao/inexigibilidade-art-74-i/show-artistico',
      },
    ],
  },
  {
    name: 'EtpLivreGroup',
    label: 'ETP Livre',
    icon: 'fa-file-pen',
    children: [
      {
        name: 'EtpLivre',
        label: 'ETP Livre',
        icon: 'fa-file-signature',
        to: '/geracao/etp-livre',
      },
    ],
  },
];

const generationRouteNames = new Set(
  generationPages.flatMap((page) => [page.name, ...(page.children || []).map((child) => child.name)]),
);

const mainTabs = [
  { key: 'geracao', label: 'Geração', icon: 'fa-file-lines', to: '/geracao/etp-livre' },
  { key: 'biblioteca', label: 'Biblioteca', icon: 'fa-book', to: '/biblioteca' },
  { key: 'analisador', label: 'Analisador', icon: 'fa-magnifying-glass-chart', to: '/analisador' },
  { key: 'pncp', label: 'Pesquisa de Preços', icon: 'fa-database', to: '/pesquisador-pncp' },
  { key: 'usuario', label: 'Área do Usuário', icon: 'fa-user', to: '/area-do-usuario' },
];

const isGenerationSectionActive = computed(() => {
  return route.name === 'DocumentGenerator' || generationRouteNames.has(route.name);
});

const activeMainTabKey = computed(() => {
  if (isGenerationSectionActive.value) return 'geracao';
  if (route.name === 'TemplateList') return 'biblioteca';
  if (route.name === 'DocumentAnalyzer') return 'analisador';
  if (route.name === 'PncpResearcher' || String(route.path || '').startsWith('/pesquisador-pncp')) return 'pncp';
  if (route.name === 'AreaDoUsuario') return 'usuario';
  return 'geracao';
});

const activeSectionLabel = computed(() => {
  if (activeMainTabKey.value === 'geracao') return 'Geração de Documentos';
  if (activeMainTabKey.value === 'biblioteca') return 'Biblioteca de Documentos';
  if (activeMainTabKey.value === 'analisador') return 'Analisador de Documentos';
  if (activeMainTabKey.value === 'pncp') return 'Pesquisa de Preços';
  if (activeMainTabKey.value === 'usuario') return 'Área do Usuário';
  return 'Módulo';
});

function isMainTabActive(key) {
  return activeMainTabKey.value === key;
}

function onMainTabClick(tab) {
  if (tab.key === 'geracao') {
    generationMenuOpen.value = true;
  }
  if (tab.to) router.push(tab.to);
}

function isRouteActive(name) {
  return route.name === name;
}

function toggleGroup(name) {
  groupOpenState.value[name] = !groupOpenState.value[name];
}

function isGroupOpen(name) {
  return !!groupOpenState.value[name];
}

function isGroupActive(page) {
  return page.children?.some((child) => child.name === route.name) || false;
}

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

function toggleDarkMode() {
  darkMode.value = !darkMode.value;
  try {
    localStorage.setItem(DARK_MODE_KEY, darkMode.value ? '1' : '0');
  } catch (_) {
    // noop
  }
}

onMounted(() => {
  try {
    darkMode.value = localStorage.getItem(DARK_MODE_KEY) === '1';
  } catch (_) {
    darkMode.value = false;
  }
  fetchMe();
  if (isGenerationSectionActive.value) generationMenuOpen.value = true;
});
</script>

<style scoped>
.dm-layout-bg {
  height: 100vh;
  overflow: hidden;
  background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 52%, #eef2f6 100%);
}
.dm-layout-bg.dm-dark {
  background: linear-gradient(180deg, #020617 0%, #0f172a 52%, #111827 100%);
}

.dm-layout-wrap {
  height: 100%;
  width: 100%;
  max-width: none;
  margin: 0;
  padding: 0;
}

.dm-shell {
  height: 100%;
  width: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  border: 0;
  background: rgba(255, 255, 255, 0.75);
  box-shadow: none;
}
.dm-dark .dm-shell {
  background: rgba(2, 6, 23, 0.78);
}

.dm-topbar {
  flex-shrink: 0;
  background: #254e78;
  color: #fff;
  border-bottom: 1px solid rgba(255, 255, 255, 0.14);
}
.dm-dark .dm-topbar {
  background: #020617;
}

.dm-topbar-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 14px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.14);
}

.dm-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.dm-brand-logo-wrap {
  width: 48px;
  height: 48px;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px;
}

.dm-brand-logo {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.dm-brand-text h1 {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
  letter-spacing: 0.03em;
}

.dm-brand-text span {
  display: inline-flex;
  margin-top: 4px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 999px;
  padding: 2px 10px;
  background: rgba(255, 255, 255, 0.12);
}

.dm-topbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dm-topbar-meta {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.9);
}

.dm-uf-flag {
  width: 24px;
  height: 16px;
  object-fit: cover;
  border-radius: 2px;
}

.dm-chip-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.22);
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  padding: 8px 14px;
  cursor: pointer;
}

.dm-chip-btn:hover {
  background: rgba(255, 255, 255, 0.18);
}

.dm-top-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 10px 20px;
}

.dm-top-tab {
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  padding: 7px 12px;
  font-size: 13px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.dm-top-tab:hover {
  background: rgba(255, 255, 255, 0.15);
}

.dm-top-tab--active {
  background: #fff;
  color: #254e78;
  border-color: rgba(255, 255, 255, 0.45);
}
.dm-dark .dm-top-tab {
  border-color: rgba(148, 163, 184, 0.25);
  background: rgba(15, 23, 42, 0.8);
  color: #e2e8f0;
}
.dm-dark .dm-top-tab:hover {
  background: rgba(30, 41, 59, 0.95);
}
.dm-dark .dm-top-tab--active {
  background: #1e293b;
  color: #f8fafc;
  border-color: #475569;
}

.dm-body {
  min-height: 0;
  flex: 1;
  display: grid;
  grid-template-columns: 284px minmax(0, 1fr);
}

.dm-sidebar {
  overflow: hidden;
  border-right: 1px solid #c6d3e1;
  background: #dce5ee;
}
.dm-dark .dm-sidebar {
  border-right-color: #1e293b;
  background: #020617;
}

.dm-sidebar-head {
  padding: 16px 18px;
  border-bottom: 1px solid #bccbda;
  background: #d2dee9;
}
.dm-dark .dm-sidebar-head {
  border-bottom-color: #1e293b;
  background: #0f172a;
}

.dm-sidebar-head .dm-sidebar-kicker {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #2c5a89;
}
.dm-dark .dm-sidebar-head .dm-sidebar-kicker {
  color: #94a3b8;
}

.dm-sidebar-head .dm-sidebar-title {
  margin-top: 6px;
  font-size: 15px;
  font-weight: 700;
  color: #254e78;
}
.dm-dark .dm-sidebar-head .dm-sidebar-title {
  color: #f8fafc;
}

.dm-sidebar-head p {
  margin: 6px 0 0;
  font-size: 12px;
  color: #475569;
}
.dm-dark .dm-sidebar-head p {
  color: #cbd5e1;
}

.dm-sidebar-nav {
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dm-nav-item,
.dm-nav-item:visited {
  text-decoration: none;
  color: #334155;
  border: 1px solid #cbd5e1;
  background: #fff;
  border-radius: 14px;
  padding: 10px 12px;
  font-size: 13px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.dm-dark .dm-nav-item,
.dm-dark .dm-nav-item:visited {
  color: #cbd5e1;
  border-color: #334155;
  background: #0f172a;
}

.dm-nav-item--expandable {
  width: 100%;
  justify-content: space-between;
  cursor: pointer;
}

.dm-nav-item--expandable span {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.dm-nav-item:hover,
.dm-subnav-btn:hover,
.dm-subsubnav-link:hover {
  background: #f8fafc;
}

.dm-nav-item--active {
  border-color: #254e78;
  color: #254e78;
  background: #f1f5f9;
}
.dm-dark .dm-nav-item--active {
  border-color: #64748b;
  color: #f8fafc;
  background: #1e293b;
}

.dm-subnav {
  margin-left: 8px;
  padding-left: 10px;
  border-left: 1px solid #cbd5e1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.dm-dark .dm-subnav {
  border-left-color: #334155;
}

.dm-subnav-btn {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  background: #fff;
  color: #334155;
  padding: 8px 10px;
  font-size: 12px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
}
.dm-dark .dm-subnav-btn {
  border-color: #334155;
  background: #0f172a;
  color: #cbd5e1;
}

.dm-subnav-btn span {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.dm-subnav-btn--active {
  border-color: #254e78;
  color: #254e78;
}
.dm-dark .dm-subnav-btn--active {
  border-color: #64748b;
  color: #f8fafc;
}

.dm-subsubnav {
  margin-left: 10px;
  padding-left: 10px;
  border-left: 1px solid #d1d5db;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.dm-dark .dm-subsubnav {
  border-left-color: #334155;
}

.dm-subsubnav-link,
.dm-subsubnav-link:visited {
  text-decoration: none;
  color: #334155;
  border: 1px solid #d1d5db;
  border-radius: 10px;
  background: #fff;
  padding: 7px 10px;
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.dm-dark .dm-subsubnav-link,
.dm-dark .dm-subsubnav-link:visited {
  color: #cbd5e1;
  border-color: #334155;
  background: #0f172a;
}

.dm-subsubnav-link--active {
  border-color: #254e78;
  background: #254e78;
  color: #fff;
}

.dm-content {
  min-height: 0;
  overflow-y: auto;
  padding: 16px;
  background: rgba(248, 250, 252, 0.62);
}
.dm-dark .dm-content {
  background: rgba(2, 6, 23, 0.48);
}

@media (max-width: 1279px) {
  .dm-body {
    grid-template-columns: 1fr;
  }
  .dm-sidebar {
    display: none;
  }
}
</style>
