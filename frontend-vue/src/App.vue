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

        <div class="dm-body" :class="{ 'dm-body--nav-hidden': sidebarNavHidden }">
          <aside class="dm-sidebar">
            <div class="dm-sidebar-head">
              <div class="dm-sidebar-head__row">
                <div class="dm-sidebar-kicker">Navegação da seção</div>
                <button
                  type="button"
                  class="dm-sidebar-hide-btn"
                  title="Ocultar painel lateral"
                  aria-label="Ocultar navegação da seção"
                  @click="sidebarNavHidden = true"
                >
                  Ocultar
                </button>
              </div>
              <div class="dm-sidebar-title">{{ activeSectionLabel }}</div>
              <p>Selecione uma opção para avançar no fluxo.</p>
            </div>
            <nav class="dm-sidebar-nav">
              <template v-if="['dispensa', 'inexigibilidade', 'etp'].includes(activeMainTabKey)">
                <button
                  v-if="activeMainTabKey !== 'dispensa'"
                  type="button"
                  class="dm-nav-item dm-nav-item--expandable"
                  :class="{ 'dm-nav-item--active': isGenerationSectionActive }"
                  @click="generationMenuOpen = !generationMenuOpen"
                >
                  <span><i class="fa-solid fa-file-lines" aria-hidden="true"></i>{{ activeSectionLabel }}</span>
                  <i
                    class="fa-solid fa-chevron-down dm-sidebar-chevron"
                    :class="{ 'dm-sidebar-chevron--open': generationMenuOpen }"
                    aria-hidden="true"
                  ></i>
                </button>

                <div v-if="activeMainTabKey === 'dispensa' || generationMenuOpen" class="dm-subnav">
                  <div v-for="page in visibleGenerationPages" :key="page.name" class="dm-subnav-item">
                    <button
                      type="button"
                      class="dm-subnav-btn"
                      :class="{ 'dm-subnav-btn--active': isGroupActive(page) }"
                      @click="toggleGroup(page.name)"
                    >
                      <span><i class="fa-solid" :class="page.icon" aria-hidden="true"></i>{{ page.label }}</span>
                      <i
                        class="fa-solid fa-chevron-down dm-sidebar-chevron"
                        :class="{ 'dm-sidebar-chevron--open': isGroupOpen(page.name) }"
                        aria-hidden="true"
                      ></i>
                    </button>
                    <div v-if="isGroupOpen(page.name) && page.children?.length" class="dm-subsubnav">
                      <template v-for="section in groupedChildren(page)" :key="section.key">
                        <template v-if="isArt75DropdownSection(section)">
                          <button
                            type="button"
                            class="dm-subnav-art-btn"
                            :class="{
                              'dm-subnav-art-btn--open': isArtSectionOpen(page.name, section.key),
                              'dm-subnav-art-btn--selected': isSectionRouteActive(section),
                            }"
                            :aria-expanded="isArtSectionOpen(page.name, section.key)"
                            :aria-controls="`art-dd-${page.name}-${section.key}`"
                            @click="toggleArtSection(page.name, section.key)"
                          >
                            <span class="dm-subnav-art-btn__label">{{ section.title }}</span>
                            <i
                              class="fa-solid fa-chevron-down dm-sidebar-chevron"
                              :class="{ 'dm-sidebar-chevron--open': isArtSectionOpen(page.name, section.key) }"
                              aria-hidden="true"
                            ></i>
                          </button>
                          <div
                            :id="`art-dd-${page.name}-${section.key}`"
                            v-show="isArtSectionOpen(page.name, section.key)"
                            class="dm-art-dropdown-links"
                            role="region"
                            :aria-label="`${section.title}: fluxos`"
                          >
                            <router-link
                              v-for="child in section.items"
                              :key="child.name"
                              :to="child.to"
                              class="dm-subsubnav-link"
                              :class="{ 'dm-subsubnav-link--active': isRouteActive(child.name) }"
                              :aria-current="isRouteActive(child.name) ? 'page' : undefined"
                            >
                              <i class="fa-solid dm-subsubnav-link__icon" :class="child.icon" aria-hidden="true"></i>
                              <span class="dm-subsubnav-link__text">{{ child.label }}</span>
                              <i class="fa-solid fa-chevron-right dm-subsubnav-link__chevron" aria-hidden="true"></i>
                            </router-link>
                          </div>
                        </template>
                        <template v-else>
                          <div class="dm-subsubnav-section-title">{{ section.title }}</div>
                          <router-link
                            v-for="child in section.items"
                            :key="child.name"
                            :to="child.to"
                            class="dm-subsubnav-link"
                            :class="{ 'dm-subsubnav-link--active': isRouteActive(child.name) }"
                            :aria-current="isRouteActive(child.name) ? 'page' : undefined"
                          >
                            <i class="fa-solid dm-subsubnav-link__icon" :class="child.icon" aria-hidden="true"></i>
                            <span class="dm-subsubnav-link__text">{{ child.label }}</span>
                            <i class="fa-solid fa-chevron-right dm-subsubnav-link__chevron" aria-hidden="true"></i>
                          </router-link>
                        </template>
                      </template>
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

          <button
            v-if="sidebarNavHidden"
            type="button"
            class="dm-nav-reveal-fab"
            title="Mostrar painel lateral de navegação"
            aria-label="Mostrar navegação da seção"
            @click="sidebarNavHidden = false"
          >
            <i class="fa-solid fa-bars dm-nav-reveal-fab__icon" aria-hidden="true"></i>
            <span>Mostrar navegação</span>
          </button>

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
import { getApiBase } from '@/utils/apiBase.js';

