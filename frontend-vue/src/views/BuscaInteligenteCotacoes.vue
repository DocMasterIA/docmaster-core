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
        <label class="bia-filter">
          <span>Descricao</span>
          <input v-model.trim="filtros.descricao" type="text" placeholder="Ex.: PARAFUSO DE AÇO" />
        </label>
        <div class="bia-filter">
          <span>UF</span>
          <details class="bia-uf-dropdown">
            <summary class="bia-uf-dropdown__summary">
              <span>{{ selectedUfLabel }}</span>
              <i class="fa-solid fa-chevron-down" aria-hidden="true"></i>
            </summary>
            <div class="bia-uf-dropdown__menu" role="group" aria-label="Selecionar UFs">
              <label class="bia-uf-dropdown__item bia-uf-dropdown__item--all">
                <input
                  type="checkbox"
                  :checked="allUfsSelected"
                  :indeterminate.prop="isPartiallySelectedUf"
                  @change="toggleAllUfs"
                />
                <span>Todos os estados</span>
              </label>
              <label
                v-for="uf in ufOptions"
                :key="uf.code"
                class="bia-uf-dropdown__item"
              >
                <input
                  type="checkbox"
                  :checked="filtros.ufs.includes(uf.code)"
                  @change="toggleUf(uf.code)"
                />
                <img :src="uf.flag" :alt="`Bandeira ${uf.code}`" class="bia-uf-option__flag" />
                <span>{{ uf.code }} - {{ uf.name }}</span>
              </label>
            </div>
          </details>
        </div>
        <button type="button" class="bia-search-btn" @click="applyFilters">Buscar</button>
      </section>
      <p v-if="searchError" class="bia-meta bia-meta--error">{{ searchError }}</p>
      <p v-else-if="isSearching" class="bia-meta">Consultando backend PNCP...</p>

      <section class="bia-table-shell">
        <div class="bia-table-head">
          <div class="bia-table-head__pills">
            <span class="bia-pill bia-pill--ok">{{ displayedRows.length }} resultados</span>
            <span class="bia-pill">{{ totalUfs }} UFs</span>
          </div>
          <RouterLink
            :to="`/pesquisador-pncp/cotacoes/${cotacaoId}`"
            class="bia-add-cotacao-btn bia-add-cotacao-btn--ghost"
          >
            Ir para cotação
          </RouterLink>
          <button
            type="button"
            class="bia-add-cotacao-btn"
            :disabled="isSavingSelecionados || totalSelecionados === 0"
            @click="adicionarSelecionadosNaCotacao"
          >
            {{ isSavingSelecionados ? 'Salvando...' : 'Salvar selecionados' }}
          </button>
        </div>
        <p v-if="saveMessage" class="bia-meta">{{ saveMessage }}</p>

        <div class="bia-table-scroll">
          <table class="bia-table">
            <thead>
              <tr>
                <th>Seleção</th>
                <th>Cotação</th>
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
              <tr v-for="row in displayedRows" :key="row.id">
                <td class="bia-cell-center">
                  <input type="checkbox" :checked="row.selecionado" @change="toggleSelecionado(row.id)" />
                </td>
                <td>
                  <div class="bia-main">{{ row.titulo }}</div>
                  <div class="bia-sub">
                    <span class="bia-meta-token">{{ row.orgao }}</span>
                    <span v-if="row.cidade && row.cidade !== '-'" class="bia-meta-sep">·</span>
                    <span v-if="row.cidade && row.cidade !== '-'">{{ row.cidade }}</span>
                  </div>
                  <div class="bia-sub">
                    {{ row.modalidade }} • {{ row.status }} • {{ row.normalizado }}
                  </div>
                </td>
                <td>{{ row.qtd }}</td>
                <td class="bia-cell-center">{{ row.uf }}</td>
                <td class="bia-cell-center">{{ row.data }}</td>
                <td class="bia-bold">{{ row.valor }}</td>
                <td class="bia-cell-center">
                  <span
                    class="bia-badge"
                    :class="confiabilidadeClass(row.confiabilidade)"
                  >
                    {{ row.confiabilidade }}
                  </span>
                </td>
                <td class="bia-cell-center">
                  <span
                    class="bia-badge"
                    :class="riscoClass(row.risco)"
                  >
                    {{ row.risco }}
                  </span>
                </td>
                <td class="bia-cell-center">{{ row.score }}</td>
                <td>{{ row.processo }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed, reactive, ref } from 'vue';
