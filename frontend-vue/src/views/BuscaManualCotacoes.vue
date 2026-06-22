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
          <button type="button" class="manual-btn-search" @click="buscarNoBackend">Buscar</button>
        </div>
        <div class="manual-geo-panel">
          <div class="manual-geo-panel__top">
            <div class="manual-geo-panel__intro">
              <p class="manual-geo-panel__kicker">Busca geográfica</p>
              <h2 class="manual-geo-panel__title">Escolher cidade</h2>
              <p class="manual-geo-panel__hint">
                Opcional: uma linha por UF; marque várias cidades na lista. Sem nenhuma marcada = UF inteira. Sem linhas
                = busca em todo o país.
              </p>
            </div>
            <button type="button" class="manual-geo-add-link" @click="addLinhaCidade">+ Adicionar UF</button>
          </div>
          <div v-if="!filtros.cidades.length" class="manual-geo-empty">Nenhum recorte por cidade/UF (cobertura nacional).</div>
          <div v-for="(linha, idx) in filtros.cidades" :key="linha._id" class="manual-geo-row">
            <label class="manual-geo-field">
              <span>UF</span>
              <div class="manual-geo-uf-filter">
                <img
                  v-if="ufBandeiraUrl(linha.uf)"
                  :src="ufBandeiraUrl(linha.uf)"
                  :alt="`Bandeira ${linha.uf}`"
                  class="manual-geo-uf-flag"
                />
                <select v-model="linha.uf" class="manual-geo-select manual-geo-select--uf" @change="onUfLinhaCidadeChange(linha)">
                  <option value="">—</option>
                  <option v-for="u in ufOptions" :key="u.code" :value="u.code">{{ u.code }}</option>
                </select>
              </div>
            </label>
            <div class="manual-geo-field manual-geo-field--grow manual-geo-field--mun">
              <span>Cidades</span>
              <p v-if="!linha.uf" class="manual-geo-mun-hint">Escolha a UF para listar os municípios.</p>
              <template v-else>
                <input
                  v-model="linha.filtroMun"
                  type="search"
                  class="manual-geo-mun-search"
                  placeholder="Filtrar cidades…"
                  autocomplete="off"
                />
                <p class="manual-geo-mun-hint">
                  Marque quantas quiser; nenhuma marcada = inclui a <strong>UF inteira</strong>.
                </p>
                <div class="manual-geo-mun-list" role="group" :aria-label="`Cidades ${linha.uf}`">
                  <label v-for="m in municipiosListaUfFiltrada(linha)" :key="m" class="manual-geo-mun-item">
                    <input
                      type="checkbox"
                      :checked="linha.municipios.includes(m)"
                      @change="toggleMunicipioLinha(linha, m, $event.target.checked)"
                    />
                    <span>{{ m }}</span>
                  </label>
                </div>
              </template>
            </div>
            <button type="button" class="manual-geo-remove" title="Remover esta linha" @click="removeLinhaCidade(idx)">×</button>
          </div>
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
          <label class="manual-field">
            <span>Direção da variação</span>
            <select v-model="filtros.variacaoSentido" :disabled="variacaoGlobalDaSessao != null">
              <option value="cima">Para cima</option>
              <option value="baixo">Para baixo</option>
              <option value="ambos">Ambos</option>
            </select>
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
          <button
            type="button"
            class="manual-add-cotacao-btn"
            :disabled="isSavingSelecionados || totalSelecionados === 0"
            @click="adicionarSelecionadosNaCotacao(true)"
          >
            {{ isSavingSelecionados ? 'Salvando...' : addButtonLabel }}
          </button>
          <RouterLink
            :to="`/pesquisador-pncp/cotacoes/${cotacaoId}`"
            class="manual-add-cotacao-btn manual-add-cotacao-btn--ghost"
          >
            Ir para cotação
          </RouterLink>
        </div>
        <p v-if="saveMessage" class="manual-meta">{{ saveMessage }}</p>
        <div class="manual-results-table-scroll">
          <table class="manual-results-table">
            <thead>
              <tr>
                <th>Seleção</th>
                <th>Cotação</th>
                <th>Quantidade</th>
                <th>Inciso</th>
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
                  <div v-if="item.similaridadeEncontrada" class="manual-cot-sub">
                    <span class="manual-similaridade-tag" title="Match por variação de contexto">
                      Similaridade parcial encontrada
                    </span>
                  </div>
                </td>
                <td>{{ item.quantidade }}</td>
                <td class="manual-cell-center">{{ item.inciso }}</td>
                <td class="manual-cell-center">
                  <div class="manual-uf-cell">
                    <img
                      v-if="ufBandeiraUrl(item.uf)"
                      :src="ufBandeiraUrl(item.uf)"
                      :alt="`UF ${item.uf}`"
                      class="manual-geo-uf-flag manual-geo-uf-flag--table"
                    />
                    <span>{{ item.uf }}</span>
                  </div>
                </td>
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
import { useRoute, useRouter } from 'vue-router';
import {
  addItemsToResearchSession,
  addCotacoesToItemInResearchSession,
  backfillLocalIndex,
  getResearchSession,
  getLocalIndexStats,
  intelligentMarketSearch,
  searchLocalItems,
} from '../services/pncpResearch';
import { MUNICIPIOS_POR_UF } from '../data/brasilMunicipiosPorUf';
import { buildRecortesGeograficosPayload, itemMatchesRecortesGeograficos } from '../utils/recortesGeograficos';
import { displayPnCpUnitario, hasDisplayPnCpPrecoPositivo } from '../utils/pncpPricing';

