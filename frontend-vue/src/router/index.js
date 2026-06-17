import { createRouter, createWebHistory } from 'vue-router';
/** Import estático: evita chunk lazy `DispensaArt75IIRapidaReactPreview-*.js` (falha com index.html ou CDN em cache após deploy). */
import DispensaArt75IIRapidaReactPreview from '../views/DispensaArt75IIRapidaReactPreview.vue';
import { useSessionUser } from '../composables/useSessionUser.js';

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
    path: '/geracao/dispensa',
    name: 'DispensaGeracaoHub',
    component: () => import('../views/GeracaoSecaoPlaceholder.vue'),
    meta: { title: 'Dispensa', geracaoHubSection: 'dispensa' },
  },
  {
    path: '/geracao/inexigibilidade',
    name: 'InexigibilidadeGeracaoHub',
    component: () => import('../views/GeracaoSecaoPlaceholder.vue'),
    meta: { title: 'Inexigibilidade', geracaoHubSection: 'inexigibilidade' },
  },
  {
    path: '/geracao/dispensa-art-75-i',
    redirect: '/geracao/dispensa',
  },
  {
    path: '/geracao/dispensa-art-75-i/obras-servicos-engenharia',
    name: 'DispensaArt75IObrasEngenharia',
    component: () => import('../views/DispensaArt75IINormalReactPreview.vue'),
    meta: { title: 'Dispensa - Art. 75, I - Obras e Serviços de Engenharia' },
  },
  {
    path: '/geracao/dispensa-art-75-i/manutencao-veiculos',
    name: 'DispensaArt75IManutencaoVeiculos',
    component: () => import('../views/DispensaArt75IINormalReactPreview.vue'),
    meta: { title: 'Dispensa - Art. 75, I - Manutenção de Veículos' },
  },
  {
    path: '/geracao/dispensa-art-75-ii',
    redirect: '/geracao/dispensa',
  },
  {
    path: '/geracao/dispensa-art-75-ii/compras',
    name: 'DispensaArt75IICompras',
    component: () => import('../views/DispensaArt75IINormalReactPreview.vue'),
    meta: { title: 'Dispensa - Art. 75, II - Compras' },
  },
  {
    path: '/geracao/dispensa-art-75-ii/servicos',
    name: 'DispensaArt75IIServicos',
    component: () => import('../views/DispensaArt75IINormalReactPreview.vue'),
    meta: { title: 'Dispensa - Art. 75, II - Serviços' },
  },
  {
    path: '/geracao/dispensa-art-75-ii/compras-servicos-inclusos',
    name: 'DispensaArt75IIComprasServicosInclusos',
    component: () => import('../views/DispensaArt75IINormalReactPreview.vue'),
    meta: { title: 'Dispensa - Art. 75, II - Compras com Serviços Inclusos' },
  },
  {
    path: '/geracao/dispensa-rapida',
    redirect: '/geracao/dispensa',
  },
  {
    path: '/geracao/dispensa-rapida/art-75-i/obras-servicos-engenharia',
    name: 'DispensaRapidaArt75IObrasEngenharia',
    component: DispensaArt75IIRapidaReactPreview,
    meta: {
      title: 'Dispensa - Art. 75, I - Obras e Serviços de Engenharia',
      dispensaRapidaUi: true,
    },
  },
  {
    path: '/geracao/dispensa-rapida/art-75-i/manutencao-veiculos',
    name: 'DispensaRapidaArt75IManutencaoVeiculos',
    component: DispensaArt75IIRapidaReactPreview,
    meta: {
      title: 'Dispensa - Art. 75, I - Manutenção de Veículos',
      dispensaRapidaUi: true,
    },
  },
  {
    path: '/geracao/dispensa-rapida/art-75-ii/compras',
    name: 'DispensaRapidaArt75IICompras',
    component: DispensaArt75IIRapidaReactPreview,
    meta: { title: 'Dispensa - Art. 75, II - Compras', dispensaRapidaUi: true },
  },
  {
    path: '/geracao/dispensa-rapida/art-75-ii/servicos',
    name: 'DispensaRapidaArt75IIServicos',
    component: DispensaArt75IIRapidaReactPreview,
    meta: { title: 'Dispensa - Art. 75, II - Serviços', dispensaRapidaUi: true },
  },
  {
    path: '/geracao/dispensa-rapida/art-75-ii/compras-servicos-inclusos',
    name: 'DispensaRapidaArt75IIComprasServicosInclusos',
    component: DispensaArt75IIRapidaReactPreview,
    meta: {
      title: 'Dispensa - Art. 75, II - Compras com Serviços Inclusos',
      dispensaRapidaUi: true,
    },
  },
  {
    path: '/geracao/inexigibilidade-art-74-i',
    redirect: '/geracao/inexigibilidade',
  },
  {
    path: '/geracao/inexigibilidade-art-74-i/show-artistico',
    redirect: '/geracao/inexigibilidade-art-74-i/manutencao-veiculos',
  },
  {
    path: '/geracao/inexigibilidade-art-74-i/manutencao-veiculos',
    name: 'InexigibilidadeArt74IManutencaoVeiculosPreview',
    component: () => import('../views/InexigibilidadeManutencaoVeiculosPreview.vue'),
    meta: {
      title: 'Inexigibilidade - Art. 74, I - Manutenção de Veículos',
    },
  },
  {
    path: '/geracao/inexigibilidade-art-74-i/fornecedor-exclusivo',
    name: 'InexigibilidadeArt74IFornecedorExclusivoPreview',
    component: () => import('../views/InexigibilidadeManutencaoVeiculosPreview.vue'),
    meta: {
      title: 'Inexigibilidade - Art. 74, I - Fornecedor Exclusivo',
    },
  },
  {
    path: '/geracao/inexigibilidade-art-74-i/manutencao-veiculos-preview',
    redirect: '/geracao/inexigibilidade-art-74-i/manutencao-veiculos',
  },
  {
    path: '/geracao/inexigibilidade-art-74-i/fornecedor-exclusivo-preview',
    redirect: '/geracao/inexigibilidade-art-74-i/fornecedor-exclusivo',
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
  const { fetchMe } = useSessionUser();
  const me = await fetchMe();
  if (to.meta?.public) {
    if (me && to.name === 'Login') {
      return to.query?.redirect ? { path: to.query.redirect } : { path: '/' };
    }
    return;
  }
  if (!me) {
    return { path: '/login', query: { redirect: to.fullPath } };
  }
  /* Módulos sem permissão: a navegação prossegue; o App.vue mostra «Módulo Não Liberado». */
});

router.afterEach((to) => {
  document.title = to.meta?.title ? `${to.meta.title} – DocMasterIA` : 'DocMasterIA';
});

export default router;
