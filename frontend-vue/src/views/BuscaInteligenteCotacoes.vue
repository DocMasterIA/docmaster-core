<template>
  <section class="gov-page">
    <header class="gov-page__header">
      <div class="bia-header-row">
        <div>
          <p class="bia-kicker">DocMaster IA • Pesquisa de Precos</p>
          <h1 class="gov-page__title">Busca Inteligente de Cotacoes</h1>
          <p class="gov-page__subtitle">
            Interface compacta para analise, comparacao e selecao das cotacoes mais consistentes.
          </p>
        </div>
        <RouterLink :to="`/pesquisador-pncp/cotacoes/${cotacaoId}`" class="bia-back-btn">
          <i class="fa-solid fa-arrow-left" aria-hidden="true"></i>
          Voltar aos itens da cotacao
        </RouterLink>
      </div>
    </header>

    <div class="gov-surface gov-page__content">
      <section class="bia-summary">
        <div class="bia-summary-card">
          <span>Resultados</span>
          <strong>{{ displayedRows.length }}</strong>
        </div>
        <div class="bia-summary-card">
          <span>Media</span>
          <strong>{{ mediaValor }}</strong>
        </div>
        <div class="bia-summary-card bia-summary-card--highlight">
          <span>Selecionados</span>
          <strong>{{ totalSelecionados }}</strong>
        </div>
      </section>

      <section class="bia-filters">
        <div class="bia-geo-panel">
          <div class="bia-geo-panel__top">
            <div class="bia-geo-panel__intro">
              <p class="bia-geo-panel__kicker">Busca geográfica</p>
              <h2 class="bia-geo-panel__title">Escolher cidade</h2>
              <p class="bia-geo-panel__hint">
                Opcional: escolha a UF e marque várias cidades na lista (uma linha por estado). Sem nenhuma cidade
                marcada, vale a UF inteira. Sem linhas, a pesquisa segue a UF do item ou cobertura ampla.
              </p>
            </div>
            <div class="bia-geo-panel__actions">
              <button
                type="button"
                class="bia-geo-search-btn"
                :disabled="!itemContext?.descricao_item && allItemContexts.length === 0"
                @click="applyFilters"
              >
                <i class="fa-solid fa-map-location-dot" aria-hidden="true"></i>
                {{ pesquisaUfBotaoLabel }}
              </button>
              <button type="button" class="bia-geo-add-link" @click="addLinhaCidade">+ Adicionar UF</button>
            </div>
          </div>
          <div v-if="!filtros.cidades.length" class="bia-geo-empty">Nenhum recorte por cidade/UF definido.</div>
          <div v-for="(linha, idx) in filtros.cidades" :key="linha._id" class="bia-geo-row">
            <label class="bia-geo-field">
              <span>UF</span>
              <div class="bia-geo-uf-filter">
                <img
                  v-if="ufBandeiraUrl(linha.uf)"
                  :src="ufBandeiraUrl(linha.uf)"
                  :alt="`Bandeira ${linha.uf}`"
                  class="bia-geo-uf-flag"
                />
                <select v-model="linha.uf" class="bia-geo-select bia-geo-select--uf" @change="onUfLinhaCidadeChange(linha)">
                  <option value="">—</option>
                  <option v-for="u in ufOptions" :key="u.code" :value="u.code">{{ u.code }}</option>
                </select>
              </div>
            </label>
            <div class="bia-geo-field bia-geo-field--grow bia-geo-field--mun">
              <span>Cidades</span>
              <p v-if="!linha.uf" class="bia-geo-mun-hint">Escolha a UF para listar os municípios.</p>
              <template v-else>
                <input
                  v-model="linha.filtroMun"
                  type="search"
                  class="bia-geo-mun-search"
                  placeholder="Filtrar cidades…"
                  autocomplete="off"
                />
                <p class="bia-geo-mun-hint">
                  Marque quantas quiser; nenhuma marcada = inclui a <strong>UF inteira</strong>.
                </p>
                <div class="bia-geo-mun-list" role="group" :aria-label="`Cidades ${linha.uf}`">
                  <label v-for="m in municipiosListaUfFiltrada(linha)" :key="m" class="bia-geo-mun-item">
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
            <button type="button" class="bia-geo-remove" title="Remover esta linha" @click="removeLinhaCidade(idx)">×</button>
          </div>
        </div>
      </section>
      <p v-if="isAutoSearchingAll" class="bia-meta">
        Busca automática em andamento: item {{ autoSearchProgress.done }} de {{ autoSearchProgress.total }}...
      </p>
      <p v-else-if="autoSearchProgress.total > 0" class="bia-meta">
        Busca automática concluída: {{ autoSearchProgress.done }} item(ns) processado(s).
      </p>
      <p v-if="itemContext" class="bia-meta">
        Item de referência: <strong>{{ itemContext.descricao_item }}</strong>
        <span v-if="itemContext.quantidade != null"> • Qtd {{ itemContext.quantidade }}</span>
        <span v-if="itemContext.unidade_medida"> {{ itemContext.unidade_medida }}</span>
      </p>
      <p v-if="searchError" class="bia-meta bia-meta--error">{{ searchError }}</p>
      <p v-else-if="isSearching" class="bia-meta">Consultando backend PNCP...</p>

      <section class="bia-table-shell">
        <div class="bia-table-head">
          <div class="bia-table-head__pills">
            <span class="bia-pill bia-pill--ok">{{ displayedRows.length }} resultados</span>
            <span class="bia-pill">{{ totalUfs }} UFs</span>
          </div>
          <div class="bia-table-head__actions">
            <RouterLink
              :to="`/pesquisador-pncp/cotacoes/${cotacaoId}`"
              class="bia-add-cotacao-btn bia-add-cotacao-btn--ghost"
            >
              Ir para cotação
            </RouterLink>
            <button
              type="button"
              class="bia-add-cotacao-btn bia-add-cotacao-btn--ghost"
              :disabled="displayedRows.length === 0"
              @click="toggleSelecionarTop3"
            >
              {{ bulkSelectLabel }}
            </button>
            <button
              type="button"
              class="bia-add-cotacao-btn"
              :disabled="isSavingSelecionados || totalSelecionados === 0"
              @click="adicionarSelecionadosNaCotacao"
            >
              {{ isSavingSelecionados ? 'Salvando...' : (itemId ? '+ Adicionar cotações ao item' : '+ Adicionar itens na cotação') }}
            </button>
          </div>
        </div>
        <p v-if="saveMessage" class="bia-meta">{{ saveMessage }}</p>

        <div class="bia-groups">
          <article v-for="group in groupedRows" :key="group.key" class="bia-group-card">
            <header class="bia-group-head">
              <div>
                <h3 class="bia-group-title">{{ group.label }}</h3>
                <p class="bia-meta">
                  {{ group.rows.length }} cotações sugeridas para este item
                  <span v-if="group.backendItensCount != null && group.backendItensCount !== group.rows.length">
                    (IA retornou {{ group.backendItensCount }})
                  </span>
                </p>
              </div>
              <button
                type="button"
                class="bia-add-cotacao-btn bia-add-cotacao-btn--ghost"
                :disabled="group.rows.length === 0"
                @click="toggleSelecionarGrupo(group)"
              >
                {{ group.allSelected ? 'Desmarcar bloco' : 'Selecionar bloco' }}
              </button>
            </header>
            <div class="bia-table-scroll">
              <table class="bia-table">
                <thead>
                  <tr>
                    <th>Seleção</th>
                    <th>Cotação</th>
                    <th>Esfera</th>
                    <th>Inciso</th>
                    <th>Quantidade</th>
                    <th>UF</th>
                    <th>Data</th>
                    <th>Valor Unit.</th>
                    <th>Confiabilidade IA</th>
                    <th>Risco</th>
                    <th>Score</th>
                    <th>Cotação usada</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in group.rows" :key="row.id">
                    <td class="bia-cell-center">
                      <input type="checkbox" :checked="row.selecionado" @change="toggleSelecionado(row.id)" />
                    </td>
                    <td>
                      <div class="bia-main">{{ row.titulo }}</div>
                      <div v-if="row.interpretacaoIa" class="bia-ia-hint" title="Leitura auxiliar gerada por IA">
                        <strong>IA:</strong> {{ row.interpretacaoIa }}
                      </div>
                      <div class="bia-sub">
                        <span class="bia-meta-token">{{ row.orgao }}</span>
                        <span v-if="row.cidade && row.cidade !== '-'" class="bia-meta-sep">·</span>
                        <span v-if="row.cidade && row.cidade !== '-'">{{ row.cidade }}</span>
                      </div>
                      <div class="bia-sub">
                        {{ row.modalidade }} • {{ row.status }} • {{ row.normalizado }}
                      </div>
                      <div v-if="row.similaridadeEncontrada" class="bia-sub">
                        <span class="bia-badge bia-badge--warn">Similaridade parcial encontrada</span>
                      </div>
                    </td>
                    <td class="bia-cell-center">
                      <span class="bia-badge">{{ labelEsfera(row.esferaAdministrativa) }}</span>
                    </td>
                    <td class="bia-cell-center">
                      <span class="bia-badge bia-badge--ok">{{ labelInciso(row.incisoClassificacao) }}</span>
                    </td>
                    <td>{{ row.qtd }}</td>
                    <td class="bia-cell-center">
                      <div class="bia-uf-cell">
                        <img
                          v-if="ufBandeiraUrl(row.uf)"
                          :src="ufBandeiraUrl(row.uf)"
                          :alt="`UF ${row.uf}`"
                          class="bia-geo-uf-flag bia-geo-uf-flag--table"
                        />
                        <span>{{ row.uf }}</span>
                      </div>
                    </td>
                    <td class="bia-cell-center">{{ row.data }}</td>
                    <td class="bia-bold">{{ row.valor }}</td>
                    <td class="bia-cell-center">
                      <span class="bia-badge" :class="confiabilidadeClass(row.confiabilidade)">
                        {{ row.confiabilidade }}
                      </span>
                    </td>
                    <td class="bia-cell-center">
                      <span class="bia-badge" :class="riscoClass(row.risco)">
                        {{ row.risco }}
                      </span>
                    </td>
                    <td class="bia-cell-center">{{ formatScorePercent(row.score) }}</td>
                    <td>{{ row.processo }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </article>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  addCotacoesToItemInResearchSession,
  addItemsToResearchSession,
  getResearchSession,
  intelligentMarketSearch,
} from '../services/pncpResearch';
import { MUNICIPIOS_POR_UF } from '../data/brasilMunicipiosPorUf';
import { buildRecortesGeograficosPayload } from '../utils/recortesGeograficos';