const route = useRoute();
const router = useRouter();
const cotacaoId = computed(() => route.params.cotacaoId || 'CT-2026-00421');
const itemId = computed(() => {
  const n = Number(route.query.itemId);
  return Number.isFinite(n) && n > 0 ? n : null;
});

const filtros = reactive({
  descricao: '',
  periodo: 'Último Ano',
  tipo: 'Todos',
  modalidade: 'Todas',
  /** @type {Array<{ _id: string, uf: string, municipios: string[], filtroMun: string }>} */
  cidades: [],
  ordenarPor: 'Produto',
  ordem: 'Decrescente',
  valorBase: '15,00',
  variacao: '20',
  variacaoSentido: 'ambos',
});

function newLinhaCidade() {
  return {
    _id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
    uf: '',
    municipios: [],
    filtroMun: '',
  };
}

function addLinhaCidade() {
  filtros.cidades.push(newLinhaCidade());
}

function removeLinhaCidade(idx) {
  filtros.cidades.splice(idx, 1);
}

function onUfLinhaCidadeChange(linha) {
  const list = MUNICIPIOS_POR_UF[String(linha.uf || '').toUpperCase()] || [];
  linha.municipios = (linha.municipios || []).filter((m) => list.includes(m));
  linha.filtroMun = '';
}

function municipiosListaUf(linha) {
  const uf = String(linha.uf || '').toUpperCase();
  if (!uf) return [];
  const list = MUNICIPIOS_POR_UF[uf];
  return Array.isArray(list) ? list : [];
}

