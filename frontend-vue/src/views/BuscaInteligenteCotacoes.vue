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
          <strong>{{ filteredRows.length }}</strong>
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
          <input v-model.trim="filtros.descricao" type="text" placeholder="Ex.: ABACATE" />
        </label>
        <label class="bia-filter">
          <span>Periodo</span>
          <select v-model="filtros.periodo">
            <option>Ultimos 3 meses</option>
            <option>Ultimos 6 meses</option>
            <option>Ultimos 12 meses</option>
            <option>Ultimos 24 meses</option>
          </select>
        </label>
        <label class="bia-filter">
          <span>Tipo</span>
          <select v-model="filtros.tipo">
            <option>Material</option>
            <option>Servico</option>
          </select>
        </label>
        <label class="bia-filter">
          <span>Modalidade</span>
          <select v-model="filtros.modalidade">
            <option>Todas</option>
            <option>Pregao Eletronico</option>
            <option>Chamada Publica</option>
            <option>Dispensa Eletronica</option>
            <option>Pregao Eletronico SRP</option>
          </select>
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
          </div>
          <RouterLink
            :to="`/pesquisador-pncp/cotacoes/${cotacaoId}`"
            class="bia-add-cotacao-btn"
          >
            <i class="fa-solid fa-plus" aria-hidden="true"></i>
            Adicionar itens na cotação {{ cotacaoId }}
          </RouterLink>
          <button type="button" class="bia-add-cotacao-btn" @click="adicionarSelecionadosNaCotacao">
            Salvar selecionados
          </button>
        </div>
        <p v-if="saveMessage" class="bia-meta">{{ saveMessage }}</p>

        <div class="bia-table-scroll">
          <table class="bia-table">
            <thead>
              <tr>
                <th>Selecao</th>
                <th>Cotacao</th>
                <th>Orgao / Local</th>
                <th>Processo</th>
                <th>Qtd.</th>
                <th>Valor</th>
                <th>Score</th>
                <th>Confiabilidade</th>
                <th>Risco</th>
                <th>Status</th>
                <th>Acoes</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in displayedRows" :key="row.id">
                <td><input type="checkbox" :checked="row.selecionado" @change="toggleSelecionado(row.id)" /></td>
                <td>
                  <div class="bia-cotacao-line">
                    <div class="bia-main">{{ row.titulo }}</div>
                    <div class="bia-meta-inline">
                      <span>Item: <strong>{{ row.item }}</strong></span>
                      <span>IA: <strong>{{ row.normalizado }}</strong></span>
                      <span>Modalidade: {{ row.modalidade }} • Data: {{ row.data }}</span>
                    </div>
                  </div>
                </td>
                <td>
                  <div class="bia-main">{{ row.orgao }}</div>
                  <div class="bia-sub">{{ row.cidade }}</div>
                </td>
                <td>{{ row.processo }}</td>
                <td>{{ row.qtd }}</td>
                <td class="bia-bold">{{ row.valor }}</td>
                <td>{{ row.score }}</td>
                <td>
                  <span
                    class="bia-badge"
                    :class="confiabilidadeClass(row.confiabilidade)"
                  >
                    {{ row.confiabilidade }}
                  </span>
                </td>
                <td>
                  <span
                    class="bia-badge"
                    :class="riscoClass(row.risco)"
                  >
                    {{ row.risco }}
                  </span>
                </td>
                <td><span class="bia-badge">{{ row.status }}</span></td>
                <td>
                  <div class="bia-actions">
                    <button type="button" class="bia-action-btn bia-action-btn--primary">
                      <i class="fa-solid fa-folder-open" aria-hidden="true"></i>
                      Docs
                    </button>
                    <button type="button" class="bia-action-btn">
                      <i class="fa-solid fa-wand-magic-sparkles" aria-hidden="true"></i>
                      IA
                    </button>
                  </div>
                </td>
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
import { addItemsToResearchSession, searchLocalItems } from '../services/pncpResearch';

const route = useRoute();
const cotacaoId = computed(() => route.params.cotacaoId || 'CT-2026-00421');

