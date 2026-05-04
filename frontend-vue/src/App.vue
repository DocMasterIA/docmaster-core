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
              v-for="tab in visibleMainTabs"
              :key="tab.key"
              type="button"
              class="dm-top-tab"
              :class="{ 'dm-top-tab--active': isMainTabActive(tab.key) }"
              @click="onMainTabClick(tab)"
            >
              <span class="dm-top-tab__icon">
                <i class="fa-solid" :class="tab.icon" aria-hidden="true"></i>
              </span>
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
              <template v-if="['dispensa', 'inexigibilidade', 'etp'].includes(activeMainTabKey)">
                <button
                  type="button"
                  class="dm-nav-item dm-nav-item--expandable"
                  :class="{ 'dm-nav-item--active': isGenerationSectionActive }"
                  @click="generationMenuOpen = !generationMenuOpen"
                >
                  <span><i class="fa-solid fa-file-lines" aria-hidden="true"></i>{{ activeSectionLabel }}</span>
                  <i class="fa-solid" :class="generationMenuOpen ? 'fa-chevron-up' : 'fa-chevron-down'" aria-hidden="true"></i>
                </button>

                <div v-if="generationMenuOpen" class="dm-subnav">
                  <div v-for="page in visibleGenerationPages" :key="page.name" class="dm-subnav-item">
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

              <template v-else-if="activeMainTabKey === 'analisador'">
                <router-link to="/analisador" class="dm-nav-item dm-nav-item--active">
                  <i class="fa-solid fa-magnifying-glass-chart" aria-hidden="true"></i>
                  Analisador de Documentos
                </router-link>
              </template>

              <template v-else-if="activeMainTabKey === 'pesquisa'">
                <router-link to="/pesquisador-pncp" class="dm-nav-item dm-nav-item--active">
                  <i class="fa-solid fa-database" aria-hidden="true"></i>
                  Pesquisa de Preços Inteligente
                </router-link>
              </template>

              <template v-else-if="activeMainTabKey === 'usuario'">
                <router-link to="/area-do-usuario" class="dm-nav-item dm-nav-item--active">
                  <i class="fa-solid fa-user" aria-hidden="true"></i>
                  Área do Usuário
                </router-link>
              </template>

              <template v-else-if="PLACEHOLDER_TAB_KEYS.includes(activeMainTabKey)">
                <div class="dm-nav-item dm-nav-item--static dm-nav-item--active" aria-current="page">
                  <i class="fa-solid fa-layer-group" aria-hidden="true"></i>
                  {{ activeSectionLabel }}
                </div>
                <p class="dm-sidebar-placeholder-note">
                  Módulo reservado; em breve haverá fluxos e formulários aqui. A URL já pode ser usada em links e favoritos.
                </p>
              </template>

              <template v-else></template>
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
import { ref, computed, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { firstAllowedPath, normalizeAllowedModules, resolveModuleKey } from './moduleAccess';

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

const PLACEHOLDER_TAB_KEYS = [
  'dispensa_eletronica',
  'pregao',
  'pregao_eletronico',
  'contratos',
  'controle_interno',
  'impugnacao',
  'recurso',
];

const mainTabs = [
  { key: 'dispensa', label: 'Dispensa', icon: 'fa-file-lines', to: '/geracao/dispensa-art-75-i/obras-servicos-engenharia' },
  { key: 'dispensa_eletronica', label: 'Dispensa Eletrônica', icon: 'fa-file-lines', to: '/dispensa-eletronica' },
  { key: 'pregao', label: 'Pregão', icon: 'fa-file-lines', to: '/pregao' },
  { key: 'pregao_eletronico', label: 'Pregão Eletrônico', icon: 'fa-file-lines', to: '/pregao-eletronico' },
  { key: 'inexigibilidade', label: 'Inexigibilidade', icon: 'fa-file-lines', to: '/geracao/inexigibilidade-art-74-i/show-artistico' },
  { key: 'etp', label: 'ETP', icon: 'fa-file-lines', to: '/geracao/etp-livre' },
  { key: 'analisador', label: 'Analisador de Documentos', icon: 'fa-magnifying-glass-chart', to: '/analisador' },
  { key: 'pesquisa', label: 'Pesquisa de Preços Inteligente', icon: 'fa-database', to: '/pesquisador-pncp' },
  { key: 'contratos', label: 'Contratos', icon: 'fa-file-lines', to: '/contratos' },
  { key: 'controle_interno', label: 'Controle Interno', icon: 'fa-file-lines', to: '/controle-interno' },
  { key: 'impugnacao', label: 'Impugnação', icon: 'fa-file-lines', to: '/impugnacao' },
  { key: 'recurso', label: 'Recurso Processo Licitatório', icon: 'fa-file-lines', to: '/recurso-processo-licitatorio' },
  { key: 'usuario', label: 'Área do Usuário', icon: 'fa-user', to: '/area-do-usuario' },
];

const allowedModules = computed(() => normalizeAllowedModules(user.value?.allowed_modules, !!user.value?.is_superuser));
const allowedModuleSet = computed(() => new Set(allowedModules.value));
const visibleMainTabs = computed(() => mainTabs.filter((tab) => allowedModuleSet.value.has(tab.key)));

const isGenerationSectionActive = computed(() => {
  return route.name === 'DocumentGenerator' || generationRouteNames.has(route.name);
});

function inferMainTabFromRoute() {
  const rname = String(route.name || '');
  const rpath = String(route.path || '');
  if (rname === 'ModuleDispensaEletronica' || rpath.startsWith('/dispensa-eletronica')) return 'dispensa_eletronica';
  if (rname === 'ModulePregao' || rpath === '/pregao') return 'pregao';
  if (rname === 'ModulePregaoEletronico' || rpath.startsWith('/pregao-eletronico')) return 'pregao_eletronico';
  if (rname === 'ModuleContratos' || rpath.startsWith('/contratos')) return 'contratos';
  if (rname === 'ModuleControleInterno' || rpath.startsWith('/controle-interno')) return 'controle_interno';
  if (rname === 'ModuleImpugnacao' || rpath.startsWith('/impugnacao')) return 'impugnacao';
  if (rname === 'ModuleRecursoLicitatorio' || rpath.startsWith('/recurso-processo-licitatorio')) return 'recurso';
  if (rname.startsWith('DispensaArt75')) return 'dispensa';
  if (rname.startsWith('InexigibilidadeArt74')) return 'inexigibilidade';
  if (rname === 'EtpLivre' || rpath.startsWith('/geracao/etp-livre')) return 'etp';
  if (rname === 'DocumentAnalyzer') return 'analisador';
  if (rname === 'PncpResearcher' || rpath.startsWith('/pesquisador-pncp')) return 'pesquisa';
  if (rname === 'AreaDoUsuario') return 'usuario';
  return 'dispensa';
}

const selectedMainTabKey = ref(inferMainTabFromRoute());
const activeMainTabKey = computed(() => selectedMainTabKey.value);

const visibleGenerationPages = computed(() => {
  if (activeMainTabKey.value === 'dispensa') {
    return generationPages.filter((p) => p.name === 'DispensaArt75I' || p.name === 'DispensaArt75II');
  }
  if (activeMainTabKey.value === 'inexigibilidade') {
    return generationPages.filter((p) => p.name === 'InexigibilidadeArt74I');
  }
  if (activeMainTabKey.value === 'etp') {
    return generationPages.filter((p) => p.name === 'EtpLivreGroup');
  }
  return [];
});

const activeSectionLabel = computed(() => {
  if (activeMainTabKey.value === 'dispensa') return 'Dispensa';
  if (activeMainTabKey.value === 'dispensa_eletronica') return 'Dispensa Eletrônica';
  if (activeMainTabKey.value === 'pregao') return 'Pregão';
  if (activeMainTabKey.value === 'pregao_eletronico') return 'Pregão Eletrônico';
  if (activeMainTabKey.value === 'inexigibilidade') return 'Inexigibilidade';
  if (activeMainTabKey.value === 'etp') return 'ETP';
  if (activeMainTabKey.value === 'analisador') return 'Analisador de Documentos';
  if (activeMainTabKey.value === 'pesquisa') return 'Pesquisa de Preços Inteligente';
  if (activeMainTabKey.value === 'contratos') return 'Contratos';
  if (activeMainTabKey.value === 'controle_interno') return 'Controle Interno';
  if (activeMainTabKey.value === 'impugnacao') return 'Impugnação';
  if (activeMainTabKey.value === 'recurso') return 'Recurso Processo Licitatório';
  if (activeMainTabKey.value === 'usuario') return 'Área do Usuário';
  return 'Módulo';
});

function isMainTabActive(key) {
  return activeMainTabKey.value === key;
}

function onMainTabClick(tab) {
  if (!allowedModuleSet.value.has(tab.key)) return;
  selectedMainTabKey.value = tab.key;
  if (['dispensa', 'inexigibilidade', 'etp'].includes(tab.key)) {
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

function syncDarkModeRootClass(enabled) {
  if (typeof document === 'undefined') return;
  document.documentElement.classList.toggle('dm-dark-theme', !!enabled);
  document.body.classList.toggle('dm-dark-theme', !!enabled);
}

onMounted(() => {
  try {
    darkMode.value = localStorage.getItem(DARK_MODE_KEY) === '1';
  } catch (_) {
    darkMode.value = false;
  }
  syncDarkModeRootClass(darkMode.value);
  fetchMe().then(() => {
    const currentModule = resolveModuleKey(route);
    if (currentModule && !allowedModuleSet.value.has(currentModule)) {
      router.replace(firstAllowedPath(allowedModuleSet.value));
      return;
    }
    if (visibleMainTabs.value.length && !allowedModuleSet.value.has(activeMainTabKey.value)) {
      selectedMainTabKey.value = visibleMainTabs.value[0].key;
    }
  });
  if (['dispensa', 'inexigibilidade', 'etp'].includes(activeMainTabKey.value)) generationMenuOpen.value = true;
});

watch(
  () => darkMode.value,
  (enabled) => {
    syncDarkModeRootClass(enabled);
  }
);

watch(
  () => route.fullPath,
  () => {
    const currentModule = resolveModuleKey(route);
    if (currentModule && !allowedModuleSet.value.has(currentModule)) {
      router.replace(firstAllowedPath(allowedModuleSet.value));
      return;
    }
    selectedMainTabKey.value = inferMainTabFromRoute();
  }
);
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

.dm-brand-text {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.dm-brand-text h1 {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
  letter-spacing: 0.03em;
}

.dm-brand-text span {
  display: inline-flex;
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

.dm-chip-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  font-size: 12px;
  font-weight: 800;
  padding: 8px 16px;
  cursor: pointer;
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.1);
  backdrop-filter: blur(6px);
  transition: transform 0.2s ease, background 0.2s ease, border-color 0.2s ease;
}

.dm-chip-btn:hover {
  transform: translateY(-1px);
  background: rgba(255, 255, 255, 0.18);
  border-color: rgba(255, 255, 255, 0.3);
}

.dm-top-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 10px 20px;
}

.dm-top-tab {
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  padding: 6px 12px 6px 10px;
  font-size: 13px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.dm-top-tab:hover {
  transform: translateY(-2px);
  border-color: rgba(255, 255, 255, 0.28);
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
}

.dm-top-tab--active {
  background: #fff;
  color: #254e78;
  border-color: rgba(255, 255, 255, 0.45);
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.14);
}

.dm-top-tab__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  transition: all 0.2s ease;
}

.dm-top-tab:hover .dm-top-tab__icon {
  background: rgba(255, 255, 255, 0.18);
}

.dm-top-tab--active .dm-top-tab__icon {
  background: #e8eef5;
  color: #254e78;
}
.dm-dark .dm-top-tab {
  border-color: rgba(51, 65, 85, 0.8);
  background: rgba(15, 23, 42, 0.7);
  color: #e2e8f0;
}
.dm-dark .dm-top-tab:hover {
  border-color: #64748b;
  background: #1e293b;
}
.dm-dark .dm-top-tab--active {
  border-color: #64748b;
  background: #1e293b;
  color: #f8fafc;
  box-shadow: 0 10px 22px rgba(2, 6, 23, 0.26);
}
.dm-dark .dm-top-tab__icon {
  background: #0f172a;
  color: #cbd5e1;
}
.dm-dark .dm-top-tab:hover .dm-top-tab__icon,
.dm-dark .dm-top-tab--active .dm-top-tab__icon {
  background: #334155;
  color: #f8fafc;
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

.dm-nav-item--static {
  cursor: default;
  pointer-events: none;
}

.dm-sidebar-placeholder-note {
  margin: 8px 0 0;
  padding: 0 4px 0 2px;
  font-size: 12px;
  line-height: 1.45;
  color: #64748b;
}

.dm-dark .dm-sidebar-placeholder-note {
  color: #94a3b8;
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

/* Remove títulos/subtítulos legados das views internas;
   o contexto principal agora é dado pelo shell (topbar + sidebar). */
:deep(.gov-page__header .gov-page__title),
:deep(.gov-page__header .gov-page__subtitle) {
  display: none !important;
}

:deep(.gov-page-header .gov-page-title),
:deep(.gov-page-header .gov-page-subtitle) {
  display: none !important;
}
.dm-dark .dm-content {
  background: rgba(2, 6, 23, 0.48);
}

/* Base visual global para todas as views internas */
:deep(.gov-surface) {
  border-radius: 24px !important;
  border: 1px solid #e2e8f0 !important;
  background: rgba(255, 255, 255, 0.96) !important;
  box-shadow: 0 14px 36px rgba(15, 23, 42, 0.045) !important;
}

:deep(.gov-surface__title) {
  font-size: 18px !important;
  font-weight: 700 !important;
  color: #0f172a !important;
}

:deep(.gov-surface__subtitle),
:deep(.gov-text-soft),
:deep(.gov-page__meta) {
  color: #64748b !important;
}

:deep(.gov-input) {
  border-radius: 16px !important;
  border: 1px solid #cbd5e1 !important;
  background: #fff !important;
  transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
}

:deep(.gov-input:focus) {
  border-color: #254e78 !important;
  box-shadow: 0 0 0 4px rgba(37, 78, 120, 0.1) !important;
}

:deep(.gov-btn) {
  border-radius: 999px !important;
  font-weight: 700 !important;
  transition: transform 0.15s ease, box-shadow 0.15s ease !important;
}

:deep(.gov-btn:hover) {
  transform: translateY(-1px);
}

:deep(.gov-btn--primary) {
  background: #254e78 !important;
  border-color: #254e78 !important;
  color: #fff !important;
  box-shadow: 0 16px 34px rgba(37, 78, 120, 0.24) !important;
}

:deep(.gov-btn--primary:hover) {
  background: #1f4468 !important;
  border-color: #1f4468 !important;
}

:deep(.gov-btn--outline) {
  border-color: #cbd5e1 !important;
  background: #fff !important;
}

.dm-dark :deep(.gov-surface) {
  border-color: #1e293b !important;
  background: rgba(15, 23, 42, 0.74) !important;
  box-shadow: 0 16px 36px rgba(2, 6, 23, 0.3) !important;
}

.dm-dark :deep(.gov-surface__title) {
  color: #f8fafc !important;
}

.dm-dark :deep(.gov-surface__subtitle),
.dm-dark :deep(.gov-text-soft),
.dm-dark :deep(.gov-page__meta) {
  color: #94a3b8 !important;
}

.dm-dark :deep(.gov-input) {
  border-color: #334155 !important;
  background: #0f172a !important;
  color: #e2e8f0 !important;
}

.dm-dark :deep(.gov-input--readonly) {
  background: #111827 !important;
  color: #94a3b8 !important;
}

.dm-dark :deep(.gov-btn--outline) {
  border-color: #475569 !important;
  color: #e2e8f0 !important;
  background: #0f172a !important;
}

.dm-dark :deep(.gov-btn--outline:hover) {
  background: #1e293b !important;
}

/* Padrao visual unificado para telas PNCP/Cotacoes (bia/pncp/cot/manual/item/cd) */
.dm-content :deep(.pncp-mock__summary-card),
.dm-content :deep(.bia-summary-card),
.dm-content :deep(.manual-summary-card),
.dm-content :deep(.cot-card),
.dm-content :deep(.item-card),
.dm-content :deep(.item-price-card),
.dm-content :deep(.cd-item-card),
.dm-content :deep(.bia-group-card),
.dm-content :deep(.item-cotacao-card),
.dm-content :deep(.pncp-modal),
.dm-content :deep(.cd-modal) {
  border: 1px solid #dbe4ef !important;
  border-radius: 16px !important;
  background: #ffffff !important;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06) !important;
}

.dm-content :deep(.pncp-new-btn),
.dm-content :deep(.pncp-chip),
.dm-content :deep(.pncp-action-btn),
.dm-content :deep(.pncp-modal__btn),
.dm-content :deep(.bia-add-cotacao-btn),
.dm-content :deep(.bia-back-btn),
.dm-content :deep(.manual-btn-search),
.dm-content :deep(.manual-btn-backfill),
.dm-content :deep(.manual-add-cotacao-btn),
.dm-content :deep(.cot-btn),
.dm-content :deep(.cot-back-btn),
.dm-content :deep(.item-search-btn),
.dm-content :deep(.item-back-btn),
.dm-content :deep(.cd-btn),
.dm-content :deep(.cd-back-btn) {
  border-radius: 999px !important;
  border: 1px solid #cfd9e6 !important;
  background: #fff !important;
  color: #1e293b !important;
  font-weight: 700 !important;
  transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease !important;
}

.dm-content :deep(.pncp-new-btn:hover),
.dm-content :deep(.pncp-chip:hover),
.dm-content :deep(.pncp-action-btn:hover),
.dm-content :deep(.pncp-modal__btn:hover),
.dm-content :deep(.bia-add-cotacao-btn:hover),
.dm-content :deep(.bia-back-btn:hover),
.dm-content :deep(.manual-btn-search:hover),
.dm-content :deep(.manual-btn-backfill:hover),
.dm-content :deep(.manual-add-cotacao-btn:hover),
.dm-content :deep(.cot-btn:hover),
.dm-content :deep(.cot-back-btn:hover),
.dm-content :deep(.item-search-btn:hover),
.dm-content :deep(.item-back-btn:hover),
.dm-content :deep(.cd-btn:hover),
.dm-content :deep(.cd-back-btn:hover) {
  transform: translateY(-1px) !important;
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.1) !important;
}

.dm-content :deep(.pncp-new-btn),
.dm-content :deep(.pncp-modal__btn--primary),
.dm-content :deep(.bia-add-cotacao-btn:not(.bia-add-cotacao-btn--ghost)),
.dm-content :deep(.manual-btn-search),
.dm-content :deep(.manual-add-cotacao-btn:not(.manual-add-cotacao-btn--ghost)),
.dm-content :deep(.cot-btn--primary),
.dm-content :deep(.item-search-btn),
.dm-content :deep(.cd-btn:not(.cd-btn--ghost)) {
  background: #254e78 !important;
  border-color: #254e78 !important;
  color: #fff !important;
}

.dm-content :deep(.pncp-chip--active),
.dm-content :deep(.pncp-status),
.dm-content :deep(.bia-pill),
.dm-content :deep(.bia-badge),
.dm-content :deep(.manual-status),
.dm-content :deep(.item-cotacao-card__fonte),
.dm-content :deep(.item-cotacao-card__similaridade) {
  border-radius: 999px !important;
}

.dm-content :deep(.pncp-mock__table-wrap),
.dm-content :deep(.bia-table-shell),
.dm-content :deep(.bia-table-scroll),
.dm-content :deep(.manual-results-table-shell),
.dm-content :deep(.manual-results-table-scroll),
.dm-content :deep(.cot-sheet-shell),
.dm-content :deep(.cot-sheet-scroll) {
  border: 1px solid #dbe4ef !important;
  border-radius: 16px !important;
  background: #fff !important;
}

.dm-content :deep(.pncp-mock__table th),
.dm-content :deep(.pncp-mock__table td),
.dm-content :deep(.bia-table th),
.dm-content :deep(.bia-table td),
.dm-content :deep(.manual-results-table th),
.dm-content :deep(.manual-results-table td),
.dm-content :deep(.cot-sheet-table th),
.dm-content :deep(.cot-sheet-table td) {
  border-color: #e2e8f0 !important;
}

.dm-content :deep(.gov-page__content input:not([type='checkbox']):not([type='radio'])),
.dm-content :deep(.gov-page__content select),
.dm-content :deep(.gov-page__content textarea) {
  border-radius: 14px !important;
  border: 1px solid #cbd5e1 !important;
  background: #fff !important;
  color: #0f172a !important;
}

.dm-content :deep(.gov-page__content input:not([type='checkbox']):not([type='radio']):focus),
.dm-content :deep(.gov-page__content select:focus),
.dm-content :deep(.gov-page__content textarea:focus) {
  border-color: #254e78 !important;
  box-shadow: 0 0 0 4px rgba(37, 78, 120, 0.1) !important;
  outline: none !important;
}

.dm-dark .dm-content :deep(.pncp-mock__summary-card),
.dm-dark .dm-content :deep(.bia-summary-card),
.dm-dark .dm-content :deep(.manual-summary-card),
.dm-dark .dm-content :deep(.cot-card),
.dm-dark .dm-content :deep(.item-card),
.dm-dark .dm-content :deep(.item-price-card),
.dm-dark .dm-content :deep(.item-cotacao-card__field),
.dm-dark .dm-content :deep(.item-empty-state),
.dm-dark .dm-content :deep(.cd-item-card),
.dm-dark .dm-content :deep(.bia-group-card),
.dm-dark .dm-content :deep(.item-cotacao-card),
.dm-dark .dm-content :deep(.pncp-modal),
.dm-dark .dm-content :deep(.cd-modal),
.dm-dark .dm-content :deep(.pncp-mock__table-wrap),
.dm-dark .dm-content :deep(.bia-table-shell),
.dm-dark .dm-content :deep(.bia-table-scroll),
.dm-dark .dm-content :deep(.manual-results-table-shell),
.dm-dark .dm-content :deep(.manual-results-table-scroll),
.dm-dark .dm-content :deep(.cot-sheet-shell),
.dm-dark .dm-content :deep(.cot-sheet-scroll) {
  border-color: #334155 !important;
  background: rgba(15, 23, 42, 0.86) !important;
}

.dm-dark .dm-content :deep(.pncp-new-btn),
.dm-dark .dm-content :deep(.pncp-chip),
.dm-dark .dm-content :deep(.pncp-action-btn),
.dm-dark .dm-content :deep(.pncp-modal__btn),
.dm-dark .dm-content :deep(.bia-add-cotacao-btn),
.dm-dark .dm-content :deep(.bia-back-btn),
.dm-dark .dm-content :deep(.manual-btn-search),
.dm-dark .dm-content :deep(.manual-btn-backfill),
.dm-dark .dm-content :deep(.manual-add-cotacao-btn),
.dm-dark .dm-content :deep(.cot-btn),
.dm-dark .dm-content :deep(.cot-back-btn),
.dm-dark .dm-content :deep(.item-search-btn),
.dm-dark .dm-content :deep(.item-back-btn),
.dm-dark .dm-content :deep(.cd-btn),
.dm-dark .dm-content :deep(.cd-back-btn) {
  border-color: #475569 !important;
  background: #0f172a !important;
  color: #e2e8f0 !important;
}

.dm-dark .dm-content :deep(.pncp-new-btn),
.dm-dark .dm-content :deep(.pncp-modal__btn--primary),
.dm-dark .dm-content :deep(.bia-add-cotacao-btn:not(.bia-add-cotacao-btn--ghost)),
.dm-dark .dm-content :deep(.manual-btn-search),
.dm-dark .dm-content :deep(.manual-add-cotacao-btn:not(.manual-add-cotacao-btn--ghost)),
.dm-dark .dm-content :deep(.cot-btn--primary),
.dm-dark .dm-content :deep(.item-search-btn),
.dm-dark .dm-content :deep(.cd-btn:not(.cd-btn--ghost)) {
  border-color: #64748b !important;
  background: #1e293b !important;
  color: #f8fafc !important;
}

.dm-dark .dm-content :deep(.gov-page__content input:not([type='checkbox']):not([type='radio'])),
.dm-dark .dm-content :deep(.gov-page__content select),
.dm-dark .dm-content :deep(.gov-page__content textarea) {
  border-color: #334155 !important;
  background: #0f172a !important;
  color: #e2e8f0 !important;
}

.dm-dark .dm-content :deep(.pncp-mock),
.dm-dark .dm-content :deep(.bia-table-shell),
.dm-dark .dm-content :deep(.manual-results-table-shell),
.dm-dark .dm-content :deep(.cot-sheet-shell),
.dm-dark .dm-content :deep(.item-cotacao-card),
.dm-dark .dm-content :deep(.cot-card),
.dm-dark .dm-content :deep(.manual-summary-card),
.dm-dark .dm-content :deep(.bia-summary-card) {
  background: #0f172a !important;
  border-color: #334155 !important;
}

.dm-dark .dm-content :deep(.pncp-mock__title),
.dm-dark .dm-content :deep(.pncp-mock__desc),
.dm-dark .dm-content :deep(.pncp-mock__usuario),
.dm-dark .dm-content :deep(.pncp-mock__table td),
.dm-dark .dm-content :deep(.bia-main),
.dm-dark .dm-content :deep(.manual-cot-main),
.dm-dark .dm-content :deep(.cot-sheet-table td),
.dm-dark .dm-content :deep(.item-cotacao-card__field strong) {
  color: #e2e8f0 !important;
}

/* Força final para cards da tela de cotação */
.dm-dark .dm-content :deep(.cot-title-editor),
.dm-dark .dm-content :deep(.cot-formula),
.dm-dark .dm-content :deep(.cot-global-variacao),
.dm-dark .dm-content :deep(.cot-fornecedor-field),
.dm-dark .dm-content :deep(.cot-new-item-block) {
  background: #0f172a !important;
  border-color: #334155 !important;
}

.dm-dark .dm-content :deep(.cot-title-editor__field span),
.dm-dark .dm-content :deep(.cot-formula__subtitle),
.dm-dark .dm-content :deep(.cot-global-variacao__subtitle),
.dm-dark .dm-content :deep(.cot-fornecedor-field__label),
.dm-dark .dm-content :deep(.cot-new-item-block__text p) {
  color: #94a3b8 !important;
}

.dm-dark .dm-content :deep(.cot-formula__title),
.dm-dark .dm-content :deep(.cot-global-variacao__title),
.dm-dark .dm-content :deep(.cot-fornecedor-field__value),
.dm-dark .dm-content :deep(.cot-new-item-block__text h2) {
  color: #e2e8f0 !important;
}

.dm-dark .dm-content :deep(.cot-title-editor__field input),
.dm-dark .dm-content :deep(.cot-formula__select) {
  background: #111827 !important;
  border-color: #334155 !important;
  color: #e2e8f0 !important;
}

/* CotacaoDetalhe: reforco em Status, Buscar item e colunas da tabela */
.dm-dark .dm-content :deep(.cot-sheet-search),
.dm-dark .dm-content :deep(.cot-sheet-status-filter) {
  background: #0f172a !important;
  border-color: #334155 !important;
  color: #cbd5e1 !important;
}

.dm-dark .dm-content :deep(.cot-sheet-search input),
.dm-dark .dm-content :deep(.cot-sheet-status-filter select) {
  background: transparent !important;
  color: #e2e8f0 !important;
}

.dm-dark .dm-content :deep(.cot-sheet-status-filter span) {
  color: #94a3b8 !important;
}

.dm-dark .dm-content :deep(.cot-sheet-table thead th) {
  background: #1e293b !important;
  color: #cbd5e1 !important;
}

.dm-dark .dm-content :deep(.cot-sheet-table tbody td) {
  background: #0f172a !important;
  color: #e2e8f0 !important;
}

.dm-dark .dm-content :deep(.cot-sheet-group),
.dm-dark .dm-content :deep(.cot-sheet-source) {
  background: #1e293b !important;
  color: #cbd5e1 !important;
}

.dm-dark .dm-content :deep(.pncp-mock__subtitle),
.dm-dark .dm-content :deep(.pncp-mock__summary-label),
.dm-dark .dm-content :deep(.pncp-mock__table th),
.dm-dark .dm-content :deep(.pncp-mock__desc-sub),
.dm-dark .dm-content :deep(.bia-meta),
.dm-dark .dm-content :deep(.manual-meta),
.dm-dark .dm-content :deep(.cot-sheet-table th),
.dm-dark .dm-content :deep(.item-cotacao-card__field span) {
  color: #94a3b8 !important;
}

/* Pedido do usuário: textos cinza -> branco no dark mode */
.dm-dark :deep(.gov-surface__subtitle),
.dm-dark :deep(.gov-text-soft),
.dm-dark :deep(.gov-page__meta),
.dm-dark .dm-content :deep(.pncp-mock__subtitle),
.dm-dark .dm-content :deep(.pncp-mock__summary-label),
.dm-dark .dm-content :deep(.pncp-mock__table th),
.dm-dark .dm-content :deep(.pncp-mock__desc-sub),
.dm-dark .dm-content :deep(.bia-meta),
.dm-dark .dm-content :deep(.manual-meta),
.dm-dark .dm-content :deep(.cot-sheet-table th),
.dm-dark .dm-content :deep(.item-cotacao-card__field span),
.dm-dark .dm-content :deep(.cot-title-editor__field span),
.dm-dark .dm-content :deep(.cot-formula__subtitle),
.dm-dark .dm-content :deep(.cot-global-variacao__subtitle),
.dm-dark .dm-content :deep(.cot-fornecedor-field__label),
.dm-dark .dm-content :deep(.cot-new-item-block__text p),
.dm-dark .dm-content :deep(.cot-sheet-status-filter span) {
  color: #ffffff !important;
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
