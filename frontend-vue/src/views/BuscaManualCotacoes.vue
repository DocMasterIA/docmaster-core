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
        <PriceSourcesPanel
          v-model="fontesHabilitadas"
          :fontes="fontesCatalog"
          :loading="isLoadingFontes"
        />
        <div class="manual-local-db-row">
          <p class="manual-meta">
            Base local (`pncp_researcher_service`):
            <strong>{{ totalItensBaseLocalFmt }}</strong> itens indexados
            <span v-if="detalheBaseLocalPorFonte"> ({{ detalheBaseLocalPorFonte }})</span>.
          </p>
          <button type="button" class="manual-btn-backfill" :disabled="isBackfilling" @click="atualizarBaseLocalAgora">
            {{ isBackfilling ? 'Atualizando base...' : 'Atualizar base local (.db)' }}
          </button>
        </div>
      </section>
      <p v-if="searchError" class="manual-meta manual-meta--error">{{ searchError }}</p>
      <p v-else-if="isSearching" class="manual-meta">Consultando índices locais ({{ fontesBuscaLabel }})…</p>

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
                <th>Fonte</th>
                <th>Cotação</th>
                <th>Quantidade</th>
                <th>Inciso</th>
                <th>UF</th>
                <th>Data</th>
                <th>Valor Unit.</th>
                <th>Faixa Regional do Item</th>
                <th>Confiabilidade IA</th>
                <th>Observação</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in resultadosFiltradosOrdenados" :key="item.id">
                <td class="manual-cell-center">
                  <input type="checkbox" :checked="item.selecionado" @change="toggleSelecionado(item.id)" />
                </td>
                <td class="manual-cell-center">
                  <span class="manual-plat-badge" :class="`manual-plat-badge--${item.plataforma}`">
                    {{ item.plataformaLabel }}
                  </span>
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
                <td class="manual-faixa-cell">
                  <template v-if="faixaRegionalItemDisplay">
                    <div class="manual-faixa-cell__row">
                      <span class="manual-faixa-cell__label">BASE</span>
                      <strong>{{ faixaRegionalItemDisplay.baseFmt }}</strong>
                    </div>
                    <div class="manual-faixa-cell__row">
                      <span class="manual-faixa-cell__label">VAR</span>
                      <strong>{{ faixaRegionalItemDisplay.variacaoFmt }}</strong>
                    </div>
                    <div class="manual-faixa-cell__range">{{ faixaRegionalItemDisplay.rangeFmt }}</div>
                  </template>
                  <span v-else class="manual-meta">—</span>
                </td>
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
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  backfillLocalIndex,
  federatedMarketSearch,
  formatResearchError,
  getResearchSessionResilient,
  getLocalIndexStats,
} from '../services/pncpResearch';
import PriceSourcesPanel from '../components/PriceSourcesPanel.vue';
import {
  federatedItemPlataforma,
  federatedItemProcessoRef,
  isComprasGovPlatform,
  isNotasFiscaisPlatform,
  isTceRsPlatform,
  loadPriceSourcesCatalog,
  mergeFontesWithLocalStats,
  pickDefaultFontes,
  plataformaBadgeShort,
  platformSaveMeta,
} from '../utils/pncpPriceSources';
import {
  formatCotacaoSaveFeedback,
  persistCotacoesToResearchSession,
  shouldClearSavedSelection,
} from '../utils/pncpSaveCotacoes';
import { takeManualSearchPrefill } from '../utils/manualSearchPrefill';
import { MUNICIPIOS_POR_UF } from '../data/brasilMunicipiosPorUf';
import { buildRecortesGeograficosPayload, itemMatchesRecortesGeograficos } from '../utils/recortesGeograficos';
import { canSalvarCotacaoPnCp, displayPnCpUnitario, extractCnpjFornecedorSalvar, formatFaixaResumo, passesPnCpSearchDisplayGate, computeFaixaRegional, pickFornecedorDisplayName, buildFaixaRegionalItemDisplay, resolveRowPlataforma, pnCpRowWithinFaixaRegional } from '../utils/pncpPricing';
import { labelModalidadeFonte } from '../utils/tceModalidade';
import { formatMunicipioUf, resolveMunicipioUf } from '../utils/tceLocalidade';

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
  valorBase: '0,00',
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
let searchGeneration = 0;
const saveMessage = ref('');
const localStats = ref(null);
const fontesCatalog = ref([]);
/** Todas as fontes ready por padrão (PNCP + TCE + Compras.gov…). */
const fontesHabilitadas = ref([]);
const isLoadingFontes = ref(false);