const route = useRoute();
const router = useRouter();
const cotacaoId = computed(() => route.params.cotacaoId || 'CT-2026-00421');
const itemId = computed(() => {
  const n = Number(route.query.itemId);
  return Number.isFinite(n) && n > 0 ? n : null;
});
const autostart = computed(() => String(route.query.autostart || '').trim() === '1');

const filtros = reactive({
  descricao: '',
  /** @type {Array<{ _id: string, uf: string, municipios: string[], filtroMun: string }>} */
  cidades: [],
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

const pesquisaUfBotaoLabel = computed(() => {
  const n = buildRecortesGeograficosPayload(filtros.cidades).length;
  if (n > 1) return `Pesquisar (${n} trechos: cidades ou UF inteira)`;
  if (n === 1) return 'Pesquisar (1 trecho geográfico)';
  return 'Fazer pesquisa (recorte do item)';
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
  { code: 'AC', name: 'Acre' },
  { code: 'AL', name: 'Alagoas' },
  { code: 'AP', name: 'Amapa' },
  { code: 'AM', name: 'Amazonas' },
  { code: 'BA', name: 'Bahia' },
  { code: 'CE', name: 'Ceara' },
  { code: 'DF', name: 'Distrito Federal' },
  { code: 'ES', name: 'Espirito Santo' },
  { code: 'GO', name: 'Goias' },
  { code: 'MA', name: 'Maranhao' },
  { code: 'MT', name: 'Mato Grosso' },
  { code: 'MS', name: 'Mato Grosso do Sul' },
  { code: 'MG', name: 'Minas Gerais' },
  { code: 'PA', name: 'Para' },
  { code: 'PB', name: 'Paraiba' },
  { code: 'PR', name: 'Parana' },
  { code: 'PE', name: 'Pernambuco' },
  { code: 'PI', name: 'Piaui' },
  { code: 'RJ', name: 'Rio de Janeiro' },
  { code: 'RN', name: 'Rio Grande do Norte' },
  { code: 'RS', name: 'Rio Grande do Sul' },
  { code: 'RO', name: 'Rondonia' },
  { code: 'RR', name: 'Roraima' },
  { code: 'SC', name: 'Santa Catarina' },
  { code: 'SP', name: 'Sao Paulo' },
  { code: 'SE', name: 'Sergipe' },
  { code: 'TO', name: 'Tocantins' },
].map((uf) => ({ ...uf, flag: UF_FLAGS[uf.code] }));

function ufBandeiraUrl(code) {
  const k = String(code || '').trim().toUpperCase();
  return UF_FLAGS[k] || '';
}

const rows = ref([]);
const isSearching = ref(false);
/** Conta chamadas HTTP de busca em voo (várias sequenciais ou reinício). */
const activeSearchOps = ref(0);
const searchGeneration = ref(0);
let searchAbortController = null;

function beginNewSearchSession() {
  try {
    searchAbortController?.abort();
  } catch (_) {
    /* ignore */
  }
  searchAbortController = new AbortController();
  searchGeneration.value += 1;
  return { generation: searchGeneration.value, signal: searchAbortController.signal };
}

function isAbortError(err) {
  const name = String(err?.name || '');
  const msg = String(err?.message || '');
  return name === 'AbortError' || /aborted|abort|canceled|cancelled/i.test(msg);
}

const searchError = ref('');
const saveMessage = ref('');
const isSavingSelecionados = ref(false);
const itemContext = ref(null);
const allItemContexts = ref([]);
const variacaoPercentualGlobal = ref(null);
const variacaoSentidoGlobal = ref('ambos');
const isAutoSearchingAll = ref(false);
const autoSearchProgress = ref({ done: 0, total: 0 });
const totalSelecionados = computed(() => displayedRows.value.filter((x) => x.selecionado).length);
const allDisplayedSelecionados = computed(
  () => displayedRows.value.length > 0 && displayedRows.value.every((x) => x.selecionado),
);
const bulkSelectLabel = computed(() => {
  const n = displayedRows.value.length;
  if (n <= 0) return 'Selecionar os 3';
  return allDisplayedSelecionados.value ? `Desmarcar os ${n}` : `Selecionar os ${n}`;
});
const totalUfs = computed(() => new Set(displayedRows.value.map((x) => x.uf).filter(Boolean)).size);
const mediaValor = computed(() => {
  const nums = displayedRows.value.map((x) => parseMoeda(x.valor)).filter((x) => typeof x === 'number');
  if (!nums.length) return 'R$ -';
  const media = nums.reduce((a, b) => a + b, 0) / nums.length;
  return formatCurrency(media);
});
function confiabilidadeClass(value) {
  if (value === 'Alta') return 'bia-badge--conf-high';
  if (value === 'Media' || value === 'Média') return 'bia-badge--conf-mid';
  if (value === 'Baixa') return 'bia-badge--conf-low';
  return '';
}

function riscoClass(value) {
  if (value === 'Baixo') return 'bia-badge--risk-low';
  if (value === 'Medio' || value === 'Médio') return 'bia-badge--risk-mid';
  if (value === 'Alto') return 'bia-badge--risk-high';
  return '';
}

const displayedRows = computed(() => {
  const base = [...rows.value];
  const filtrados = base;
  // Ordena sempre por score decrescente e, em seguida, por valor unitário crescente.
  filtrados.sort((a, b) => {
    const sa = Number(a.score ?? 0);
    const sb = Number(b.score ?? 0);
    if (sa !== sb) return sb - sa;
    const va = Number(a.valorUnitario ?? a.valorTotal ?? parseMoeda(a.valor));
    const vb = Number(b.valorUnitario ?? b.valorTotal ?? parseMoeda(b.valor));
    const av = Number.isFinite(va) ? va : Number.POSITIVE_INFINITY;
    const bv = Number.isFinite(vb) ? vb : Number.POSITIVE_INFINITY;
    return av - bv;
  });
  return filtrados;
});

const groupedRows = computed(() => {
  const map = new Map();
  for (const row of displayedRows.value) {
    const key = Number.isFinite(Number(row.itemId)) ? `item-${row.itemId}` : `legacy-${row.itemRefLabel || '-'}`;
    if (!map.has(key)) {
      map.set(key, {
        key,
        itemId: row.itemId ?? null,
        label: row.itemRefLabel || `Item ${row.itemId ?? '-'}`,
        rows: [],
        allSelected: false,
        backendItensCount: null,
      });
    }
    map.get(key).rows.push(row);
    if (Number.isFinite(Number(row.backendItensCount))) {
      map.get(key).backendItensCount = Number(row.backendItensCount);
    }
  }
  const groups = [...map.values()];
  for (const g of groups) {
    g.allSelected = g.rows.length > 0 && g.rows.every((x) => x.selecionado);
  }
  groups.sort((a, b) => String(a.label).localeCompare(String(b.label), 'pt-BR'));
  return groups;
});

async function applyFilters() {
  const { generation, signal } = beginNewSearchSession();
  searchError.value = '';

  // Fluxo item único (abertura por itemId)
  if (String(itemContext.value?.descricao_item || '').trim()) {
    if (Number(itemContext.value?.total_cotacoes_item || 0) >= 3) {
      searchError.value = 'Item já está completo (3+ preços). A busca automática é aplicada apenas em itens incompletos.';
      return;
    }
    rows.value = [];
    return runSearchWithContext({
      descricao: itemContext.value?.descricao_item || '',
      context: itemContext.value,
      append: false,
      generation,
      signal,
    });
  }

  // Fluxo cotação completa: reaplica busca para todos os itens.
  const pendentes = allItemContexts.value.filter((ctx) => Number(ctx?.total_cotacoes_item || 0) < 3);
  if (!pendentes.length) {
    searchError.value = 'Todos os itens já estão completos (3+ preços).';
    return;
  }
  rows.value = [];
  isAutoSearchingAll.value = true;
  autoSearchProgress.value = { done: 0, total: pendentes.length };
  for (const ctx of pendentes) {
    if (generation !== searchGeneration.value) {
      isAutoSearchingAll.value = false;
      return;
    }
    await runSearchWithContext({
      descricao: ctx.descricao_item,
      context: ctx,
      append: true,
      generation,
      signal,
    });
    if (generation !== searchGeneration.value) {
      isAutoSearchingAll.value = false;
      return;
    }
    autoSearchProgress.value.done += 1;
  }
  if (generation !== searchGeneration.value) {
    isAutoSearchingAll.value = false;
    return;
  }
  isAutoSearchingAll.value = false;
  if (!rows.value.length) {
    searchError.value = 'Nenhuma cotação aderente encontrada para os itens da cotação nas cidades/UF definidas.';
  }
}

function buildContextFromItem(it) {
  const src = it?.source || {};
  const faixa = src?.faixa_regional || src?.faixaRegional || {};
  const fontes = it?.fontes_contagem || {};
  const totalCotacoesItem = Number(fontes.governamentais || 0)
    + Number(fontes.entesPublicos || 0)
    + Number(fontes.dominioAmplo || 0)
    + Number(fontes.cotacaoDireta || 0)
    + Number(fontes.notasFiscais || 0);
  const valorBaseRef = parseNumericRef(
    src?.valor_base,
    src?.valorBase,
    src?.preco_base,
    src?.precoBase,
    faixa?.valor_base,
    faixa?.valorBase,
  );
  let variacaoRef = parseNumericRef(
    src?.variacao_percentual,
    src?.variacaoPercentual,
    src?.variacao,
    faixa?.variacao_percentual,
    faixa?.variacaoPercentual,
    faixa?.variacao,
  );
  if (Number.isFinite(Number(variacaoPercentualGlobal.value)) && Number(variacaoPercentualGlobal.value) >= 0) {
    variacaoRef = Number(variacaoPercentualGlobal.value);
  }
  // Faixa de preço só quando há valor base explícito (source/faixa/sessão) — não usar valor_unitario do item.
  if (
    (variacaoRef === null || !Number.isFinite(variacaoRef))
    && valorBaseRef != null
    && Number.isFinite(valorBaseRef)
    && Number.isFinite(Number(variacaoPercentualGlobal.value))
  ) {
    variacaoRef = Number(variacaoPercentualGlobal.value);
  }
  const sentidoRaw = String(variacaoSentidoGlobal.value || 'ambos').trim().toLowerCase();
  const sentidoRef = ['cima', 'baixo', 'ambos'].includes(sentidoRaw) ? sentidoRaw : 'ambos';
  const fator = Number.isFinite(Number(variacaoRef)) ? Math.max(0, Number(variacaoRef)) / 100 : null;
  let valorMinRef = null;
  let valorMaxRef = null;
  if (valorBaseRef != null && Number.isFinite(Number(valorBaseRef)) && fator != null) {
    const vb = Number(valorBaseRef);
    if (sentidoRef === 'baixo') {
      valorMinRef = Math.max(0, vb * (1 - fator));
      valorMaxRef = vb;
    } else if (sentidoRef === 'cima') {
      valorMinRef = vb;
      valorMaxRef = vb * (1 + fator);
    } else {
      valorMinRef = Math.max(0, vb * (1 - fator));
      valorMaxRef = vb * (1 + fator);
    }
  }
  return {
    id: it.id,
    descricao_item: String(it?.descricao_item || '').trim(),
    quantidade: it?.quantidade ?? null,
    unidade_medida: it?.unidade_medida || null,
    valor_base_referencia: valorBaseRef,
    variacao_percentual_referencia: variacaoRef,
    variacao_sentido_referencia: sentidoRef,
    valor_min_referencia: valorMinRef,
    valor_max_referencia: valorMaxRef,
    uf_padrao: String(it?.uf || '').trim().toUpperCase() || null,
    total_cotacoes_item: totalCotacoesItem,
  };
}

function parseNumericRef(...vals) {
  for (const v of vals) {
    if (v === null || v === undefined) continue;
    if (typeof v === 'number' && Number.isFinite(v)) return v;
    const raw = String(v).trim();
    if (!raw) continue;
    const cleaned = raw
      .replace(/\s+/g, '')
      .replace(/[R$r$\u00A0]/g, '')
      .replace(/%/g, '')
      .replace(/\./g, '')
      .replace(',', '.');
    const n = Number(cleaned);
    if (Number.isFinite(n)) return n;
  }
  return null;
}

async function runSearchWithContext({
  descricao,
  context = null,
  append = false,
  generation = null,
  signal = undefined,
} = {}) {
  if (!String(descricao || '').trim()) return;
  activeSearchOps.value += 1;
  isSearching.value = true;
  if (!append) searchError.value = '';
  try {
    const recortes = buildRecortesGeograficosPayload(filtros.cidades);
    const basePayload = {
      somente_homologados: true,
      termo_busca: String(descricao).trim(),
      codigo_modalidade: null,
      max_paginas: 500,
      tamanho_pagina: 200,
      quantidade_referencia: context?.quantidade ?? null,
      unidade_medida_referencia: context?.unidade_medida ?? null,
      valor_base_referencia: context?.valor_base_referencia ?? null,
      variacao_percentual_referencia: context?.variacao_percentual_referencia ?? null,
      variacao_sentido_referencia: context?.variacao_sentido_referencia ?? null,
      valor_min_referencia: context?.valor_min_referencia ?? null,
      valor_max_referencia: context?.valor_max_referencia ?? null,
    };

    const aggregated = [];

    function rowDedupeKey(row) {
      const pncp = String(row.numeroPncp || '').trim();
      const nitem = String(row.numeroItem ?? '').trim();
      const price = row.valorUnitario ?? row.valorTotal ?? parseMoeda(row.valor);
      return [
        String(row.itemId || ''),
        pncp || 'no-pncp',
        nitem || 'no-item',
        String(row.sequencialCompra ?? ''),
        String(price ?? ''),
        String(row.orgao || '').toLowerCase(),
      ].join('|');
    }

    function sortRowsByScore(rows) {
      return [...rows].sort((a, b) => {
        const sa = Number(a.score ?? 0);
        const sb = Number(b.score ?? 0);
        if (sa !== sb) return sb - sa;
        const va = Number(a.valorUnitario ?? a.valorTotal ?? parseMoeda(a.valor));
        const vb = Number(b.valorUnitario ?? b.valorTotal ?? parseMoeda(b.valor));
        const av = Number.isFinite(va) ? va : Number.POSITIVE_INFINITY;
        const bv = Number.isFinite(vb) ? vb : Number.POSITIVE_INFINITY;
        return av - bv;
      });
    }

    function dedupeRows(rows) {
      const unique = [];
      const seen = new Set();
      for (const row of rows) {
        const key = rowDedupeKey(row);
        if (seen.has(key)) continue;
        seen.add(key);
        unique.push(row);
      }
      return unique;
    }

    function mapBackendToRows(backend, geoKeyPart) {
      if (!backend?.ok || !Array.isArray(backend.itens)) return 0;
      const mapped = backend.itens.map((it, idx) => ({
        esferaAdministrativa: classificarEsferaAdministrativa(it),
        incisoClassificacao: mapEsferaParaInciso(classificarEsferaAdministrativa(it)),
        id: `backend-${context?.id || 'none'}-${geoKeyPart}-${idx}-${it.numero_pncp || ''}`,
        itemId: context?.id || null,
        itemRefLabel: context?.descricao_item || '-',
        sourceRaw: it,
        numeroPncp: it.numero_pncp || null,
        anoCompra: it.ano_compra ?? null,
        sequencialCompra: it.sequencial_compra ?? null,
        numeroItem: it.numero_item ?? null,
        titulo: it.descricao_item || it.objeto_resumido || 'Descrição indisponível',
        item: it.descricao_item || it.objeto_resumido || '-',
        normalizado: it.material_servico || resolveTipoItem(it) || '-',
        orgao: it.orgao || '-',
        cidade: `${it.municipio || '-'}${it.uf ? `/${it.uf}` : ''}`,
        uf: it.uf || '-',
        municipio: it.municipio || null,
        modalidade: it.modalidade || '-',
        processo: it.numero_pncp || '-',
        data: it.data_publicacao || '-',
        qtd: `${it.quantidade || '-'} ${it.unidade_medida || ''}`.trim(),
        quantidadeNum: it.quantidade ?? null,
        unidadeMedida: it.unidade_medida || null,
        valor: formatCurrency(it.valor_unitario ?? it.valor_total ?? 0),
        valorUnitario: it.valor_unitario ?? null,
        valorTotal: it.valor_total ?? null,
        score: Number.isFinite(Number(it.score_aprovacao)) ? Number(it.score_aprovacao) : 0,
        confiabilidade: it.confiabilidade || 'Média',
        risco: it.risco || 'Médio',
        status: it.status || 'Aprovado',
        interpretacaoIa: String(it.ia_interpretacao_item || '').trim() || null,
        similaridadeEncontrada: Boolean(it.similaridade_encontrada),
        fornecedor: String(it.fornecedor || '').trim() || null,
        cnpjFornecedor: String(it.cnpj_fornecedor || it.cnpjFornecedor || '').trim() || null,
        selecionado: false,
        backendItensCount: backend.itens.length,
      }));
      aggregated.push(...mapped);
      return mapped.length;
    }

    let backendItensTotal = 0;
    if (recortes.length > 0) {
      const backend = await intelligentMarketSearch(
        {
          ...basePayload,
          recortes_geograficos: recortes,
          uf: null,
          municipio: null,
        },
        signal,
      );
      if (generation != null && generation !== searchGeneration.value) return;
      backendItensTotal += mapBackendToRows(backend, 'rec') || 0;
    } else {
      const ufsToRun = context?.uf_padrao ? [context.uf_padrao] : [null];
      for (const ufCode of ufsToRun) {
        if (generation != null && generation !== searchGeneration.value) return;
        const backend = await intelligentMarketSearch(
          {
            ...basePayload,
            uf: ufCode || null,
            municipio: null,
          },
          signal,
        );
        if (generation != null && generation !== searchGeneration.value) return;
        backendItensTotal += mapBackendToRows(backend, ufCode || 'all') || 0;
      }
    }
    if (generation != null && generation !== searchGeneration.value) return;
    if (aggregated.length > 0) {
      // Backend já devolve top3 distintos; dedupe só quando há fusão multi-UF/geo (>3 linhas).
      let picks;
      if (aggregated.length <= 3) {
        picks = sortRowsByScore(aggregated);
      } else {
        picks = sortRowsByScore(dedupeRows(aggregated)).slice(0, 3);
      }
      if (backendItensTotal > picks.length && backendItensTotal <= 3) {
        picks = sortRowsByScore(aggregated);
      }
      rows.value = append ? [...rows.value, ...picks] : picks;
    } else if (!append) {
      searchError.value = 'A IA não encontrou 3 cotações aderentes para este termo no recorte atual.';
    }
  } catch (err) {
    if (isAbortError(err)) return;
    if (generation != null && generation !== searchGeneration.value) return;
    searchError.value = `Não foi possível consultar o backend (${err.message || 'erro desconhecido'}).`;
  } finally {
    activeSearchOps.value -= 1;
    if (activeSearchOps.value < 0) activeSearchOps.value = 0;
    isSearching.value = activeSearchOps.value > 0;
  }
}

function formatCurrency(v) {
  const n = Number(v);
  if (Number.isNaN(n)) return 'R$ -';
  return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function toggleSelecionado(id) {
  rows.value = rows.value.map((r) => (r.id === id ? { ...r, selecionado: !r.selecionado } : r));
}

function toggleSelecionarTop3() {
  if (!displayedRows.value.length) return;
  const ids = new Set(displayedRows.value.map((r) => r.id));
  const mark = !allDisplayedSelecionados.value;
  rows.value = rows.value.map((r) => (ids.has(r.id) ? { ...r, selecionado: mark } : r));
}

function toggleSelecionarGrupo(group) {
  const ids = new Set(group.rows.map((r) => r.id));
  const mark = !group.allSelected;
  rows.value = rows.value.map((r) => (ids.has(r.id) ? { ...r, selecionado: mark } : r));
}

async function adicionarSelecionadosNaCotacao() {
  if (isSavingSelecionados.value) return;
  const sessionId = Number(cotacaoId.value);
  if (Number.isNaN(sessionId)) {
    saveMessage.value = 'Cotação inválida para salvar no backend.';
    return;
  }
  const selecionados = displayedRows.value
    .filter((r) => r.selecionado)
    .map((r) => ({
      item_ref_id: r.itemId ?? null,
      esfera_administrativa: r.esferaAdministrativa || null,
      inciso_classificacao: r.incisoClassificacao || null,
      fonte:
        r.incisoClassificacao === 'inciso_i'
          ? 'governamentais'
          : r.incisoClassificacao === 'inciso_ii'
            ? 'entes_publicos'
            : null,
      numero_pncp: r.numeroPncp,
      ano_compra: r.anoCompra,
      sequencial_compra: r.sequencialCompra,
      numero_item: r.numeroItem,
      descricao_item: r.item,
      orgao: r.orgao,
      municipio: r.municipio,
      uf: r.uf,
      quantidade: r.quantidadeNum,
      unidade_medida: r.unidadeMedida,
      modalidade: r.modalidade,
      valor_unitario: r.valorUnitario ?? parseMoeda(r.valor),
      valor_total: r.valorTotal,
      material_servico: r.normalizado,
      score_aprovacao: r.score,
      confiabilidade: r.confiabilidade,
      risco: r.risco,
      status: r.status,
      similaridade_encontrada: Boolean(r.similaridadeEncontrada),
      data_publicacao: r.data,
      fornecedor: r.fornecedor || null,
      cnpj_fornecedor: r.cnpjFornecedor || null,
      source: {
        ...(r.sourceRaw && typeof r.sourceRaw === 'object' ? r.sourceRaw : {}),
        fornecedor: r.fornecedor || null,
        cnpj_fornecedor: r.cnpjFornecedor || null,
      },
    }));
  if (!selecionados.length) {
    saveMessage.value = 'Selecione ao menos um item.';
    return;
  }
  const MAX_ITENS_POR_ENVIO = 2000;
  let enviar = selecionados;
  if (selecionados.length > MAX_ITENS_POR_ENVIO) {
    enviar = selecionados.slice(0, MAX_ITENS_POR_ENVIO);
    saveMessage.value = `Limite de ${MAX_ITENS_POR_ENVIO} itens por envio; gravando os primeiros ${MAX_ITENS_POR_ENVIO}.`;
  }
  try {
    isSavingSelecionados.value = true;
    const selectedWithItem = enviar.filter((x) => Number.isFinite(Number(x.item_ref_id || x.itemId)));
    if (selectedWithItem.length > 0) {
      const byItem = new Map();
      for (const row of selectedWithItem) {
        const iid = Number(row.item_ref_id || row.itemId);
        if (!byItem.has(iid)) byItem.set(iid, []);
        byItem.get(iid).push(row);
      }
      let total = 0;
      for (const [iid, arr] of byItem.entries()) {
        const res = await addCotacoesToItemInResearchSession(sessionId, iid, arr);
        total += Number(res?.cotacoes_inseridas || arr.length);
      }
      saveMessage.value = `${total} cotação(ões) adicionadas aos itens da cotação.`;
      const selectedIds = new Set(displayedRows.value.filter((r) => r.selecionado).map((r) => r.id));
      rows.value = rows.value.filter((r) => !selectedIds.has(r.id));
      await router.push(`/pesquisador-pncp/cotacoes/${sessionId}`);
    } else if (itemId.value) {
      const res = await addCotacoesToItemInResearchSession(sessionId, itemId.value, enviar);
      const inseridas = Number(res?.cotacoes_inseridas ?? 0);
      const ignoradas = Number(res?.cotacoes_ignoradas_duplicadas ?? 0);
      saveMessage.value = ignoradas > 0
        ? `${inseridas} cotação(ões) adicionadas ao item (${ignoradas} duplicada(s) ignorada(s)).`
        : `${inseridas || enviar.length} cotação(ões) adicionadas ao item.`;
      const selectedIds = new Set(displayedRows.value.filter((r) => r.selecionado).map((r) => r.id));
      rows.value = rows.value.filter((r) => !selectedIds.has(r.id));
      await router.push(`/pesquisador-pncp/cotacoes/${sessionId}`);
    } else {
      const res = await addItemsToResearchSession(sessionId, enviar);
      saveMessage.value = `${res.itens_inseridos ?? enviar.length} item(ns) adicionados à cotação.`;
    }
  } catch (err) {
    saveMessage.value = `Falha ao salvar: ${err.message || 'erro desconhecido'}`;
  } finally {
    isSavingSelecionados.value = false;
  }
}

onMounted(async () => {
  const sessionId = Number(cotacaoId.value);
  if (!Number.isFinite(sessionId) || sessionId <= 0) return;
  try {
    const data = await getResearchSession(sessionId);
    const filtrosSessao = (data?.sessao?.filtros && typeof data.sessao.filtros === 'object') ? data.sessao.filtros : {};
    const variacaoGlobal = Number(
      filtrosSessao.variacao_percentual_global ?? filtrosSessao.variacao_global_percentual ?? null,
    );
    variacaoPercentualGlobal.value = Number.isFinite(variacaoGlobal) && variacaoGlobal >= 0
      ? variacaoGlobal
      : null;
    const sentidoRaw = String(filtrosSessao.variacao_sentido_global || '').trim().toLowerCase();
    variacaoSentidoGlobal.value = ['cima', 'baixo', 'ambos'].includes(sentidoRaw) ? sentidoRaw : 'ambos';
    const itens = Array.isArray(data?.itens) ? data.itens : [];
    allItemContexts.value = itens.map((it) => buildContextFromItem(it)).filter((x) => x.descricao_item);
    if (itemId.value) {
      const it = itens.find((x) => Number(x?.id) === Number(itemId.value));
      if (!it) return;
      itemContext.value = buildContextFromItem(it);
      filtros.descricao = String(it.descricao_item || '').trim();
      if (String(it.uf || '').trim()) {
        filtros.cidades = [
        {
          ...newLinhaCidade(),
          uf: String(it.uf || '').trim().toUpperCase(),
        },
      ];
      }
      if (filtros.descricao) {
        await applyFilters();
      }
      return;
    }

    if (autostart.value && itens.length) {
      const pendentes = itens.filter((it) => {
        const fontes = it?.fontes_contagem || {};
        const totalCot = Number(fontes.governamentais || 0)
          + Number(fontes.entesPublicos || 0)
          + Number(fontes.dominioAmplo || 0)
          + Number(fontes.cotacaoDireta || 0)
          + Number(fontes.notasFiscais || 0);
        return totalCot < 3;
      });
      if (!pendentes.length) {
        searchError.value = 'Todos os itens da cotação já estão completos (3+ preços).';
        return;
      }
      const { generation, signal } = beginNewSearchSession();
      isAutoSearchingAll.value = true;
      rows.value = [];
      autoSearchProgress.value = { done: 0, total: pendentes.length };
      for (const it of pendentes) {
        if (generation !== searchGeneration.value) {
          isAutoSearchingAll.value = false;
          return;
        }
        const ctx = buildContextFromItem(it);
        if (!ctx.descricao_item) {
          autoSearchProgress.value.done += 1;
          continue;
        }
        await runSearchWithContext({
          descricao: ctx.descricao_item,
          context: ctx,
          append: true,
          generation,
          signal,
        });
        if (generation !== searchGeneration.value) {
          isAutoSearchingAll.value = false;
          return;
        }
        autoSearchProgress.value.done += 1;
      }
      if (generation !== searchGeneration.value) {
        isAutoSearchingAll.value = false;
        return;
      }
      isAutoSearchingAll.value = false;
      if (!rows.value.length) {
        searchError.value = 'Nenhuma cotação aderente encontrada para os itens da cotação.';
      }
    }
  } catch (_) {
    // contexto do item é opcional; não bloqueia uso normal da tela
    isAutoSearchingAll.value = false;
  }
});

function parseMoeda(v) {
  const n = Number(String(v || '').replace(/[^\d,.-]/g, '').replace(',', '.'));
  return Number.isNaN(n) ? null : n;
}

function formatScorePercent(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return '0%';
  const clamped = Math.max(0, Math.min(100, Math.round(n)));
  return `${clamped}%`;
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
  if (label.includes('3')) {
    months = 3;
  } else if (label.includes('6')) {
    months = 6;
  } else if (label.includes('24')) {
    months = 24;
  } else if (label.includes('12') || label.includes('ano')) {
    months = 12;
  }
  const cutoff = new Date(now);
  cutoff.setMonth(cutoff.getMonth() - months);
  return dt >= cutoff;
}

function resolveTipoItem(item) {
  const materialServico = normalizeText(item?.sourceRaw?.material_servico || item?.material_servico || item?.normalizado || '');
  if (materialServico.includes('servico') || materialServico.includes('serviço')) return 'Servico';
  if (materialServico.includes('material')) return 'Material';
  const desc = normalizeText(item?.descricao || item?.item || item?.titulo || '');
  if (desc.includes('servico') || desc.includes('serviço')) return 'Servico';
  return 'Material';
}

function normalizeKey(v) {
  return String(v ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

function classificarEsferaAdministrativa(raw) {
  const esferaId = normalizeKey(
    raw?.esfera_id ||
    raw?.esferaId ||
    raw?.sourceRaw?.esfera_id ||
    raw?.sourceRaw?.esferaId ||
    raw?.sourceRaw?.orgaoEntidade?.esferaId ||
    raw?.sourceRaw?.orgaoSubRogado?.esferaId,
  ).toUpperCase();
  if (esferaId === 'F') return 'federal';
  if (esferaId === 'E') return 'estadual';
  if (esferaId === 'M') return 'municipal';
  if (esferaId === 'D') return 'distrital';

  const candidatos = [
    raw?.esfera,
    raw?.esfera_administrativa,
    raw?.esferaAdministrativa,
    raw?.poder,
    raw?.sourceRaw?.esfera,
    raw?.sourceRaw?.esfera_administrativa,
    raw?.sourceRaw?.poder,
    raw?.orgao,
  ];
  const joined = candidatos.map((x) => normalizeKey(x)).filter(Boolean).join(' | ');
  if (joined.includes('federal') || joined.includes('uniao') || joined.includes('união')) return 'federal';
  if (joined.includes('estadual') || joined.includes('estado')) return 'estadual';
  if (joined.includes('municipal') || joined.includes('municipio') || joined.includes('município')) return 'municipal';
  return 'nao_definida';
}

function mapEsferaParaInciso(esfera) {
  if (esfera === 'federal') return 'inciso_i';
  if (esfera === 'estadual' || esfera === 'municipal' || esfera === 'distrital') return 'inciso_ii';
  return null;
}

function labelEsfera(esfera) {
  if (esfera === 'federal') return 'Federal';
  if (esfera === 'estadual') return 'Estadual';
  if (esfera === 'municipal') return 'Municipal';
  if (esfera === 'distrital') return 'Distrital';
  return 'Não definida';
}

function labelInciso(inciso) {
  if (inciso === 'inciso_i') return 'Inciso I';
  if (inciso === 'inciso_ii') return 'Inciso II';
  return 'Não classificado';
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
</script>

<style scoped>
.gov-page { display: flex; flex-direction: column; gap: 16px; width: 100%; min-width: 0; }
.gov-page__title { margin: 0; font-size: 24px; }
.gov-page__subtitle { margin: 6px 0 0; color: var(--color-text-soft); max-width: 900px; }
.gov-page__content { padding: 16px; display: flex; flex-direction: column; gap: 12px; min-width: 0; }

.bia-kicker { margin: 0 0 6px; font-size: 11px; text-transform: uppercase; letter-spacing: .08em; color: #1f4e79; font-weight: 700; }
.bia-header-row { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; flex-wrap: wrap; }
.bia-back-btn { border: 1px solid #cfd8e3; border-radius: 10px; background: #fff; color: #1f2937; padding: 7px 12px; font-size: 12px; text-decoration: none; display: inline-flex; align-items: center; gap: 7px; }

.bia-summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 8px; }
.bia-summary-card { border: 1px solid #d6dde8; border-radius: 10px; background: #f8fafc; padding: 10px; display: flex; flex-direction: column; gap: 4px; }
.bia-summary-card span { font-size: 11px; text-transform: uppercase; color: #64748b; }
.bia-summary-card strong { font-size: 20px; color: #0f172a; }
.bia-summary-card--highlight strong { color: #0f4c81; }

.bia-filters { display: block; }
.bia-controls { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px; }
.bia-controls__left,
.bia-controls__right { display: flex; flex-wrap: wrap; gap: 8px; }

.bia-geo-panel {
  border: 1px solid #dbe4f0;
  border-radius: 12px;
  background: linear-gradient(165deg, #fbfdff 0%, #f3f7fb 100%);
  padding: 12px 14px 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.bia-geo-panel__top {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px 16px;
}
.bia-geo-panel__intro {
  flex: 1 1 220px;
  min-width: 0;
}
.bia-geo-panel__kicker {
  margin: 0;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #3d6ea3;
}
.bia-geo-panel__title {
  margin: 4px 0 0;
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.25;
}
.bia-geo-panel__hint {
  margin: 6px 0 0;
  max-width: 520px;
  font-size: 12px;
  color: #64748b;
  line-height: 1.45;
}
.bia-geo-panel__actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
  flex-shrink: 0;
}
.bia-geo-search-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid rgba(37, 99, 235, 0.35);
  background: rgba(239, 246, 255, 0.95);
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}
.bia-geo-search-btn:hover:not(:disabled) {
  background: #dbeafe;
  border-color: rgba(37, 99, 235, 0.55);
  color: #1e40af;
}
.bia-geo-search-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.bia-geo-add-link {
  border: 0;
  background: transparent;
  padding: 2px 0;
  font-size: 12px;
  font-weight: 600;
  color: #2563eb;
  text-decoration: underline;
  text-underline-offset: 3px;
  cursor: pointer;
}
.bia-geo-add-link:hover {
  color: #1d4ed8;
}
.bia-geo-empty {
  font-size: 12px;
  color: #94a3b8;
  font-style: italic;
  padding: 2px 0;
}
.bia-geo-row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 8px;
}
.bia-geo-row + .bia-geo-row {
  margin-top: 6px;
  padding-top: 8px;
  border-top: 1px solid #e8eef5;
}
.bia-geo-field {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 76px;
}
.bia-geo-field--grow {
  flex: 1 1 180px;
}
.bia-geo-field--mun {
  min-width: 200px;
  max-width: min(100%, 420px);
}
.bia-geo-mun-hint {
  margin: 0;
  font-size: 11px;
  color: #64748b;
  line-height: 1.35;
}
.bia-geo-mun-search {
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
.bia-geo-mun-search:focus {
  border-color: #3b6f9e;
  box-shadow: 0 0 0 2px rgba(59, 111, 158, 0.12);
}
.bia-geo-mun-list {
  margin-top: 6px;
  max-height: 200px;
  overflow: auto;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 6px 8px;
  background: #f8fafc;
}
.bia-geo-mun-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 3px 0;
  font-size: 12px;
  color: #0f172a;
  cursor: pointer;
  line-height: 1.3;
}
.bia-geo-mun-item input {
  margin-top: 2px;
  flex-shrink: 0;
}
.bia-geo-field span {
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #64748b;
}
.bia-geo-uf-filter {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-width: 0;
}
.bia-geo-uf-flag {
  width: 30px;
  height: 21px;
  object-fit: cover;
  border-radius: 3px;
  box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.1);
  flex-shrink: 0;
}
.bia-geo-uf-flag--table {
  width: 24px;
  height: 16px;
}
.bia-uf-cell {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  flex-wrap: wrap;
}
.bia-geo-select--uf {
  flex: 1;
  min-width: 0;
}
.bia-geo-select {
  border: 1px solid #cfd8e3;
  border-radius: 8px;
  background: #fff;
  font-size: 12px;
  padding: 6px 8px;
  width: 100%;
  color: #0f172a;
  outline: none;
}
.bia-geo-select:focus {
  border-color: #3b6f9e;
  box-shadow: 0 0 0 2px rgba(59, 111, 158, 0.12);
}
.bia-geo-remove {
  align-self: flex-start;
  margin-top: 20px;
  width: 30px;
  height: 30px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  color: #64748b;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
}
.bia-geo-remove:hover {
  border-color: #cbd5e1;
  color: #475569;
}
@media (max-width: 600px) {
  .bia-geo-panel__actions {
    align-items: stretch;
    width: 100%;
  }
  .bia-geo-search-btn {
    width: 100%;
    justify-content: center;
  }
  .bia-geo-add-link {
    width: 100%;
    text-align: center;
  }
}
.bia-meta { margin: 2px 0 0; font-size: 12px; color: #64748b; }
.bia-meta--error { color: #b91c1c; }
.bia-table-shell { border: 1px solid #d6dde8; border-radius: 10px; background: #fff; min-width: 0; overflow: hidden; }
.bia-table-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  border-bottom: 1px solid #e5eaf3;
  background: #f8fafc;
  padding: 10px;
}
.bia-table-head__pills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  min-width: 0;
}
.bia-table-head__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-left: auto;
}
.bia-add-cotacao-btn {
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
.bia-add-cotacao-btn:hover {
  filter: brightness(0.95);
}
.bia-add-cotacao-btn--ghost {
  background: #fff;
  color: #1f4e79;
}
.bia-add-cotacao-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}
.bia-pill { border: 1px solid #d5dde9; background: #eef2f7; color: #475569; border-radius: 999px; padding: 3px 10px; font-size: 12px; }
.bia-pill--ok { border-color: #b7d2ef; background: #e8f1fb; color: #1f4e79; }
.bia-pill--warn { border-color: #f2dfb7; background: #fff7e6; color: #9a6a10; }

.bia-table-scroll { width: 100%; overflow-x: auto; overflow-y: hidden; min-width: 0; }
.bia-groups { display: flex; flex-direction: column; gap: 10px; }
.bia-group-card { border-top: 1px solid #e5eaf3; }
.bia-group-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px;
  background: #fff;
}
.bia-group-title { margin: 0; font-size: 14px; color: #0f172a; }
.bia-table { width: 100%; min-width: 1300px; border-collapse: collapse; table-layout: fixed; }
.bia-table th, .bia-table td { border-bottom: 1px solid #e5eaf3; padding: 10px 8px; font-size: 12px; vertical-align: top; }
.bia-table th { text-align: left; font-size: 11px; text-transform: uppercase; color: #64748b; background: #fff; }
.bia-table th:last-child,
.bia-table td:last-child {
  padding-right: 14px;
}
.bia-main { font-weight: 600; color: #0f172a; line-height: 1.3; }
.bia-ia-hint {
  margin-top: 6px;
  font-size: 0.875rem;
  color: #475569;
  font-style: italic;
  line-height: 1.45;
  border-left: 3px solid #cbd5e1;
  padding-left: 10px;
}
.bia-ia-hint strong { font-style: normal; font-weight: 600; color: #334155; margin-right: 4px; }
.bia-sub { color: #64748b; margin-top: 4px; line-height: 1.4; }
.bia-cell-center { text-align: center; }
.bia-meta-token { white-space: nowrap; }
.bia-meta-sep { margin: 0 6px; color: #94a3b8; }
.bia-bold { font-weight: 700; white-space: nowrap; }
.bia-badge { display: inline-flex; border: 1px solid #d5dde9; border-radius: 999px; padding: 2px 8px; font-size: 10px; white-space: nowrap; }
.bia-badge--ok { border-color: #b7d2ef; background: #e8f1fb; color: #1f4e79; }
.bia-badge--warn { border-color: #f2dfb7; background: #fff7e6; color: #9a6a10; }
.bia-badge--danger { border-color: #f0c8c8; background: #fff0f0; color: #a63f3f; }
.bia-badge--conf-high { border-color: #86efac; background: #f0fdf4; color: #166534; }
.bia-badge--conf-mid { border-color: #fde68a; background: #fffbeb; color: #92400e; }
.bia-badge--conf-low { border-color: #fca5a5; background: #fef2f2; color: #991b1b; }
.bia-badge--risk-low { border-color: #93c5fd; background: #eff6ff; color: #1d4ed8; }
.bia-badge--risk-mid { border-color: #c4b5fd; background: #f5f3ff; color: #6d28d9; }
.bia-badge--risk-high { border-color: #fda4af; background: #fff1f2; color: #be123c; }
</style>