import { useRoute } from 'vue-router';
import { addItemsToResearchSession, intelligentMarketSearch } from '../services/pncpResearch';

const route = useRoute();
const cotacaoId = computed(() => route.params.cotacaoId || 'CT-2026-00421');

const filtros = reactive({
  descricao: '',
  ufs: [],
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

function toggleUf(code) {
  if (filtros.ufs.includes(code)) {
    filtros.ufs = filtros.ufs.filter((uf) => uf !== code);
    return;
  }
  filtros.ufs.push(code);
}

const selectedUfLabel = computed(() => {
  if (!filtros.ufs.length) return 'Selecionar UFs';
  if (filtros.ufs.length <= 3) return filtros.ufs.join(', ');
  return `${filtros.ufs.length} UFs selecionadas`;
});

const allUfsSelected = computed(() => filtros.ufs.length === ufOptions.length);

const isPartiallySelectedUf = computed(
  () => filtros.ufs.length > 0 && filtros.ufs.length < ufOptions.length,
);

function toggleAllUfs(event) {
  if (event.target.checked) {
    filtros.ufs = ufOptions.map((uf) => uf.code);
    return;
  }
  filtros.ufs = [];
}

const rows = ref([]);
const isSearching = ref(false);
const searchError = ref('');
const saveMessage = ref('');
const isSavingSelecionados = ref(false);
const totalSelecionados = computed(() => displayedRows.value.filter((x) => x.selecionado).length);
const totalUfs = computed(() => new Set(displayedRows.value.map((x) => x.uf).filter(Boolean)).size);
const mediaValor = computed(() => {
  const nums = displayedRows.value.map((x) => parseMoeda(x.valor)).filter((x) => typeof x === 'number');
  if (!nums.length) return 'R$ -';
  const media = nums.reduce((a, b) => a + b, 0) / nums.length;
  return formatCurrency(media);
});
function confiabilidadeClass(value) {
  if (value === 'Alta') return 'bia-badge--ok';
  if (value === 'Media' || value === 'Média') return 'bia-badge--warn';
  if (value === 'Baixa') return 'bia-badge--danger';
  return '';
}

function riscoClass(value) {
  if (value === 'Baixo') return 'bia-badge--ok';
  if (value === 'Medio' || value === 'Médio') return 'bia-badge--warn';
  if (value === 'Alto') return 'bia-badge--danger';
  return '';
}

const displayedRows = computed(() => {
  const base = [...rows.value];
  let filtrados = base;
  if (filtros.ufs.length > 0 && filtros.ufs.length < ufOptions.length) {
    const selected = new Set(filtros.ufs);
    filtrados = filtrados.filter((item) => selected.has(String(item.uf || '').toUpperCase()));
  }
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

async function applyFilters() {
  if (!filtros.descricao.trim()) return;
  isSearching.value = true;
  searchError.value = '';
  try {
    const backend = await intelligentMarketSearch({
      termo_busca: filtros.descricao.trim(),
      uf: filtros.ufs.length === 1 ? filtros.ufs[0] : null,
      codigo_modalidade: null,
      max_paginas: 500,
      tamanho_pagina: 200,
    });
    if (backend?.ok && Array.isArray(backend.itens)) {
      const mapped = backend.itens.map((it, idx) => ({
        id: `backend-${idx}-${it.numero_pncp || ''}`,
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
        selecionado: false,
      }));
      rows.value = mapped;
      if (!mapped.length) {
        searchError.value = 'A IA não encontrou 3 cotações aderentes para este termo no recorte atual.';
      }
    }
  } catch (err) {
    searchError.value = `Não foi possível consultar o backend (${err.message || 'erro desconhecido'}).`;
  } finally {
    isSearching.value = false;
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

async function adicionarSelecionadosNaCotacao() {
  if (isSavingSelecionados.value) return;
  const sessionId = Number(cotacaoId.value);
  if (Number.isNaN(sessionId)) {
    saveMessage.value = 'Cotação inválida para salvar no backend.';
    return;
  }
  const itens = displayedRows.value
    .filter((r) => r.selecionado)
    .map((r) => ({
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
    }));
  if (!itens.length) {
    saveMessage.value = 'Selecione ao menos um item.';
    return;
  }
  const MAX_ITENS_POR_ENVIO = 2000;
  let enviar = itens;
  if (itens.length > MAX_ITENS_POR_ENVIO) {
    enviar = itens.slice(0, MAX_ITENS_POR_ENVIO);
    saveMessage.value = `Limite de ${MAX_ITENS_POR_ENVIO} itens por envio; gravando os primeiros ${MAX_ITENS_POR_ENVIO}.`;
  }
  try {
    isSavingSelecionados.value = true;
    const res = await addItemsToResearchSession(sessionId, enviar);
    saveMessage.value = `${res.itens_inseridos ?? enviar.length} item(ns) adicionados à cotação.`;
  } catch (err) {
    saveMessage.value = `Falha ao salvar: ${err.message || 'erro desconhecido'}`;
  } finally {
    isSavingSelecionados.value = false;
  }
}

function parseMoeda(v) {
  const n = Number(String(v || '').replace(/[^\d,.-]/g, '').replace(',', '.'));
  return Number.isNaN(n) ? null : n;
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

.bia-filters { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 6px; align-items: stretch; }
.bia-controls { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px; }
.bia-controls__left,
.bia-controls__right { display: flex; flex-wrap: wrap; gap: 8px; }
.bia-filter { border: 1px solid #d6dde8; border-radius: 10px; background: #f8fafc; padding: 7px 8px; display: flex; flex-direction: column; gap: 4px; }
.bia-filter > span { font-size: 9px; color: #64748b; text-transform: uppercase; line-height: 1.1; }
.bia-meta { margin: 2px 0 0; font-size: 12px; color: #64748b; }
.bia-meta--error { color: #b91c1c; }
.bia-filter input,
.bia-filter select {
  border: 1px solid #cfd8e3;
  border-radius: 8px;
  background: #fff;
  color: #0f172a;
  font-size: 12px;
  padding: 6px 8px;
  outline: none;
}

.bia-uf-option__flag {
  width: 18px;
  height: 13px;
  object-fit: cover;
  border-radius: 2px;
}

.bia-uf-dropdown {
  position: relative;
}

.bia-uf-dropdown__summary {
  list-style: none;
  border: 1px solid #cfd8e3;
  border-radius: 8px;
  background: #fff;
  color: #1f2937;
  font-size: 12px;
  padding: 6px 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
}

.bia-uf-dropdown__summary::-webkit-details-marker {
  display: none;
}

.bia-uf-dropdown__menu {
  position: absolute;
  z-index: 20;
  top: calc(100% + 6px);
  left: 0;
  width: 100%;
  min-width: 280px;
  max-height: 270px;
  overflow: auto;
  border: 1px solid #cfd8e3;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);
  padding: 6px;
}

.bia-uf-dropdown__item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 12px;
}

.bia-uf-dropdown__item:hover {
  background: #f6f9fc;
}

.bia-uf-dropdown__item input {
  margin: 0;
}

.bia-uf-dropdown__item--all {
  border-bottom: 1px solid #e5eaf3;
  margin-bottom: 4px;
  padding-bottom: 8px;
  font-weight: 600;
}

.bia-filter input:focus,
.bia-filter select:focus {
  border-color: #1f4e79;
  box-shadow: 0 0 0 2px rgba(31, 78, 121, 0.12);
}
.bia-search-btn {
  height: 100%;
  min-height: 52px;
  border-radius: 10px;
  border: 1px solid #1f4e79;
  background: #1f4e79;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  align-self: stretch;
}

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
  margin-left: auto;
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
.bia-table { width: 100%; min-width: 1300px; border-collapse: collapse; table-layout: fixed; }
.bia-table th, .bia-table td { border-bottom: 1px solid #e5eaf3; padding: 10px 8px; font-size: 12px; vertical-align: top; }
.bia-table th { text-align: left; font-size: 11px; text-transform: uppercase; color: #64748b; background: #fff; }
.bia-table th:last-child,
.bia-table td:last-child {
  padding-right: 14px;
}
.bia-main { font-weight: 600; color: #0f172a; line-height: 1.3; }
.bia-sub { color: #64748b; margin-top: 4px; line-height: 1.4; }
.bia-cell-center { text-align: center; }
.bia-meta-token { white-space: nowrap; }
.bia-meta-sep { margin: 0 6px; color: #94a3b8; }
.bia-bold { font-weight: 700; white-space: nowrap; }
.bia-badge { display: inline-flex; border: 1px solid #d5dde9; border-radius: 999px; padding: 2px 8px; font-size: 10px; white-space: nowrap; }
.bia-badge--ok { border-color: #b7d2ef; background: #e8f1fb; color: #1f4e79; }
.bia-badge--warn { border-color: #f2dfb7; background: #fff7e6; color: #9a6a10; }
.bia-badge--danger { border-color: #f0c8c8; background: #fff0f0; color: #a63f3f; }
</style>