const fontesBuscaLabel = computed(() => {
  const ids = fontesHabilitadas.value?.length ? fontesHabilitadas.value : ['pncp'];
  return ids.map((id) => plataformaBadgeShort(id)).join(' + ');
});
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
  const nums = resultados.value
    .filter((x) => x.selecionado)
    .map((x) => parseMoeda(x.valor))
    .filter((x) => typeof x === 'number');
  if (!nums.length) return 'R$ -';
  return formatCurrency(nums.reduce((a, b) => a + b, 0) / nums.length);
});
/** Volume bruto indexado (PNCP + TCE-RS + …), não só o subconjunto homologado na busca. */
const totalItensBaseLocal = computed(() => {
  const s = localStats.value;
  if (!s) return 0;
  const todas = Number(s.total_itens_todas_fontes);
  if (Number.isFinite(todas) && todas > 0) return todas;
  return Number(s.total_itens || 0);
});
const totalItensBaseLocalFmt = computed(() =>
  totalItensBaseLocal.value.toLocaleString('pt-BR'),
);
const detalheBaseLocalPorFonte = computed(() => {
  const rows = Array.isArray(localStats.value?.por_plataforma)
    ? localStats.value.por_plataforma
    : [];
  const parts = rows
    .map((r) => {
      const n = Number(r?.total_itens || 0);
      if (!Number.isFinite(n) || n <= 0) return null;
      const label = String(r?.label || r?.id || '').trim() || 'fonte';
      return `${label} ${n.toLocaleString('pt-BR')}`;
    })
    .filter(Boolean);
  return parts.length > 1 ? parts.join(' · ') : '';
});
const faixaValorAtiva = computed(() => {
  const base = parseMoeda(filtros.valorBase);
  if (base == null || base <= 0) return '';
  const p = Number.parseFloat(String(filtros.variacao || '0'));
  const perc = Number.isFinite(p) ? Math.max(0, p) : 0;
  const sentido = ['baixo', 'cima', 'ambos'].includes(filtros.variacaoSentido) ? filtros.variacaoSentido : 'ambos';
  return formatFaixaResumo(base, perc, sentido);
});
const faixaRegionalItemDisplay = computed(() => {
  const base = parseMoeda(filtros.valorBase);
  if (base == null || base <= 0) return null;
  const p = Number.parseFloat(String(filtros.variacao || '0'));
  const perc = Number.isFinite(p) ? Math.max(0, p) : 0;
  const sentido = ['baixo', 'cima', 'ambos'].includes(filtros.variacaoSentido) ? filtros.variacaoSentido : 'ambos';
  return buildFaixaRegionalItemDisplay(base, perc, sentido);
});
const resultadosFiltradosOrdenados = computed(() => {
  const base = [...resultados.value];
  const valorBase = parseMoeda(filtros.valorBase);
  const variacao = Number.parseFloat(String(filtros.variacao || '0'));
  const variacaoValida = Number.isFinite(variacao) ? Math.max(0, variacao) : 0;

  let filtrados = base;
  if (valorBase != null && valorBase > 0) {
    const sentido = ['baixo', 'cima', 'ambos'].includes(filtros.variacaoSentido) ? filtros.variacaoSentido : 'ambos';
    const { min, max } = computeFaixaRegional(valorBase, variacaoValida, sentido);
    filtrados = base.filter((item) => {
      const vBruto = item.valorUnitario ?? item.valorTotal ?? parseMoeda(item.valor);
      const v = Number(vBruto);
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

async function carregarFontesPreco() {
  isLoadingFontes.value = true;
  try {
    const catalog = await loadPriceSourcesCatalog();
    fontesCatalog.value = mergeFontesWithLocalStats(catalog, localStats.value);
    // Sempre inicia com todas as fontes ready (união multi-fonte).
    fontesHabilitadas.value = pickDefaultFontes(fontesCatalog.value);
  } catch (_err) {
    fontesCatalog.value = [];
    fontesHabilitadas.value = ['pncp'];
  } finally {
    isLoadingFontes.value = false;
  }
}

async function carregarStatusBaseLocal() {
  try {
    localStats.value = await getLocalIndexStats();
    if (fontesCatalog.value.length) {
      fontesCatalog.value = mergeFontesWithLocalStats(fontesCatalog.value, localStats.value);
    }
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

function faixaPayloadForApi() {
  const valorBase = parseMoeda(filtros.valorBase);
  const variacao = Number.parseFloat(String(filtros.variacao || '0'));
  if (valorBase == null || valorBase <= 0 || !Number.isFinite(variacao) || variacao < 0) {
    return {};
  }
  const sentido = ['baixo', 'cima', 'ambos'].includes(filtros.variacaoSentido) ? filtros.variacaoSentido : 'ambos';
  return {
    valor_base_referencia: valorBase,
    variacao_percentual_referencia: variacao,
    variacao_sentido_referencia: sentido,
  };
}

function mapFederatedItemToRow(it, idx, { termoBuscaEfetivo, termoFallbackUsado, fallbackPorSimilaridadeIa }) {
  const plat = federatedItemPlataforma(it);
  const descricaoLinha = it.descricao_item || it.objeto_resumido || '';
  const similaridadeBackend = Boolean(it?.similaridade_encontrada);
  const similaridadeParcial = similaridadeBackend || isSimilaridadeParcialManual(
    termoBuscaEfetivo,
    descricaoLinha,
  ) || fallbackPorSimilaridadeIa;
  const termoParaConfiabilidade = termoFallbackUsado || termoBuscaEfetivo;
  const conf = confiabilidadeManual(termoParaConfiabilidade, descricaoLinha);
  const processoRef = federatedItemProcessoRef(it);
  return {
    id: `backend-${plat}-${idx}-${processoRef || it.numero_item || idx}`,
    plataforma: plat,
    plataformaLabel: plataformaBadgeShort(plat),
    sourceRaw: it,
    numeroPncp: it.numero_pncp || null,
    processoRef,
    anoCompra: it.ano_compra ?? null,
    sequencialCompra: it.sequencial_compra ?? null,
    numeroItem: it.numero_item ?? null,
    titulo: it.orgao || (
      isTceRsPlatform(plat)
        ? 'Órgão RS (LicitaCon)'
        : isComprasGovPlatform(plat)
          ? 'Órgão (Compras.gov)'
          : 'Órgão não informado'
    ),
    descricao: descricaoLinha || 'Descrição indisponível',
    municipioUfCompacto: formatMunicipioUf(
      { municipio: it.municipio, uf: it.uf, orgao: it.orgao },
      it,
      '-',
    ),
    quantidade: `${it.quantidade || '-'} ${it.unidade_medida || ''}`.trim(),
    quantidadeNum: it.quantidade ?? null,
    unidadeMedida: it.unidade_medida || null,
    inciso: resolveIncisoFromItem(it),
    uf: it.uf || '-',
    municipio: resolveMunicipioUf({ municipio: it.municipio, uf: it.uf, orgao: it.orgao }, it).municipio || null,
    data: it.data_publicacao || it.data_referencia || '-',
    valor: formatCurrency(displayPnCpUnitario({ sourceRaw: it })),
    valorUnitario: displayPnCpUnitario({ sourceRaw: it }),
    valorTotal: it.valor_total ?? null,
    statusIa: (similaridadeParcial && conf === 'Alta') || fallbackPorSimilaridadeIa ? 'Média' : conf,
    modalidadeLabel: (() => {
      const lab = labelModalidadeFonte({ modalidade: it.modalidade, processo_id: processoRef }, it);
      return lab !== 'N/D' ? lab : '';
    })(),
    observacao: isTceRsPlatform(plat)
      ? `TCE-RS · ${(() => {
        const lab = labelModalidadeFonte({ modalidade: it.modalidade, processo_id: processoRef }, it);
        return lab !== 'N/D' ? lab : (it.modalidade || 'LicitaCon');
      })()}${processoRef ? ` · proc. ${processoRef}` : ''}`
      : isComprasGovPlatform(plat)
        ? `Compras.gov · ${it.modalidade || 'Dados Abertos'}${processoRef ? ` · ${processoRef}` : ''}`
      : isNotasFiscaisPlatform(plat)
        ? `Notas Fiscais · Portal da Transparência${processoRef ? ` · ${String(processoRef).replace(/^notas_fiscais:/i, '').split(':')[0]}` : ''}`
      : (it.modalidade || 'PNCP'),
    similaridadeEncontrada: similaridadeParcial,
    selecionado: false,
  };
}

async function buscarNoBackend() {
  if (!filtros.descricao.trim()) return;
  const gen = ++searchGeneration;
  isSearching.value = true;
  searchError.value = '';
  try {
    const codigoModalidade =
      filtros.modalidade && filtros.modalidade !== 'Todas'
        ? (MODALIDADE_TO_CODIGO[filtros.modalidade] ?? null)
        : null;
    const termoBuscaEfetivo = filtros.descricao.trim();
    const geo = geoApiSlice();
    const faixaPayload = faixaPayloadForApi();
    const fontes = fontesHabilitadas.value?.length ? [...fontesHabilitadas.value] : ['pncp'];
    const searchBase = {
      termo_busca: termoBuscaEfetivo,
      ...geo,
      ...faixaPayload,
      codigo_modalidade: codigoModalidade,
      somente_homologados: true,
      max_paginas: 500,
      tamanho_pagina: 200,
      fontes_habilitadas: fontes,
      // Lista ampla dos índices locais (PNCP + TCE) — sem top-3 / pipeline IA.
      lista_completa: true,
    };
    let data = await federatedMarketSearch(searchBase, undefined, {
      timeoutMs: 90000,
      maxAttempts: 2,
    });
    if (gen !== searchGeneration) return;
    let fallbackPorSimilaridadeIa = false;
    let termoFallbackUsado = '';
    if (!data?.ok || !Array.isArray(data?.itens) || data.itens.length === 0) {
      const fallbackTerms = buildSimilarityFallbackTerms(termoBuscaEfetivo);
      for (const term of fallbackTerms) {
        if (gen !== searchGeneration) return;
        const iaFallback = await federatedMarketSearch({
          ...searchBase,
          termo_busca: term,
        }, undefined, {
          timeoutMs: 90000,
          maxAttempts: 2,
        });
        if (iaFallback?.ok && Array.isArray(iaFallback?.itens) && iaFallback.itens.length > 0) {
          data = iaFallback;
          fallbackPorSimilaridadeIa = true;
          termoFallbackUsado = term;
          break;
        }
      }
    }
    if (gen !== searchGeneration) return;
    if (data?.ok && Array.isArray(data.itens)) {
      resultados.value = data.itens
        .filter((it) => passesPnCpSearchDisplayGate({ sourceRaw: it }))
        .map((it, idx) => mapFederatedItemToRow(it, idx, {
          termoBuscaEfetivo,
          termoFallbackUsado,
          fallbackPorSimilaridadeIa,
        }));
    } else {
      resultados.value = [];
    }
  } catch (err) {
    if (gen !== searchGeneration) return;
    searchError.value = `Não foi possível consultar o backend (${formatResearchError(err)}).`;
  } finally {
    if (gen === searchGeneration) {
      isSearching.value = false;
    }
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
    saveMessage.value = `Base PNCP atualizada. Itens PNCP no índice: ${Number(res?.total_itens || 0).toLocaleString('pt-BR')}.`;
    await carregarStatusBaseLocal();
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
  const plat = normalizeText(it?.plataforma || '').toLowerCase();
  if (isTceRsPlatform(plat)) return 'Inciso II';
  if (isComprasGovPlatform(plat)) return 'Inciso I';

  const inciso = normalizeText(it?.inciso_classificacao || it?.incisoClassificacao);
  if (inciso.includes('inciso_i') || inciso === 'inciso-i' || inciso.includes('governament')) return 'Inciso I';
  if (inciso.includes('inciso_ii') || inciso === 'inciso-ii' || inciso.includes('entes')) return 'Inciso II';

  const esferaId = normalizeText(it?.esfera_id || it?.esferaId).toUpperCase();
  const esferaAdm = normalizeText(
    it?.esfera_administrativa || it?.esferaAdministrativa || it?.esfera,
  );
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

function rowSalvavelNaCotacao(row) {
  return canSalvarCotacaoPnCp(row);
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
  const semFornecedor = brutos.filter((r) => !rowSalvavelNaCotacao(r)).length;
  const variacaoSave = Number.parseFloat(String(filtros.variacao || '0'));
  const sentidoSave = ['baixo', 'cima', 'ambos'].includes(filtros.variacaoSentido)
    ? filtros.variacaoSentido
    : 'ambos';
  const faixaAtivaSave = faixaBaseSelecionada != null
    && faixaBaseSelecionada > 0
    && Number.isFinite(variacaoSave)
    && variacaoSave >= 0;
  const foraFaixa = faixaAtivaSave
    ? brutos.filter((r) => !pnCpRowWithinFaixaRegional(r, faixaBaseSelecionada, variacaoSave, sentidoSave))
    : [];
  if (foraFaixa.length) {
    saveMessage.value = `${foraFaixa.length} preço(s) fora da faixa (VAR) — não podem ser salvos.`;
  }
  const registros = brutos
    .filter((r) => rowSalvavelNaCotacao(r))
    .filter((r) => (
      !faixaAtivaSave
      || pnCpRowWithinFaixaRegional(r, faixaBaseSelecionada, variacaoSave, sentidoSave)
    ))
    .map((r) => {
      const raw = (r.sourceRaw && typeof r.sourceRaw === 'object') ? r.sourceRaw : {};
      const cad = (raw.fornecedor_cadastro && typeof raw.fornecedor_cadastro === 'object')
        ? raw.fornecedor_cadastro
        : {};
      const plat = resolveRowPlataforma(r);
      const saveMeta = platformSaveMeta(plat, {
        inciso_classificacao: raw.inciso_classificacao || raw.incisoClassificacao || null,
        esfera_administrativa: raw.esfera_administrativa || raw.esferaAdministrativa || raw.esfera || null,
        fonte: raw.fonte || null,
      });
      const incisoSave = saveMeta.inciso_classificacao;
      const esferaSave = saveMeta.esfera_administrativa;
      const fonteSave = saveMeta.fonte;
      return {
      numero_pncp: toNullableText(r.numeroPncp),
      plataforma: plat,
      plataforma_item_id: toNullableText(raw.plataforma_item_id || r.processoRef),
      processo_id: toNullableText(raw.processo_id || r.processoRef),
      url_origem: toNullableText(raw.url_origem || raw.link_licitacon_cidadao),
      ano_compra: r.anoCompra,
      sequencial_compra: r.sequencialCompra,
      numero_item: toNullableText(r.numeroItem),
      descricao_item: toNullableText(r.descricao),
      quantidade: r.quantidadeNum,
      unidade_medida: toNullableText(r.unidadeMedida),
      valor_unitario: r.valorUnitario ?? parseMoeda(r.valor),
      valor_total: r.valorTotal,
      orgao: toNullableText(r.titulo),
      municipio: (() => {
        const resolved = resolveMunicipioUf(
          {
            municipio: r.municipio || raw.municipio,
            uf: r.uf || raw.uf,
            orgao: r.titulo || raw.orgao,
          },
          raw,
        );
        return toNullableText(resolved.municipio);
      })(),
      uf: toNullableText(r.uf),
      modalidade: (() => {
        const resolved = labelModalidadeFonte(
          {
            modalidade: raw.modalidade || raw.modalidadeNome || raw.modalidade_nome || r.modalidadeLabel,
            processo_id: raw.processo_id || r.processoRef,
            plataforma_item_id: raw.plataforma_item_id,
          },
          raw,
        );
        return toNullableText(resolved !== 'N/D' ? resolved : (raw.modalidade || raw.modalidadeNome || raw.modalidade_nome));
      })(),
      // Mantém metadados úteis sem inflar demais o JSON.
      origem: 'busca_manual',
      observacao: toNullableText(r.observacao),
      data_publicacao: (() => {
        const candidates = [
          r.data,
          raw.data_publicacao,
          raw.data_referencia,
          raw.dataPublicacaoPncp,
        ];
        for (const c of candidates) {
          const t = toNullableText(c);
          if (t) return t.slice(0, 64);
        }
        return null;
      })(),
      material_servico: toNullableText(r.sourceRaw?.material_servico),
      fornecedor: toNullableText(pickFornecedorDisplayName(r)),
      cnpj_fornecedor: toNullableText(extractCnpjFornecedorSalvar(r) || r.cnpjFornecedor || raw.cnpj_fornecedor),
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
      inciso_classificacao: incisoSave,
      esfera_administrativa: esferaSave,
      esfera: esferaSave,
      fonte: fonteSave,
      source: {
        ...raw,
        plataforma: plat,
        url_origem: raw.url_origem || raw.link_licitacon_cidadao || null,
        inciso_classificacao: incisoSave || raw.inciso_classificacao || null,
        esfera: esferaSave || raw.esfera || null,
        esfera_administrativa: esferaSave || raw.esfera_administrativa || null,
        fonte: fonteSave || raw.fonte || null,
      },
    };
    })
    .filter((it) =>
      !!it.descricao_item
      || !!it.numero_pncp
      || !!it.plataforma_item_id
      || !!it.processo_id
      || (it.ano_compra != null && it.sequencial_compra != null),
    );
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
    const stats = await persistCotacoesToResearchSession(sessionId, enviar, {
      routeItemId: itemId.value,
      batchSize: BATCH_SIZE,
    });
    saveMessage.value = formatCotacaoSaveFeedback(stats, {
      routeItemId: itemId.value,
      semFornecedorUi: semFornecedor,
    });
    if (shouldClearSavedSelection(stats, enviar.length)) {
      resultados.value = resultados.value.map((r) => (r.selecionado ? { ...r, selecionado: false } : r));
    }
    if (goToCotacao && (stats.inseridas > 0 || stats.itensNovos > 0)) {
      if (itemId.value) {
        await router.push(`/pesquisador-pncp/cotacoes/${sessionId}/itens/${itemId.value}`);
      } else {
        await router.push(`/pesquisador-pncp/cotacoes/${sessionId}`);
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
  const faixa = src?.faixa_regional || src?.faixaRegional || {};
  const base = Number(
    faixa?.valor_base
    ?? faixa?.valorBase
    ?? src?.valor_base
    ?? src?.valorBase
    ?? src?.preco_base
    ?? src?.precoBase
    ?? it?.valor_base
    ?? null,
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

function applyPrefillPayload(prefill) {
  if (!prefill || typeof prefill !== 'object') return;
  const descricao = String(prefill.descricao || '').trim();
  if (descricao) filtros.descricao = descricao;
  const base = Number(prefill.valor_base);
  if (Number.isFinite(base) && base > 0) {
    const centavos = Math.round(base * 100);
    filtros.valorBase = (centavos / 100).toFixed(2).replace('.', ',');
  }
  const variacao = Number(prefill.variacao_percentual);
  if (Number.isFinite(variacao) && variacao >= 0) {
    filtros.variacao = String(Math.round(variacao));
  }
  if (prefill.source && typeof prefill.source === 'object') {
    applyFaixaDefaultsFromItem({ source: prefill.source, valor_base: prefill.valor_base });
  }
}

let hydrateGeneration = 0;

function applySessionHydrate(data, iid) {
  const filtrosSessao = (data?.sessao?.filtros && typeof data.sessao.filtros === 'object')
    ? data.sessao.filtros
    : {};
  const variacaoGlobal = Number(
    filtrosSessao.variacao_percentual_global ?? filtrosSessao.variacao_global_percentual ?? null,
  );
  variacaoGlobalDaSessao.value = Number.isFinite(variacaoGlobal) && variacaoGlobal >= 0
    ? variacaoGlobal
    : null;
  if (variacaoGlobalDaSessao.value != null) {
    filtros.variacao = String(Math.round(variacaoGlobalDaSessao.value));
  }
  const sentidoRaw = String(filtrosSessao.variacao_sentido_global || '').trim().toLowerCase();
  filtros.variacaoSentido = ['cima', 'baixo', 'ambos'].includes(sentidoRaw) ? sentidoRaw : 'ambos';
  const itens = Array.isArray(data?.itens) ? data.itens : [];
  const target = iid
    ? itens.find((x) => Number(x?.id) === Number(iid))
    : itens.find((x) => {
      const src = x?.source || {};
      return Number.isFinite(Number(src?.valor_base ?? src?.valorBase ?? src?.preco_base ?? src?.precoBase))
        || Number.isFinite(Number(src?.variacao_percentual ?? src?.variacaoPercentual ?? src?.variacao));
    });
  if (iid && target) {
    const descricaoItem = String(target?.descricao_item || target?.descricao || '').trim();
    if (descricaoItem) filtros.descricao = descricaoItem;
  }
  applyFaixaDefaultsFromItem(target || null);
}

async function hydrateManualFromRoute({ autoSearch = true } = {}) {
  const gen = ++hydrateGeneration;
  const sessionId = Number(cotacaoId.value);
  const iid = itemId.value;

  // 1) Prefill síncrono — descrição/faixa na UI antes de qualquer await.
  if (iid) {
    applyPrefillPayload(takeManualSearchPrefill(cotacaoId.value, iid));
  }
  const qDesc = String(route.query.descricao || '').trim();
  if (qDesc && !filtros.descricao) filtros.descricao = qDesc;
  const hadDescricaoEarly = Boolean(filtros.descricao.trim());

  // 2) Stats + fontes (ainda necessários para fontes_habilitadas no auto-search).
  await Promise.all([carregarStatusBaseLocal(), carregarFontesPreco()]);
  if (gen !== hydrateGeneration) return;

  // 3) Sessão: se já há descrição do prefill, não bloqueia a busca.
  const sessionPromise = (Number.isFinite(sessionId) && sessionId > 0)
    ? getResearchSessionResilient(sessionId, { maxAttempts: 3, timeoutMs: 120_000 })
      .then((data) => {
        if (gen !== hydrateGeneration) return;
        applySessionHydrate(data, iid);
      })
      .catch((err) => {
        if (gen !== hydrateGeneration) return;
        if (!filtros.descricao.trim()) {
          searchError.value = `Não foi possível carregar o item da cotação (${formatResearchError(err)}).`;
        }
      })
    : Promise.resolve();

  if (!hadDescricaoEarly) {
    await sessionPromise;
    if (gen !== hydrateGeneration) return;
  } else {
    void sessionPromise;
  }

  if (iid && !filtros.descricao.trim()) {
    searchError.value = searchError.value
      || 'Item sem descrição carregada. Volte ao detalhe do item e abra a busca manual de novo.';
  }

  if (autoSearch && filtros.descricao.trim()) {
    await buscarNoBackend();
  }
}

onMounted(() => {
  hydrateManualFromRoute({ autoSearch: true });
});

watch(
  () => [String(route.params.cotacaoId || ''), String(route.query.itemId || '')],
  ([cot, iid], [prevCot, prevIid]) => {
    if (cot === prevCot && iid === prevIid) return;
    hydrateManualFromRoute({ autoSearch: true });
  },
);
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

.manual-faixa-cell {
  min-width: 118px;
  font-size: 11px;
  line-height: 1.35;
  color: #334155;
}
.manual-faixa-cell__row {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-bottom: 2px;
}
.manual-faixa-cell__label {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: #64748b;
}
.manual-faixa-cell__range {
  margin-top: 2px;
  font-size: 10px;
  color: #0f4c81;
  font-weight: 600;
}
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

.manual-plat-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.02em;
  border: 1px solid #dbe4f0;
  background: #f4f8fc;
  color: #2f557d;
  white-space: nowrap;
}
.manual-plat-badge--tce_rs {
  background: #eef6ff;
  border-color: #c5daf5;
  color: #1e4f8a;
}
.manual-plat-badge--compras_gov {
  background: #f3f0ff;
  border-color: #d4c8f5;
  color: #4c3d8a;
}
.manual-plat-badge--notas_fiscais {
  background: #fffbeb;
  border-color: #fcd34d;
  color: #92400e;
}
.manual-plat-badge--pncp {
  background: #eef8f2;
  border-color: #c8e6d4;
  color: #1f6b45;
}
.manual-ia-dot--high { background: #e7f6ee; border-color: #cfe9da; color: #1f7a53; }
.manual-ia-dot--mid { background: #fff6e6; border-color: #f0dfb3; color: #9a6a00; }
.manual-ia-dot--low { background: #fff0f0; border-color: #f0d0d0; color: #b54747; }
</style>
