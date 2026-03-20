import { createRouter, createWebHistory } from 'vue-router';

const API_BASE = import.meta.env.VITE_API_URL || '';

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { title: 'Entrar', public: true },
  },
  {
    path: '/preview/slots-card',
    name: 'SlotsCardPreview',
    component: () => import('../views/SlotsCardPreview.vue'),
    meta: { title: 'Preview Card TR/DFD', public: true },
  },
  {
    path: '/',
    name: 'DocumentGenerator',
    component: () => import('../views/DocumentGenerator.vue'),
    meta: { title: 'Gerador de Documentos' },
  },
  {
    path: '/geracao/dispensa-art-75-i',
    name: 'DispensaArt75I',
    component: () => import('../views/DocumentGenerator.vue'),
    meta: { title: 'Dispensa - Art. 75, I' },
  },
  {
    path: '/geracao/dispensa-art-75-i/obras-servicos-engenharia',
    name: 'DispensaArt75IObrasEngenharia',
    component: () => import('../views/DocumentGenerator.vue'),
    meta: { title: 'Dispensa - Art. 75, I - Obras e Serviços de Engenharia' },
  },
  {
    path: '/geracao/dispensa-art-75-i/manutencao-veiculos',
    name: 'DispensaArt75IManutencaoVeiculos',
    component: () => import('../views/DocumentGenerator.vue'),
    meta: { title: 'Dispensa - Art. 75, I - Manutenção de Veículos' },
  },
  {
    path: '/geracao/dispensa-art-75-ii',
    name: 'DispensaArt75II',
    component: () => import('../views/DocumentGenerator.vue'),
    meta: { title: 'Dispensa - Art. 75, II' },
  },
  {
    path: '/geracao/dispensa-art-75-ii/compras',
    name: 'DispensaArt75IICompras',
    component: () => import('../views/DocumentGenerator.vue'),
    meta: { title: 'Dispensa - Art. 75, II - Compras' },
  },
  {
    path: '/geracao/dispensa-art-75-ii/servicos',
    name: 'DispensaArt75IIServicos',
    component: () => import('../views/DocumentGenerator.vue'),
    meta: { title: 'Dispensa - Art. 75, II - Serviços' },
  },
  {
    path: '/geracao/dispensa-art-75-ii/compras-servicos-inclusos',
    name: 'DispensaArt75IIComprasServicosInclusos',
    component: () => import('../views/DocumentGenerator.vue'),
    meta: { title: 'Dispensa - Art. 75, II - Compras com Serviços Inclusos' },
  },
  {
    path: '/geracao/inexigibilidade-art-74-i',
    name: 'InexigibilidadeArt74I',
    component: () => import('../views/DocumentGenerator.vue'),
    meta: { title: 'Inexigibilidade - Art. 74, I' },
  },
  {
    path: '/geracao/inexigibilidade-art-74-i/show-artistico',
    name: 'InexigibilidadeArt74IShowArtistico',
    component: () => import('../views/DocumentGenerator.vue'),
    meta: { title: 'Inexigibilidade - Art. 74, I - Show Artístico' },
  },
  {
    path: '/geracao/etp-livre',
    name: 'EtpLivre',
    component: () => import('../views/DocumentGenerator.vue'),
    meta: { title: 'ETP Livre' },
  },
  {
    path: '/gerador-documentos',
    redirect: '/',
  },
  {
    path: '/biblioteca',
    name: 'TemplateList',
    component: () => import('../views/TemplateList.vue'),
    meta: { title: 'Biblioteca de Documentos' },
  },
  {
    path: '/analisador',
    name: 'DocumentAnalyzer',
    component: () => import('../views/DocumentAnalyzer.vue'),
    meta: { title: 'Analisador de Documentos' },
  },
  {
    path: '/area-do-usuario',
    name: 'AreaDoUsuario',
    component: () => import('../views/AreaDoUsuario.vue'),
    meta: { title: 'Área do Usuário' },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

/** Verifica autenticação: rotas sem meta.public exigem login. */
router.beforeEach(async (to) => {
  if (to.meta?.public) {
    const isLoggedIn = await checkAuth();
    if (isLoggedIn && to.name === 'Login') {
      return to.query?.redirect ? { path: to.query.redirect } : { path: '/' };
    }
    return;
  }
  const isLoggedIn = await checkAuth();
  if (!isLoggedIn) {
    return { path: '/login', query: { redirect: to.fullPath } };
  }
});

function checkAuth() {
  return fetch(`${API_BASE}/api/me/`, { method: 'GET', credentials: 'include' })
    .then((res) => res.status === 200)
    .catch(() => false);
}

router.afterEach((to) => {
  document.title = to.meta?.title ? `${to.meta.title} – DocMasterIA` : 'DocMasterIA';
});

export default router;