const API_BASE = getApiBase();
const DARK_MODE_KEY = 'docmaster.ui.darkmode';
const SIDEBAR_NAV_HIDDEN_KEY = 'docmaster.ui.sidebarNavHidden';
const router = useRouter();
const route = useRoute();

const user = ref(null);
const darkMode = ref(false);
/** Painel lateral (≥1280px); em viewports estreitas a sidebar já fica oculta por CSS. */
const sidebarNavHidden = ref(false);
const generationMenuOpen = ref(false);
/** Abre/fecha dropdown «Art. 75, I / II» por grupo: chave `${pageName}::${sectionKey}`. */
const artSectionOpen = ref({});
const groupOpenState = ref({
  DispensaRapidaGroup: false,
  DispensaArt75II: false,
  InexigibilidadeArt74I: false,
  EtpLivreGroup: false,
});

const generationPages = [
  {
    name: 'DispensaRapidaGroup',
    label: 'Dispensa rápida',
    icon: 'fa-gavel',
    children: [
      {
        name: 'DispensaRapidaArt75IObrasEngenharia',
        label: 'Obras e serviços de engenharia',
        icon: 'fa-compass-drafting',
        subsection: 'Art. 75, I',
        to: '/geracao/dispensa-rapida/art-75-i/obras-servicos-engenharia',
      },
      {
        name: 'DispensaRapidaArt75IManutencaoVeiculos',
        label: 'Manutenção de veículos',
        icon: 'fa-car-side',
        subsection: 'Art. 75, I',
        to: '/geracao/dispensa-rapida/art-75-i/manutencao-veiculos',
      },
      {
        name: 'DispensaRapidaArt75IICompras',
        label: 'Compras',
        icon: 'fa-cart-shopping',
        subsection: 'Art. 75, II',
        to: '/geracao/dispensa-rapida/art-75-ii/compras',
      },
      {
        name: 'DispensaRapidaArt75IIServicos',
        label: 'Serviços',
        icon: 'fa-screwdriver-wrench',
        subsection: 'Art. 75, II',
        to: '/geracao/dispensa-rapida/art-75-ii/servicos',
      },
      {
        name: 'DispensaRapidaArt75IIComprasServicosInclusos',
        label: 'Compras com serviços inclusos',
        icon: 'fa-boxes-stacked',
        subsection: 'Art. 75, II',
        to: '/geracao/dispensa-rapida/art-75-ii/compras-servicos-inclusos',
      },
    ],
  },
  {
    name: 'DispensaArt75II',
    label: 'Dispensa normal',
    icon: 'fa-scale-balanced',
    children: [
      {
        name: 'DispensaArt75IICompras',
        label: 'Compras',
        icon: 'fa-cart-shopping',
        subsection: 'Art. 75, II',
        to: '/geracao/dispensa-art-75-ii/compras',
      },
      {
        name: 'DispensaArt75IIServicos',
        label: 'Serviços',
        icon: 'fa-screwdriver-wrench',
        subsection: 'Art. 75, II',
        to: '/geracao/dispensa-art-75-ii/servicos',
      },
      {
        name: 'DispensaArt75IIComprasServicosInclusos',
        label: 'Compras com serviços inclusos',
        icon: 'fa-boxes-stacked',
        subsection: 'Art. 75, II',
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
        name: 'InexigibilidadeArt74IManutencaoVeiculosPreview',
        label: 'Manutenção de veículos',
        icon: 'fa-car-side',
        to: '/geracao/inexigibilidade-art-74-i/manutencao-veiculos',
      },
      {
        name: 'InexigibilidadeArt74IFornecedorExclusivoPreview',
        label: 'Fornecedor exclusivo',
        icon: 'fa-industry',
        to: '/geracao/inexigibilidade-art-74-i/fornecedor-exclusivo',
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

const generationRouteNames = new Set([
  'DispensaGeracaoHub',
  'InexigibilidadeGeracaoHub',
  ...generationPages.flatMap((page) => [page.name, ...(page.children || []).map((child) => child.name)]),
]);

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
  { key: 'dispensa', label: 'Dispensa', icon: 'fa-file-lines', to: '/geracao/dispensa' },
  { key: 'dispensa_eletronica', label: 'Dispensa Eletrônica', icon: 'fa-file-lines', to: '/dispensa-eletronica' },
  { key: 'pregao', label: 'Pregão', icon: 'fa-file-lines', to: '/pregao' },
  { key: 'pregao_eletronico', label: 'Pregão Eletrônico', icon: 'fa-file-lines', to: '/pregao-eletronico' },
  { key: 'inexigibilidade', label: 'Inexigibilidade', icon: 'fa-file-lines', to: '/geracao/inexigibilidade' },
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
  if (rname === 'DispensaGeracaoHub' || rpath === '/geracao/dispensa') return 'dispensa';
  if (rname === 'InexigibilidadeGeracaoHub' || rpath === '/geracao/inexigibilidade') return 'inexigibilidade';
  if (rname === 'ModuleDispensaEletronica' || rpath.startsWith('/dispensa-eletronica')) return 'dispensa_eletronica';
  if (rname === 'ModulePregao' || rpath === '/pregao') return 'pregao';
  if (rname === 'ModulePregaoEletronico' || rpath.startsWith('/pregao-eletronico')) return 'pregao_eletronico';
  if (rname === 'ModuleContratos' || rpath.startsWith('/contratos')) return 'contratos';
  if (rname === 'ModuleControleInterno' || rpath.startsWith('/controle-interno')) return 'controle_interno';
  if (rname === 'ModuleImpugnacao' || rpath.startsWith('/impugnacao')) return 'impugnacao';
  if (rname === 'ModuleRecursoLicitatorio' || rpath.startsWith('/recurso-processo-licitatorio')) return 'recurso';
  if (
    rname.startsWith('DispensaArt75')
    || rname.startsWith('DispensaRapida')
    || rpath.startsWith('/geracao/dispensa-rapida')
  ) {
    return 'dispensa';
  }
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
    return generationPages.filter((p) => p.name === 'DispensaRapidaGroup' || p.name === 'DispensaArt75II');
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

/** Algum fluxo desta secção (Art. 75, I / II ou «Outros») corresponde à rota actual. */
function isSectionRouteActive(section) {
  const items = section?.items;
  if (!Array.isArray(items) || !items.length) return false;
  return items.some((c) => c.name === route.name);
}

function toggleGroup(name) {
  const willClose = !!groupOpenState.value[name];
  if (willClose) {
    groupOpenState.value = { ...groupOpenState.value, [name]: false };
    return;
  }
  const next = {};
  for (const key of Object.keys(groupOpenState.value)) {
    next[key] = key === name;
  }
  groupOpenState.value = next;
  /* Ao mudar de «Dispensa rápida» / «Dispensa normal», etc., fecha dropdowns Art. 75 abertos no grupo anterior. */
  artSectionOpen.value = {};
}

function isGroupOpen(name) {
  return !!groupOpenState.value[name];
}

function isGroupActive(page) {
  return page.children?.some((child) => child.name === route.name) || false;
}

function isArt75DropdownSection(section) {
  return section?.key === 'Art. 75, I' || section?.key === 'Art. 75, II';
}

function toggleArtSection(pageName, sectionKey) {
  const k = `${pageName}::${sectionKey}`;
  const isOpen = !!artSectionOpen.value[k];
  if (isOpen) {
    artSectionOpen.value = { ...artSectionOpen.value, [k]: false };
    return;
  }
  /* Só uma secção Art. 75 (I ou II) aberta de cada vez na navegação lateral. */
  artSectionOpen.value = { [k]: true };
}

function isArtSectionOpen(pageName, sectionKey) {
  return !!artSectionOpen.value[`${pageName}::${sectionKey}`];
}

function groupedChildren(page) {
  const children = Array.isArray(page?.children) ? page.children : [];
  const sections = [
    { key: 'Art. 75, I', title: 'Art. 75, I', items: [] },
    { key: 'Art. 75, II', title: 'Art. 75, II', items: [] },
  ];
  const byKey = new Map(sections.map((s) => [s.key, s]));
  const fallback = [];
  children.forEach((child) => {
    const section = byKey.get(child.subsection || '');
    if (section) section.items.push(child);
    else fallback.push(child);
  });
  const ordered = sections.filter((s) => s.items.length > 0);
  if (fallback.length > 0) ordered.push({ key: 'Outros', title: 'Outros', items: fallback });
  return ordered.length > 0 ? ordered : [{ key: 'Itens', title: 'Itens', items: children }];
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
  try {
    sidebarNavHidden.value = localStorage.getItem(SIDEBAR_NAV_HIDDEN_KEY) === '1';
  } catch (_) {
    sidebarNavHidden.value = false;
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

watch(sidebarNavHidden, (hidden) => {
  try {
    if (hidden) localStorage.setItem(SIDEBAR_NAV_HIDDEN_KEY, '1');
    else localStorage.removeItem(SIDEBAR_NAV_HIDDEN_KEY);
  } catch (_) {
    // noop
  }
});

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

watch(
  () => route.name,
  (n) => {
    const name = String(n || '');
    if (name === 'DispensaGeracaoHub' || name === 'InexigibilidadeGeracaoHub') {
      artSectionOpen.value = {};
      return;
    }
    for (const page of generationPages) {
      if (page.name !== 'DispensaRapidaGroup' && page.name !== 'DispensaArt75II') continue;
      for (const c of page.children || []) {
        if (c.name === name && c.subsection) {
          artSectionOpen.value = {
            [`${page.name}::${c.subsection}`]: true,
          };
          const nextG = {};
          for (const key of Object.keys(groupOpenState.value)) {
            nextG[key] = key === page.name;
          }
          groupOpenState.value = nextG;
          return;
        }
      }
    }
  },
  { immediate: true },
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

.dm-body--nav-hidden {
  grid-template-columns: minmax(0, 1fr);
  position: relative;
}

.dm-body--nav-hidden .dm-sidebar {
  display: none;
}

/* Navegação lateral — hierarquia com cantos arredondados moderados (nível 1 branco; nível 2 azul escuro; nível 3 activo mesmo azul escuro). */
.dm-sidebar {
  --dm-nav-bg: #e4ecf4;
  --dm-nav-l1-bg: #ffffff;
  --dm-nav-l1-text: #154e78;
  --dm-nav-l2-bg: #154e78;
  --dm-nav-l2-text: #ffffff;
  --dm-nav-l2-hover: #1a5d8f;
  --dm-nav-l3-active-bg: var(--dm-nav-l2-bg);
  --dm-nav-l3-active-text: #ffffff;
  --dm-nav-l3-bg: #ffffff;
  --dm-nav-l3-text: #154e78;
  --dm-nav-tree: #c5d0e0;
  --dm-nav-chevron-muted: #94a3b8;
  --dm-nav-item-radius: 12px;
  --dm-subnav-major-to-nested-gap: 10px;
  overflow: hidden;
  border-right: 1px solid #c6d3e1;
  background: var(--dm-nav-bg);
}
.dm-dark .dm-sidebar {
  --dm-nav-bg: #020617;
  --dm-nav-l1-bg: #0f172a;
  --dm-nav-l1-text: #e2e8f0;
  --dm-nav-l2-bg: #1e3a5f;
  --dm-nav-l2-text: #f8fafc;
  --dm-nav-l2-hover: #2563eb;
  --dm-nav-l3-active-bg: var(--dm-nav-l2-bg);
  --dm-nav-l3-active-text: #f8fafc;
  --dm-nav-l3-bg: #0f172a;
  --dm-nav-l3-text: #e2e8f0;
  --dm-nav-tree: #334155;
  --dm-nav-chevron-muted: #94a3b8;
  --dm-nav-item-radius: 12px;
  --dm-subnav-major-to-nested-gap: 10px;
  border-right-color: #1e293b;
  background: var(--dm-nav-bg);
}

.dm-sidebar-head {
  padding: 16px 18px;
  border-bottom: 1px solid #c5d4e4;
  background: rgba(255, 255, 255, 0.45);
}
.dm-dark .dm-sidebar-head {
  border-bottom-color: #1e293b;
  background: rgba(15, 23, 42, 0.65);
}

.dm-sidebar-head__row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.dm-sidebar-head__row .dm-sidebar-kicker {
  flex: 1 1 auto;
  min-width: 0;
  line-height: 1.35;
}

.dm-sidebar-hide-btn {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin: 0;
  padding: 4px 8px;
  border: 1px solid #94a3b8;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.65);
  color: #334155;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}
.dm-sidebar-hide-btn:hover {
  background: #fff;
  border-color: #254e78;
  color: #254e78;
}
.dm-dark .dm-sidebar-hide-btn {
  border-color: #475569;
  background: rgba(30, 41, 59, 0.6);
  color: #cbd5e1;
}
.dm-dark .dm-sidebar-hide-btn:hover {
  border-color: #60a5fa;
  color: #f8fafc;
  background: #1e293b;
}

@media (max-width: 1279px) {
  .dm-sidebar-hide-btn {
    display: none;
  }
}

/* Botão flutuante (sem faixa) quando a sidebar está oculta — desktop. */
.dm-nav-reveal-fab {
  display: none;
  position: absolute;
  top: 10px;
  left: 12px;
  z-index: 40;
  margin: 0;
  gap: 8px;
  padding: 8px 14px;
  border: 1px solid #94a3b8;
  border-radius: 10px;
  background: #fff;
  color: #254e78;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.12);
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease, box-shadow 0.15s ease;
}

.dm-nav-reveal-fab__icon {
  font-size: 14px;
  line-height: 1;
}

.dm-nav-reveal-fab:hover {
  background: #f1f5f9;
  border-color: #254e78;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.16);
}
.dm-dark .dm-nav-reveal-fab {
  border-color: #475569;
  background: #1e293b;
  color: #93c5fd;
  box-shadow: 0 4px 16px rgba(2, 6, 23, 0.45);
}
.dm-dark .dm-nav-reveal-fab:hover {
  background: #334155;
  border-color: #60a5fa;
  color: #f8fafc;
}

@media (min-width: 1280px) {
  .dm-body--nav-hidden .dm-nav-reveal-fab {
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }

  /* Espaço para o FAB não cobrir o primeiro bloco da página. */
  .dm-body--nav-hidden .dm-content {
    padding-top: 52px;
  }
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
  padding: 14px 12px 18px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* Chevron da sidebar: fechado aponta à direita (−90°), aberto para baixo (0°). */
.dm-sidebar-chevron {
  display: inline-block;
  flex-shrink: 0;
  transform: rotate(-90deg);
  transform-origin: 50% 50%;
  transition: transform 0.22s cubic-bezier(0.33, 1, 0.68, 1);
}
.dm-sidebar-chevron.dm-sidebar-chevron--open {
  transform: rotate(0deg);
}
@media (prefers-reduced-motion: reduce) {
  .dm-sidebar-chevron {
    transition: none;
  }
}

.dm-nav-item,
.dm-nav-item:visited {
  text-decoration: none;
  color: var(--dm-nav-l1-text);
  border: none;
  background: var(--dm-nav-l1-bg);
  border-radius: var(--dm-nav-item-radius, 12px);
  padding: 11px 14px 11px 16px;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.01em;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transition: background 0.15s ease, color 0.15s ease;
}
.dm-dark .dm-nav-item,
.dm-dark .dm-nav-item:visited {
  color: var(--dm-nav-l1-text);
  background: var(--dm-nav-l1-bg);
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

.dm-nav-item--expandable .dm-sidebar-chevron {
  color: var(--dm-nav-chevron-muted);
  font-size: 11px;
  opacity: 0.95;
}

.dm-nav-item:not(.dm-nav-item--static):hover {
  background: #eef3f9;
}
.dm-dark .dm-nav-item:not(.dm-nav-item--static):hover {
  background: #1e293b;
}
.dm-nav-item--active:not(.dm-nav-item--static):hover {
  background: var(--dm-nav-l1-bg);
}
.dm-dark .dm-nav-item--active:not(.dm-nav-item--static):hover {
  background: var(--dm-nav-l1-bg);
}

.dm-subnav-btn:hover:not(.dm-subnav-btn--active) {
  background: #eef3f9;
}
.dm-dark .dm-subnav-btn:hover:not(.dm-subnav-btn--active) {
  background: #1e293b;
}

.dm-subsubnav-link:hover:not(.dm-subsubnav-link--active) {
  background: #eef3f9;
}
.dm-dark .dm-subsubnav-link:hover:not(.dm-subsubnav-link--active) {
  background: #1e293b;
}

.dm-nav-item--active {
  color: var(--dm-nav-l1-text);
  background: var(--dm-nav-l1-bg);
}
.dm-dark .dm-nav-item--active {
  color: var(--dm-nav-l1-text);
  background: var(--dm-nav-l1-bg);
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
  margin-left: 4px;
  padding-left: 12px;
  border-left: 1px solid var(--dm-nav-tree);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.dm-dark .dm-subnav {
  border-left-color: var(--dm-nav-tree);
}

/* Nível 1 (grupo: Dispensa rápida, etc.) — fundo branco, texto azul escuro. */
.dm-subnav-btn {
  width: 100%;
  border: none;
  border-radius: var(--dm-nav-item-radius, 12px);
  background: var(--dm-nav-l1-bg);
  color: var(--dm-nav-l1-text);
  padding: 10px 14px 10px 16px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.02em;
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}
.dm-dark .dm-subnav-btn {
  background: var(--dm-nav-l1-bg);
  color: var(--dm-nav-l1-text);
}

.dm-subnav-btn span {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.dm-subnav-btn .dm-sidebar-chevron {
  color: var(--dm-nav-chevron-muted);
  font-size: 10px;
}

/* Grupo com rota activa: mantém nível 1. */
.dm-subnav-btn--active {
  color: var(--dm-nav-l1-text);
  background: var(--dm-nav-l1-bg);
}
.dm-dark .dm-subnav-btn--active {
  color: var(--dm-nav-l1-text);
  background: var(--dm-nav-l1-bg);
}
.dm-subnav-btn--active:hover {
  background: #e8eef6;
}
.dm-dark .dm-subnav-btn--active:hover {
  background: #1e293b;
}

/* Nível 2 (Art. 75, I / II) — pílula azul escuro, texto branco, chevron branco. */
.dm-subnav-art-btn {
  width: 100%;
  margin-top: 4px;
  border: none;
  border-radius: var(--dm-nav-item-radius, 12px);
  background: var(--dm-nav-l2-bg);
  color: var(--dm-nav-l2-text);
  padding: 9px 14px 9px 16px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.03em;
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  cursor: pointer;
  text-align: left;
  transition: background 0.15s ease;
}
.dm-subnav-art-btn:first-child {
  margin-top: 0;
}
.dm-dark .dm-subnav-art-btn {
  background: var(--dm-nav-l2-bg);
  color: var(--dm-nav-l2-text);
}
.dm-subnav-art-btn:hover {
  background: var(--dm-nav-l2-hover);
}
.dm-dark .dm-subnav-art-btn:hover {
  background: var(--dm-nav-l2-hover);
}
.dm-subnav-art-btn--open {
  background: var(--dm-nav-l2-bg);
  color: var(--dm-nav-l2-text);
}
.dm-dark .dm-subnav-art-btn--open {
  background: var(--dm-nav-l2-bg);
  color: var(--dm-nav-l2-text);
}

.dm-subnav-art-btn .dm-sidebar-chevron {
  color: rgba(255, 255, 255, 0.85);
  font-size: 10px;
}

.dm-subnav-art-btn__label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.dm-subnav-art-btn--selected {
  background: var(--dm-nav-l2-bg);
  color: var(--dm-nav-l2-text);
  outline: 2px solid rgba(255, 255, 255, 0.45);
  outline-offset: 0;
}
.dm-dark .dm-subnav-art-btn--selected {
  background: var(--dm-nav-l2-bg);
  color: var(--dm-nav-l2-text);
  outline: 2px solid rgba(147, 197, 253, 0.55);
  outline-offset: 0;
}
.dm-subnav-art-btn--selected.dm-subnav-art-btn--open {
  background: var(--dm-nav-l2-hover);
}
.dm-dark .dm-subnav-art-btn--selected.dm-subnav-art-btn--open {
  background: var(--dm-nav-l2-hover);
}

.dm-art-dropdown-links {
  margin: 6px 0 4px 6px;
  padding-left: 12px;
  border-left: 1px solid var(--dm-nav-tree);
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.dm-dark .dm-art-dropdown-links {
  border-left-color: var(--dm-nav-tree);
}

.dm-subsubnav {
  margin-top: var(--dm-subnav-major-to-nested-gap);
  margin-left: 6px;
  padding-left: 12px;
  border-left: 1px solid var(--dm-nav-tree);
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.dm-dark .dm-subsubnav {
  border-left-color: var(--dm-nav-tree);
}

.dm-subsubnav-section-title {
  margin-top: 6px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #64748b;
}
.dm-subsubnav-section-title:first-child {
  margin-top: 0;
}
.dm-dark .dm-subsubnav-section-title {
  color: #94a3b8;
}

/* Nível 3 — inactivo: pílula branca texto azul; activo: pílula azul médio texto branco. */
.dm-subsubnav-link,
.dm-subsubnav-link:visited {
  text-decoration: none;
  color: var(--dm-nav-l3-text);
  border: none;
  border-radius: var(--dm-nav-item-radius, 12px);
  background: var(--dm-nav-l3-bg);
  padding: 8px 14px 8px 16px;
  font-size: 12px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  box-sizing: border-box;
  justify-content: flex-start;
  transition: background 0.15s ease, color 0.15s ease;
}
.dm-subsubnav-link__text {
  flex: 1 1 auto;
  min-width: 0;
  text-align: left;
  line-height: 1.25;
}
.dm-subsubnav-link__icon {
  color: var(--dm-nav-l3-text);
  opacity: 0.88;
  flex-shrink: 0;
}
.dm-subsubnav-link__chevron {
  flex-shrink: 0;
  margin-left: auto;
  padding-left: 6px;
  font-size: 10px;
  color: var(--dm-nav-chevron-muted);
  opacity: 0.95;
}
.dm-dark .dm-subsubnav-link,
.dm-dark .dm-subsubnav-link:visited {
  color: var(--dm-nav-l3-text);
  background: var(--dm-nav-l3-bg);
}

.dm-subsubnav-link.dm-subsubnav-link--active,
.dm-subsubnav-link.dm-subsubnav-link--active:visited {
  border: none;
  background: var(--dm-nav-l3-active-bg);
  color: var(--dm-nav-l3-active-text);
  font-weight: 700;
}
.dm-subsubnav-link.dm-subsubnav-link--active .dm-subsubnav-link__icon {
  color: rgba(255, 255, 255, 0.92);
}
.dm-subsubnav-link.dm-subsubnav-link--active .dm-subsubnav-link__chevron {
  color: rgba(255, 255, 255, 0.78);
}
.dm-dark .dm-subsubnav-link.dm-subsubnav-link--active,
.dm-dark .dm-subsubnav-link.dm-subsubnav-link--active:visited {
  background: var(--dm-nav-l3-active-bg);
  color: var(--dm-nav-l3-active-text);
}

/* Foco por teclado: contorno azul discreto (sem anel largo). */
.dm-nav-item:focus:not(:focus-visible),
.dm-subnav-btn:focus:not(:focus-visible),
.dm-subnav-art-btn:focus:not(:focus-visible),
.dm-subsubnav-link:focus:not(:focus-visible) {
  outline: none;
}
.dm-nav-item:focus-visible,
.dm-subnav-btn:focus-visible,
.dm-subnav-art-btn:focus-visible,
.dm-subsubnav-link:focus-visible {
  outline: 2px solid #254e78;
  outline-offset: 2px;
}
.dm-dark .dm-nav-item:focus-visible,
.dm-dark .dm-subnav-btn:focus-visible,
.dm-dark .dm-subnav-art-btn:focus-visible,
.dm-dark .dm-subsubnav-link:focus-visible {
  outline-color: #60a5fa;
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

.dm-dark .dm-content :deep(.item-cotacao-card__remove) {
  border-color: #7f1d1d !important;
  background: #0f172a !important;
  color: #fca5a5 !important;
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
