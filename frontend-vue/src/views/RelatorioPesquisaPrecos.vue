<template>
  <section class="rpv-page">
    <header class="rpv-top">
      <div>
        <h1 class="rpv-top__title">Relatório de pesquisa de preços</h1>
        <p class="rpv-top__subtitle">Modelo oficial alinhado ao preview aprovado</p>
      </div>
      <RouterLink v-if="cotacaoIdQuery" :to="`/pesquisador-pncp/cotacoes/${cotacaoIdQuery}`" class="rpv-back">Voltar à cotação</RouterLink>
      <RouterLink v-else to="/pesquisador-pncp" class="rpv-back">Pesquisador PNCP</RouterLink>
    </header>
    <p v-if="loadError" class="rpv-status rpv-status--error">{{ loadError }}</p>
    <p v-else-if="isLoading" class="rpv-status">Carregando dados da cotação...</p>

    <div class="rpv-wrap">
      <section class="rpv-hero">
        <div class="rpv-hero__logo-wrap">
          <img class="rpv-hero__logo" :src="logoBrancaUrl" alt="DocMaster" />
        </div>
        <div>
          <p class="rpv-kicker">Relatório institucional</p>
          <h2 class="rpv-hero__title">{{ tituloRelatorio }}</h2>
          <p class="rpv-hero__subtitle">Pesquisa de preços com rastreabilidade completa das fontes</p>
        </div>
      </section>

      <section class="rpv-grid">
        <article class="rpv-info-card rpv-info-card--strong"><p class="rpv-label">Cotação</p><p class="rpv-value">{{ tituloCotacao }}</p></article>
        <article class="rpv-info-card"><p class="rpv-label">Data da pesquisa</p><p class="rpv-value">{{ dataPesquisa }}</p></article>
        <article class="rpv-info-card"><p class="rpv-label">Emitido em</p><p class="rpv-value">{{ emitidoEm }}</p></article>
        <article class="rpv-info-card"><p class="rpv-label">Responsável</p><p class="rpv-value">{{ criadoPor }}</p></article>
        <article class="rpv-info-card"><p class="rpv-label">Itens</p><p class="rpv-value">{{ grupos.length }}</p></article>
        <article class="rpv-info-card"><p class="rpv-label">Valor total estimado</p><p class="rpv-value">{{ valorTotalEstimado }}</p></article>
      </section>

      <section class="rpv-block">
        <h3 class="rpv-block__title">Resultado consolidado</h3>
        <div class="rpv-table-wrap">
          <table class="rpv-table">
            <thead>
              <tr>
                <th>Item</th>
                <th>Descrição</th>
                <th>Quantidade</th>
                <th>Cotações válidas</th>
                <th>Média</th>
                <th>Valor total</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="g in grupos" :key="'c-' + g.ordem">
                <td>{{ g.ordem }}</td>
                <td>{{ g.nome }}</td>
                <td>{{ g.quantidade_fmt }} {{ g.unidade }}</td>
                <td>{{ g.n_cotacoes }}</td>
                <td>{{ g.media_fmt }}</td>
                <td>{{ valorTotalItem(g) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="rpv-block">
        <h3 class="rpv-block__title">Detalhamento dos itens</h3>
        <div class="rpv-items">
          <article v-for="g in grupos" :key="'d-' + g.ordem" class="rpv-item">
            <header class="rpv-item__head">
              <span class="rpv-item__kicker">Item {{ g.ordem }}</span>
              <strong class="rpv-item__name">{{ g.nome }}</strong>
            </header>
            <div class="rpv-sources">
              <div v-for="(f, fi) in g.fontes" :key="fi" class="rpv-source">
                <span class="rpv-source__index">{{ fi + 1 }}</span>
                <div class="rpv-source__content">
                  <div class="rpv-row rpv-row--3">
                    <div class="rpv-mini rpv-mini--featured"><span>Fornecedor</span><b>{{ f.fornecedor }}</b></div>
                    <div class="rpv-mini"><span>CNPJ</span><b>{{ f.cnpj }}</b></div>
                    <div class="rpv-mini rpv-mini--featured"><span>Valor</span><b>{{ f.valor }}</b></div>
                  </div>
                  <div class="rpv-row rpv-row--3">
                    <div class="rpv-mini"><span>Órgão</span><b>{{ f.orgao }}</b></div>
                    <div class="rpv-mini"><span>Modalidade</span><b>{{ obterModalidade(f.tipo) }}</b></div>
                    <div class="rpv-mini"><span>Data</span><b>{{ f.data }}</b></div>
                  </div>
                  <div class="rpv-row rpv-row--5">
                    <div class="rpv-mini"><span>ID / Processo</span><b>{{ fi + 1 }} / {{ f.processo || 'N/D' }}</b></div>
                    <div class="rpv-mini"><span>Qtd.</span><b>{{ g.quantidade_fmt }}</b></div>
                    <div class="rpv-mini"><span>Unid.</span><b>{{ g.unidade }}</b></div>
                    <div class="rpv-mini"><span>Fonte</span><b>{{ obterFonte(f.tipo) }}</b></div>
                    <div class="rpv-mini"><span>UF</span><b>{{ ufFromMunicipio(g, f) }}</b></div>
                  </div>
                  <div class="rpv-row rpv-row--2">
                    <div class="rpv-mini"><span>Descrição do item</span><b>{{ g.nome }}</b></div>
                    <div class="rpv-mini"><span>Ajuste</span><b>{{ f.ajuste }}</b></div>
                  </div>
                </div>
              </div>
            </div>
          </article>
        </div>
      </section>

      <section class="rpv-block">
        <h3 class="rpv-block__title">Informações dos fornecedores</h3>
        <div class="rpv-suppliers">
          <article v-for="(f, idx) in fornecedoresUnicos" :key="`${f.cnpj}-${idx}`" class="rpv-supplier">
            <strong>{{ f.fornecedor }}</strong>
            <p><b>CNPJ:</b> {{ f.cnpj }}</p>
            <p><b>Telefone:</b> {{ f.telefone || 'Não informado' }}</p>
            <p><b>Email:</b> {{ f.email || 'Não informado' }}</p>
            <p><b>Endereço:</b> {{ f.endereco || 'Não informado' }}</p>
          </article>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { getResearchSession } from '../services/pncpResearch';
import logoBrancaUrl from '../assets/logo_branca.png';

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
const valorTotalEstimado = computed(() => {
  let total = 0;
  for (const g of grupos.value) {
    const qtd = Number(String(g.quantidade_fmt || '').replace('.', '').replace(',', '.')) || 0;
    const media = Number(String(g.media_fmt || '').replace(/[^\d,]/g, '').replace('.', '').replace(',', '.')) || 0;
    total += qtd * media;
  }
  return `R$ ${formatarMoedaBr(total)}`;
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

function valorTotalItem(g) {
  const qtd = Number(String(g?.quantidade_fmt || '').replace('.', '').replace(',', '.')) || 0;
  const media = Number(String(g?.media_fmt || '').replace(/[^\d,]/g, '').replace('.', '').replace(',', '.')) || 0;
  return `R$ ${formatarMoedaBr(qtd * media)}`;
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
.rpv-page { padding: 16px; background: #f1f5f9; min-height: 100vh; }
.rpv-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; margin-bottom: 12px; }
.rpv-top__title { margin: 0; font-size: 24px; color: #0f172a; }
.rpv-top__subtitle { margin: 4px 0 0; color: #64748b; font-size: 13px; }
.rpv-back { border: 1px solid #cbd5e1; border-radius: 10px; background: #fff; color: #1e293b; text-decoration: none; padding: 8px 12px; font-size: 12px; }
.rpv-status { margin: 6px 0 12px; font-size: 12px; color: #64748b; }
.rpv-status--error { color: #b91c1c; }
.rpv-wrap { max-width: 1200px; margin: 0 auto; display: grid; gap: 14px; }
.rpv-hero { border-radius: 20px; background: linear-gradient(135deg, #1f4e79 0%, #5f7f9a 100%); color: #fff; padding: 18px; display: grid; grid-template-columns: 140px minmax(0,1fr); gap: 14px; align-items: center; }
.rpv-hero__logo-wrap { background: #ffffff14; border: 1px solid #ffffff33; border-radius: 14px; padding: 10px; text-align: center; }
.rpv-hero__logo { width: 100%; max-width: 110px; object-fit: contain; }
.rpv-kicker { margin: 0; font-size: 10px; text-transform: uppercase; letter-spacing: .08em; opacity: .9; }
.rpv-hero__title { margin: 4px 0 0; font-size: 24px; }
.rpv-hero__subtitle { margin: 6px 0 0; font-size: 13px; opacity: .95; }
.rpv-grid { display: grid; grid-template-columns: repeat(6, minmax(0,1fr)); gap: 8px; }
.rpv-info-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 14px; padding: 10px; }
.rpv-info-card--strong { background: #eff6ff; border-color: #bfdbfe; }
.rpv-label { margin: 0; font-size: 10px; text-transform: uppercase; color: #64748b; font-weight: 700; letter-spacing: .04em; }
.rpv-value { margin: 6px 0 0; font-size: 13px; font-weight: 700; color: #0f172a; line-height: 1.25; }
.rpv-block { border: 1px solid #e2e8f0; border-radius: 20px; background: #fff; padding: 14px; }
.rpv-block__title { margin: 0 0 10px; font-size: 18px; color: #0f172a; }
.rpv-table-wrap { overflow: auto; border: 1px solid #e2e8f0; border-radius: 12px; }
.rpv-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.rpv-table th { background: #f1f5f9; text-align: left; font-size: 11px; color: #334155; padding: 8px; border-bottom: 1px solid #e2e8f0; }
.rpv-table td { padding: 8px; border-top: 1px solid #e2e8f0; color: #334155; }
.rpv-items { display: grid; gap: 10px; }
.rpv-item { border: 1px solid #e2e8f0; border-radius: 14px; overflow: hidden; }
.rpv-item__head { background: #f8fafc; border-bottom: 1px solid #e2e8f0; padding: 8px 10px; }
.rpv-item__kicker { display: block; font-size: 10px; text-transform: uppercase; color: #64748b; font-weight: 700; letter-spacing: .05em; }
.rpv-item__name { display: block; margin-top: 2px; font-size: 13px; color: #0f172a; }
.rpv-sources { padding: 8px; display: grid; gap: 8px; }
.rpv-source { position: relative; border: 1px solid #e2e8f0; border-radius: 10px; background: #f8fafcb3; padding-left: 30px; }
.rpv-source__index { position: absolute; left: 8px; top: 50%; transform: translateY(-50%); width: 18px; height: 18px; border-radius: 999px; background: #5f7f9a; color: #fff; font-size: 9px; font-weight: 700; display: inline-flex; align-items: center; justify-content: center; }
.rpv-source__content { padding: 6px; display: grid; gap: 4px; }
.rpv-row { display: grid; gap: 4px; }
.rpv-row--3 { grid-template-columns: repeat(3, minmax(0,1fr)); }
.rpv-row--5 { grid-template-columns: repeat(5, minmax(0,1fr)); }
.rpv-row--2 { grid-template-columns: repeat(2, minmax(0,1fr)); }
.rpv-mini { border: 1px solid #d6dde8; border-radius: 8px; background: #fff; padding: 6px 8px; min-height: 34px; }
.rpv-mini--featured { background: #f8fafc; }
.rpv-mini span { display: block; font-size: 9px; font-weight: 700; text-transform: uppercase; color: #64748b; letter-spacing: .04em; line-height: 1; }
.rpv-mini b { display: block; margin-top: 4px; font-size: 11px; color: #1e293b; line-height: 1.2; word-break: break-word; }
.rpv-suppliers { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 10px; }
.rpv-supplier { border: 1px solid #e2e8f0; border-radius: 12px; background: #f8fafc; padding: 10px; }
.rpv-supplier strong { font-size: 13px; color: #0f172a; display: block; margin-bottom: 6px; }
.rpv-supplier p { margin: 2px 0; font-size: 12px; color: #334155; }
@media (max-width: 1100px) { .rpv-grid { grid-template-columns: repeat(3, minmax(0,1fr)); } }
@media (max-width: 900px) {
  .rpv-hero { grid-template-columns: 1fr; }
  .rpv-row--3, .rpv-row--5, .rpv-row--2, .rpv-suppliers { grid-template-columns: 1fr; }
  .rpv-grid { grid-template-columns: repeat(2, minmax(0,1fr)); }
}
</style>