function normalizeMunFilter(v) {
  return String(v ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

function municipiosListaUfFiltrada(linha) {
  const list = municipiosListaUf(linha);
  const q = normalizeMunFilter(linha.filtroMun);
  if (!q) return list;
  return list.filter((m) => normalizeMunFilter(m).includes(q));
}

function toggleMunicipioLinha(linha, nome, checked) {
  const set = new Set(linha.municipios || []);
  if (checked) set.add(nome);
  else set.delete(nome);
  linha.municipios = Array.from(set);
}

const recortesGeograficosAtivos = computed(() => buildRecortesGeograficosPayload(filtros.cidades));

function geoApiSlice() {
  const recortes = buildRecortesGeograficosPayload(filtros.cidades);
  if (recortes.length > 0) {
    return { recortes_geograficos: recortes };
  }
  return { uf: null, municipio: null };
}

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

function ufBandeiraUrl(code) {
  const k = String(code || '').trim().toUpperCase();
  return UF_FLAGS[k] || '';
}

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

function onVariacaoInput(event) {
  if (Number.isFinite(Number(variacaoGlobalDaSessao.value)) && Number(variacaoGlobalDaSessao.value) >= 0) {
    const locked = String(Math.round(Number(variacaoGlobalDaSessao.value)));
    filtros.variacao = locked;
    event.target.value = locked;
    return;
  }
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
const variacaoGlobalDaSessao = ref(null);
const addButtonLabel = computed(() => (
  itemId.value
    ? '+ Adicionar preços ao item selecionado'
    : '+ Adicionar itens na cotação'
));
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
  const fator = perc / 100;
  const sentido = ['baixo', 'cima', 'ambos'].includes(filtros.variacaoSentido) ? filtros.variacaoSentido : 'ambos';
  const min = sentido === 'baixo' ? Math.max(0, base * (1 - fator)) : (sentido === 'cima' ? base : Math.max(0, base * (1 - fator)));
  const max = sentido === 'baixo' ? base : (sentido === 'cima' ? base * (1 + fator) : base * (1 + fator));
  const labelSentido = sentido === 'baixo' ? 'para baixo' : (sentido === 'cima' ? 'para cima' : 'para baixo/cima');
  return `${formatCurrency(min)} até ${formatCurrency(max)} (${perc}% ${labelSentido})`;
});
const resultadosFiltradosOrdenados = computed(() => {
  const base = [...resultados.value];
  const valorBase = parseMoeda(filtros.valorBase);
  const variacao = Number.parseFloat(String(filtros.variacao || '0'));
  const variacaoValida = Number.isFinite(variacao) ? Math.max(0, variacao) : 0;

  let filtrados = base;
  if (valorBase != null && valorBase > 0) {
    const fator = variacaoValida / 100;
    const sentido = ['baixo', 'cima', 'ambos'].includes(filtros.variacaoSentido) ? filtros.variacaoSentido : 'ambos';
    const min = sentido === 'baixo'
      ? Math.max(0, valorBase * (1 - fator))
      : (sentido === 'cima' ? valorBase : Math.max(0, valorBase * (1 - fator)));
    const max = sentido === 'baixo'
      ? valorBase
      : (sentido === 'cima' ? valorBase * (1 + fator) : valorBase * (1 + fator));
    filtrados = base.filter((item) => {
      // Usa valor numérico bruto do item para evitar ruído de formatação.
      const vBruto = item.valorUnitario ?? item.valorTotal ?? parseMoeda(item.valor);
      const v = Number(vBruto);
      if (v == null) return false;
      if (!Number.isFinite(v)) return false;
      return v >= min && v <= max;
    });
  }
  if (recortesGeograficosAtivos.value.length > 0) {
    filtrados = filtrados.filter((item) =>
      itemMatchesRecortesGeograficos(
        { uf: item.uf, municipio: item.municipio },
        recortesGeograficosAtivos.value,
      ),
    );
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

function tokenizeForSimilarity(v) {
  return normalizeText(v)
    .split(/\s+/)
    .map((x) => x.trim())
    .filter((x) => x.length >= 3);
}

function isSpecToken(tok) {
  return /\d/.test(tok) && /(ml|mg|g|kg|l|lt|mcg|ui|mm|cm|m|un|und|cp|caps|comprim|amp|fr)$/.test(tok);
}

function hasWordLikeMatch(word, token) {
  if (!word || !token) return false;
  if (word === token) return true;
  if (token.length >= 4 && word.startsWith(token)) return true;
  if (word.length >= 4 && token.startsWith(word.slice(0, 4))) return true;
  return false;
}

function isSimilaridadeParcialManual(query, desc) {
  const qTokens = tokenizeForSimilarity(query);
  const dWords = tokenizeForSimilarity(desc);
  if (!qTokens.length || !dWords.length) return false;
  const hasExactFull = qTokens.every((t) => dWords.some((w) => hasWordLikeMatch(w, t)));
  if (hasExactFull) return false;
  const specTokens = qTokens.filter((t) => isSpecToken(t));
  const coreTokens = qTokens.filter((t) => !/\d/.test(t) && t.length >= 4);
  const coreHit = coreTokens.some((t) => dWords.some((w) => hasWordLikeMatch(w, t)));
  if (!coreHit) return false;
  if (specTokens.length > 0) {
    return specTokens.some((t) => dWords.some((w) => hasWordLikeMatch(w, t)));
  }
  const hits = coreTokens.filter((t) => dWords.some((w) => hasWordLikeMatch(w, t))).length;
  if (hits >= Math.min(2, coreTokens.length)) return true;
  // Fallback mais permissivo para variações claras no manual.
  return scoreAderenciaManual(query, desc) >= 0.45;
}

function scoreAderenciaManual(query, desc) {
  const qTokens = tokenizeForSimilarity(query);
  const dWords = tokenizeForSimilarity(desc);
  if (!qTokens.length || !dWords.length) return 0;
  let hits = 0;
  for (const t of qTokens) {
    if (dWords.some((w) => hasWordLikeMatch(w, t))) hits += 1;
  }
  return hits / Math.max(1, qTokens.length);
}

function confiabilidadeManual(query, desc) {
  const score = scoreAderenciaManual(query, desc);
  if (score >= 0.85) return 'Alta';
  if (score >= 0.55) return 'Média';
  return 'Baixa';
}

function buildSimilarityFallbackTerms(query) {
  const raw = String(query || '').trim().replace(/\s+/g, ' ');
  if (!raw) return [];
  const out = [];
  const push = (s) => {
    const t = String(s || '').trim().replace(/\s+/g, ' ');
    if (t && t.length >= 8 && !out.includes(t)) out.push(t);
  };

  // Caso "item x com y": tenta a parte antes do conector.
  const splitByConnector = raw.match(/^(.*?)\s+\b(com|para|tipo|modelo|marca)\b\s+.+$/i);
  if (splitByConnector?.[1]) push(splitByConnector[1]);

  const tokens = raw.split(/\s+/).filter(Boolean);
  if (tokens.length >= 4) {
    // Remove sufixos gradualmente (termo base + especificação principal tende a ficar).
    for (let cut = 1; cut <= Math.min(5, tokens.length - 3); cut += 1) {
      push(tokens.slice(0, tokens.length - cut).join(' '));
    }
  }

  // Prefixo até o primeiro token de especificação (ex.: 1mg/ml), incluindo esse token.
  const specIdx = tokens.findIndex((t) => isSpecToken(normalizeText(t)));
  if (specIdx >= 1) {
    push(tokens.slice(0, specIdx + 1).join(' '));
  }

  return out;
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
    const termoBuscaEfetivo = filtros.descricao.trim();
    const geo = geoApiSlice();
    let data = await searchLocalItems({
      termo_busca: termoBuscaEfetivo,
      ...geo,
      codigo_modalidade: codigoModalidade,
      somente_homologados: true,
      // Busca agressiva para varrer o máximo possível (backend limita teto de segurança).
      max_paginas: 500,
      tamanho_pagina: 200,
    });
    const localItemsCount = Array.isArray(data?.itens) ? data.itens.length : 0;
    let fallbackPorSimilaridadeIa = false;
    let termoFallbackUsado = '';
    if (!data?.ok || !Array.isArray(data?.itens) || localItemsCount === 0) {
      const iaData = await intelligentMarketSearch({
        termo_busca: termoBuscaEfetivo,
        ...geo,
        codigo_modalidade: codigoModalidade,
        somente_homologados: true,
        max_paginas: 500,
        tamanho_pagina: 200,
      });
      if (iaData?.ok && Array.isArray(iaData?.itens) && iaData.itens.length > 0) {
        data = iaData;
        fallbackPorSimilaridadeIa = true;
      }
    }
    if (!data?.ok || !Array.isArray(data?.itens) || (Array.isArray(data?.itens) && data.itens.length === 0)) {
      const fallbackTerms = buildSimilarityFallbackTerms(termoBuscaEfetivo);
      for (const term of fallbackTerms) {
        const iaFallback = await intelligentMarketSearch({
          termo_busca: term,
          ...geo,
          codigo_modalidade: codigoModalidade,
          max_paginas: 500,
          tamanho_pagina: 200,
        });
        if (iaFallback?.ok && Array.isArray(iaFallback?.itens) && iaFallback.itens.length > 0) {
          data = iaFallback;
          fallbackPorSimilaridadeIa = true;
          termoFallbackUsado = term;
          break;
        }
      }
    }
    if (data?.ok && Array.isArray(data.itens)) {
      resultados.value = data.itens
        .filter((it) => hasDisplayPnCpPrecoPositivo({ sourceRaw: it }))
        .map((it, idx) => {
        const descricaoLinha = it.descricao_item || it.objeto_resumido || '';
        const similaridadeBackend = Boolean(it?.similaridade_encontrada);
        const similaridadeParcial = similaridadeBackend || isSimilaridadeParcialManual(
          termoBuscaEfetivo,
          descricaoLinha,
        ) || fallbackPorSimilaridadeIa;
        const termoParaConfiabilidade = termoFallbackUsado || termoBuscaEfetivo;
        const conf = confiabilidadeManual(termoParaConfiabilidade, descricaoLinha);
        return {
        id: `backend-${idx}-${it.numero_pncp || ''}`,
        sourceRaw: it,
        numeroPncp: it.numero_pncp || null,
        anoCompra: it.ano_compra ?? null,
        sequencialCompra: it.sequencial_compra ?? null,
        numeroItem: it.numero_item ?? null,
        titulo: it.orgao || 'Órgão não informado',
        descricao: descricaoLinha || 'Descrição indisponível',
        municipioUfCompacto: [it.municipio, it.uf].filter(Boolean).join('/') || '-',
        quantidade: `${it.quantidade || '-'} ${it.unidade_medida || ''}`.trim(),
        quantidadeNum: it.quantidade ?? null,
        unidadeMedida: it.unidade_medida || null,
        inciso: resolveIncisoFromItem(it),
        uf: it.uf || '-',
        municipio: it.municipio || null,
        data: it.data_publicacao || '-',
        valor: formatCurrency(displayPnCpUnitario({ sourceRaw: it })),
        valorUnitario: displayPnCpUnitario({ sourceRaw: it }),
        valorTotal: it.valor_total ?? null,
        statusIa: (similaridadeParcial && conf === 'Alta') || fallbackPorSimilaridadeIa ? 'Média' : conf,
        observacao: it.modalidade || 'Importado do backend PNCP',
        similaridadeEncontrada: similaridadeParcial,
        selecionado: false,
      };
      });
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
  if (v == null || v === '') return 'R$ -';
  const n = Number(v);
  if (!Number.isFinite(n)) return 'R$ -';
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

function resolveIncisoFromItem(it) {
  const esferaId = normalizeText(it?.esfera_id || it?.esferaId).toUpperCase();
  const esferaAdm = normalizeText(it?.esfera_administrativa || it?.esferaAdministrativa);
  if (esferaId === 'F' || esferaAdm === 'federal') return 'Inciso I';
  if (['E', 'M', 'D'].includes(esferaId) || ['estadual', 'municipal', 'distrital'].includes(esferaAdm)) {
    return 'Inciso II';
  }
  return '—';
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

function rowTemCnpjFornecedor(row) {
  const raw = (row?.sourceRaw && typeof row.sourceRaw === 'object') ? row.sourceRaw : {};
  const digits = String(row?.cnpjFornecedor || raw.cnpj_fornecedor || raw.cnpjFornecedor || '')
    .replace(/\D/g, '');
  return digits.length === 14;
}

async function adicionarSelecionadosNaCotacao(goToCotacao = false) {
  if (isSavingSelecionados.value) return;
  const sessionId = Number(cotacaoId.value);
  if (Number.isNaN(sessionId)) {
    saveMessage.value = 'Cotação inválida para salvar no backend.';
    return;
  }
  saveMessage.value = '';
  const faixaBaseSelecionada = parseMoeda(filtros.valorBase);
  const brutos = resultados.value.filter((r) => r.selecionado);
  const semFornecedor = brutos.filter((r) => !rowTemCnpjFornecedor(r)).length;
  const registros = brutos
    .filter((r) => rowTemCnpjFornecedor(r))
    .map((r) => {
      const raw = (r.sourceRaw && typeof r.sourceRaw === 'object') ? r.sourceRaw : {};
      const cad = (raw.fornecedor_cadastro && typeof raw.fornecedor_cadastro === 'object')
        ? raw.fornecedor_cadastro
        : {};
      return {
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
      fornecedor: toNullableText(r.fornecedor || raw.fornecedor),
      cnpj_fornecedor: toNullableText(r.cnpjFornecedor || raw.cnpj_fornecedor),
      fornecedor_cadastro: Object.keys(cad).length ? cad : null,
      telefone: raw.telefone || cad.telefone || cad.ddd_telefone_1 || null,
      email: raw.email || cad.email || null,
      valor_base: faixaBaseSelecionada,
      faixa_regional: {
        valor_base: faixaBaseSelecionada,
      },
      similaridade_encontrada: Boolean(r.similaridadeEncontrada),
      temResultado: r.sourceRaw?.temResultado ?? null,
      situacaoCompraItemNome: r.sourceRaw?.situacaoCompraItemNome ?? null,
      situacao: r.sourceRaw?.situacao_compra || r.sourceRaw?.situacao || null,
      valor_unitario_homologado: r.sourceRaw?.valor_unitario_homologado ?? null,
      valor_total_homologado: r.sourceRaw?.valor_total_homologado ?? null,
      valor_unitario_estimado: r.sourceRaw?.valor_unitario_estimado ?? null,
      valor_total_estimado: r.sourceRaw?.valor_total_estimado ?? null,
      item_homologado: r.sourceRaw?.item_homologado ?? null,
      source: {
        ...raw,
      },
    };
    })
    .filter((it) => !!it.descricao_item || !!it.numero_pncp || (it.ano_compra != null && it.sequencial_compra != null));
  if (!registros.length) {
    saveMessage.value = semFornecedor > 0
      ? 'Nenhuma fonte com CNPJ de fornecedor homologado. Itens em andamento não entram na cotação.'
      : 'Selecione ao menos um item.';
    return;
  }
  if (semFornecedor > 0) {
    saveMessage.value = `${semFornecedor} fonte(s) ignorada(s) por não ter CNPJ de fornecedor.`;
  }
  const MAX_ITENS_TOTAL = 2000;
  const BATCH_SIZE = 250;
  let enviar = registros;
  if (registros.length > MAX_ITENS_TOTAL) {
    enviar = registros.slice(0, MAX_ITENS_TOTAL);
    saveMessage.value = `Limite de ${MAX_ITENS_TOTAL} itens por operação; gravando os primeiros ${MAX_ITENS_TOTAL}.`;
  }
  isSavingSelecionados.value = true;
  try {
    let totalInseridos = 0;
    for (let i = 0; i < enviar.length; i += BATCH_SIZE) {
      const lote = enviar.slice(i, i + BATCH_SIZE);
      if (itemId.value) {
        const res = await addCotacoesToItemInResearchSession(sessionId, itemId.value, lote);
        totalInseridos += Number(res.cotacoes_inseridas ?? lote.length);
      } else {
        const res = await addItemsToResearchSession(sessionId, lote);
        totalInseridos += Number(res.itens_inseridos ?? lote.length);
      }
    }
    saveMessage.value = itemId.value
      ? `${totalInseridos} cotação(ões) adicionadas ao item #${itemId.value}.`
      : `${totalInseridos} item(ns) adicionados à cotação ${sessionId}.`;
    if (totalInseridos > 0) {
      resultados.value = resultados.value.map((r) => (r.selecionado ? { ...r, selecionado: false } : r));
      if (goToCotacao) {
        if (itemId.value) {
          await router.push(`/pesquisador-pncp/cotacoes/${sessionId}/itens/${itemId.value}`);
        } else {
          await router.push(`/pesquisador-pncp/cotacoes/${sessionId}`);
        }
      }
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

function applyFaixaDefaultsFromItem(it) {
  if (!it) return;
  const src = it?.source || {};
  const base = Number(
    src?.valor_base ?? src?.valorBase ?? src?.preco_base ?? src?.precoBase ?? it?.valor_base ?? null,
  );
  const variacao = Number(
    src?.variacao_percentual ?? src?.variacaoPercentual ?? src?.variacao ?? it?.variacao_percentual ?? null,
  );
  if (Number.isFinite(base) && base > 0) {
    const centavos = Math.round(base * 100);
    filtros.valorBase = (centavos / 100).toFixed(2).replace('.', ',');
  }
  if (
    variacaoGlobalDaSessao.value == null
    && Number.isFinite(variacao)
    && variacao >= 0
  ) {
    filtros.variacao = String(Math.round(variacao));
  }
}

onMounted(async () => {
  carregarStatusBaseLocal();
  const sessionId = Number(cotacaoId.value);
  if (Number.isFinite(sessionId) && sessionId > 0) {
    try {
      const data = await getResearchSession(sessionId);
      const filtrosSessao = (data?.sessao?.filtros && typeof data.sessao.filtros === 'object') ? data.sessao.filtros : {};
      const variacaoGlobal = Number(
        filtrosSessao.variacao_percentual_global ?? filtrosSessao.variacao_global_percentual ?? null,
      );
      variacaoGlobalDaSessao.value = Number.isFinite(variacaoGlobal) && variacaoGlobal >= 0 ? variacaoGlobal : null;
      if (variacaoGlobalDaSessao.value != null) {
        filtros.variacao = String(Math.round(variacaoGlobalDaSessao.value));
      }
      const sentidoRaw = String(filtrosSessao.variacao_sentido_global || '').trim().toLowerCase();
      filtros.variacaoSentido = ['cima', 'baixo', 'ambos'].includes(sentidoRaw) ? sentidoRaw : 'ambos';
      const itens = Array.isArray(data?.itens) ? data.itens : [];
      const target = itemId.value
        ? itens.find((x) => Number(x?.id) === Number(itemId.value))
        : itens.find((x) => {
            const src = x?.source || {};
            return Number.isFinite(Number(src?.valor_base ?? src?.valorBase ?? src?.preco_base ?? src?.precoBase))
              || Number.isFinite(Number(src?.variacao_percentual ?? src?.variacaoPercentual ?? src?.variacao));
          });
      if (itemId.value && target) {
        const descricaoItem = String(target?.descricao_item || '').trim();
        if (descricaoItem) {
          filtros.descricao = descricaoItem;
        }
      }
      applyFaixaDefaultsFromItem(target || null);
    } catch (_) {
      // Faixa padrão é opcional; mantém valores existentes se falhar.
    }
  }
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
.manual-geo-panel {
  margin-top: 10px;
  padding: 12px 14px 10px;
  border: 1px solid #dbe4f0;
  border-radius: 12px;
  background: linear-gradient(165deg, #fbfdff 0%, #f3f7fb 100%);
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.manual-geo-panel__top {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px 14px;
}
.manual-geo-panel__intro {
  flex: 1 1 220px;
  min-width: 0;
}
.manual-geo-panel__kicker {
  margin: 0;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #3d6ea3;
}
.manual-geo-panel__title {
  margin: 4px 0 0;
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.25;
}
.manual-geo-panel__hint {
  margin: 6px 0 0;
  max-width: 520px;
  font-size: 12px;
  color: #64748b;
  line-height: 1.45;
}
.manual-geo-add-link {
  flex-shrink: 0;
  align-self: flex-start;
  border: 0;
  background: transparent;
  padding: 6px 0 0;
  font-size: 12px;
  font-weight: 600;
  color: #2563eb;
  text-decoration: underline;
  text-underline-offset: 3px;
  cursor: pointer;
}
.manual-geo-add-link:hover {
  color: #1d4ed8;
}
.manual-geo-empty {
  font-size: 12px;
  color: #94a3b8;
  font-style: italic;
}
.manual-geo-row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 8px;
}
.manual-geo-row + .manual-geo-row {
  margin-top: 6px;
  padding-top: 8px;
  border-top: 1px solid #e8eef5;
}
.manual-geo-field {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 88px;
}
.manual-geo-field--grow {
  flex: 1 1 200px;
  min-width: 160px;
}
.manual-geo-field--mun {
  min-width: 200px;
  max-width: min(100%, 420px);
}
.manual-geo-mun-hint {
  margin: 0;
  font-size: 11px;
  color: #64748b;
  line-height: 1.35;
}
.manual-geo-mun-search {
  margin-top: 4px;
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #cfd8e3;
  border-radius: 8px;
  background: #fff;
  font-size: 12px;
  padding: 5px 8px;
  color: #0f172a;
  outline: none;
}
.manual-geo-mun-search:focus {
  border-color: #3b6f9e;
  box-shadow: 0 0 0 2px rgba(59, 111, 158, 0.12);
}
.manual-geo-mun-list {
  margin-top: 6px;
  max-height: 200px;
  overflow: auto;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 6px 8px;
  background: #f8fafc;
}
.manual-geo-mun-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 3px 0;
  font-size: 12px;
  color: #0f172a;
  cursor: pointer;
  line-height: 1.3;
}
.manual-geo-mun-item input {
  margin-top: 2px;
  flex-shrink: 0;
}
.manual-geo-field span {
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #64748b;
}
.manual-geo-uf-filter {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-width: 0;
}
.manual-geo-uf-flag {
  width: 30px;
  height: 21px;
  object-fit: cover;
  border-radius: 3px;
  box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.1);
  flex-shrink: 0;
}
.manual-geo-uf-flag--table {
  width: 24px;
  height: 16px;
}
.manual-uf-cell {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  flex-wrap: wrap;
}
.manual-geo-select--uf {
  flex: 1;
  min-width: 0;
}
.manual-geo-select {
  border: 1px solid #cfd8e3;
  border-radius: 8px;
  background: #fff;
  font-size: 13px;
  padding: 6px 8px;
  color: #0f172a;
  width: 100%;
  outline: none;
}
.manual-geo-select:focus {
  border-color: #3b6f9e;
  box-shadow: 0 0 0 2px rgba(59, 111, 158, 0.12);
}
.manual-geo-remove {
  align-self: flex-start;
  margin-top: 20px;
  width: 32px;
  height: 32px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  color: #64748b;
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
}
.manual-geo-remove:hover {
  color: #b91c1c;
  border-color: #fecaca;
}
@media (max-width: 600px) {
  .manual-geo-panel__top {
    flex-direction: column;
    align-items: stretch;
  }
  .manual-geo-add-link {
    width: 100%;
    text-align: center;
    padding-top: 0;
  }
}
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

.manual-add-cotacao-btn--ghost {
  background: #fff;
  color: #1f4e79;
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
.manual-similaridade-tag {
  display: inline-flex;
  align-items: center;
  border: 1px solid #f2dfb7;
  border-radius: 999px;
  background: #fff7e6;
  color: #9a6a10;
  padding: 2px 8px;
  font-size: 10px;
  font-weight: 700;
  white-space: nowrap;
}

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
