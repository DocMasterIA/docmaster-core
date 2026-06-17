<template>
  <div class="rpv-shell">
    <RouterLink
      v-if="cotacaoIdQuery"
      :to="`/pesquisador-pncp/cotacoes/${cotacaoIdQuery}`"
      class="rpv-shell__back"
    >
      Voltar à cotação
    </RouterLink>
    <RouterLink v-else to="/pesquisador-pncp" class="rpv-shell__back">Pesquisador PNCP</RouterLink>

    <p v-if="loadError" class="rpv-shell__status rpv-shell__status--error">{{ loadError }}</p>
    <p v-else-if="isLoading" class="rpv-shell__status">Carregando dados da cotação…</p>

    <div class="rpv-inner">
      <header class="rpv-header-card">
        <div class="rpv-header-card__body">
          <h1 class="rpv-header-card__title">Relatório de pesquisa de preços</h1>
          <p class="rpv-header-card__lead">{{ tituloCotacao }}</p>
          <p class="rpv-header-card__muted">{{ DOCUMENTO_TECNICO_LEAD }}</p>
        </div>
      </header>

      <div class="rpv-info-grid">
        <article class="rpv-info-card">
          <div class="rpv-info-card__row">
            <span class="rpv-info-card__icon" aria-hidden="true">{{ icon('building') }}</span>
            <span class="rpv-info-card__label">Órgão</span>
          </div>
          <p class="rpv-info-card__value">{{ orgaoExibicao }}</p>
        </article>
        <article class="rpv-info-card">
          <div class="rpv-info-card__row">
            <span class="rpv-info-card__icon" aria-hidden="true">{{ icon('user') }}</span>
            <span class="rpv-info-card__label">Responsável</span>
          </div>
          <p class="rpv-info-card__value">{{ criadoPor }}</p>
        </article>
        <article class="rpv-info-card">
          <div class="rpv-info-card__row">
            <span class="rpv-info-card__icon" aria-hidden="true">{{ icon('calendar') }}</span>
            <span class="rpv-info-card__label">Data da pesquisa</span>
          </div>
          <p class="rpv-info-card__value">{{ dataPesquisa }}</p>
        </article>
        <article class="rpv-info-card">
          <div class="rpv-info-card__row">
            <span class="rpv-info-card__icon" aria-hidden="true">{{ icon('sigma') }}</span>
            <span class="rpv-info-card__label">Método aplicado</span>
          </div>
          <p class="rpv-info-card__value">{{ metodoAplicadoExibicao }}</p>
        </article>
        <article class="rpv-info-card rpv-info-card--strong">
          <div class="rpv-info-card__row">
            <span class="rpv-info-card__icon" aria-hidden="true">{{ icon('badge') }}</span>
            <span class="rpv-info-card__label">Valor total estimado</span>
          </div>
          <p class="rpv-info-card__value rpv-info-card__value--strong">{{ valorTotalEstimadoFmt }}</p>
        </article>
      </div>

      <section class="rpv-panel rpv-panel--padded">
        <div class="rpv-panel__head">
          <div>
            <h2 class="rpv-panel__title">Metodologia aplicada</h2>
            <p class="rpv-panel__subtitle">Base legal, método matemático e critérios técnicos adotados</p>
          </div>
          <span class="rpv-chip">IN 65/2021 · Lei 14.133</span>
        </div>
        <div class="rpv-prose">
          <p>A pesquisa foi realizada com base na Lei nº 14.133/2021 e na IN nº 65/2021.</p>
          <p>
            As cotações selecionadas foram obtidas por meio de consultas ao Portal Nacional de Contratações Públicas – PNCP,
            bancos de dados públicos e pesquisa direta de mercado, observando-se a compatibilidade da descrição do objeto,
            a unidade de medida, a recência das informações, a natureza da contratação e a consistência dos dados utilizados
            para formação do preço estimado.
          </p>
          <p>Os valores estimados mostram-se compatíveis com o mercado e adequados para subsidiar a contratação.</p>
        </div>
        <div class="rpv-metrics">
          <div class="rpv-metric">
            <div class="rpv-metric__title">Critério</div>
            <div class="rpv-metric__value">Compatibilidade</div>
          </div>
          <div class="rpv-metric">
            <div class="rpv-metric__title">Recência</div>
            <div class="rpv-metric__value">Até 12 meses</div>
          </div>
          <div class="rpv-metric">
            <div class="rpv-metric__title">Rastreabilidade</div>
            <div class="rpv-metric__value">CNPJ, fonte e data</div>
          </div>
        </div>
      </section>

      <section class="rpv-panel rpv-panel--flush">
        <div class="rpv-panel__bar">
          <div>
            <h2 class="rpv-panel__title">Resultado consolidado</h2>
            <p class="rpv-panel__subtitle">Resumo dos itens com média definida e situação da pesquisa</p>
          </div>
        </div>
        <div class="rpv-table-scroll">
          <table class="rpv-table">
            <thead>
              <tr>
                <th class="rpv-table__th rpv-table__th--narrow">Item</th>
                <th class="rpv-table__th rpv-table__th--wide">Descrição</th>
                <th class="rpv-table__th">Quantidade</th>
                <th class="rpv-table__th">Cotações válidas</th>
                <th class="rpv-table__th">Média</th>
                <th class="rpv-table__th rpv-table__th--accent">Valor total</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="g in grupos" :key="'c-' + g.ordem" class="rpv-table__tr">
                <td class="rpv-table__td rpv-table__td--num">{{ g.ordem }}</td>
                <td class="rpv-table__td">
                  <div class="rpv-table__name">{{ g.nome }}</div>
                </td>
                <td class="rpv-table__td">{{ quantidadeExibicao(g) }}</td>
                <td class="rpv-table__td">{{ g.n_cotacoes }}</td>
                <td class="rpv-table__td rpv-table__td--medium">{{ g.media_fmt }}</td>
                <td class="rpv-table__td rpv-table__td--accent">{{ formatarMoedaPtBr(calcularTotalItemNum(g)) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="rpv-panel rpv-panel--flush">
        <div class="rpv-panel__bar rpv-panel__bar--simple">
          <div>
            <h2 class="rpv-panel__title">Detalhamento dos itens</h2>
            <p class="rpv-panel__subtitle">Ficha técnica do item e fontes utilizadas na composição do preço</p>
          </div>
        </div>
        <div class="rpv-detail-list">
          <article v-for="g in grupos" :key="'d-' + g.ordem" class="rpv-detail-item">
            <header class="rpv-detail-item__head">
              <span class="rpv-detail-item__kicker">Item {{ g.ordem }}</span>
              <div class="rpv-detail-item__name">{{ g.nome }}</div>
            </header>
            <div class="rpv-detail-item__body">
              <div v-for="(f, fi) in g.fontes" :key="fi" class="rpv-source">
                <span class="rpv-source__badge">{{ fi + 1 }}</span>
                <div class="rpv-source__inner">
                  <div class="rpv-fonte-stack">
                  <div class="rpv-fonte-fields">
                    <div class="rpv-mini-grid rpv-mini-grid--1">
                      <div class="rpv-dcard rpv-dcard--featured">
                        <span class="rpv-dcard__label">Fornecedor</span>
                        <span class="rpv-dcard__value rpv-dcard__value--strong">{{ f.fornecedor }}</span>
                      </div>
                    </div>
                    <div class="rpv-mini-grid rpv-mini-grid--2">
                      <div class="rpv-dcard"><span class="rpv-dcard__label">CNPJ</span><span class="rpv-dcard__value">{{ f.cnpj }}</span></div>
                      <div class="rpv-dcard rpv-dcard--featured">
                        <span class="rpv-dcard__label">Valor</span>
                        <span class="rpv-dcard__value rpv-dcard__value--strong">{{ f.valor }}</span>
                      </div>
                    </div>
                    <div class="rpv-mini-grid rpv-mini-grid--1">
                      <div class="rpv-dcard"><span class="rpv-dcard__label">Órgão</span><span class="rpv-dcard__value">{{ f.orgao }}</span></div>
                    </div>
                    <div class="rpv-mini-grid rpv-mini-grid--2">
                      <div class="rpv-dcard">
                        <span class="rpv-dcard__label">Modalidade</span>
                        <span class="rpv-dcard__value">{{ obterModalidade(f.tipo) }}</span>
                      </div>
                      <div class="rpv-dcard"><span class="rpv-dcard__label">Data</span><span class="rpv-dcard__value">{{ f.data }}</span></div>
                    </div>
                  </div>
                  <div class="rpv-mini-grid rpv-mini-grid--5">
                    <div class="rpv-dcard rpv-dcard--wide">
                      <span class="rpv-dcard__label">Processo</span>
                      <span class="rpv-dcard__value">{{ f.processo || 'N/D' }}</span>
                    </div>
                    <div class="rpv-dcard">
                      <span class="rpv-dcard__label">Qtd.</span>
                      <span class="rpv-dcard__value">{{ parseQuantidadeStr(quantidadeExibicao(g)).valor }}</span>
                    </div>
                    <div class="rpv-dcard">
                      <span class="rpv-dcard__label">Unid.</span>
                      <span class="rpv-dcard__value">{{ parseQuantidadeStr(quantidadeExibicao(g)).unidade }}</span>
                    </div>
                    <div class="rpv-dcard">
                      <span class="rpv-dcard__label">Fonte</span>
                      <span class="rpv-dcard__value">{{ obterFonte(f.tipo) }}</span>
                    </div>
                    <div class="rpv-dcard">
                      <span class="rpv-dcard__label">UF</span>
                      <span class="rpv-dcard__value">{{ ufFromMunicipio(g, f) }}</span>
                    </div>
                  </div>
                  <div class="rpv-mini-grid rpv-mini-grid--2">
                    <div class="rpv-dcard rpv-dcard--wide">
                      <span class="rpv-dcard__label">Descrição do item</span>
                      <span class="rpv-dcard__value">{{ f.descricao_fonte || '—' }}</span>
                    </div>
                    <div class="rpv-dcard rpv-dcard--wide">
                      <span class="rpv-dcard__label">Ajuste</span>
                      <span class="rpv-dcard__value">{{ f.ajuste }}</span>
                    </div>
                  </div>
                  </div>
                </div>
              </div>
            </div>
          </article>
        </div>
      </section>

      <section class="rpv-panel rpv-panel--padded">
        <div class="rpv-icon-title">
          <div class="rpv-icon-title__bubble">{{ icon('check') }}</div>
          <div>
            <h2 class="rpv-panel__title">Conclusão técnica</h2>
            <p class="rpv-panel__subtitle">Síntese conclusiva da pesquisa de preços</p>
          </div>
        </div>
        <div class="rpv-quote">
          <p>
            Com base nas cotações obtidas, na metodologia aplicada e na análise técnica dos dados, conclui-se que os valores
            estimados refletem adequadamente os preços praticados no mercado, estando aptos a subsidiar a contratação pública
            pretendida, com observância aos princípios da economicidade, razoabilidade e eficiência.
          </p>
        </div>
      </section>

      <section class="rpv-panel rpv-panel--padded">
        <div class="rpv-icon-title">
          <div class="rpv-icon-title__bubble rpv-icon-title__bubble--alt">{{ icon('shield') }}</div>
          <div>
            <h2 class="rpv-panel__title">Responsabilidade sobre as informações</h2>
            <p class="rpv-panel__subtitle">Esclarecimento quanto ao uso da plataforma</p>
          </div>
        </div>
        <div class="rpv-quote rpv-quote--stack">
          <p>
            A plataforma disponibiliza um ambiente digital de apoio à pesquisa de preços, no qual são consolidadas informações
            oriundas de diferentes origens, tais como bases públicas, sistemas oficiais e registros de mercado, com o objetivo
            de auxiliar na formação de referência de valores.
          </p>
          <p>
            Compete exclusivamente ao servidor público responsável pela pesquisa a análise crítica, validação, seleção e
            utilização dos preços, em conformidade com a legislação vigente, especialmente a Lei nº 14.133/2021, normativos
            aplicáveis e orientações dos órgãos de controle.
          </p>
          <p>
            Dessa forma, a plataforma atua como ferramenta de apoio à tomada de decisão, não substituindo o dever de diligência,
            responsabilidade técnica e julgamento administrativo do agente público.
          </p>
        </div>
      </section>

      <section class="rpv-panel rpv-panel--padded">
        <div class="rpv-icon-title">
          <div class="rpv-icon-title__bubble rpv-icon-title__bubble--alt">{{ icon('building') }}</div>
          <div>
            <h2 class="rpv-panel__title">Informações dos fornecedores</h2>
            <p class="rpv-panel__subtitle">Dados cadastrais e de contato</p>
          </div>
        </div>
        <div class="rpv-supplier-grid">
          <article v-for="(f, idx) in fornecedoresUnicos" :key="`${f.cnpj}-${idx}`" class="rpv-supplier-card">
            <div class="rpv-supplier-card__name">{{ f.fornecedor }}</div>
            <div class="rpv-supplier-card__lines">
              <div><span class="rpv-supplier-card__k">CNPJ:</span> {{ f.cnpj }}</div>
              <div><span class="rpv-supplier-card__k">Telefone:</span> {{ f.telefone || 'Não informado' }}</div>
              <div><span class="rpv-supplier-card__k">Email:</span> {{ f.email || 'Não informado' }}</div>
              <div><span class="rpv-supplier-card__k">Endereço:</span> {{ f.endereco || 'Não informado' }}</div>
            </div>
          </article>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { getResearchSession } from '../services/pncpResearch';

const DOCUMENTO_TECNICO_LEAD =
  'Documento técnico consolidado com metodologia, análise técnica, rastreabilidade das cotações e conclusão para suporte à contratação.';

const MIN_FONTES = 3;

const route = useRoute();

const isLoading = ref(false);
const loadError = ref('');

const tituloRelatorio = ref('Relatório de pesquisa de preços');
const tituloCotacao = ref('—');
const dataPesquisa = ref('—');
const criadoPor = ref('—');
const criadoPorEmail = ref('');
const termoPncp = ref('—');
const formulaCalculo = ref('');
const formulaCalculoId = ref('');
const grupos = ref([]);
const totalLinhasCotacao = ref(0);
/** Órgão da capa (prefeitura da sessão/usuário); alinhado ao PDF. */
const orgaoExibicaoApi = ref('');

const cotacaoIdQuery = computed(() => {
  const raw = route.query.cotacaoId;
  if (raw == null || raw === '') return '';
  return String(raw);
});

const orgaoExibicao = computed(() => {
  const api = String(orgaoExibicaoApi.value || '').trim();
  if (api && api !== '—') return api;
  for (const g of grupos.value) {
    const fontes = g?.fontes || [];
    for (const f of fontes) {
      const o = String(f?.orgao || '').trim();
      if (o && o !== '—') return o;
    }
  }
  return '—';
});

const metodoAplicadoExibicao = computed(() => {
  const id = String(formulaCalculoId.value || '').trim();
  const short = {
    media_aritmetica_precos_obtidos: 'Média Aritmética',
    mediana_precos_obtidos: 'Mediana',
    menor_preco: 'Menor preço',
    media_saneada: 'Média saneada',
    media_ponderada: 'Média ponderada',
    media_relativa_25_50: 'Média relativa 25%–50%',
  };
  if (id && short[id]) return short[id];
  const lbl = String(formulaCalculo.value || '').trim();
  if (lbl.includes('aritmética')) return 'Média Aritmética';
  return lbl || '—';
});

const valorTotalEstimadoFmt = computed(() => {
  let total = 0;
  for (const g of grupos.value) {
    total += calcularTotalItemNum(g);
  }
  return formatarMoedaPtBr(total);
});

const fornecedoresUnicos = computed(() => {
  const out = [];
  const seen = new Set();
  for (const g of grupos.value) {
    for (const f of g.fontes || []) {
      const key = `${f.cnpj || 'nd'}|${f.fornecedor || 'nd'}`;
      if (seen.has(key)) continue;
      seen.add(key);
      out.push({
        fornecedor: f.fornecedor || 'Fornecedor',
        cnpj: f.cnpj || 'Não informado',
        telefone: f.telefone || '',
        email: f.email || '',
        endereco: f.endereco || '',
      });
    }
  }
  return out;
});

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

function icon(name) {
  const icons = {
    building: '🏛️',
    user: '👤',
    calendar: '📅',
    sigma: 'Σ',
    check: '✓',
    shield: '🛡️',
    badge: '✓',
  };
  return icons[name] || '•';
}

function parseQuantidadeStr(quantidade) {
  if (quantidade == null || String(quantidade).trim() === '') {
    return { valor: 'N/D', unidade: 'N/D' };
  }
  const texto = String(quantidade).trim().replace(/\s+/g, ' ');
  const match = texto.match(/^([\d.,]+)\s*(.*)$/);
  if (!match) {
    return { valor: texto, unidade: 'N/D' };
  }
  const valor = (match[1] || '').trim() || 'N/D';
  const unidade = (match[2] || '').trim() || 'N/D';
  return { valor, unidade };
}

function moedaParaNumero(valor) {
  if (!valor) return 0;
  const n = parseFloat(
    String(valor)
      .replace('R$', '')
      .trim()
      .replace(/\./g, '')
      .replace(',', '.'),
  );
  return Number.isFinite(n) ? n : 0;
}

function quantidadeParaNumero(quantidade) {
  const parsed = parseQuantidadeStr(quantidade);
  const v = parseFloat(String(parsed.valor).replace(/\./g, '').replace(',', '.'));
  return Number.isFinite(v) ? v : 0;
}

function formatarMoedaPtBr(valor) {
  return Number(valor || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

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

function quantidadeExibicao(g) {
  const q = String(g?.quantidade_fmt || '').trim();
  const u = String(g?.unidade || '').trim();
  if (q && u) return `${q} ${u}`.trim();
  return q || u || '—';
}

function calcularTotalItemNum(g) {
  return quantidadeParaNumero(quantidadeExibicao(g)) * moedaParaNumero(g?.media_fmt);
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
  const fornecedor = src.fornecedor || src.nomeRazaoSocialFornecedor
    || (src.fornecedor_cadastro && (src.fornecedor_cadastro.razao_social || src.fornecedor_cadastro.nome_fantasia))
    || '—';
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
  const mun = String(it.municipio || src.municipio || src.municipioNome || '').trim()
    || String((src.unidadeOrgao && src.unidadeOrgao.municipioNome) || '').trim();
  const uf = String(it.uf || src.uf || src.ufSigla || '').trim()
    || String((src.unidadeOrgao && src.unidadeOrgao.ufSigla) || '').trim();
  let municipioUf = '—';
  if (mun && uf) municipioUf = `${mun}/${uf}`;
  else if (mun) municipioUf = mun;
  else if (uf) municipioUf = uf;
  const orgaoRaw = String(it.orgao || src.orgao || '').trim();
  let orgaoExib = orgaoRaw || '—';
  if (municipioUf !== '—' && orgaoRaw) {
    orgaoExib = `${municipioUf} - ${orgaoRaw}`;
  } else if (municipioUf !== '—') {
    orgaoExib = municipioUf;
  }
  const processo = src.processo || it.numero_pncp || '—';
  const ajuste = src.ajuste || src.observacao_frete || 'Sem frete';
  const descricaoFonte = String(
    src.descricao
      || src.descricaoItem
      || src.descricao_item
      || src.objeto_resumido
      || src.objetoResumido
      || src.objetoCompra
      || it.descricao_item
      || '',
  ).trim() || '—';
  return {
    tipo,
    descricao_fonte: descricaoFonte,
    fornecedor,
    cnpj,
    data,
    valor,
    orgao: orgaoExib,
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
    const situacao = n >= MIN_FONTES ? 'Válido' : `Insuficiente (${n} de ${MIN_FONTES} fontes)`;
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

function obterModalidade(tipo) {
  const map = {
    PNCP: 'Pregão Eletrônico',
    BBMNET: 'Dispensa',
    CMED: 'Pregão Eletrônico',
    'Cotação Direta': 'Dispensa',
    ComprasGov: 'Pregão',
  };
  const raw = String(tipo || '').trim();
  return map[raw] || raw || 'N/D';
}

function obterFonte(tipo) {
  const fontesConvertidas = new Set(['Cotação Direta', 'BBMNET', 'ComprasGov', 'CMED']);
  const raw = String(tipo || '').trim();
  if (!raw) return 'N/D';
  return fontesConvertidas.has(raw) ? 'PNCP' : raw;
}

function aplicarDemo() {
  orgaoExibicaoApi.value = '';
  tituloCotacao.value =
    'Aquisição de medicamentos específicos para atender doações a pacientes em situação de vulnerabilidade social e risco à saúde';
  dataPesquisa.value = '01/04/2026 08:59';
  criadoPor.value = 'Edislene Ferreira da Silva';
  criadoPorEmail.value = '';
  termoPncp.value = '—';
  formulaCalculo.value = 'Média aritmética dos preços obtidos';
  formulaCalculoId.value = 'media_aritmetica_precos_obtidos';
  grupos.value = DEMO_GRUPOS;
  totalLinhasCotacao.value = DEMO_GRUPOS.reduce((s, g) => s + g.n_cotacoes, 0);
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
    orgaoExibicaoApi.value = String(s.orgao_exibicao ?? '').trim();
    tituloCotacao.value = s.titulo || '—';
    dataPesquisa.value = formatDataHoraIso(s.created_at);
    criadoPor.value = s.criado_por || '—';
    criadoPorEmail.value = (s.criado_por_email || '').trim();
    termoPncp.value = s.termo_busca || '—';
    formulaCalculo.value = String(s.formula_calculo || '').trim();
    formulaCalculoId.value = String(s.formula_calculo_id || '').trim();

    const itens = Array.isArray(data.itens) ? [...data.itens].sort((a, b) => (a.id ?? 0) - (b.id ?? 0)) : [];

    if (Array.isArray(data.grupos_relatorio) && data.grupos_relatorio.length > 0) {
      grupos.value = data.grupos_relatorio;
      totalLinhasCotacao.value =
        typeof data.total_linhas_cotacao === 'number' ? data.total_linhas_cotacao : itens.length;
    } else if (itens.length) {
      grupos.value = montarGruposFromItens(itens);
      totalLinhasCotacao.value = itens.length;
    } else {
      grupos.value = [];
      totalLinhasCotacao.value = 0;
    }
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

<style src="../assets/relatorio-pesquisa-precos.css"></style>
