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
                <button
                  type="button"
                  class="gov-nav__link gov-nav__link--expandable"
                  :class="{ 'gov-nav__link--active': isGenerationSectionActive }"
                  @click="generationMenuOpen = !generationMenuOpen"
                >
                  <span class="gov-nav__link-main">
                    <i class="gov-nav__link-icon fa-solid fa-file-lines" aria-hidden="true"></i>
                    Geração de Documentos
                  </span>
                  <i
                    class="fa-solid"
                    :class="generationMenuOpen ? 'fa-chevron-up' : 'fa-chevron-down'"
                    aria-hidden="true"
                  ></i>
                </button>
                <ul v-if="generationMenuOpen" class="gov-subnav">
                  <li
                    v-for="page in generationPages"
                    :key="page.name"
                    class="gov-subnav__item"
                  >
                    <button
                      type="button"
                      class="gov-subnav__link gov-subnav__link--expandable"
                      :class="{ 'gov-subnav__link--active': isGroupActive(page) }"
                      @click="toggleGroup(page.name)"
                    >
                      <span class="gov-subnav__link-main">
                        <i class="gov-nav__link-icon fa-solid" :class="page.icon" aria-hidden="true"></i>
                        {{ page.label }}
                      </span>
                      <i
                        class="fa-solid"
                        :class="isGroupOpen(page.name) ? 'fa-chevron-up' : 'fa-chevron-down'"
                        aria-hidden="true"
                      ></i>
                    </button>
                    <ul v-if="isGroupOpen(page.name) && page.children?.length" class="gov-subsubnav">
                      <li
                        v-for="child in page.children"
                        :key="child.name"
                        class="gov-subsubnav__item"
                      >
                        <router-link
                          :to="child.to"
                          class="gov-subsubnav__link"
                          :class="{ 'gov-subsubnav__link--active': isRouteActive(child.name) }"
                        >
                          <i class="gov-nav__link-icon fa-solid" :class="child.icon" aria-hidden="true"></i>
                          {{ child.label }}
                        </router-link>
                      </li>
                    </ul>
                    <div
                      v-else-if="isGroupOpen(page.name)"
                      class="gov-subsubnav__empty"
                    >
                      Em breve...
                    </div>
                  </li>
                </ul>
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
import { useRoute, useRouter } from 'vue-router';

const API_BASE = import.meta.env.VITE_API_URL || '';
const router = useRouter();
const route = useRoute();

const user = ref(null);
const generationMenuOpen = ref(true);
const groupOpenState = ref({
  DispensaArt75I: true,
  DispensaArt75II: false,
  InexigibilidadeArt74I: false,
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
    children: [],
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
];

const generationRouteNames = new Set(
  generationPages.flatMap((page) => [page.name, ...(page.children || []).map((child) => child.name)]),
);

const isGenerationSectionActive = computed(() => {
  return route.name === 'DocumentGenerator' || generationRouteNames.has(route.name);
});

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

onMounted(() => {
  fetchMe();
  if (isGenerationSectionActive.value) {
    generationMenuOpen.value = true;
    const activeGroup = generationPages.find((page) =>
      page.children?.some((child) => child.name === route.name),
    );
    if (activeGroup) {
      groupOpenState.value[activeGroup.name] = true;
    }
  }
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

.gov-nav__link--expandable {
  justify-content: space-between;
}

.gov-nav__link-main {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.gov-subnav,
.gov-subsubnav {
  list-style: none;
  margin: 4px 0 8px;
  padding: 0;
}

.gov-subnav {
  padding-left: 12px;
}

.gov-subsubnav {
  padding-left: 14px;
}

.gov-subnav__item,
.gov-subsubnav__item {
  margin: 2px 0;
}

.gov-subnav__link,
.gov-subsubnav__link {
  display: block;
  border-radius: var(--radius-md);
  padding: 5px 8px;
  color: var(--color-text);
  font-size: 12px;
  text-decoration: none;
}

.gov-subnav__link:hover,
.gov-subsubnav__link:hover {
  background: #dde4ef;
  text-decoration: none;
}

.gov-subnav__link--active,
.gov-subsubnav__link--active {
  border: 1px solid var(--color-primary);
  background-color: #d5edf7;
}

.gov-subnav__link--expandable {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border: 1px solid transparent;
  background: transparent;
  font-family: inherit;
  cursor: pointer;
}

.gov-subnav__link-main {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.gov-subsubnav__link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.gov-subsubnav__empty {
  margin: 4px 0 8px 14px;
  color: var(--color-text-soft);
  font-size: 12px;
}
</style>
