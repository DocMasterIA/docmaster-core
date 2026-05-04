import { createRouter, createWebHistory } from 'vue-router';

const API_BASE = import.meta.env.VITE_API_URL || 'https://api.docmasteria.com.br';

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
    redirect: '/geracao/etp-livre',
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
    path: '/pesquisador-pncp',
    name: 'PncpResearcher',
    component: () => import('../views/PncpResearcher.vue'),
    meta: { title: 'Pesquisador de Dados PNCP' },
  },
  {
    path: '/pesquisador-pncp/cotacoes/:cotacaoId',
    name: 'CotacaoDetalhe',
    component: () => import('../views/CotacaoDetalhe.vue'),
    meta: { title: 'Detalhes da Cotação' },
  },
  {
    path: '/pesquisador-pncp/cotacoes/:cotacaoId/itens/:itemId',
    name: 'CotacaoItemDetalhe',
    component: () => import('../views/CotacaoItemDetalhe.vue'),
    meta: { title: 'Item da Cotação' },
  },
  {
    path: '/pesquisador-pncp/cotacoes/:cotacaoId/itens/:itemId/cotacao-direta',
    name: 'CotacaoDiretaRegistro',
    component: () => import('../views/CotacaoDiretaRegistro.vue'),
    meta: { title: 'Registro de Cotação Direta' },
  },
  {
    path: '/pesquisador-pncp/cotacoes/:cotacaoId/busca-inteligente',
    name: 'BuscaInteligenteCotacoes',
    component: () => import('../views/BuscaInteligenteCotacoes.vue'),
    meta: { title: 'Busca Inteligente de Cotações' },
  },
  {
    path: '/pesquisador-pncp/cotacoes/:cotacaoId/busca-manual',
    name: 'BuscaManualCotacoes',
    component: () => import('../views/BuscaManualCotacoes.vue'),
    meta: { title: 'Busca Manual de Cotações' },
  },
  {
    path: '/pesquisador-pncp/relatorio-pesquisa-precos',
    name: 'RelatorioPesquisaPrecos',
    component: () => import('../views/RelatorioPesquisaPrecos.vue'),
    meta: { title: 'Relatório de pesquisa de preços' },
  },
  {
    path: '/cotacoes/:cotacaoId',
    redirect: (to) => `/pesquisador-pncp/cotacoes/${to.params.cotacaoId}`,
  },
  {
    path: '/cotacoes/:cotacaoId/busca-inteligente',
    redirect: (to) => `/pesquisador-pncp/cotacoes/${to.params.cotacaoId}/busca-inteligente`,
  },
  {
    path: '/cotacoes/:cotacaoId/busca-manual',
    redirect: (to) => `/pesquisador-pncp/cotacoes/${to.params.cotacaoId}/busca-manual`,
  },
  {
    path: '/cotacao',
    redirect: '/pesquisador-pncp/cotacoes/CT-2026-00421',
  },
  {
    path: '/busca-item',
    redirect: '/pesquisador-pncp/cotacoes/CT-2026-00421/busca-inteligente',
  },
  {
    path: '/busca-manual',
    redirect: '/pesquisador-pncp/cotacoes/CT-2026-00421/busca-manual',
  },
  {
    path: '/area-do-usuario',
    name: 'AreaDoUsuario',
    component: () => import('../views/AreaDoUsuario.vue'),
    meta: { title: 'Área do Usuário' },
  },
  /* Módulos sem implementação ainda: rota ativa + página reservada */
  {
    path: '/dispensa-eletronica',
    name: 'ModuleDispensaEletronica',
    component: () => import('../views/ModulePlaceholder.vue'),
    meta: { title: 'Dispensa Eletrônica', subtitle: 'Fluxo em desenvolvimento.' },
  },
  {
    path: '/pregao',
    name: 'ModulePregao',
    component: () => import('../views/ModulePlaceholder.vue'),
    meta: { title: 'Pregão', subtitle: 'Fluxo em desenvolvimento.' },
  },
  {
    path: '/pregao-eletronico',
    name: 'ModulePregaoEletronico',
    component: () => import('../views/ModulePlaceholder.vue'),
    meta: { title: 'Pregão Eletrônico', subtitle: 'Fluxo em desenvolvimento.' },
  },
  {
    path: '/contratos',
    name: 'ModuleContratos',
    component: () => import('../views/ModulePlaceholder.vue'),
    meta: { title: 'Contratos', subtitle: 'Fluxo em desenvolvimento.' },
  },
  {
    path: '/controle-interno',
    name: 'ModuleControleInterno',
    component: () => import('../views/ModulePlaceholder.vue'),
    meta: { title: 'Controle Interno', subtitle: 'Fluxo em desenvolvimento.' },
  },
  {
    path: '/impugnacao',
    name: 'ModuleImpugnacao',
    component: () => import('../views/ModulePlaceholder.vue'),
    meta: { title: 'Impugnação', subtitle: 'Fluxo em desenvolvimento.' },
  },
  {
    path: '/recurso-processo-licitatorio',
    name: 'ModuleRecursoLicitatorio',
    component: () => import('../views/ModulePlaceholder.vue'),
    meta: { title: 'Recurso — Processo Licitatório', subtitle: 'Fluxo em desenvolvimento.' },
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
    .then(async (res) => {
      if (res.status !== 200) return false;
      const ctype = (res.headers.get('content-type') || '').toLowerCase();
      if (!ctype.includes('application/json')) return false;
      try {
        const data = await res.json();
        return !!data && typeof data === 'object';
      } catch (_) {
        return false;
      }
    })
    .catch(() => false);
}

router.afterEach((to) => {
  document.title = to.meta?.title ? `${to.meta.title} – DocMasterIA` : 'DocMasterIA';
});

export default router;