const filtros = reactive({
  descricao: 'ABACATE',
  periodo: 'Ultimos 12 meses',
  tipo: 'Material',
  modalidade: 'Todas',
  ufs: ['GO', 'MS'],
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
const filteredRows = ref([]);
const displayedRows = computed(() => filteredRows.value);
const isSearching = ref(false);
const searchError = ref('');
const saveMessage = ref('');
const totalSelecionados = computed(() => filteredRows.value.filter((x) => x.selecionado).length);
const mediaValor = computed(() => {
  const nums = filteredRows.value.map((x) => parseMoeda(x.valor)).filter((x) => typeof x === 'number');
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

async function applyFilters() {
  if (!filtros.descricao.trim()) return;
  isSearching.value = true;
  searchError.value = '';
  try {
    const backend = await searchLocalItems({
      termo_busca: filtros.descricao.trim(),
      uf: filtros.ufs.length === 1 ? filtros.ufs[0] : null,
      codigo_modalidade: null,
      max_paginas: 1,
      tamanho_pagina: 50,
    });
    if (backend?.ok && Array.isArray(backend.itens)) {
      const mapped = backend.itens.map((it, idx) => ({
        id: `backend-${idx}-${it.numero_pncp || ''}`,
        numeroPncp: it.numero_pncp || null,
        titulo: it.descricao_item || it.objeto_resumido || 'Item sem descrição',
        item: it.descricao_item || '-',
        normalizado: it.material_servico || '-',
        orgao: it.orgao || '-',
        cidade: `${it.municipio || '-'}${it.uf ? `/${it.uf}` : ''}`,
        modalidade: it.modalidade || '-',
        processo: it.numero_pncp || '-',
        data: it.data_publicacao || '-',
        qtd: it.quantidade || '-',
        valor: formatCurrency(it.valor_unitario ?? it.valor_total ?? 0),
        score: '-',
        confiabilidade: 'Média',
        risco: 'Médio',
        status: 'Disponível',
        selecionado: false,
      }));
      rows.value = mapped;
      filteredRows.value = mapped;
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
  filteredRows.value = filteredRows.value.map((r) => (r.id === id ? { ...r, selecionado: !r.selecionado } : r));
}

async function adicionarSelecionadosNaCotacao() {
  const sessionId = Number(cotacaoId.value);
  if (Number.isNaN(sessionId)) {
    saveMessage.value = 'Cotação inválida para salvar no backend.';
    return;
  }
  const itens = filteredRows.value
    .filter((r) => r.selecionado)
    .map((r) => ({
      numero_pncp: r.numeroPncp,
      descricao_item: r.item,
      orgao: r.orgao,
      municipio: r.cidade,
      modalidade: r.modalidade,
      valor_unitario: parseMoeda(r.valor),
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
    const res = await addItemsToResearchSession(sessionId, enviar);
    saveMessage.value = `${res.itens_inseridos ?? enviar.length} item(ns) adicionados à cotação.`;
  } catch (err) {
    saveMessage.value = `Falha ao salvar: ${err.message || 'erro desconhecido'}`;
  }
}

function parseMoeda(v) {
  const n = Number(String(v || '').replace(/[^\d,.-]/g, '').replace(',', '.'));
  return Number.isNaN(n) ? null : n;
}

onMounted(() => {
  applyFilters();
});
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
.bia-cotacao-line { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
.bia-meta-inline { display: inline-flex; gap: 10px; flex-wrap: wrap; color: #64748b; font-size: 11px; line-height: 1.3; }
.bia-meta-inline span { white-space: nowrap; }
.bia-bold { font-weight: 700; white-space: nowrap; }
.bia-badge { display: inline-flex; border: 1px solid #d5dde9; border-radius: 999px; padding: 2px 8px; font-size: 10px; white-space: nowrap; }
.bia-badge--ok { border-color: #b7d2ef; background: #e8f1fb; color: #1f4e79; }
.bia-badge--warn { border-color: #f2dfb7; background: #fff7e6; color: #9a6a10; }
.bia-badge--danger { border-color: #f0c8c8; background: #fff0f0; color: #a63f3f; }
.bia-actions { display: flex; flex-direction: row; gap: 4px; min-width: 94px; }
.bia-action-btn {
  border: 1px solid #cfd8e3;
  border-radius: 8px;
  background: #fff;
  color: #1f2937;
  padding: 5px 6px;
  font-size: 10px;
  text-align: center;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-width: 44px;
  transition: background-color .15s ease, border-color .15s ease, color .15s ease;
}

.bia-action-btn:hover {
  background: #f6f9fc;
}

.bia-action-btn:focus-visible {
  outline: none;
  border-color: #1f4e79;
  box-shadow: 0 0 0 2px rgba(31, 78, 121, 0.12);
}

.bia-action-btn--primary {
  border-color: #1f4e79;
  background: #e8f1fb;
  color: #1f4e79;
}
</style>
