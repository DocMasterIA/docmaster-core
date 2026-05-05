<template>
  <section class="gov-page">
    <header class="gov-page__header">
      <div class="cot-header-row">
        <div>
          <h1 class="gov-page__title">Relatório de pesquisa de preços</h1>
          <p class="gov-page__subtitle">
            Itens agrupados por produto com várias fontes/cotações (como em relatorio-pesquisa-precos). Sem «Diagnóstico da Pesquisa».
          </p>
        </div>
        <RouterLink
          v-if="cotacaoIdQuery"
          :to="`/pesquisador-pncp/cotacoes/${cotacaoIdQuery}`"
          class="cot-back-btn"
        >
          <i class="fa-solid fa-arrow-left" aria-hidden="true"></i>
          Voltar à cotação
        </RouterLink>
        <RouterLink v-else to="/pesquisador-pncp" class="cot-back-btn">
          <i class="fa-solid fa-arrow-left" aria-hidden="true"></i>
          Pesquisador PNCP
        </RouterLink>
      </div>
      <p v-if="loadError" class="cot-meta cot-meta--error">{{ loadError }}</p>
      <p v-else-if="isLoading" class="cot-meta">Carregando dados da cotação…</p>
    </header>

    <div class="gov-page__content gov-page__content--relatorio-rpp">
      <div class="rpp-body">
        <div class="rpp-page">
          <div class="rpp-watermark">{{ marcaAgua }}</div>

          <header id="rpp-head-main" class="rpp-head-main">
            <div class="rpp-head-main__col rpp-head-main__col--logo">
              <img class="rpp-head-main__logo" :src="logoBrancaUrl" width="120" height="44" alt="DocMaster" />
            </div>
            <div class="rpp-head-main__col rpp-head-main__col--main">
              <p class="rpp-kicker">Relatório institucional</p>
              <h1 class="rpp-title">{{ tituloRelatorio }}</h1>
              <p class="rpp-subtitle">
                {{
                  cotacaoIdQuery
                    ? 'Pré-visualização — o QR do PDF abre esta cotação no app quando estiver logado.'
                    : 'Exemplo com itens e 3+ fontes por produto. Use ?cotacaoId= para dados reais.'
                }}
              </p>
            </div>
            <div class="rpp-head-main__col rpp-head-main__col--qr">
              <div class="rpp-head-main__qr-placeholder">QR no PDF (topo)</div>
            </div>
          </header>

          <div class="rpp-meta-grid">
            <div class="rpp-card rpp-card--accent">
              <span class="rpp-card__label">Cotação (título interno)</span>
              <span class="rpp-card__value">{{ tituloCotacao }}</span>
            </div>
            <div class="rpp-card">
              <span class="rpp-card__label">Data da pesquisa</span>
              <span class="rpp-card__value">{{ dataPesquisa }}</span>
            </div>
            <div class="rpp-card">
              <span class="rpp-card__label">Emitido em</span>
              <span class="rpp-card__value">{{ emitidoEm }}</span>
            </div>
            <div class="rpp-card">
              <span class="rpp-card__label">Responsável</span>
              <span class="rpp-card__value">
                {{ criadoPor
                }}<span v-if="criadoPorEmail" class="rpp-card__value--muted"> — {{ criadoPorEmail }}</span>
              </span>
            </div>
            <div class="rpp-card">
              <span class="rpp-card__label">Termo PNCP</span>
              <span class="rpp-card__value">{{ termoPncp }}</span>
            </div>
            <div class="rpp-card">
              <span class="rpp-card__label">Itens (grupos)</span>
              <span class="rpp-card__value">{{ grupos.length }}</span>
            </div>
            <div class="rpp-card">
              <span class="rpp-card__label">Cotações registradas</span>
              <span class="rpp-card__value">{{ totalLinhasCotacao }}</span>
            </div>
          </div>

          <section class="rpp-block">
            <h2 class="rpp-section-title">Resultado consolidado</h2>
            <p class="rpp-section-lead">
              Resumo dos itens com média das cotações e situação da pesquisa (mínimo de 3 fontes por item para «Válido»).
            </p>
            <div class="rpp-table-wrap">
              <table class="rpp-table rpp-table--consolidado">
                <thead>
                  <tr>
                    <th>Item</th>
                    <th>Descrição</th>
                    <th>Quantidade</th>
                    <th>Cotações</th>
                    <th>Média</th>
                    <th>Situação</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="g in grupos" :key="'c-' + g.ordem">
                    <td>{{ g.ordem }}</td>
                    <td>{{ g.nome }}</td>
                    <td>{{ g.quantidade_fmt }} {{ g.unidade }}</td>
                    <td>{{ g.n_cotacoes }}</td>
                    <td>{{ g.media_fmt }}</td>
                    <td>{{ g.situacao }}</td>
                  </tr>
                  <tr v-if="!grupos.length">
                    <td colspan="6" class="rpp-cnpj-empty">Nenhum item agrupado nesta cotação.</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section class="rpp-block">
            <h2 class="rpp-section-title">Detalhamento dos itens</h2>
            <p class="rpp-section-lead">
              Ficha técnica do item e fontes utilizadas na composição do preço.
            </p>
            <template v-for="g in grupos" :key="'d-' + g.ordem">
              <div class="rpp-detalhe-item">
                <div class="rpp-detalhe-item__head">
                  <span class="rpp-detalhe-item__kicker">Item {{ g.ordem }}</span>
                  <div class="rpp-detalhe-item__nome">{{ g.nome }}</div>
                </div>
                <div class="rpp-detalhe-item__meta">
                  <div class="rpp-mini-card">
                    <span class="rpp-mini-card__label">Identificação (ID do item)</span>
                    <span class="rpp-mini-card__value">ID {{ g.ordem }}</span>
                  </div>
                  <div class="rpp-mini-card">
                    <span class="rpp-mini-card__label">Quantidade</span>
                    <span class="rpp-mini-card__value">{{ g.quantidade_fmt }}</span>
                  </div>
                  <div class="rpp-mini-card">
                    <span class="rpp-mini-card__label">Unidade</span>
                    <span class="rpp-mini-card__value">{{ g.unidade }}</span>
                  </div>
                </div>
                <div class="rpp-fontes-cards">
                  <div v-for="(f, fi) in g.fontes" :key="fi" class="rpp-fonte-card">
                    <div class="rpp-fonte-card__index">{{ fi + 1 }}</div>
                    <div class="rpp-fonte-card__content">
                      <div class="rpp-fonte-row rpp-fonte-row--3">
                        <div class="rpp-mini-compact rpp-mini-compact--featured">
                          <span class="rpp-mini-compact__label">Fornecedor</span>
                          <span class="rpp-mini-compact__value rpp-mini-compact__value--strong">{{ f.fornecedor }}</span>
                        </div>
                        <div class="rpp-mini-compact">
                          <span class="rpp-mini-compact__label">CNPJ</span>
                          <span class="rpp-mini-compact__value">{{ f.cnpj }}</span>
                        </div>
                        <div class="rpp-mini-compact rpp-mini-compact--featured">
                          <span class="rpp-mini-compact__label">Valor</span>
                          <span class="rpp-mini-compact__value rpp-mini-compact__value--strong">{{ f.valor }}</span>
                        </div>
                      </div>

                      <div class="rpp-fonte-row rpp-fonte-row--3">
                        <div class="rpp-mini-compact">
                          <span class="rpp-mini-compact__label">Órgão</span>
                          <span class="rpp-mini-compact__value">{{ f.orgao }}</span>
                        </div>
                        <div class="rpp-mini-compact">
                          <span class="rpp-mini-compact__label">Modalidade</span>
                          <span class="rpp-mini-compact__value">{{ f.tipo }}</span>
                        </div>
                        <div class="rpp-mini-compact">
                          <span class="rpp-mini-compact__label">Data</span>
                          <span class="rpp-mini-compact__value">{{ f.data }}</span>
                        </div>
                      </div>

                      <div class="rpp-fonte-row rpp-fonte-row--5">
                        <div class="rpp-mini-compact rpp-mini-compact--wide">
                          <span class="rpp-mini-compact__label">ID / Processo</span>
                          <span class="rpp-mini-compact__value">{{ fi + 1 }} / {{ f.processo || 'N/D' }}</span>
                        </div>
                        <div class="rpp-mini-compact">
                          <span class="rpp-mini-compact__label">Qtd.</span>
                          <span class="rpp-mini-compact__value">{{ g.quantidade_fmt }}</span>
                        </div>
                        <div class="rpp-mini-compact">
                          <span class="rpp-mini-compact__label">Unid.</span>
                          <span class="rpp-mini-compact__value">{{ g.unidade }}</span>
                        </div>
                        <div class="rpp-mini-compact">
                          <span class="rpp-mini-compact__label">Fonte</span>
                          <span class="rpp-mini-compact__value">{{ f.tipo }}</span>
                        </div>
                        <div class="rpp-mini-compact">
                          <span class="rpp-mini-compact__label">UF</span>
                          <span class="rpp-mini-compact__value">{{ ufFromMunicipio(g, f) }}</span>
                        </div>
                      </div>

                      <div class="rpp-fonte-row rpp-fonte-row--2">
                        <div class="rpp-mini-compact rpp-mini-compact--wide">
                          <span class="rpp-mini-compact__label">Descrição do item</span>
                          <span class="rpp-mini-compact__value">{{ g.nome }}</span>
                        </div>
                        <div class="rpp-mini-compact rpp-mini-compact--wide">
                          <span class="rpp-mini-compact__label">Ajuste</span>
                          <span class="rpp-mini-compact__value">{{ f.ajuste }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </section>

          <section class="rpp-block">
            <h2 class="rpp-section-title">CNPJ identificados nas fontes (quando disponíveis)</h2>
            <ul v-if="cnpjs.length" class="rpp-cnpj-list">
              <li v-for="(c, i) in cnpjs" :key="i">{{ c }}</li>
            </ul>
            <p v-else class="rpp-cnpj-empty">
              Nenhum CNPJ estruturado foi localizado nos metadados salvos dos itens.
            </p>
          </section>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { getResearchSession } from '../services/pncpResearch';
import logoBrancaUrl from '../assets/logo_branca.png';
import '../assets/relatorio-pesquisa-precos.css';

const MIN_FONTES = 3;

const route = useRoute();

const marcaAgua = 'DocMaster — Pesquisador PNCP';

const isLoading = ref(false);
const loadError = ref('');

const tituloRelatorio = ref('Relatório de pesquisa de preços');
const tituloCotacao = ref('—');
const dataPesquisa = ref('—');
const criadoPor = ref('—');
const criadoPorEmail = ref('');
const termoPncp = ref('—');
const grupos = ref([]);
const totalLinhasCotacao = ref(0);
const cnpjs = ref([]);

const cotacaoIdQuery = computed(() => {
  const raw = route.query.cotacaoId;
  if (raw == null || raw === '') return '';
  return String(raw);
});

const emitidoEm = computed(() => formatDataHora(new Date()));

/** Demo alinhada a `DocMasterRelatorioPesquisaPrecos.jsx` (3 fontes por item). */
const DEMO_GRUPOS = [
  {
    ordem: 1,
    nome: 'FORFIG',
    quantidade_fmt: '1,00',
    unidade: 'CX',
    n_cotacoes: 3,
    media_fmt: 'R$ 199,53',
    situacao: 'Válido',
    fontes: [
      {
        tipo: 'Cotação Direta',
        fornecedor: 'ITAFARMA Drogaria e Perfumaria Ltda',
        cnpj: '01.012.426/0001-28',
        data: '31/03/2026',
        valor: 'R$ 198,00',
        orgao: 'Fornecedor Privado',
        municipio_uf: 'Itajá/GO',
        processo: '-',
        ajuste: 'Sem frete',
      },
      {
        tipo: 'PNCP',
        fornecedor: 'Play Pharma Comércio de Produtos Hospitalares Ltda',
        cnpj: '32.321.488/0001-45',
        data: '02/04/2025',
        valor: 'R$ 200,75',
        orgao: 'Prefeitura Municipal',
        municipio_uf: 'Goiânia/GO',
        processo: 'PNCP-2025',
        ajuste: 'Sem frete',
      },
      {
        tipo: 'BBMNET',
        fornecedor: 'Carla Janaina Rodrigues Silva',
        cnpj: '25.257.455/0002-07',
        data: '07/04/2025',
        valor: 'R$ 199,85',
        orgao: 'Órgão Licitante',
        municipio_uf: 'Rio Verde/GO',
        processo: 'PE-102/2025',
        ajuste: 'Sem frete',
      },
    ],
  },
];

function formatarMoedaBr(v) {
  if (v == null || v === '') return '—';
  const n = Number(v);
  if (Number.isNaN(n)) return '—';
  const s = n.toFixed(2);
  const [inteiro, frac] = s.split('.');
  return `${inteiro},${frac}`;
}

function formatDataHora(d) {
  if (!(d instanceof Date) || Number.isNaN(d.getTime())) return '—';
  const pad = (n) => String(n).padStart(2, '0');
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} às ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function formatDataHoraIso(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return formatDataHora(d);
}

function chaveGrupo(it) {
  const ni = String(it.numero_item || '').trim();
  if (ni) return `n:${ni}`;
  const desc = String(it.descricao_item || '').trim();
  const und = String(it.unidade_medida || '').trim();
  const q = it.quantidade;
  let qk = '';
  if (q != null && q !== '') {
    const f = Number(q);
    qk = Number.isNaN(f) ? String(q) : String(f);
  }
  return `d:${desc}|${und}|${qk}`;
}

function valorNum(it) {
  if (it.valor_total != null) {
    const f = Number(it.valor_total);
    if (!Number.isNaN(f)) return f;
  }
  if (it.valor_unitario != null) {
    const f = Number(it.valor_unitario);
    if (!Number.isNaN(f)) return f;
  }
  return null;
}

function fmtQtd(q) {
  if (q == null || q === '') return '—';
  const f = Number(q);
  if (Number.isNaN(f)) return String(q).slice(0, 32);
  if (Math.abs(f - Math.round(f)) < 1e-9) return String(Math.round(f));
  return f.toFixed(2).replace('.', ',');
}

function itemToFonte(it) {
  const src = it.source && typeof it.source === 'object' ? it.source : {};
  let tipo = src.tipo_fonte || src.fonte || src.origem || '';
  if (!tipo) tipo = String(it.numero_pncp || '').trim() ? 'PNCP' : 'Registro importado';
  const fornecedor = src.fornecedor || src.nomeRazaoSocialFornecedor || it.orgao || '—';
  const cnpj = src.cnpj || src.cnpj_fornecedor || '—';
  let data = '—';
  if (it.created_at) {
    const d = new Date(it.created_at);
    if (!Number.isNaN(d.getTime())) {
      data = d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
    }
  }
  const vn = valorNum(it);
  const valor = vn != null ? `R$ ${formatarMoedaBr(vn)}` : '—';
  const mun = String(it.municipio || '').trim();
  const uf = String(it.uf || '').trim();
  let municipioUf = '—';
  if (mun && uf) municipioUf = `${mun}/${uf}`;
  else if (mun) municipioUf = mun;
  else if (uf) municipioUf = uf;
  const processo = src.processo || it.numero_pncp || '—';
  const ajuste = src.ajuste || src.observacao_frete || 'Sem frete';
  return {
    tipo,
    fornecedor,
    cnpj,
    data,
    valor,
    orgao: it.orgao || '—',
    municipio_uf: municipioUf,
    processo,
    ajuste,
  };
}

function montarGruposFromItens(itens) {
  const map = new Map();
  const order = [];
  for (const it of itens) {
    const k = chaveGrupo(it);
    if (!map.has(k)) {
      map.set(k, []);
      order.push(k);
    }
    map.get(k).push(it);
  }
  return order.map((k, i) => {
    const members = [...map.get(k)].sort((a, b) => (a.id || 0) - (b.id || 0));
    const first = members[0];
    const nome = String(first.descricao_item || '—').slice(0, 500);
    const vals = members.map(valorNum).filter((v) => v != null);
    const mediaFmt =
      vals.length > 0 ? `R$ ${formatarMoedaBr(vals.reduce((a, b) => a + b, 0) / vals.length)}` : '—';
    const n = members.length;
    const situacao =
      n >= MIN_FONTES ? 'Válido' : `Insuficiente (${n} de ${MIN_FONTES} fontes)`;
    return {
      ordem: i + 1,
      nome,
      quantidade_fmt: fmtQtd(first.quantidade),
      unidade: first.unidade_medida || '—',
      n_cotacoes: n,
      media_fmt: mediaFmt,
      situacao,
      fontes: members.map(itemToFonte),
    };
  });
}

function ufFromMunicipio(g, f) {
  const raw = String(f?.municipio_uf || '').trim();
  if (!raw) return '—';
  const parts = raw.split('/');
  if (parts.length >= 2) return String(parts[parts.length - 1] || '').trim() || '—';
  return String(g?.unidade || '').trim() || '—';
}

function aplicarDemo() {
  tituloCotacao.value = 'Cotação de exemplo';
  dataPesquisa.value = '—';
  criadoPor.value = '—';
  criadoPorEmail.value = '';
  termoPncp.value = '—';
  grupos.value = DEMO_GRUPOS;
  totalLinhasCotacao.value = DEMO_GRUPOS.reduce((s, g) => s + g.n_cotacoes, 0);
  cnpjs.value = [];
}

async function carregar() {
  const tituloQ = route.query.titulo;
  if (tituloQ != null && String(tituloQ).trim()) {
    tituloRelatorio.value = String(tituloQ).trim().slice(0, 500);
  }

  const idStr = cotacaoIdQuery.value;
  if (!idStr) {
    loadError.value = '';
    aplicarDemo();
    return;
  }

  const sessionId = Number(idStr);
  if (Number.isNaN(sessionId)) {
    loadError.value = 'Parâmetro cotacaoId inválido.';
    aplicarDemo();
    return;
  }

  isLoading.value = true;
  loadError.value = '';
  try {
    const data = await getResearchSession(sessionId);
    if (!data?.ok || !data.sessao) {
      loadError.value = data?.error || 'Sessão não encontrada.';
      aplicarDemo();
      return;
    }
    const s = data.sessao;
    tituloCotacao.value = s.titulo || '—';
    dataPesquisa.value = formatDataHoraIso(s.created_at);
    criadoPor.value = s.criado_por || '—';
    criadoPorEmail.value = (s.criado_por_email || '').trim();
    termoPncp.value = s.termo_busca || '—';

    const itens = Array.isArray(data.itens) ? [...data.itens].sort((a, b) => (a.id ?? 0) - (b.id ?? 0)) : [];

    if (Array.isArray(data.grupos_relatorio) && data.grupos_relatorio.length > 0) {
      grupos.value = data.grupos_relatorio;
      totalLinhasCotacao.value =
        typeof data.total_linhas_cotacao === 'number'
          ? data.total_linhas_cotacao
          : itens.length;
    } else if (itens.length) {
      grupos.value = montarGruposFromItens(itens);
      totalLinhasCotacao.value = itens.length;
    } else {
      grupos.value = [];
      totalLinhasCotacao.value = 0;
    }

    cnpjs.value = Array.isArray(data.cnpjs_fontes) ? data.cnpjs_fontes : [];
  } catch (err) {
    loadError.value = err?.message || 'Falha ao carregar a cotação.';
    aplicarDemo();
  } finally {
    isLoading.value = false;
  }
}

onMounted(() => {
  carregar();
});

watch(
  () => [route.query.cotacaoId, route.query.titulo],
  () => {
    carregar();
  },
);
</script>

<style scoped>
.gov-page__content--relatorio-rpp {
  padding: 0 16px 24px;
}
.cot-header-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}
.cot-back-btn {
  border: 1px solid #cfd8e3;
  border-radius: 10px;
  background: #fff;
  color: #1f2937;
  padding: 7px 12px;
  font-size: 12px;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 7px;
}
.cot-meta {
  margin: 8px 0 0;
  font-size: 12px;
  color: #64748b;
}
.cot-meta--error {
  color: #b91c1c;
}
</style>
