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
    path: '/',
    name: 'DocumentGenerator',
    component: () => import('../views/DocumentGenerator.vue'),
    meta: { title: 'Gerador de Documentos' },
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
