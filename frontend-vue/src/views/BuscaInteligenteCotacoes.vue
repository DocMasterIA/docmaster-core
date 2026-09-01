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
          <span v-if="totalSalvaveis < displayedRows.length" class="bia-meta">
            ({{ totalSalvaveis }} com CNPJ para salvar)
          </span>
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

      <p v-if="faixaGlobalResumo" class="bia-faixa-banner">
        Faixa global: <strong>{{ faixaGlobalResumo }}</strong>
        <span class="bia-faixa-banner__hint">(definida em «Itens da cotação» → Salvar variação global)</span>
      </p>

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

      <PriceSourcesPanel
        v-model="fontesHabilitadas"
        :fontes="fontesCatalog"
        :loading="isLoadingFontes"
      />

      <p v-if="isLoadingSessionItems" class="bia-meta">
        Carregando itens da cotação{{ sessionItemsLoadHint ? ` (${sessionItemsLoadHint})` : '' }}...
      </p>
      <p v-if="isAutoSearchingAll" class="bia-meta">
        Busca automática em andamento: item {{ autoSearchProgress.done }} de {{ autoSearchProgress.total }}
        <span v-if="rebuscarCompletos && cotacaoResumo.completos > 0">
          (rebusca todos — {{ cotacaoResumo.completos }} já tinham 3+ preços)
        </span>
        <span v-else-if="cotacaoResumo.totalItens > autoSearchProgress.total">
          ({{ cotacaoResumo.totalItens }} na cotação, {{ cotacaoResumo.completos }} já completos)
        </span>
        <span v-if="autoSearchProgress.precos > 0 || autoSearchProgress.fail > 0 || autoSearchProgress.skipped > 0">
          — {{ autoSearchProgress.precos }} preço(s), {{ autoSearchProgress.fail }} falha(s)<span v-if="autoSearchProgress.skipped > 0">, {{ autoSearchProgress.skipped }} ignorado(s)</span>
        </span>
        ...
      </p>
      <p v-if="isAutoSearchingAll && lastBulkFailure" class="bia-meta bia-meta--error">
        Última falha: {{ lastBulkFailure }}
      </p>
      <p v-else-if="autoSearchProgress.total > 0" class="bia-meta">
        Busca automática {{ autoSearchProgress.done < autoSearchProgress.total ? 'parcial' : 'concluída' }}:
        {{ autoSearchProgress.done }} de {{ autoSearchProgress.total }} item(ns) processados,
        {{ autoSearchProgress.precos }} preço(s) encontrados
        <span v-if="autoSearchProgress.skipped > 0">, {{ autoSearchProgress.skipped }} item(ns) já com 3+ na tabela</span>
        <span v-if="autoSearchProgress.fail > 0">, {{ autoSearchProgress.fail }} falha(s) de rede</span>.
        <span v-if="cotacaoResumo.completos > 0 && !rebuscarCompletos">
          {{ cotacaoResumo.completos }} item(ns) já tinham 3+ preços salvos e foram ignorados
          (cotação: {{ cotacaoResumo.totalItens }} itens).
        </span>
      </p>
      <p v-else-if="cotacaoResumo.totalItens > 0 && !rebuscarCompletos" class="bia-meta">
        Cotação: {{ cotacaoResumo.totalItens }} itens • {{ cotacaoResumo.incompletos }} incompletos (&lt; 3 preços salvos)
        • {{ cotacaoResumo.completos }} completos (ignorados na busca automática).
      </p>
      <p v-if="lastSearchDebug && !isAutoSearchingAll" class="bia-meta">
        Última busca ({{ lastSearchDebug.termo }}):
        API retornou <strong>{{ lastSearchDebug.apiItens }}</strong>,
        exibindo <strong>{{ lastSearchDebug.exibidos }}</strong>
        <span v-if="lastSearchDebug.faixaAtiva"> • {{ lastSearchDebug.faixaResumo || `faixa R$ ${lastSearchDebug.faixaMin}–${lastSearchDebug.faixaMax}` }}</span>
        <span v-if="lastSearchDebug.apiItens > lastSearchDebug.exibidos" class="bia-meta--error">
          — {{ lastSearchDebug.apiItens - lastSearchDebug.exibidos }} filtrado(s) no front (preço ou fornecedor inválido)
        </span>
      </p>
      <p v-if="itemContext" class="bia-meta">
        Item de referência: <strong>{{ itemContext.descricao_item }}</strong>
        <span v-if="itemContext.quantidade != null"> • Qtd {{ itemContext.quantidade }}</span>
        <span v-if="itemContext.unidade_medida"> {{ itemContext.unidade_medida }}</span>
      </p>
      <p v-if="searchError" class="bia-meta bia-meta--error">{{ searchError }}</p>
      <p v-else-if="isSearching" class="bia-meta">Consultando índices locais ({{ fontesBuscaLabel }})…</p>

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
                <h3 class="bia-group-title">
                  {{ group.label }}
                  <span class="bia-group-media">· Média escolhida: <strong>{{ mediaEscolhidaGrupo(group) }}</strong></span>
                </h3>
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
                    <th>Faixa Regional do Item</th>
                    <th>Confiabilidade IA</th>
                    <th>Risco</th>
                    <th>Score</th>
                    <th>Cotação usada</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in group.rows" :key="row.id">
                    <td class="bia-cell-center">
                      <input
                        type="checkbox"
                        :checked="isRowSelected(row.id)"
                        @change="setRowSelected(row.id, $event.target.checked)"
                      />
                    </td>
                    <td>
                      <div class="bia-main">{{ row.titulo }}</div>
                      <div v-if="row.interpretacaoIa" class="bia-ia-hint" title="Leitura auxiliar gerada por IA">
                        <strong>IA:</strong> {{ row.interpretacaoIa }}
                      </div>
                      <div v-if="(row.orgao && row.orgao !== '-') || (row.cidade && row.cidade !== '-')" class="bia-sub">
                        <span v-if="row.orgao && row.orgao !== '-'" class="bia-meta-token">{{ row.orgao }}</span>
                        <span v-if="row.orgao && row.orgao !== '-' && row.cidade && row.cidade !== '-'" class="bia-meta-sep">·</span>
                        <span v-if="row.cidade && row.cidade !== '-'">{{ row.cidade }}</span>
                      </div>
                      <div v-if="biaMetaParts(row).length" class="bia-sub">
                        <template v-for="(part, idx) in biaMetaParts(row)" :key="idx">
                          <span v-if="idx > 0"> • </span>{{ part }}
                        </template>
                      </div>
                      <div v-if="row.similaridadeEncontrada" class="bia-sub">
                        <span class="bia-badge bia-badge--warn">Similaridade parcial encontrada</span>
                      </div>
                      <div class="bia-sub">
                        <span class="bia-plat-badge" :class="`bia-plat-badge--${row.plataforma}`">
                          {{ row.plataformaLabel }}
                        </span>
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
                    <td class="bia-faixa-cell">
                      <template v-if="faixaRegionalItemForRow(row)">
                        <div class="bia-faixa-cell__row">
                          <span class="bia-faixa-cell__label">BASE</span>
                          <strong>{{ faixaRegionalItemForRow(row).baseFmt }}</strong>
                        </div>
                        <div class="bia-faixa-cell__row">
                          <span class="bia-faixa-cell__label">VAR</span>
                          <strong>{{ faixaRegionalItemForRow(row).variacaoFmt }}</strong>
                        </div>
                        <div class="bia-faixa-cell__range">{{ faixaRegionalItemForRow(row).rangeFmt }}</div>
                      </template>
                      <span v-else class="bia-meta">—</span>
                    </td>
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
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  fetchAllItemsForBulkSearch,
  federatedMarketSearch,
  formatResearchError,
  getLocalIndexStatsResilient,
  getResearchSession,
} from '../services/pncpResearch';
import PriceSourcesPanel from '../components/PriceSourcesPanel.vue';
import {
  applyFontesWhenStatsUnavailable,
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
import { MUNICIPIOS_POR_UF } from '../data/brasilMunicipiosPorUf';
import { buildRecortesGeograficosPayload } from '../utils/recortesGeograficos';
import {
  bulkAutostartRegistry,
  beginBulkAutostartSession,
  bulkRunShouldStop as bulkRunShouldStopBase,
  clearBulkPausedFlag,
  getBulkAutostartController,
  isBulkRunActive,
  isPncpResearchRoute,
  isRegistryAutostartBulk,
  runBulkAutostartOnce,
} from '../composables/usePncpBulkAutostart.js';
import {
  displayPnCpTotal,
  displayPnCpUnitario,
  canSalvarCotacaoPnCp,
  buildFaixaRegionalItemDisplay,
  computeFaixaRegional,
  extractCnpjFornecedorSalvar,
  extractPnCpHomologadoTotal,
  extractPnCpHomologadoUnit,
  formatFaixaResumo,
  passesPnCpSearchDisplayGate,
  pickFornecedorDisplayName,
  pnCpRowWithinFaixaRegional,
  resolveRowPlataforma,
} from '../utils/pncpPricing';
import { labelModalidadeFonte } from '../utils/tceModalidade';
import { formatMunicipioUf, resolveMunicipioUf } from '../utils/tceLocalidade';

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

/** IDs das fontes de preço habilitadas na busca federada. */
const fontesHabilitadas = ref(['pncp']);
const fontesCatalog = ref([]);
const isLoadingFontes = ref(false);
const localStats = ref(null);

const fontesBuscaLabel = computed(() => {
  const ids = fontesHabilitadas.value?.length ? fontesHabilitadas.value : ['pncp'];
  return ids.map((id) => plataformaBadgeShort(id)).join(' + ');
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
/** Seleções persistem mesmo quando a lista de linhas é atualizada (bulk/autostart). */
const selectedRowIds = ref(new Set());
const isSearching = ref(false);
/** Conta chamadas HTTP de busca em voo (várias sequenciais ou reinício). */
const activeSearchOps = ref(0);
const searchGeneration = ref(0);
let searchAbortController = null;
/** Evita corrida quando o Vue remonta o componente (autostart duplicado). */
let mountRunSeq = 0;
let activeBulkRunId = 0;

function bulkRunShouldStop(opts) {
  return bulkRunShouldStopBase({
    ...opts,
    mountRunSeq,
    searchGeneration: searchGeneration.value,
  });
}

function beginNewSearchSession() {
  try {
    searchAbortController?.abort();
  } catch (_) {
    /* ignore */
  }
  activeBulkRunId += 1;
  if (!bulkAutostartRegistry.isRunning) {
    try {
      getBulkAutostartController()?.abort();
    } catch (_) {
      /* ignore */
    }
  }
  searchAbortController = new AbortController();
  searchGeneration.value += 1;
  return { generation: searchGeneration.value, signal: searchAbortController.signal };
}

function isAbortError(err) {
  if (isTimeoutError(err)) return false;
  const name = String(err?.name || '');
  const msg = String(err?.message || '');
  return name === 'AbortError' || /aborted|abort|canceled|cancelled/i.test(msg);
}

function isTimeoutError(err) {
  const name = String(err?.name || '');
  const msg = String(err?.message || '');
  if (name === 'TimeoutError') return true;
  const reason = err?.cause || err?.reason;
  if (reason && String(reason?.name || '') === 'TimeoutError') return true;
  return /timed out|timeout|time.?out|signal timed out/i.test(msg);
}

function bulkSearchFailResult(err, { superseded = false, timeoutSec = 180 } = {}) {
  if (superseded) {
    return {
      ok: false,
      exibidos: 0,
      aborted: true,
      ghost: true,
      error: 'Busca substituída por outra sessão.',
    };
  }
  if (isTimeoutError(err)) {
    return {
      ok: false,
      exibidos: 0,
      aborted: false,
      error: `Tempo esgotado aguardando a pesquisa (${timeoutSec}s). O lote continua; use «Pesquisar UF» depois para os que faltarem.`,
    };
  }
  if (isAbortError(err)) {
    return {
      ok: false,
      exibidos: 0,
      aborted: true,
      ghost: true,
      error: 'Requisição interrompida (remontagem da página).',
    };
  }
  return {
    ok: false,
    exibidos: 0,
    aborted: false,
    error: formatResearchError(err),
  };
}

const BULK_SEARCH_TIMEOUT_MS = 200000;
const BULK_CONCURRENCY = 1;
const BULK_ITEM_DELAY_MS = 50;

const searchError = ref('');
const lastSearchDebug = ref(null);
const saveMessage = ref('');
const isSavingSelecionados = ref(false);
const itemContext = ref(null);
const allItemContexts = ref([]);
const variacaoPercentualGlobal = ref(null);
const variacaoSentidoGlobal = ref('ambos');

const faixaGlobalResumo = computed(() => {
  const pct = Number(variacaoPercentualGlobal.value);
  if (!Number.isFinite(pct) || pct < 0) return '';
  const sentido = ['cima', 'baixo', 'ambos'].includes(variacaoSentidoGlobal.value)
    ? variacaoSentidoGlobal.value
    : 'ambos';
  if (sentido === 'cima') return `até ${Math.round(pct)}% acima do valor base (só para cima)`;
  if (sentido === 'baixo') return `até ${Math.round(pct)}% abaixo do valor base (só para baixo)`;
  return `±${Math.round(pct)}% (ambos os lados)`;
});
const isAutoSearchingAll = ref(false);
const isLoadingSessionItems = ref(false);
const sessionItemsLoadHint = ref('');
const autoSearchProgress = ref({ done: 0, total: 0, ok: 0, fail: 0, empty: 0, precos: 0, skipped: 0 });
const lastBulkFailure = ref('');
const cotacaoResumo = ref({
  totalItens: 0,
  carregados: 0,
  incompletos: 0,
  completos: 0,
});
const rebuscarCompletos = computed(() => String(route.query.rebuscar || '').trim() === '1');

function itemTotalCotacoesSalvas(it) {
  const fontes = it?.fontes_contagem || {};
  return Number(fontes.governamentais || 0)
    + Number(fontes.entesPublicos || 0)
    + Number(fontes.dominioAmplo || 0)
    + Number(fontes.cotacaoDireta || 0)
    + Number(fontes.notasFiscais || 0);
}

function buildPendentesFromItens(itens) {
  if (rebuscarCompletos.value) return [...itens];
  return itens.filter((it) => itemTotalCotacoesSalvas(it) < 3);
}

function refreshCotacaoResumo(itens, totalSessao, stats = null) {
  const carregados = Array.isArray(itens) ? itens.length : 0;
  const totalItens = Number(stats?.total_itens ?? totalSessao) > 0
    ? Number(stats?.total_itens ?? totalSessao)
    : carregados;
  const incompletos = Number.isFinite(Number(stats?.total_incompletos))
    ? Number(stats.total_incompletos)
    : buildPendentesFromItens(itens).length;
  const completos = Number.isFinite(Number(stats?.total_completos))
    ? Number(stats.total_completos)
    : Math.max(0, totalItens - incompletos);
  cotacaoResumo.value = {
    totalItens,
    carregados,
    incompletos,
    completos,
  };
  if (!stats && totalItens > carregados) {
    searchError.value =
      `Resposta incompleta da API: ${carregados} de ${totalItens} itens carregados. `
      + 'Recarregue a página após atualizar o backend (endpoint paginado).';
    return false;
  }
  return true;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** União por id — evita perder linhas quando o snapshot do lote sobrescreve append recente. */
function mergeBulkSearchRows(localRows, registryRows) {
  const map = new Map();
  const ingest = (list) => {
    for (const row of list || []) {
      const id = String(row?.id || '').trim();
      if (!id) continue;
      map.set(id, row);
    }
  };
  ingest(registryRows);
  ingest(localRows);
  return Array.from(map.values());
}

function persistBulkUiSnapshot(sessionId) {
  if (!Number.isFinite(Number(sessionId))) return;
  bulkAutostartRegistry.sessionId = Number(sessionId);
  bulkAutostartRegistry.progress = { ...autoSearchProgress.value };
  bulkAutostartRegistry.rows = mergeBulkSearchRows(rows.value, bulkAutostartRegistry.rows);
  bulkAutostartRegistry.lastFailure = String(lastBulkFailure.value || '');
}

function applyBulkUiSnapshot(sessionId) {
  if (Number(bulkAutostartRegistry.sessionId) !== Number(sessionId)) return false;
  if (bulkAutostartRegistry.progress) {
    autoSearchProgress.value = { ...bulkAutostartRegistry.progress };
  }
  if (Array.isArray(bulkAutostartRegistry.rows)) {
    rows.value = mergeBulkSearchRows(rows.value, bulkAutostartRegistry.rows);
  }
  lastBulkFailure.value = bulkAutostartRegistry.lastFailure || '';
  isAutoSearchingAll.value = Boolean(bulkAutostartRegistry.isRunning);
  return true;
}

function isRowSelected(id) {
  return selectedRowIds.value.has(id);
}

function setRowSelected(id, checked) {
  const next = new Set(selectedRowIds.value);
  if (checked) next.add(id);
  else next.delete(id);
  selectedRowIds.value = next;
}

function clearRowSelections() {
  selectedRowIds.value = new Set();
}

function mediaEscolhidaGrupo(group) {
  const nums = (group?.rows || [])
    .filter((r) => selectedRowIds.value.has(r.id))
    .map((r) => Number(r.valorUnitario ?? parseMoeda(r.valor)))
    .filter((n) => Number.isFinite(n) && n > 0);
  if (!nums.length) return 'R$ -';
  return formatCurrency(nums.reduce((a, b) => a + b, 0) / nums.length);
}

async function awaitBulkAutostartRegistry(sessionId) {
  applyBulkUiSnapshot(sessionId);
  const pollMs = 400;
  while (bulkAutostartRegistry.isRunning && Number(bulkAutostartRegistry.sessionId) === Number(sessionId)) {
    await sleep(pollMs);
    applyBulkUiSnapshot(sessionId);
  }
  if (bulkAutostartRegistry.promise) {
    try {
      await bulkAutostartRegistry.promise;
    } catch (_) {
      /* erros tratados em runBulkItemSearches */
    }
  }
  applyBulkUiSnapshot(sessionId);
}

function itemRowsCount(itemId) {
  if (!Number.isFinite(Number(itemId))) return 0;
  return rows.value.filter((r) => Number(r.itemId) === Number(itemId)).length;
}

async function processOneBulkItem(ctx, {
  mountRunId,
  myBulkRunId,
  generation,
  autostartBulk = false,
  fetchSignal = undefined,
  sessionId,
} = {}) {
  const sid = Number(sessionId);
  const stopOpts = { mountRunId, myBulkRunId, generation, autostartBulk };
  if (bulkRunShouldStop(stopOpts)) {
    if (autostartBulk && bulkAutostartRegistry.pausedByNavigation) {
      lastBulkFailure.value = 'Busca pausada (navegação para outro módulo).';
    } else if (autostartBulk) {
      lastBulkFailure.value = 'Autostart cancelado (requisição abortada).';
    }
    return { stop: true };
  }
  if (!String(ctx?.descricao_item || '').trim()) {
    autoSearchProgress.value.done += 1;
    return { stop: false };
  }
  const salvosNoBackend = Number(ctx?.total_cotacoes_item || 0);
  const linhasNaSessao = itemRowsCount(ctx.id);
  if (salvosNoBackend >= 3 || linhasNaSessao >= 3) {
    autoSearchProgress.value.done += 1;
    autoSearchProgress.value.skipped += 1;
    autoSearchProgress.value.ok += 1;
    return { stop: false };
  }
  let result;
  try {
    result = await runSearchWithContext({
      descricao: ctx.descricao_item,
      context: ctx,
      append: true,
      bulkMode: true,
      generation,
      bulkRunId: myBulkRunId,
      autostartBulk,
      signal: fetchSignal,
    });
  } catch (err) {
    result = bulkSearchFailResult(err, {
      timeoutSec: Math.round(BULK_SEARCH_TIMEOUT_MS / 1000),
    });
  }
  if (!result) {
    result = { ok: false, exibidos: 0, error: 'Resposta vazia do motor de busca.' };
  }
  if (bulkRunShouldStop(stopOpts)) {
    return { stop: true };
  }
  autoSearchProgress.value.done += 1;
  if (result?.aborted) {
    if (!result?.ghost) {
      autoSearchProgress.value.fail += 1;
      lastBulkFailure.value = String(result?.error || '').trim()
        || 'Requisição interrompida (tente «Pesquisar UF» para os restantes).';
    }
  } else if (result?.ok) {
    autoSearchProgress.value.ok += 1;
    autoSearchProgress.value.precos += Number(result.exibidos || 0);
  } else if (result?.empty) {
    autoSearchProgress.value.empty += 1;
  } else {
    autoSearchProgress.value.fail += 1;
    const errMsg = String(result?.error || '').trim();
    if (errMsg) {
      lastBulkFailure.value = `${ctx.descricao_item?.slice(0, 60) || 'Item'}: ${errMsg}`;
    }
  }
  if (Number.isFinite(sid)) persistBulkUiSnapshot(sid);
  if (BULK_ITEM_DELAY_MS > 0) await sleep(BULK_ITEM_DELAY_MS);
  return { stop: false };
}

/** Evita dois autostarts em paralelo (Vue Strict Mode / remount). */
let bulkAutostartLaunchGuard = 0;

async function launchBulkAutostart(sessionId, pendentesCtx) {
  return runBulkAutostartOnce(sessionId, async () => {
    const launchId = ++bulkAutostartLaunchGuard;
    bulkAutostartRegistry.sessionId = sessionId;
    bulkAutostartRegistry.isRunning = true;
    const { bulkRunId } = beginBulkAutostartSession(sessionId);
    const bulkPromise = runBulkItemSearches(pendentesCtx, {
      bulkRunId,
      autostartBulk: true,
      clearRows: true,
      sessionId,
    });
    bulkAutostartRegistry.promise = bulkPromise;
    try {
      await bulkPromise;
    } finally {
      if (launchId === bulkAutostartLaunchGuard && Number(bulkAutostartRegistry.bulkRunId) === Number(bulkRunId)) {
        bulkAutostartRegistry.isRunning = false;
        bulkAutostartRegistry.promise = null;
      }
      persistBulkUiSnapshot(sessionId);
    }
  });
}

async function runBulkItemSearches(pendentes, {
  generation = null,
  bulkRunId = null,
  mountRunId = null,
  autostartBulk = false,
  fetchSignal = undefined,
  clearRows = false,
  sessionId = null,
} = {}) {
  const myBulkRunId = bulkRunId;
  const sid = Number(sessionId);
  const stopOpts = { mountRunId, myBulkRunId, generation, autostartBulk };
  if (clearRows) {
    rows.value = [];
    clearRowSelections();
    bulkAutostartRegistry.rows = [];
  }
  isAutoSearchingAll.value = true;
  autoSearchProgress.value = {
    done: 0,
    total: pendentes.length,
    ok: 0,
    fail: 0,
    empty: 0,
    precos: 0,
    skipped: 0,
  };
  searchError.value = '';
  lastBulkFailure.value = '';
  if (Number.isFinite(sid)) persistBulkUiSnapshot(sid);

  let nextIdx = 0;
  let stopRequested = false;

  async function bulkWorker() {
    while (!stopRequested) {
      if (bulkRunShouldStop(stopOpts)) {
        stopRequested = true;
        break;
      }
      const idx = nextIdx;
      nextIdx += 1;
      if (idx >= pendentes.length) break;
      try {
        const outcome = await processOneBulkItem(pendentes[idx], {
          mountRunId,
          myBulkRunId,
          generation,
          autostartBulk,
          fetchSignal,
          sessionId: sid,
        });
        if (outcome?.stop) {
          stopRequested = true;
          break;
        }
      } catch (err) {
        autoSearchProgress.value.done += 1;
        autoSearchProgress.value.fail += 1;
        lastBulkFailure.value = String(err?.message || err || 'Erro inesperado no lote').slice(0, 120);
        if (Number.isFinite(sid)) persistBulkUiSnapshot(sid);
      }
    }
  }

  const workers = Math.max(1, Math.min(BULK_CONCURRENCY, pendentes.length || 1));
  await Promise.all(Array.from({ length: workers }, () => bulkWorker()));

  if (bulkRunShouldStop(stopOpts)) {
    isAutoSearchingAll.value = false;
    return;
  }
  isAutoSearchingAll.value = false;
  const p = autoSearchProgress.value;
  if (p.total > 0 && p.done === 0) {
    const hint = String(lastBulkFailure.value || '').trim();
    searchError.value = hint
      ? `${hint} Recarregue ou clique «Pesquisar UF».`
      : 'A busca automática não processou nenhum item (cancelada antes da 1ª requisição). Recarregue ou clique «Pesquisar UF».';
    return;
  }
  if (p.done < p.total) {
    const restantes = p.total - p.done;
    if (p.precos > 0 || p.fail > 0) {
      searchError.value =
        `Busca parcial (${p.done}/${p.total}): ${p.precos} preço(s), ${p.fail} falha(s). `
        + `${restantes} item(ns) restante(s) — clique «Pesquisar UF» para continuar (resultados já encontrados são mantidos).`;
    } else {
      searchError.value =
        `A busca parou em ${p.done} de ${p.total} item(ns). Clique «Pesquisar UF» para continuar.`;
    }
    return;
  }
  if (p.precos > 0 && p.fail > 0) {
    searchError.value =
      `Busca concluída com ressalvas: ${p.ok} item(ns), ${p.precos} preço(s), ${p.fail} falha(s) de rede.`;
  } else if (p.precos === 0 && p.fail > 0) {
    searchError.value =
      `Falha de rede em ${p.fail} item(ns). Verifique o serviço PNCP e clique «Pesquisar UF» para tentar de novo.`;
  }
}
const totalSelecionados = computed(() => displayedRows.value.filter((x) => selectedRowIds.value.has(x.id)).length);
const totalSalvaveis = computed(
  () => displayedRows.value.filter((r) => canSalvarCotacaoPnCp(r)).length,
);
const allDisplayedSelecionados = computed(
  () => displayedRows.value.length > 0 && displayedRows.value.every((x) => selectedRowIds.value.has(x.id)),
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
  const filtrados = [...rows.value];
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

const itemFaixaRegionalById = computed(() => {
  const map = new Map();
  const contexts = [];
  if (itemContext.value) contexts.push(itemContext.value);
  for (const ctx of allItemContexts.value) {
    if (ctx && !contexts.some((c) => c?.id === ctx?.id)) contexts.push(ctx);
  }
  for (const ctx of contexts) {
    const id = Number(ctx?.id);
    if (!Number.isFinite(id) || id <= 0) continue;
    const display = buildFaixaRegionalItemDisplay(
      ctx.valor_base_referencia,
      ctx.variacao_percentual_referencia,
      ctx.variacao_sentido_referencia,
    );
    if (display) map.set(id, display);
  }
  return map;
});

function faixaRegionalItemForRow(row) {
  if (row?.faixaRegionalItem) return row.faixaRegionalItem;
  const id = Number(row?.itemId);
  if (!Number.isFinite(id) || id <= 0) return null;
  return itemFaixaRegionalById.value.get(id) || null;
}

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
    g.allSelected = g.rows.length > 0 && g.rows.every((x) => selectedRowIds.value.has(x.id));
  }
  groups.sort((a, b) => {
    const ai = Number(a.itemId);
    const bi = Number(b.itemId);
    if (Number.isFinite(ai) && Number.isFinite(bi) && ai !== bi) return ai - bi;
    return String(a.label).localeCompare(String(b.label), 'pt-BR');
  });
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
    clearRowSelections();
    return runSearchWithContext({
      descricao: itemContext.value?.descricao_item || '',
      context: itemContext.value,
      append: false,
      generation,
      signal,
    });
  }

  // Fluxo cotação completa: reaplica busca para todos os itens.
  const pendentes = rebuscarCompletos.value
    ? allItemContexts.value
    : allItemContexts.value.filter((ctx) => Number(ctx?.total_cotacoes_item || 0) < 3);
  if (!pendentes.length) {
    searchError.value = 'Todos os itens já estão completos (3+ preços).';
    return;
  }
  const hadRows = rows.value.length > 0;
  const bulkSession = beginBulkAutostartSession(Number(cotacaoId.value), { forceNew: true });
  bulkAutostartRegistry.sessionId = Number(cotacaoId.value);
  bulkAutostartRegistry.isRunning = false;
  return runBulkItemSearches(pendentes, {
    bulkRunId: bulkSession.bulkRunId,
    generation,
    fetchSignal: bulkSession.signal,
    clearRows: !hadRows,
    sessionId: Number(cotacaoId.value),
  });
}

function parseSentidoRef(...vals) {
  for (const v of vals) {
    const raw = String(v || '').trim().toLowerCase();
    if (!raw) continue;
    if (['cima', 'baixo', 'ambos'].includes(raw)) return raw;
    if (raw === 'acima' || raw === 'para cima' || raw === 'pra cima') return 'cima';
    if (raw === 'abaixo' || raw === 'para baixo' || raw === 'pra baixo') return 'baixo';
  }
  return null;
}

function buildContextFromItem(it) {
  const src = it?.source || {};
  const faixa = src?.faixa_regional || src?.faixaRegional || {};
  const fontes = it?.fontes_contagem || {};
  const totalCotacoesItem = itemTotalCotacoesSalvas(it);
  let valorBaseRef = parseNumericRef(
    faixa?.valor_base,
    faixa?.valorBase,
    src?.valor_base,
    src?.valorBase,
    src?.preco_base,
    src?.precoBase,
    it?.valor_unitario_refletido,
    it?.valor_unitario,
  );
  if (valorBaseRef == null) {
    const qtdBase = parseNumericRef(it?.quantidade);
    const totalRef = parseNumericRef(it?.valor_total_refletido, it?.valor_total);
    if (qtdBase != null && qtdBase > 0 && totalRef != null && Number.isFinite(totalRef)) {
      valorBaseRef = totalRef / qtdBase;
    }
  }
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
  // Valor base: source/faixa do item; senão preço refletido (média das cotações salvas) ou ORM.
  if (
    (variacaoRef === null || !Number.isFinite(variacaoRef))
    && valorBaseRef != null
    && Number.isFinite(valorBaseRef)
    && Number.isFinite(Number(variacaoPercentualGlobal.value))
  ) {
    variacaoRef = Number(variacaoPercentualGlobal.value);
  }
  // Variação % e direção são globais da sessão; item.source não deve sobrepor CotacaoDetalhe.
  const sentidoRef = parseSentidoRef(
    it?.variacao_sentido_global,
    variacaoSentidoGlobal.value,
  ) || 'ambos';
  const faixaCalc = (
    valorBaseRef != null
    && Number.isFinite(Number(valorBaseRef))
    && Number(valorBaseRef) > 0
    && variacaoRef != null
    && Number.isFinite(Number(variacaoRef))
    && Number(variacaoRef) >= 0
  )
    ? computeFaixaRegional(Number(valorBaseRef), Number(variacaoRef), sentidoRef)
    : { min: null, max: null };
  return {
    id: it.id,
    descricao_item: String(it?.descricao_item || '').trim(),
    quantidade: it?.quantidade ?? null,
    unidade_medida: it?.unidade_medida || null,
    valor_base_referencia: valorBaseRef,
    variacao_percentual_referencia: variacaoRef,
    variacao_sentido_referencia: sentidoRef,
    valor_min_referencia: faixaCalc.min,
    valor_max_referencia: faixaCalc.max,
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
  bulkMode = false,
  generation = null,
  bulkRunId = null,
  autostartBulk = false,
  signal = undefined,
} = {}) {
  if (!String(descricao || '').trim()) {
    return bulkMode ? { ok: false, exibidos: 0 } : undefined;
  }
  activeSearchOps.value += 1;
  isSearching.value = true;
  if (!append && !bulkMode) searchError.value = '';
  let exibidos = 0;
  const bulkAutostart = bulkMode && bulkRunId != null && autostartBulk;
  const generationStale = () =>
    !bulkAutostart && generation != null && generation !== searchGeneration.value;
  const bulkSuperseded = () => {
    if (autostartBulk) {
      if (bulkAutostartRegistry.pausedByNavigation) return true;
      try {
        return Boolean(getBulkAutostartController()?.signal?.aborted);
      } catch (_) {
        return false;
      }
    }
    return bulkRunId != null && !isBulkRunActive(bulkRunId);
  };
  // Autostart: abortável ao sair do módulo PNCP (liberta API para Dispensa/outros fluxos).
  const fetchSignal = autostartBulk ? getBulkAutostartController()?.signal : signal;
  try {
    const recortes = buildRecortesGeograficosPayload(filtros.cidades);
    const valorBaseCtx = context?.valor_base_referencia ?? null;
    const variacaoCtx = context?.variacao_percentual_referencia ?? null;
    const sentidoCtx = context?.variacao_sentido_referencia ?? 'ambos';
    const faixaAtiva = valorBaseCtx != null
      && Number.isFinite(Number(valorBaseCtx))
      && Number(valorBaseCtx) > 0
      && variacaoCtx != null
      && Number.isFinite(Number(variacaoCtx))
      && Number(variacaoCtx) >= 0;

    const globalVariacaoDefinida = Number.isFinite(Number(variacaoPercentualGlobal.value))
      && Number(variacaoPercentualGlobal.value) >= 0;
    if (context && globalVariacaoDefinida && !faixaAtiva && !bulkMode) {
      searchError.value =
        'Faixa global ativa, mas este item não tem valor BASE salvo. '
        + 'Preencha a coluna BASE em «Itens da cotação» e clique Salvar antes de pesquisar.';
      return { ok: false, exibidos: 0, empty: true };
    }
    const basePayload = {
      somente_homologados: true,
      termo_busca: String(descricao).trim(),
      codigo_modalidade: null,
      max_paginas: bulkMode ? 6 : 500,
      tamanho_pagina: 200,
      quantidade_referencia: context?.quantidade ?? null,
      unidade_medida_referencia: context?.unidade_medida ?? null,
      busca_lote: Boolean(bulkMode),
      valor_base_referencia: faixaAtiva ? Number(valorBaseCtx) : null,
      variacao_percentual_referencia: faixaAtiva ? Number(variacaoCtx) : null,
      variacao_sentido_referencia: faixaAtiva ? sentidoCtx : null,
      fontes_habilitadas: (fontesHabilitadas.value?.length ? fontesHabilitadas.value : ['pncp']),
    };

    const aggregated = [];
    let lastBackend = null;

    function mapBackendToRows(backend, geoKeyPart) {
      if (!backend?.ok || !Array.isArray(backend.itens)) return 0;
      lastBackend = backend;
      const mapped = backend.itens
        .filter((it) => {
          if (!passesPnCpSearchDisplayGate({ sourceRaw: it })) return false;
          if (faixaAtiva) {
            return pnCpRowWithinFaixaRegional(
              { sourceRaw: it },
              valorBaseCtx,
              variacaoCtx,
              sentidoCtx,
            );
          }
          return true;
        })
        .map((it, idx) => {
          const plat = federatedItemPlataforma(it);
          const processoRef = federatedItemProcessoRef(it);
          return {
        esferaAdministrativa: classificarEsferaAdministrativa(it),
        incisoClassificacao: mapEsferaParaInciso(classificarEsferaAdministrativa(it)),
        id: `backend-${context?.id || 'none'}-${geoKeyPart}-${idx}-${plat}-${processoRef || it.numero_pncp || 'x'}-${it.numero_item ?? idx}`,
        plataforma: plat,
        plataformaLabel: plataformaBadgeShort(plat),
        itemId: context?.id ?? itemId.value ?? null,
        itemRefLabel: context?.descricao_item || '-',
        sourceRaw: it,
        numeroPncp: it.numero_pncp || null,
        processoRef,
        anoCompra: it.ano_compra ?? null,
        sequencialCompra: it.sequencial_compra ?? null,
        numeroItem: it.numero_item ?? null,
        titulo: it.descricao_item || it.objeto_resumido || 'Descrição indisponível',
        item: it.descricao_item || it.objeto_resumido || '-',
        normalizado: it.material_servico || resolveTipoItem(it) || '-',
        orgao: it.orgao || '-',
        cidade: formatMunicipioUf(
          { municipio: it.municipio, uf: it.uf, orgao: it.orgao },
          it,
          '-',
        ),
        uf: it.uf || '-',
        municipio: resolveMunicipioUf({ municipio: it.municipio, uf: it.uf, orgao: it.orgao }, it).municipio || null,
        modalidade: (() => {
          const lab = labelModalidadeFonte(
            { modalidade: it.modalidade, processo_id: processoRef, plataforma_item_id: it.plataforma_item_id },
            it,
          );
          return lab !== 'N/D' ? lab : (it.modalidade || '-');
        })(),
        processo: (() => {
          const raw = processoRef || it.numero_pncp || '';
          if (!raw) return '-';
          if (isNotasFiscaisPlatform(plat)) {
            return String(raw).replace(/^notas_fiscais:/i, '').split(':')[0] || String(raw);
          }
          return String(raw);
        })(),
        data: it.data_publicacao || '-',
        qtd: `${it.quantidade || '-'} ${it.unidade_medida || ''}`.trim(),
        quantidadeNum: it.quantidade ?? null,
        unidadeMedida: it.unidade_medida || null,
        valor: formatCurrency(displayPnCpUnitario({ sourceRaw: it })),
        valorUnitario: displayPnCpUnitario({ sourceRaw: it }),
        valorTotal: displayPnCpTotal({ sourceRaw: it }),
        score: Number.isFinite(Number(it.score_aprovacao)) ? Number(it.score_aprovacao) : 0,
        confiabilidade: it.confiabilidade || 'Média',
        risco: it.risco || 'Médio',
        status: it.status || 'Aprovado',
        interpretacaoIa: String(it.ia_interpretacao_item || '').trim() || null,
        similaridadeEncontrada: Boolean(it.similaridade_encontrada),
        fornecedor: pickFornecedorDisplayName({ sourceRaw: it }),
        cnpjFornecedor: extractCnpjFornecedorSalvar({ sourceRaw: it }),
        faixaRegionalItem: faixaAtiva
          ? buildFaixaRegionalItemDisplay(valorBaseCtx, variacaoCtx, sentidoCtx)
          : null,
        selecionado: false,
        backendItensCount: backend.itens.length,
      };
        });
      aggregated.push(...mapped);
      return mapped.length;
    }

    let backendItensTotal = 0;
    const bulkSearchOpts = bulkMode
      ? { timeoutMs: BULK_SEARCH_TIMEOUT_MS, maxAttempts: 2 }
      : undefined;

    async function runGeoSearch(geoPayload, geoKeyPart) {
      if (generationStale() || bulkSuperseded()) {
        return null;
      }
      const backend = await federatedMarketSearch(geoPayload, fetchSignal, bulkSearchOpts);
      return mapBackendToRows(backend, geoKeyPart) || 0;
    }

    if (recortes.length > 0) {
      const n = await runGeoSearch(
        {
          ...basePayload,
          recortes_geograficos: recortes,
          uf: null,
          municipio: null,
        },
        'rec',
      );
      if (n === null) {
        return bulkSearchFailResult(null, { superseded: bulkSuperseded() });
      }
      backendItensTotal += n;
    } else {
      const ufItem = context?.uf_padrao ? String(context.uf_padrao).trim().toUpperCase() : null;
      // Lote autostart: 1 chamada nacional (evita UF vazio + retry BR ≈ 2×90s por item).
      const ufsToRun = bulkMode ? [null] : (ufItem ? [ufItem] : [null]);
      for (const ufCode of ufsToRun) {
        const n = await runGeoSearch(
          {
            ...basePayload,
            uf: ufCode || null,
            municipio: null,
          },
          ufCode || 'all',
        );
        if (n === null) {
          return bulkSearchFailResult(null, { superseded: bulkSuperseded() });
        }
        backendItensTotal += n;
      }
      // Item com UF mas sem match local: ampliar para nacional (comum em cotações hospitalares).
      if (!bulkMode && aggregated.length === 0 && ufItem) {
        const n = await runGeoSearch(
          {
            ...basePayload,
            uf: null,
            municipio: null,
          },
          'br',
        );
        if (n === null) {
          return bulkSearchFailResult(null, { superseded: bulkSuperseded() });
        }
        backendItensTotal += n;
      }
    }
    if (aggregated.length > 0) {
      if (generationStale() || bulkSuperseded()) {
        return bulkSearchFailResult(null, { superseded: bulkSuperseded() || generationStale() });
      }
      // Confia no top3 do backend; sem dedupe agressivo (descrições PNCP iguais colapsavam 3→1).
      const picks = [...aggregated].sort((a, b) => {
        const sa = Number(a.score ?? 0);
        const sb = Number(b.score ?? 0);
        if (sa !== sb) return sb - sa;
        const va = Number(a.valorUnitario ?? a.valorTotal ?? parseMoeda(a.valor));
        const vb = Number(b.valorUnitario ?? b.valorTotal ?? parseMoeda(b.valor));
        return (Number.isFinite(va) ? va : Infinity) - (Number.isFinite(vb) ? vb : Infinity);
      });
      rows.value = append ? [...rows.value, ...picks] : picks;
      if (bulkMode) {
        const sid = Number(cotacaoId.value);
        if (Number.isFinite(sid) && sid > 0) persistBulkUiSnapshot(sid);
      }
      exibidos = picks.length;
      const apiN = Number(lastBackend?.itens?.length ?? backendItensTotal ?? picks.length);
      const filtrosResp = lastBackend?.filtros || {};
      lastSearchDebug.value = {
        termo: String(descricao).trim().slice(0, 80),
        apiItens: apiN,
        exibidos: picks.length,
        faixaAtiva: Boolean(filtrosResp.faixa_regional_min != null && filtrosResp.faixa_regional_max != null),
        faixaMin: filtrosResp.faixa_regional_min,
        faixaMax: filtrosResp.faixa_regional_max,
        faixaSentido: filtrosResp.variacao_sentido_referencia || sentidoCtx,
        faixaResumo: faixaAtiva
          ? formatFaixaResumo(valorBaseCtx, variacaoCtx, filtrosResp.variacao_sentido_referencia || sentidoCtx)
          : '',
        top3Final: lastBackend?.stats?.funil_busca?.top3_final ?? null,
      };
      if (faixaAtiva && apiN < 3 && !bulkMode) {
        searchError.value = `Faixa de preço ativa (${formatFaixaResumo(valorBaseCtx, variacaoCtx, sentidoCtx)}): API retornou ${apiN} cotação(ões). Amplie a variação ou ajuste o valor base.`;
      }
    } else if (!append && !bulkMode) {
      lastSearchDebug.value = {
        termo: String(descricao).trim().slice(0, 80),
        apiItens: 0,
        exibidos: 0,
        faixaAtiva,
        faixaMin: null,
        faixaMax: null,
        top3Final: 0,
      };
      searchError.value = faixaAtiva
        ? 'Nenhuma cotação dentro da faixa de preço configurada para este item.'
        : 'A IA não encontrou cotações aderentes para este termo no recorte atual.';
    }
    return { ok: exibidos > 0, exibidos, empty: exibidos === 0 };
  } catch (err) {
    if (bulkMode) {
      return bulkSearchFailResult(err, {
        superseded: bulkSuperseded() || generationStale(),
        timeoutSec: Math.round(BULK_SEARCH_TIMEOUT_MS / 1000),
      });
    }
    if (isAbortError(err)) return undefined;
    if (generationStale()) return undefined;
    searchError.value = `Não foi possível consultar o backend (${formatResearchError(err)}).`;
    return { ok: false, exibidos: 0, error: formatResearchError(err) };
  } finally {
    activeSearchOps.value -= 1;
    if (activeSearchOps.value < 0) activeSearchOps.value = 0;
    isSearching.value = activeSearchOps.value > 0;
  }
}

function formatCurrency(v) {
  if (v == null || v === '') return 'R$ -';
  const n = Number(v);
  if (!Number.isFinite(n)) return 'R$ -';
  return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function toggleSelecionarTop3() {
  if (!displayedRows.value.length) return;
  const ids = displayedRows.value.map((r) => r.id);
  const mark = !allDisplayedSelecionados.value;
  const next = new Set(selectedRowIds.value);
  for (const id of ids) {
    if (mark) next.add(id);
    else next.delete(id);
  }
  selectedRowIds.value = next;
}

function toggleSelecionarGrupo(group) {
  const ids = group.rows.map((r) => r.id);
  const mark = !group.allSelected;
  const next = new Set(selectedRowIds.value);
  for (const id of ids) {
    if (mark) next.add(id);
    else next.delete(id);
  }
  selectedRowIds.value = next;
}

async function adicionarSelecionadosNaCotacao() {
  if (isSavingSelecionados.value) return;
  const sessionId = Number(cotacaoId.value);
  if (Number.isNaN(sessionId)) {
    saveMessage.value = 'Cotação inválida para salvar no backend.';
    return;
  }
  const brutos = displayedRows.value.filter((r) => selectedRowIds.value.has(r.id));
  const semFornecedor = brutos.filter((r) => !canSalvarCotacaoPnCp(r)).length;
  const foraFaixa = brutos.filter((r) => {
    const fr = r.faixaRegionalItem;
    if (!fr || fr.min == null || fr.max == null) return false;
    return !pnCpRowWithinFaixaRegional(r, fr.base, fr.variacaoPct, fr.sentido || 'ambos');
  });
  if (foraFaixa.length) {
    saveMessage.value = `${foraFaixa.length} preço(s) fora da faixa (VAR) — não podem ser salvos. Ajuste a busca ou a variação.`;
  }
  const selecionados = brutos
    .filter((r) => canSalvarCotacaoPnCp(r))
    .filter((r) => {
      const fr = r.faixaRegionalItem;
      if (!fr || fr.min == null || fr.max == null) return true;
      return pnCpRowWithinFaixaRegional(r, fr.base, fr.variacaoPct, fr.sentido || 'ambos');
    })
    .map((r) => {
      const raw = (r.sourceRaw && typeof r.sourceRaw === 'object') ? r.sourceRaw : {};
      const cad = (raw.fornecedor_cadastro && typeof raw.fornecedor_cadastro === 'object')
        ? raw.fornecedor_cadastro
        : {};
      const homUnit = extractPnCpHomologadoUnit({ sourceRaw: raw });
      const homTotal = extractPnCpHomologadoTotal({ sourceRaw: raw, quantidade: r.quantidadeNum });
      const unitSave = homUnit ?? r.valorUnitario ?? parseMoeda(r.valor);
      const totalSave = homTotal ?? r.valorTotal ?? (unitSave && r.quantidadeNum ? unitSave * r.quantidadeNum : null);
      const plat = resolveRowPlataforma(r);
      const saveMeta = platformSaveMeta(plat, {
        inciso_classificacao: r.incisoClassificacao || null,
        esfera_administrativa: r.esferaAdministrativa || null,
      });
      const incisoSave = saveMeta.inciso_classificacao;
      return {
      item_ref_id: r.itemId ?? null,
      esfera_administrativa: saveMeta.esfera_administrativa,
      inciso_classificacao: incisoSave,
      fonte: saveMeta.fonte,
      numero_pncp: r.numeroPncp,
      ano_compra: r.anoCompra,
      sequencial_compra: r.sequencialCompra,
      numero_item: r.numeroItem,
      descricao_item: r.item,
      orgao: r.orgao,
      municipio: (() => {
        const resolved = resolveMunicipioUf(
          { municipio: r.municipio || raw.municipio, uf: r.uf || raw.uf, orgao: r.orgao || raw.orgao },
          raw,
        );
        return resolved.municipio || null;
      })(),
      uf: r.uf,
      quantidade: r.quantidadeNum,
      unidade_medida: r.unidadeMedida,
      modalidade: (() => {
        const resolved = labelModalidadeFonte(
          {
            modalidade: r.modalidade,
            processo_id: raw.processo_id || r.processoRef,
            plataforma_item_id: raw.plataforma_item_id,
          },
          raw,
        );
        return resolved !== 'N/D' ? resolved : (r.modalidade || null);
      })(),
      valor_unitario: unitSave,
      valor_total: totalSave,
      material_servico: r.normalizado,
      score_aprovacao: r.score,
      confiabilidade: r.confiabilidade,
      risco: r.risco,
      status: r.status,
      similaridade_encontrada: Boolean(r.similaridadeEncontrada),
      data_publicacao: (() => {
        const candidates = [
          r.data,
          raw.data_publicacao,
          raw.data_referencia,
          raw.dataPublicacaoPncp,
        ];
        for (const c of candidates) {
          const s = String(c ?? '').trim();
          if (s && s !== '-' && s !== '—' && s !== 'null' && s !== 'None') return s.slice(0, 64);
        }
        return null;
      })(),
      fornecedor: pickFornecedorDisplayName(r),
      cnpj_fornecedor: extractCnpjFornecedorSalvar(r) || r.cnpjFornecedor || null,
      fornecedor_cadastro: Object.keys(cad).length ? cad : null,
      telefone: raw.telefone || cad.telefone || cad.ddd_telefone_1 || null,
      email: raw.email || cad.email || null,
      situacao: r.sourceRaw?.situacao || r.sourceRaw?.situacaoCompraNome || null,
      situacao_compra: r.sourceRaw?.situacao || r.sourceRaw?.situacaoCompraNome || null,
      situacaoCompraNome: r.sourceRaw?.situacaoCompraNome || r.sourceRaw?.situacao || null,
      situacaoCompraItemNome: r.sourceRaw?.situacaoCompraItemNome || r.sourceRaw?.situacao_item_exibicao || null,
      temResultado: r.sourceRaw?.temResultado ?? null,
      item_homologado: r.sourceRaw?.item_homologado ?? null,
      valor_unitario_estimado: r.sourceRaw?.valor_unitario_estimado ?? null,
      valor_total_estimado: r.sourceRaw?.valor_total_estimado ?? null,
      valor_unitario_homologado: r.sourceRaw?.valor_unitario_homologado ?? homUnit ?? null,
      valor_total_homologado: r.sourceRaw?.valor_total_homologado ?? homTotal ?? null,
      quantidade_homologada: r.sourceRaw?.quantidade_homologada ?? null,
      ano_compra: r.anoCompra ?? r.sourceRaw?.ano_compra ?? null,
      sequencial_compra: r.sequencialCompra ?? r.sourceRaw?.sequencial_compra ?? null,
      plataforma: plat,
      plataforma_item_id: raw.plataforma_item_id || r.processoRef || null,
      processo_id: raw.processo_id || r.processoRef || null,
      url_origem: raw.url_origem || raw.link_licitacon_cidadao || null,
      source: {
        ...raw,
        plataforma: plat,
        url_origem: raw.url_origem || raw.link_licitacon_cidadao || null,
        fornecedor: pickFornecedorDisplayName(r),
        cnpj_fornecedor: extractCnpjFornecedorSalvar(r) || r.cnpjFornecedor || null,
      },
    };
    });
  if (!selecionados.length) {
    saveMessage.value = semFornecedor > 0
      ? 'Nenhuma fonte com CNPJ de fornecedor homologado. Itens em andamento não entram na cotação.'
      : 'Selecione ao menos um item.';
    return;
  }
  if (semFornecedor > 0) {
    saveMessage.value = `${semFornecedor} fonte(s) ignorada(s) por não ter CNPJ de fornecedor.`;
  }
  const MAX_ITENS_POR_ENVIO = 2000;
  let enviar = selecionados;
  if (selecionados.length > MAX_ITENS_POR_ENVIO) {
    enviar = selecionados.slice(0, MAX_ITENS_POR_ENVIO);
    saveMessage.value = `Limite de ${MAX_ITENS_POR_ENVIO} itens por envio; gravando os primeiros ${MAX_ITENS_POR_ENVIO}.`;
  }
  try {
    isSavingSelecionados.value = true;
    const stats = await persistCotacoesToResearchSession(sessionId, enviar, {
      routeItemId: itemId.value,
      onProgress: ({ done, total, cotacoesEnviadas, totalCotacoes }) => {
        const nCot = Number(totalCotacoes) || enviar.length;
        const env = Number(cotacoesEnviadas) || 0;
        if (nCot > 0) {
          saveMessage.value = `Salvando... ${env}/${nCot} cotação(ões)`;
          if (Number(total) > 1) {
            saveMessage.value += ` — item ${done}/${total} da cotação`;
          }
        } else if (Number(total) > 1) {
          saveMessage.value = `Salvando... item ${done}/${total} da cotação`;
        }
      },
    });
    saveMessage.value = formatCotacaoSaveFeedback(stats, {
      routeItemId: itemId.value,
      semFornecedorUi: semFornecedor,
    });
    if (shouldClearSavedSelection(stats, enviar.length)) {
      const savedIds = new Set(displayedRows.value.filter((r) => selectedRowIds.value.has(r.id)).map((r) => r.id));
      rows.value = rows.value.filter((r) => !savedIds.has(r.id));
      const next = new Set(selectedRowIds.value);
      for (const id of savedIds) next.delete(id);
      selectedRowIds.value = next;
    }
    if (stats.inseridas > 0 || stats.itensNovos > 0) {
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

onMounted(async () => {
  isLoadingFontes.value = true;
  try {
    try {
      localStats.value = await getLocalIndexStatsResilient();
    } catch (_) {
      localStats.value = null;
    }
    const catalog = await loadPriceSourcesCatalog();
    if (localStats.value) {
      fontesCatalog.value = mergeFontesWithLocalStats(catalog, localStats.value);
    } else {
      fontesCatalog.value = applyFontesWhenStatsUnavailable(catalog);
    }
    fontesHabilitadas.value = pickDefaultFontes(fontesCatalog.value);
  } finally {
    isLoadingFontes.value = false;
  }

  const sessionId = Number(cotacaoId.value);
  if (!Number.isFinite(sessionId) || sessionId <= 0) return;
  const mountRunId = ++mountRunSeq;

  // Remontagem no meio do autostart: reanexar UI ao bulk em curso (não reiniciar).
  if (autostart.value && bulkAutostartRegistry.isRunning && Number(bulkAutostartRegistry.sessionId) === sessionId) {
    await awaitBulkAutostartRegistry(sessionId);
    return;
  }

  if (
    bulkAutostartRegistry.pausedByNavigation
    && Number(bulkAutostartRegistry.sessionId) === sessionId
  ) {
    applyBulkUiSnapshot(sessionId);
    const p = autoSearchProgress.value;
    if (p.total > 0 && p.done < p.total) {
      searchError.value =
        `Busca pausada ao sair do pesquisador (${p.done}/${p.total}). Clique «Pesquisar UF» para continuar.`;
    }
    clearBulkPausedFlag();
    return;
  }

  if (!bulkAutostartRegistry.isRunning) {
    autoSearchProgress.value = { done: 0, total: 0, ok: 0, fail: 0, empty: 0, precos: 0, skipped: 0 };
    searchError.value = '';
  }
  try {
    let data;
    let itens = [];
    let stats = null;

    if (itemId.value) {
      data = await getResearchSession(sessionId);
      itens = Array.isArray(data?.itens) ? data.itens : [];
      stats = null;
    } else {
      isLoadingSessionItems.value = true;
      try {
        const bulk = await fetchAllItemsForBulkSearch(sessionId, {
          somenteIncompletos: !rebuscarCompletos.value,
          onPage: ({ loaded, stats: st }) => {
            const total = Number(st?.total_incompletos ?? st?.total_itens ?? 0);
            sessionItemsLoadHint.value = total > 0 ? `${loaded}/${total}` : String(loaded);
          },
        });
        data = { sessao: bulk.sessao, ok: true };
        itens = Array.isArray(bulk.itens) ? bulk.itens : [];
        stats = bulk.stats || null;
      } catch (bulkErr) {
        const msg = String(bulkErr?.message || '');
        if (/not found|404|search-context/i.test(msg)) {
          data = await getResearchSession(sessionId);
          itens = Array.isArray(data?.itens) ? data.itens : [];
          stats = data?.stats || null;
        } else {
          throw bulkErr;
        }
      } finally {
        isLoadingSessionItems.value = false;
        sessionItemsLoadHint.value = '';
      }
    }

    const filtrosSessao = (data?.sessao?.filtros && typeof data.sessao.filtros === 'object') ? data.sessao.filtros : {};
    const variacaoGlobal = Number(
      filtrosSessao.variacao_percentual_global ?? filtrosSessao.variacao_global_percentual ?? null,
    );
    variacaoPercentualGlobal.value = Number.isFinite(variacaoGlobal) && variacaoGlobal >= 0
      ? variacaoGlobal
      : null;
    const sentidoRaw = String(filtrosSessao.variacao_sentido_global || '').trim().toLowerCase();
    variacaoSentidoGlobal.value = ['cima', 'baixo', 'ambos'].includes(sentidoRaw) ? sentidoRaw : 'ambos';
    const totalSessao = Number(data?.sessao?.total_itens ?? data?.stats?.total_itens ?? stats?.total_itens ?? itens.length);
    if (mountRunId !== mountRunSeq) return;
    const apiOk = refreshCotacaoResumo(itens, totalSessao, stats);
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
      if (mountRunId !== mountRunSeq) return;
      if (bulkAutostartRegistry.isRunning && Number(bulkAutostartRegistry.sessionId) === sessionId) {
        await awaitBulkAutostartRegistry(sessionId);
        return;
      }
      if (!apiOk) return;
      const pendentes = buildPendentesFromItens(itens);
      const esperados = Number(stats?.total_incompletos ?? cotacaoResumo.value.incompletos ?? pendentes.length);
      if (!pendentes.length) {
        if (esperados > 0) {
          searchError.value =
            `Há ${esperados} item(ns) incompletos na cotação, mas nenhum foi carregado para busca. Recarregue após deploy do backend.`;
        } else {
          searchError.value = rebuscarCompletos.value
            ? 'Nenhum item com descrição para buscar.'
            : 'Todos os itens da cotação já estão completos (3+ preços salvos no backend).';
        }
        return;
      }
      const pendentesCtx = pendentes.map((it) => buildContextFromItem(it)).filter((x) => x.descricao_item);
      if (mountRunId !== mountRunSeq) return;
      await launchBulkAutostart(sessionId, pendentesCtx);
    }
  } catch (err) {
    isLoadingSessionItems.value = false;
    isAutoSearchingAll.value = false;
    if (bulkAutostartRegistry.isRunning && Number(bulkAutostartRegistry.sessionId) === sessionId) {
      bulkAutostartRegistry.isRunning = false;
      bulkAutostartRegistry.promise = null;
    }
    searchError.value = `Não foi possível carregar a cotação (${err?.message || 'erro desconhecido'}).`;
  }
});

onBeforeUnmount(() => {
  // Remontagem na mesma rota (Strict Mode): bulk autostart continua.
  if (bulkAutostartRegistry.isRunning && isPncpResearchRoute(route)) return;
  try {
    searchAbortController?.abort();
  } catch (_) {
    /* ignore */
  }
});

// Não abortar bulk no unmount da mesma rota — remontagem Vue (Strict Mode) gerava falhas fantasma.

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

function biaMetaParts(row) {
  return [row?.modalidade, row?.status, row?.normalizado]
    .map((v) => String(v || '').trim())
    .filter((v) => v && v !== '-');
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
  const plat = normalizeKey(
    raw?.plataforma || raw?.sourceRaw?.plataforma || '',
  );
  if (isTceRsPlatform(plat)) {
    return 'estadual';
  }
  if (isComprasGovPlatform(plat)) {
    return 'federal';
  }
  if (isNotasFiscaisPlatform(plat)) {
    return 'federal';
  }

  const inciso = normalizeKey(
    raw?.inciso_classificacao || raw?.incisoClassificacao || raw?.sourceRaw?.inciso_classificacao || '',
  );
  if (inciso.includes('inciso_ii') || inciso === 'inciso-ii') return 'estadual';
  if (inciso.includes('inciso_i') || inciso === 'inciso-i') return 'federal';

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
  ];
  const joined = candidatos.map((x) => normalizeKey(x)).filter(Boolean).join(' | ');
  if (joined.includes('federal') || joined.includes('uniao') || joined.includes('união')) return 'federal';
  if (joined.includes('estadual') || joined.includes('estado')) return 'estadual';
  if (joined.includes('municipal') || joined.includes('municipio') || joined.includes('município')) return 'municipal';
  if (joined.includes('distrital')) return 'distrital';
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

.bia-faixa-banner {
  margin: 0;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid #c5d9ef;
  background: #eef5fc;
  font-size: 13px;
  color: #1e3a5f;
}
.bia-faixa-banner__hint {
  display: block;
  margin-top: 4px;
  font-size: 11px;
  color: #64748b;
}

.bia-faixa-cell {
  min-width: 118px;
  font-size: 11px;
  line-height: 1.35;
  color: #334155;
}
.bia-faixa-cell__row {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-bottom: 2px;
}
.bia-faixa-cell__label {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: #64748b;
}
.bia-faixa-cell__range {
  margin-top: 2px;
  font-size: 10px;
  color: #0f4c81;
  font-weight: 600;
}

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
.bia-fontes-panel {
  border: 1px solid #dbe4f0;
  border-radius: 12px;
  background: #fbfdff;
  padding: 12px 14px;
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.bia-plat-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  border: 1px solid #dbe4f0;
  background: #f4f8fc;
  color: #2f557d;
}
.bia-plat-badge--tce_rs {
  background: #eef6ff;
  border-color: #c5daf5;
  color: #1e4f8a;
}
.bia-plat-badge--compras_gov {
  background: #f3f0ff;
  border-color: #d4c8f5;
  color: #4c3d8a;
}
.bia-plat-badge--notas_fiscais {
  background: #fffbeb;
  border-color: #fcd34d;
  color: #92400e;
}
.bia-plat-badge--pncp {
  background: #eef8f2;
  border-color: #c8e6d4;
  color: #1f6b45;
}
.bia-fontes-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  margin-top: 4px;
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
.bia-group-media {
  font-size: 12px;
  font-weight: 500;
  color: #475569;
}
.bia-group-media strong { color: #0f4c81; font-weight: 700; }
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
