<template>
  <section class="gov-page">
    <header class="gov-page__header">
      <div class="manual-header">
        <h1 class="gov-page__title">Busca Manual de Cotações</h1>
        <RouterLink :to="`/pesquisador-pncp/cotacoes/${cotacaoId}`" class="manual-link-back">
          <i class="fa-solid fa-arrow-left" aria-hidden="true"></i>
          Voltar à busca compacta
        </RouterLink>
      </div>
      <p class="gov-page__subtitle">Busca avançada com semáforo de confiabilidade da IA.</p>
    </header>

    <div class="gov-surface gov-page__content">
      <section class="manual-filters">
        <div class="manual-filters__row">
          <label class="manual-field manual-field--grow">
            <span>Descrição</span>
            <input v-model.trim="filtros.descricao" type="text" />
          </label>
          <label class="manual-field">
            <span>Período</span>
            <select v-model="filtros.periodo">
              <option>Último Mês</option>
              <option>Últimos 3 Meses</option>
              <option>Últimos 6 Meses</option>
              <option>Último Ano</option>
            </select>
          </label>
          <label class="manual-field">
            <span>Tipo</span>
            <select v-model="filtros.tipo">
              <option>Todos</option>
              <option>Material</option>
              <option>Serviço</option>
            </select>
          </label>
          <label class="manual-field">
            <span>Modalidade</span>
            <select v-model="filtros.modalidade">
              <option>Todas</option>
              <option>Pregão</option>
              <option>Pregão Eletrônico</option>
              <option>Pregão Eletrônico SRP</option>
              <option>Compra direta</option>
              <option>Dispensa Eletrônica</option>
              <option>Concorrência</option>
              <option>Concorrência eletrônica</option>
              <option>Inexigibilidade</option>
              <option>Dispensa</option>
              <option>Chamada Pública</option>
              <option>Leilão</option>
              <option>Concurso</option>
              <option>Diálogo Competitivo</option>
            </select>
          </label>
          <div class="manual-field manual-field--uf">
            <span>UF</span>
            <details class="manual-uf-dropdown">
              <summary class="manual-uf-dropdown__summary">
                <span>{{ selectedUfLabel }}</span>
                <i class="fa-solid fa-chevron-down" aria-hidden="true"></i>
              </summary>
              <div class="manual-uf-dropdown__menu" role="group" aria-label="Selecionar UFs">
                <label class="manual-uf-dropdown__item manual-uf-dropdown__item--all">
                  <input
                    type="checkbox"
                    :checked="allUfsSelected"
                    :indeterminate.prop="isPartiallySelectedUf"
                    @change="toggleAllUfs"
                  />
                  <span>Todos os estados</span>
                </label>
                <label v-for="uf in ufOptions" :key="uf.code" class="manual-uf-dropdown__item">
                  <input
                    type="checkbox"
                    :checked="filtros.ufs.includes(uf.code)"
                    @change="toggleUf(uf.code)"
                  />
                  <img :src="uf.flag" :alt="`Bandeira ${uf.code}`" class="manual-uf-option__flag" />
                  <span>{{ uf.code }} - {{ uf.name }}</span>
                </label>
              </div>
            </details>
          </div>
          <button type="button" class="manual-btn-search" @click="buscarNoBackend">Buscar</button>
        </div>
        <div class="manual-local-db-row">
          <p class="manual-meta">
            Base local PNCP (`pncp_researcher_service`): <strong>{{ totalItensBaseLocal }}</strong> itens indexados.
          </p>
          <button type="button" class="manual-btn-backfill" :disabled="isBackfilling" @click="atualizarBaseLocalAgora">
            {{ isBackfilling ? 'Atualizando base...' : 'Atualizar base local (.db)' }}
          </button>
        </div>
      </section>
      <p v-if="searchError" class="manual-meta manual-meta--error">{{ searchError }}</p>
      <p v-else-if="isSearching" class="manual-meta">Consultando backend PNCP...</p>

      <section class="manual-controls">
        <div class="manual-controls__left">
          <label class="manual-field">
            <span>Ordenar por</span>
            <select v-model="filtros.ordenarPor">
              <option>Produto</option>
              <option>Quantidade</option>
              <option>Valor</option>
              <option>UF</option>
            </select>
          </label>
          <label class="manual-field">
            <span>Ordem</span>
            <select v-model="filtros.ordem">
              <option>Decrescente</option>
              <option>Crescente</option>
            </select>
          </label>
        </div>
        <div class="manual-controls__right">
          <label class="manual-field">
            <span>Valor Base</span>
            <div class="manual-input-prefix-wrap">
              <span class="manual-input-prefix">R$</span>
              <input v-model="filtros.valorBase" type="text" inputmode="decimal" />
            </div>
          </label>
          <label class="manual-field">
            <span>Variação %</span>
            <div class="manual-input-suffix-wrap">
              <input
                :value="filtros.variacao"
                type="text"
                inputmode="numeric"
                maxlength="3"
                @input="onVariacaoInput"
              />
              <span class="manual-input-suffix">%</span>
            </div>
          </label>
        </div>
      </section>

      <section class="manual-summary">
        <div class="manual-summary-card"><span>Resultados</span><strong>{{ resultadosFiltradosOrdenados.length }}</strong></div>
        <div class="manual-summary-card"><span>Selecionados</span><strong>{{ totalSelecionados }}</strong></div>
        <div class="manual-summary-card"><span>Valor médio</span><strong>{{ mediaValor }}</strong></div>
        <div class="manual-summary-card"><span>UFs distintas</span><strong>{{ totalUfs }}</strong></div>
      </section>
      <p v-if="faixaValorAtiva" class="manual-meta">
        Faixa ativa por Valor Base + Variação: <strong>{{ faixaValorAtiva }}</strong>
      </p>

      <section class="manual-results-table-shell">
        <div class="manual-results-head">
          <RouterLink
            :to="`/pesquisador-pncp/cotacoes/${cotacaoId}`"
            class="manual-add-cotacao-btn"
          >
            <i class="fa-solid fa-plus" aria-hidden="true"></i>
            Adicionar itens na cotação {{ cotacaoId }}
          </RouterLink>
          <button
            type="button"
            class="manual-add-cotacao-btn"
            :disabled="isSavingSelecionados || totalSelecionados === 0"
            @click="adicionarSelecionadosNaCotacao"
          >
            {{ isSavingSelecionados ? 'Salvando...' : 'Salvar selecionados' }}
          </button>
        </div>
        <p v-if="saveMessage" class="manual-meta">{{ saveMessage }}</p>
        <div class="manual-results-table-scroll">
          <table class="manual-results-table">
            <thead>
              <tr>
                <th>Seleção</th>
                <th>Cotação</th>
                <th>Quantidade</th>
                <th>UF</th>
                <th>Data</th>
                <th>Valor Unit.</th>
                <th>Confiabilidade IA</th>
                <th>Observação</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in resultadosFiltradosOrdenados" :key="item.id">
                <td class="manual-cell-center">
                  <input type="checkbox" :checked="item.selecionado" @change="toggleSelecionado(item.id)" />
                </td>
                <td>
                  <div class="manual-cot-main">{{ item.descricao }}</div>
                  <div class="manual-cot-sub">
                    <span class="manual-cot-meta">{{ item.titulo }}</span>
                    <span v-if="item.municipioUfCompacto && item.municipioUfCompacto !== '-'" class="manual-cot-meta-sep">·</span>
                    <span v-if="item.municipioUfCompacto && item.municipioUfCompacto !== '-'">{{ item.municipioUfCompacto }}</span>
                  </div>
                </td>
                <td>{{ item.quantidade }}</td>
                <td class="manual-cell-center">{{ item.uf }}</td>
                <td class="manual-cell-center">{{ item.data }}</td>
                <td class="manual-cell-money">{{ item.valor }}</td>
                <td class="manual-cell-center">
                  <span class="manual-status" :class="statusClass(item.statusIa)">{{ item.statusIa }}</span>
                </td>
                <td>{{ item.observacao }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { useRoute } from 'vue-router';
import {
  addItemsToResearchSession,
  backfillLocalIndex,
  getLocalIndexStats,
  searchLocalItems,
} from '../services/pncpResearch';

const route = useRoute();
const cotacaoId = computed(() => route.params.cotacaoId || 'CT-2026-00421');

const filtros = reactive({
  descricao: 'FORFIG',
  periodo: 'Último Ano',
  tipo: 'Todos',
  modalidade: 'Todas',
  ufs: [],
  ordenarPor: 'Produto',
  ordem: 'Decrescente',
  valorBase: '15,00',
  variacao: '20',
});

const UF_FLAGS = {
  AC: new URL('../assets/estados/02-acre-full.svg', import.meta.url).href,
  AL: new URL('../assets/estados/03-alagoas-full.svg', import.meta.url).href,
  AP: new URL('../assets/estados/04-amapa-full.svg', import.meta.url).href,
  AM: new URL('../assets/estados/05-amazonas-full.svg', import.meta.url).href,
  BA: new URL('../assets/estados/06-bahia-full.svg', import.meta.url).href,
  CE: new URL('../assets/estados/07-ceara-full.svg', import.meta.url).href,
  DF: new URL('../assets/estados/08-distrito-federal-full.svg', import.meta.url).href,
  ES: new URL('../assets/estados/09-espirito-santo-full.svg', import.meta.url).href,
  GO: new URL('../assets/estados/10-goias-full.svg', import.meta.url).href,
  MA: new URL('../assets/estados/11-maranhao-full.svg', import.meta.url).href,
  MT: new URL('../assets/estados/12-mato-grosso-full.svg', import.meta.url).href,
  MS: new URL('../assets/estados/13-mato-grosso-do-sul-full.svg', import.meta.url).href,
  MG: new URL('../assets/estados/14-minas-gerais-full.svg', import.meta.url).href,
  PA: new URL('../assets/estados/15-para-full.svg', import.meta.url).href,
  PB: new URL('../assets/estados/16-paraiba-full.svg', import.meta.url).href,
  PR: new URL('../assets/estados/17-parana-full.svg', import.meta.url).href,
  PE: new URL('../assets/estados/18-pernambuco-full.svg', import.meta.url).href,
  PI: new URL('../assets/estados/19-piaui-full.svg', import.meta.url).href,
  RJ: new URL('../assets/estados/20-rio-de-janeiro-full.svg', import.meta.url).href,
  RN: new URL('../assets/estados/21-rio-grande-do-norte-full.svg', import.meta.url).href,
  RS: new URL('../assets/estados/22-rio-grande-do-sul-full.svg', import.meta.url).href,
  RO: new URL('../assets/estados/23-rondonia-full.svg', import.meta.url).href,
  RR: new URL('../assets/estados/24-roraima-full.svg', import.meta.url).href,
  SC: new URL('../assets/estados/25-santa-catarina-full.svg', import.meta.url).href,
  SP: new URL('../assets/estados/26-sao-paulo-full.svg', import.meta.url).href,
  SE: new URL('../assets/estados/27-sergipe-full.svg', import.meta.url).href,
  TO: new URL('../assets/estados/28-tocantins-full.svg', import.meta.url).href,
};

const ufOptions = [
  { code: 'AC', name: 'Acre' }, { code: 'AL', name: 'Alagoas' }, { code: 'AP', name: 'Amapá' },
  { code: 'AM', name: 'Amazonas' }, { code: 'BA', name: 'Bahia' }, { code: 'CE', name: 'Ceará' },
  { code: 'DF', name: 'Distrito Federal' }, { code: 'ES', name: 'Espírito Santo' }, { code: 'GO', name: 'Goiás' },
  { code: 'MA', name: 'Maranhão' }, { code: 'MT', name: 'Mato Grosso' }, { code: 'MS', name: 'Mato Grosso do Sul' },
  { code: 'MG', name: 'Minas Gerais' }, { code: 'PA', name: 'Pará' }, { code: 'PB', name: 'Paraíba' },
  { code: 'PR', name: 'Paraná' }, { code: 'PE', name: 'Pernambuco' }, { code: 'PI', name: 'Piauí' },
  { code: 'RJ', name: 'Rio de Janeiro' }, { code: 'RN', name: 'Rio Grande do Norte' }, { code: 'RS', name: 'Rio Grande do Sul' },
  { code: 'RO', name: 'Rondônia' }, { code: 'RR', name: 'Roraima' }, { code: 'SC', name: 'Santa Catarina' },
  { code: 'SP', name: 'São Paulo' }, { code: 'SE', name: 'Sergipe' }, { code: 'TO', name: 'Tocantins' },
].map((uf) => ({ ...uf, flag: UF_FLAGS[uf.code] }));

const MODALIDADE_TO_CODIGO = {
  Pregão: 8,
  'Pregão Eletrônico': 8,
  'Pregão Eletrônico SRP': 8,
  Concorrência: 6,
  'Concorrência eletrônica': 6,
  'Chamada Pública': 7,
  Dispensa: 9,
  'Compra direta': 9,
  'Dispensa Eletrônica': 9,
  Inexigibilidade: 10,
  Leilão: 11,
  Concurso: 12,
  'Diálogo Competitivo': 13,
};

function toggleUf(code) {
  if (filtros.ufs.includes(code)) {
    filtros.ufs = filtros.ufs.filter((uf) => uf !== code);
    return;
  }
  filtros.ufs = [...filtros.ufs, code];
}

function toggleAllUfs(event) {
  if (event.target.checked) {
    filtros.ufs = ufOptions.map((uf) => uf.code);
    return;
  }
  filtros.ufs = [];
}

function onVariacaoInput(event) {
  const raw = String(event.target.value || '');
  const onlyDigits = raw.replace(/\D/g, '');
  if (!onlyDigits) {
    filtros.variacao = '0';
    event.target.value = '0';
    return;
  }
  const normalized = String(Math.min(100, Math.max(0, Number.parseInt(onlyDigits, 10))));
  filtros.variacao = normalized;
  event.target.value = normalized;
}

const resultados = ref([]);
const isSearching = ref(false);
const searchError = ref('');
const saveMessage = ref('');
const localStats = ref(null);
const isBackfilling = ref(false);
const isSavingSelecionados = ref(false);
const totalSelecionados = computed(() => resultados.value.filter((x) => x.selecionado).length);
const totalUfs = computed(() => new Set(resultadosFiltradosOrdenados.value.map((x) => x.uf).filter(Boolean)).size);
const mediaValor = computed(() => {
  const nums = resultadosFiltradosOrdenados.value.map((x) => parseMoeda(x.valor)).filter((x) => typeof x === 'number');
  if (!nums.length) return 'R$ -';
  return formatCurrency(nums.reduce((a, b) => a + b, 0) / nums.length);
});
const totalItensBaseLocal = computed(() => Number(localStats.value?.total_itens || 0));
const faixaValorAtiva = computed(() => {
  const base = parseMoeda(filtros.valorBase);
  if (base == null || base <= 0) return '';
  const p = Number.parseFloat(String(filtros.variacao || '0'));
  const perc = Number.isFinite(p) ? Math.max(0, p) : 0;
  const min = base * (1 - perc / 100);
  const max = base * (1 + perc / 100);
  return `${formatCurrency(min)} até ${formatCurrency(max)} (${perc}% para baixo/cima)`;
});
const selectedUfLabel = computed(() => {
  if (!filtros.ufs.length) return 'Selecionar UFs';
  if (filtros.ufs.length <= 3) return filtros.ufs.join(', ');
  return `${filtros.ufs.length} UFs selecionadas`;
});
const allUfsSelected = computed(() => filtros.ufs.length === ufOptions.length);
const isPartiallySelectedUf = computed(
  () => filtros.ufs.length > 0 && filtros.ufs.length < ufOptions.length,
);

const resultadosFiltradosOrdenados = computed(() => {
  const base = [...resultados.value];
  const valorBase = parseMoeda(filtros.valorBase);
  const variacao = Number.parseFloat(String(filtros.variacao || '0'));
  const variacaoValida = Number.isFinite(variacao) ? Math.max(0, variacao) : 0;

  let filtrados = base;
  if (valorBase != null && valorBase > 0) {
    const fator = variacaoValida / 100;
    const min = valorBase * (1 - fator);
    const max = valorBase * (1 + fator);
    filtrados = base.filter((item) => {
      // Usa valor numérico bruto do item para evitar ruído de formatação.
      const vBruto = item.valorUnitario ?? item.valorTotal ?? parseMoeda(item.valor);
      const v = Number(vBruto);
      if (v == null) return false;
      if (!Number.isFinite(v)) return false;
      return v >= min && v <= max;
    });
  }
  if (filtros.ufs.length > 0 && filtros.ufs.length < ufOptions.length) {
    const selected = new Set(filtros.ufs);
    filtrados = filtrados.filter((item) => selected.has(String(item.uf || '').toUpperCase()));
  }
  if (filtros.periodo) {
    filtrados = filtrados.filter((item) => isWithinPeriodo(item.data, filtros.periodo));
  }
  if (filtros.tipo && filtros.tipo !== 'Todos') {
    const tipoSelecionado = normalizeText(filtros.tipo);
    filtrados = filtrados.filter((item) => normalizeText(resolveTipoItem(item)) === tipoSelecionado);
  }
  if (filtros.modalidade && filtros.modalidade !== 'Todas') {
    const modalidadeSelecionada = normalizeText(filtros.modalidade);
    filtrados = filtrados.filter((item) =>
      normalizeText(item.observacao || '').includes(modalidadeSelecionada)
    );
  }

  const ordem = filtros.ordem === 'Crescente' ? 1 : -1;
  const byText = (a, b, pick) => String(pick(a) || '').localeCompare(String(pick(b) || ''), 'pt-BR');
  const byNumber = (a, b, pick) => {
    const av = Number(pick(a));
    const bv = Number(pick(b));
    const ax = Number.isFinite(av) ? av : Number.POSITIVE_INFINITY;
    const bx = Number.isFinite(bv) ? bv : Number.POSITIVE_INFINITY;
    return ax - bx;
  };

  filtrados.sort((a, b) => {
    let cmp = 0;
    if (filtros.ordenarPor === 'Quantidade') {
      cmp = byNumber(a, b, (x) => x.quantidadeNum);
    } else if (filtros.ordenarPor === 'Valor') {
      cmp = byNumber(a, b, (x) => parseMoeda(x.valor));
    } else if (filtros.ordenarPor === 'UF') {
      cmp = byText(a, b, (x) => x.uf);
    } else {
      cmp = byText(a, b, (x) => x.descricao);
    }
    if (cmp === 0) cmp = byText(a, b, (x) => x.descricao);
    return cmp * ordem;
  });

  return filtrados;
});

async function carregarStatusBaseLocal() {
  try {
    localStats.value = await getLocalIndexStats();
  } catch (_err) {
    localStats.value = null;
  }
}

function statusClass(status) {
  if (status === 'Alta') return 'manual-ia-dot--high';
  if (status === 'Média') return 'manual-ia-dot--mid';
  return 'manual-ia-dot--low';
}

async function buscarNoBackend() {
  if (!filtros.descricao.trim()) return;
  isSearching.value = true;
  searchError.value = '';
  try {
    const codigoModalidade =
      filtros.modalidade && filtros.modalidade !== 'Todas'
        ? (MODALIDADE_TO_CODIGO[filtros.modalidade] ?? null)
        : null;
    const data = await searchLocalItems({
      termo_busca: filtros.descricao.trim(),
      uf: filtros.ufs.length === 1 ? filtros.ufs[0] : null,
      codigo_modalidade: codigoModalidade,
      // Busca agressiva para varrer o máximo possível (backend limita teto de segurança).
      max_paginas: 500,
      tamanho_pagina: 200,
    });
    if (data?.ok && Array.isArray(data.itens)) {
      resultados.value = data.itens.map((it, idx) => ({
        id: `backend-${idx}-${it.numero_pncp || ''}`,
        sourceRaw: it,
        numeroPncp: it.numero_pncp || null,
        anoCompra: it.ano_compra ?? null,
        sequencialCompra: it.sequencial_compra ?? null,
        numeroItem: it.numero_item ?? null,
        titulo: it.orgao || 'Órgão não informado',
        descricao: it.descricao_item || it.objeto_resumido || 'Descrição indisponível',
        municipioUfCompacto: [it.municipio, it.uf].filter(Boolean).join('/') || '-',
        quantidade: `${it.quantidade || '-'} ${it.unidade_medida || ''}`.trim(),
        quantidadeNum: it.quantidade ?? null,
        unidadeMedida: it.unidade_medida || null,
        uf: it.uf || '-',
        municipio: it.municipio || null,
        data: it.data_publicacao || '-',
        valor: formatCurrency(it.valor_unitario ?? it.valor_total ?? 0),
        valorUnitario: it.valor_unitario ?? null,
        valorTotal: it.valor_total ?? null,
        statusIa: 'Média',
        observacao: it.modalidade || 'Importado do backend PNCP',
        selecionado: false,
      }));
    }
  } catch (err) {
    searchError.value = `Não foi possível consultar o backend (${err.message || 'erro desconhecido'}).`;
  } finally {
    isSearching.value = false;
  }
}

async function atualizarBaseLocalAgora() {
  if (isBackfilling.value) return;
  isBackfilling.value = true;
  searchError.value = '';
  saveMessage.value = '';
  try {
    const res = await backfillLocalIndex({
      months: 12,
      max_paginas: 2,
      tamanho_pagina: 50,
      include_items: true,
    });
    localStats.value = res;
    saveMessage.value = `Base local atualizada. Itens no índice: ${Number(res?.total_itens || 0)}.`;
    await buscarNoBackend();
  } catch (err) {
    searchError.value = `Falha ao atualizar a base local (${err.message || 'erro desconhecido'}).`;
  } finally {
    isBackfilling.value = false;
  }
}

function formatCurrency(v) {
  const n = Number(v);
  if (Number.isNaN(n)) return 'R$ -';
  return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function toNullableText(v) {
  const s = String(v ?? '').trim();
  if (!s || s === '-' || s === '—') return null;
  return s;
}

function normalizeText(v) {
  return String(v ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

function parseDateFlexible(v) {
  const s = String(v ?? '').trim();
  if (!s) return null;
  const br = s.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (br) {
    const d = new Date(Number(br[3]), Number(br[2]) - 1, Number(br[1]));
    return Number.isNaN(d.getTime()) ? null : d;
  }
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? null : d;
}

function isWithinPeriodo(itemDate, periodoLabel) {
  const dt = parseDateFlexible(itemDate);
  if (!dt) return true;
  const now = new Date();
  const label = normalizeText(periodoLabel);
  let months = 12;
  if (label.includes('mes') && label.includes('ultimo') && !label.includes('3') && !label.includes('6')) {
    months = 1;
  } else if (label.includes('3')) {
    months = 3;
  } else if (label.includes('6')) {
    months = 6;
  } else if (label.includes('ano') || label.includes('12')) {
    months = 12;
  }
  const cutoff = new Date(now);
  cutoff.setMonth(cutoff.getMonth() - months);
  return dt >= cutoff;
}

function resolveTipoItem(item) {
  const materialServico = normalizeText(item?.sourceRaw?.material_servico || '');
  if (materialServico.includes('servico') || materialServico.includes('serviço')) return 'Servico';
  if (materialServico.includes('material')) return 'Material';
  const desc = normalizeText(item?.descricao || '');
  if (desc.includes('servico') || desc.includes('serviço')) return 'Servico';
  return 'Material';
}

function toggleSelecionado(id) {
  resultados.value = resultados.value.map((r) => (r.id === id ? { ...r, selecionado: !r.selecionado } : r));
}

async function adicionarSelecionadosNaCotacao() {
  if (isSavingSelecionados.value) return;
  const sessionId = Number(cotacaoId.value);
  if (Number.isNaN(sessionId)) {
    saveMessage.value = 'Cotação inválida para salvar no backend.';
    return;
  }
  saveMessage.value = '';
  const itens = resultados.value
    .filter((r) => r.selecionado)
    .map((r) => ({
      numero_pncp: toNullableText(r.numeroPncp),
      ano_compra: r.anoCompra,
      sequencial_compra: r.sequencialCompra,
      numero_item: toNullableText(r.numeroItem),
      descricao_item: toNullableText(r.descricao),
      quantidade: r.quantidadeNum,
      unidade_medida: toNullableText(r.unidadeMedida),
      valor_unitario: r.valorUnitario ?? parseMoeda(r.valor),
      valor_total: r.valorTotal,
      orgao: toNullableText(r.titulo),
      municipio: toNullableText(r.municipio),
      uf: toNullableText(r.uf),
      modalidade: toNullableText(r.observacao),
      // Mantém metadados úteis sem inflar demais o JSON.
      origem: 'busca_manual',
      data_publicacao: toNullableText(r.data),
      material_servico: toNullableText(r.sourceRaw?.material_servico),
    }))
    .filter((it) => !!it.descricao_item || !!it.numero_pncp || (it.ano_compra != null && it.sequencial_compra != null));
  if (!itens.length) {
    saveMessage.value = 'Selecione ao menos um item.';
    return;
  }
  const MAX_ITENS_TOTAL = 2000;
  const BATCH_SIZE = 250;
  let enviar = itens;
  if (itens.length > MAX_ITENS_TOTAL) {
    enviar = itens.slice(0, MAX_ITENS_TOTAL);
    saveMessage.value = `Limite de ${MAX_ITENS_TOTAL} itens por operação; gravando os primeiros ${MAX_ITENS_TOTAL}.`;
  }
  isSavingSelecionados.value = true;
  try {
    let totalInseridos = 0;
    for (let i = 0; i < enviar.length; i += BATCH_SIZE) {
      const lote = enviar.slice(i, i + BATCH_SIZE);
      const res = await addItemsToResearchSession(sessionId, lote);
      totalInseridos += Number(res.itens_inseridos ?? lote.length);
    }
    saveMessage.value = `${totalInseridos} item(ns) adicionados à cotação ${sessionId}.`;
    if (totalInseridos > 0) {
      resultados.value = resultados.value.map((r) => (r.selecionado ? { ...r, selecionado: false } : r));
    }
  } catch (err) {
    saveMessage.value = `Falha ao salvar: ${err.message || 'erro desconhecido'}`;
  } finally {
    isSavingSelecionados.value = false;
  }
}

function parseMoeda(v) {
  const raw = String(v ?? '').trim();
  if (!raw) return null;
  const normalized = raw
    .replace(/[^\d,.-]/g, '')
    .replace(/\./g, '')
    .replace(',', '.');
  const n = Number(normalized);
  return Number.isNaN(n) ? null : n;
}

onMounted(() => {
  carregarStatusBaseLocal();
  buscarNoBackend();
});
</script>

<style scoped>
.gov-page { display: flex; flex-direction: column; gap: 16px; width: 100%; min-width: 0; }
.gov-page__title { margin: 0; font-size: 24px; }
.gov-page__subtitle { margin: 6px 0 0; color: var(--color-text-soft); }
.gov-page__content { padding: 16px; display: flex; flex-direction: column; gap: 12px; min-width: 0; }

.manual-header { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
.manual-link-back { border: 1px solid #cfd8e3; border-radius: 10px; background: #fff; color: #1f2937; padding: 7px 12px; font-size: 12px; text-decoration: none; display: inline-flex; align-items: center; gap: 7px; }

.manual-filters,
.manual-controls { border: 1px solid #d6dde8; border-radius: 12px; background: #fff; padding: 10px; }
.manual-filters__row,
.manual-controls,
.manual-controls__left,
.manual-controls__right { display: flex; flex-wrap: wrap; gap: 8px; align-items: end; }
.manual-controls { justify-content: space-between; }

.manual-filters__row {
  justify-content: flex-start;
}

.manual-local-db-row {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed #d6dde8;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.manual-field { border: 1px solid #d6dde8; border-radius: 10px; background: #f8fafc; padding: 8px 10px; display: flex; flex-direction: column; gap: 4px; min-width: 170px; }
.manual-field--grow { flex: 1 1 320px; }
.manual-field--uf { min-width: 220px; }
.manual-field span { font-size: 10px; text-transform: uppercase; color: #64748b; }
.manual-meta { margin: 0; font-size: 12px; color: #64748b; }
.manual-meta--error { color: #b91c1c; }
.manual-field input,
.manual-field select { border: 1px solid #cfd8e3; border-radius: 8px; background: #fff; font-size: 13px; padding: 7px 9px; outline: none; }

.manual-input-suffix-wrap {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  border: 1px solid #cfd8e3;
  border-radius: 8px;
  background: #fff;
}

.manual-input-prefix-wrap {
  display: grid;
  grid-template-columns: auto 1fr;
  align-items: center;
  border: 1px solid #cfd8e3;
  border-radius: 8px;
  background: #fff;
}

.manual-input-prefix-wrap input {
  border: 0;
  border-radius: 0 8px 8px 0;
}

.manual-input-prefix {
  padding: 0 6px 0 9px;
  color: #475569;
  font-size: 13px;
  font-weight: 600;
}

.manual-input-suffix-wrap input {
  border: 0;
  border-radius: 8px 0 0 8px;
}

.manual-input-suffix {
  padding: 0 9px 0 4px;
  color: #475569;
  font-size: 13px;
  font-weight: 600;
}

.manual-btn-search { height: 42px; border: 1px solid #1f4e79; border-radius: 10px; background: #1f4e79; color: #fff; font-weight: 600; padding: 0 16px; }
.manual-btn-search {
  flex: 0 0 auto;
  margin-left: auto;
}

.manual-btn-backfill {
  height: 34px;
  border: 1px solid #b7d2ef;
  border-radius: 10px;
  background: #e8f1fb;
  color: #1f4e79;
  font-weight: 600;
  padding: 0 12px;
}

.manual-btn-backfill:disabled {
  opacity: 0.7;
}

.manual-uf-dropdown {
  position: relative;
}

.manual-uf-dropdown__summary {
  list-style: none;
  border: 1px solid #cfd8e3;
  border-radius: 8px;
  background: #fff;
  padding: 7px 9px;
  font-size: 13px;
  color: #1f2937;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  cursor: pointer;
}

.manual-uf-dropdown__summary::-webkit-details-marker {
  display: none;
}

.manual-uf-dropdown__menu {
  position: absolute;
  z-index: 10;
  top: calc(100% + 6px);
  left: 0;
  width: 320px;
  max-height: 280px;
  overflow: auto;
  border: 1px solid #d6dde8;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.14);
  padding: 8px;
  display: grid;
  gap: 4px;
}

.manual-uf-dropdown__item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #334155;
  padding: 4px;
}

.manual-uf-option__flag {
  width: 22px;
  height: 15px;
  object-fit: cover;
  border-radius: 2px;
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.08);
}

.manual-uf-dropdown__item--all {
  border-bottom: 1px solid #e8edf4;
  margin-bottom: 4px;
  padding-bottom: 8px;
}
/* Mantem o bloco de ordenacao/valor em linha (cards lado a lado) */
.manual-controls {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 10px;
}

.manual-controls__left,
.manual-controls__right {
  min-width: 0;
}

.manual-controls__left {
  display: grid;
  grid-template-columns: repeat(2, minmax(170px, 1fr));
  gap: 8px;
}

.manual-controls__right {
  display: grid;
  grid-template-columns: minmax(150px, 1fr) minmax(130px, 1fr);
  gap: 8px;
  align-items: end;
}

@media (min-width: 1120px) {
  .manual-controls {
    grid-template-columns: minmax(340px, 0.95fr) minmax(620px, 1.45fr);
    align-items: end;
  }
}

.manual-summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 8px; }
.manual-summary-card { border: 1px solid #d6dde8; border-radius: 12px; background: #fff; padding: 10px; }
.manual-summary-card span { display: block; font-size: 12px; color: #64748b; }
.manual-summary-card strong { display: block; margin-top: 4px; font-size: 22px; color: #0f172a; }

.manual-results-table-shell {
  border: 1px solid #d6dde8;
  border-radius: 12px;
  background: #fff;
  overflow: hidden;
}

.manual-results-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  border-bottom: 1px solid #e5eaf3;
  background: #f8fafc;
  padding: 10px;
}

.manual-add-cotacao-btn {
  border: 1px solid #1f4e79;
  border-radius: 10px;
  background: #1f4e79;
  color: #fff;
  padding: 7px 12px;
  font-size: 12px;
  font-weight: 600;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  flex-shrink: 0;
}

.manual-add-cotacao-btn:hover {
  filter: brightness(0.95);
}

.manual-results-table-scroll {
  width: 100%;
  max-height: 460px;
  overflow-x: auto;
  overflow-y: auto;
}

.manual-results-table {
  width: 100%;
  min-width: 1200px;
  border-collapse: collapse;
  table-layout: fixed;
  font-size: 12px;
}

.manual-results-table th,
.manual-results-table td {
  border-bottom: 1px solid #e8edf4;
  padding: 9px 8px;
  text-align: left;
  vertical-align: top;
}

.manual-results-table th {
  font-size: 11px;
  text-transform: uppercase;
  color: #64748b;
  background: #f8fafc;
}

.manual-cell-center { text-align: center !important; }
.manual-cell-money { white-space: nowrap; font-weight: 700; }
.manual-cot-main { font-weight: 600; color: #1f4e79; line-height: 1.25; }
.manual-cot-sub { margin-top: 3px; color: #475569; line-height: 1.3; }
.manual-cot-meta {
  display: inline-block;
  max-width: 560px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  vertical-align: bottom;
}
.manual-cot-meta-sep { margin: 0 6px; color: #94a3b8; }

.manual-status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  border: 1px solid transparent;
  padding: 2px 8px;
  font-size: 10px;
  font-weight: 700;
  white-space: nowrap;
}

.manual-ia-dot--high { background: #e7f6ee; border-color: #cfe9da; color: #1f7a53; }
.manual-ia-dot--mid { background: #fff6e6; border-color: #f0dfb3; color: #9a6a00; }
.manual-ia-dot--low { background: #fff0f0; border-color: #f0d0d0; color: #b54747; }
</style>
