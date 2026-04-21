<template>
  <section class="gov-page">
    <header class="gov-page__header">
      <div class="item-header-row">
        <div>
          <h1 class="gov-page__title">Item da cotação</h1>
          <p class="gov-page__subtitle">
            Cotação #{{ cotacaoId }} · Item #{{ itemId }}
          </p>
        </div>
        <RouterLink :to="`/pesquisador-pncp/cotacoes/${cotacaoId}`" class="item-back-btn">
          <i class="fa-solid fa-arrow-left" aria-hidden="true"></i>
          Voltar para cotação
        </RouterLink>
      </div>
    </header>

    <div class="gov-surface gov-page__content">
      <p v-if="isLoading" class="item-meta">Carregando item...</p>
      <p v-else-if="loadError" class="item-meta item-meta--error">{{ loadError }}</p>

      <template v-else-if="item">
        <section class="item-summary">
          <div class="item-card item-card--wide">
            <span class="item-card__label">Descrição</span>
            <strong>{{ item.descricao_item || '—' }}</strong>
          </div>
          <div class="item-card">
            <span class="item-card__label">Quantidade</span>
            <strong>{{ quantidadeRefletida ?? '—' }}</strong>
          </div>
          <div class="item-card">
            <span class="item-card__label">Unidade</span>
            <strong>{{ unidadeRefletida || '—' }}</strong>
          </div>
          <div class="item-card">
            <span class="item-card__label">Órgão</span>
            <strong>{{ item.orgao || '—' }}</strong>
          </div>
          <div class="item-card">
            <span class="item-card__label">Município/UF</span>
            <strong>{{ itemCidadeUf }}</strong>
          </div>
          <div class="item-card">
            <span class="item-card__label">Modalidade</span>
            <strong>{{ item.modalidade || '—' }}</strong>
          </div>
          <div class="item-card">
            <span class="item-card__label">Número PNCP</span>
            <strong>{{ item.numero_pncp || '—' }}</strong>
          </div>
          <div class="item-card">
            <span class="item-card__label">Data do registro</span>
            <strong>{{ formatDateTimePt(item.created_at) }}</strong>
          </div>
        </section>

        <section class="item-prices">
          <div class="item-price-card">
            <span>Valor unitário</span>
            <strong>{{ formatCurrency(item.valor_unitario) }}</strong>
          </div>
          <div class="item-price-card">
            <span>Valor total</span>
            <strong>{{ formatCurrency(valorTotalRefletido) }}</strong>
          </div>
          <div class="item-price-card">
            <span>Valor base (faixa regional)</span>
            <strong>{{ formatCurrency(faixaValorBase) }}</strong>
          </div>
          <div class="item-price-card">
            <span>Variação (%)</span>
            <strong>{{ faixaVariacaoFmt }}</strong>
          </div>
        </section>

        <section class="item-actions">
          <RouterLink
            class="item-search-btn"
            :to="`/pesquisador-pncp/cotacoes/${cotacaoId}/busca-inteligente?itemId=${itemId}`"
          >
            <i class="fa-solid fa-robot" aria-hidden="true"></i>
            Buscar preços com I.A para este item
          </RouterLink>
        </section>

        <section class="item-related">
          <h2>Cotações de preço deste item</h2>
          <p class="item-meta">
            {{ itemCotacoesFiltradas.length }} de {{ itemCotacoes.length }} cotação(ões) vinculadas ao item
            <template v-if="fonteSelecionadaLabel !== 'Todas'"> (filtro: {{ fonteSelecionadaLabel }})</template>.
          </p>
          <div class="item-table-scroll">
            <table class="item-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Fonte</th>
                  <th>Órgão</th>
                  <th>Município/UF</th>
                  <th>Valor unitário</th>
                  <th>Valor total</th>
                  <th>Data</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in itemCotacoesFiltradas" :key="r.id">
                  <td>{{ r.id }}</td>
                  <td>{{ labelFonte(classificarFonte(r)) }}</td>
                  <td>{{ r.orgao || '—' }}</td>
                  <td>{{ formatCidadeUf(r) }}</td>
                  <td>{{ formatCurrency(r.valor_unitario) }}</td>
                  <td>{{ formatCurrency(r.valor_total) }}</td>
                  <td>{{ formatDateTimePt(r.created_at) }}</td>
                </tr>
                <tr v-if="itemCotacoesFiltradas.length === 0">
                  <td colspan="7">Nenhuma cotação de preço registrada para este item neste filtro.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </template>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { getItemCotacoesFromResearchSession, getResearchSession } from '../services/pncpResearch';

const route = useRoute();
const cotacaoId = computed(() => String(route.params.cotacaoId || ''));
const itemId = computed(() => Number(route.params.itemId));

const isLoading = ref(false);
const loadError = ref('');
const item = ref(null);
const allItems = ref([]);
const itemCotacoes = ref([]);

const itemCidadeUf = computed(() => (item.value ? formatCidadeUf(item.value) : '—'));
const fonteSelecionada = computed(() => normalizeFonte(route.query.fonte));
const fonteSelecionadaLabel = computed(() => labelFonte(fonteSelecionada.value));
const faixaValorBase = computed(() => {
  const src = item.value?.source || {};
  return pickNumeric(src?.valor_base, src?.valorBase, src?.preco_base, src?.precoBase);
});

const faixaVariacaoFmt = computed(() => {
  const src = item.value?.source || {};
  const n = pickNumeric(src?.variacao, src?.variacao_percentual, src?.variacaoPercentual);
  if (!Number.isFinite(n)) return '—';
  return `${Number(n).toLocaleString('pt-BR')}%`;
});

const quantidadeRefletida = computed(() => {
  const first = itemCotacoes.value.find((x) => Number.isFinite(Number(x?.quantidade)));
  if (first) return Number(first.quantidade);
  if (Number.isFinite(Number(item.value?.quantidade))) return Number(item.value.quantidade);
  return null;
});

const unidadeRefletida = computed(() => {
  const first = itemCotacoes.value.find((x) => String(x?.unidade_medida || '').trim());
  if (first) return String(first.unidade_medida || '').trim();
  return String(item.value?.unidade_medida || '').trim() || null;
});

const valorTotalRefletido = computed(() => {
  const vals = itemCotacoes.value
    .map((x) => Number(x?.valor_total ?? x?.valor_unitario))
    .filter((n) => Number.isFinite(n) && n > 0);
  if (vals.length > 0) {
    const media = vals.reduce((a, b) => a + b, 0) / vals.length;
    return media;
  }
  const legacy = Number(item.value?.valor_total);
  return Number.isFinite(legacy) ? legacy : null;
});

const itemCotacoesFiltradas = computed(() => {
  const alvo = fonteSelecionada.value;
  if (!alvo) return itemCotacoes.value;
  return itemCotacoes.value.filter((c) => classificarFonte(c) === alvo);
});

onMounted(loadItem);

async function loadItem() {
  const sessionId = Number(cotacaoId.value);
  if (!Number.isFinite(sessionId) || sessionId <= 0 || !Number.isFinite(itemId.value) || itemId.value <= 0) {
    loadError.value = 'Parâmetros inválidos para abrir o item.';
    return;
  }
  isLoading.value = true;
  loadError.value = '';
  try {
    const data = await getResearchSession(sessionId);
    const itens = Array.isArray(data?.itens) ? data.itens : [];
    allItems.value = itens;
    item.value = itens.find((x) => Number(x?.id) === Number(itemId.value)) || null;
    if (!item.value) loadError.value = 'Item não encontrado nesta cotação.';
    const cot = await getItemCotacoesFromResearchSession(sessionId, itemId.value);
    itemCotacoes.value = Array.isArray(cot?.cotacoes) ? cot.cotacoes : [];
  } catch (err) {
    loadError.value = `Não foi possível carregar o item (${err?.message || 'erro desconhecido'}).`;
  } finally {
    isLoading.value = false;
  }
}

function buildGrupoStatusKey(nome, unidade, quantidade) {
  const n = String(nome || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
    .toLowerCase();
  const u = String(unidade || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
    .toLowerCase();
  const qRaw = String(quantidade ?? '').trim().replace(',', '.');
  const qNum = Number(qRaw);
  const q = Number.isFinite(qNum) ? String(qNum) : qRaw;
  return `${n}|${u}|${q}`;
}
function pickNumeric(...vals) {
  for (const v of vals) {
    const n = Number(v);
    if (Number.isFinite(n)) return n;
  }
  return null;
}

function formatCurrency(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return 'R$ —';
  return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function formatDateTimePt(iso) {
  if (!iso) return '—';
  const dt = new Date(iso);
  if (!Number.isFinite(dt.getTime())) return String(iso);
  return dt.toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatCidadeUf(r) {
  const m = String(r?.municipio || '').trim();
  const uf = String(r?.uf || '').trim();
  if (m && uf) return `${m}/${uf}`;
  return m || uf || '—';
}

function normalizeFonte(v) {
  const s = String(v || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
    .toLowerCase();
  if (!s || s === 'todas') return '';
  if (s.includes('govern') || s.includes('inciso_i') || s === 'inciso-i') return 'governamentais';
  if (s.includes('ente') || s.includes('inciso_ii') || s === 'inciso-ii') return 'entes_publicos';
  if (s.includes('dominio')) return 'dominio_amplo';
  if (s.includes('direta')) return 'cotacao_direta';
  if (s.includes('nota')) return 'notas_fiscais';
  return '';
}

function classificarFonte(cotacao) {
  const inciso = normalizeFonte(
    cotacao?.inciso_classificacao ||
      cotacao?.source?.inciso_classificacao ||
      cotacao?.source?.incisoClassificacao,
  );
  if (inciso === 'governamentais' || inciso === 'inciso_i') return 'governamentais';
  if (inciso === 'entes_publicos' || inciso === 'inciso_ii') return 'entes_publicos';
  const raw = normalizeFonte(
    cotacao?.fonte ||
      cotacao?.tipo_fonte ||
      cotacao?.source?.fonte ||
      cotacao?.source?.tipo_fonte ||
      cotacao?.source?.categoria_fonte,
  );
  if (raw) return raw;
  return '';
}

function labelFonte(code) {
  if (code === 'governamentais') return 'Preços Governamentais (Inciso I)';
  if (code === 'entes_publicos') return 'Outros Entes Públicos (Inciso II)';
  if (code === 'dominio_amplo') return 'Domínio amplo';
  if (code === 'cotacao_direta') return 'Cotação direta';
  if (code === 'notas_fiscais') return 'Notas fiscais';
  return 'Não classificada';
}
</script>

<style scoped>
.gov-page { display: flex; flex-direction: column; gap: 16px; width: 100%; min-width: 0; }
.gov-page__title { margin: 0; font-size: 24px; }
.gov-page__subtitle { margin: 6px 0 0; color: var(--color-text-soft); }
.gov-page__content { padding: 16px; display: flex; flex-direction: column; gap: 12px; min-width: 0; }
.item-header-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
.item-back-btn { border: 1px solid #cfd8e3; border-radius: 10px; background: #fff; color: #1f2937; padding: 7px 12px; font-size: 12px; text-decoration: none; display: inline-flex; align-items: center; gap: 7px; }
.item-meta { margin: 0; font-size: 12px; color: #64748b; }
.item-meta--error { color: #b91c1c; }
.item-summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 8px; }
.item-card { border: 1px solid #d6dde8; border-radius: 10px; background: #fff; padding: 10px; display: flex; flex-direction: column; gap: 4px; }
.item-card--wide { grid-column: 1 / -1; }
.item-card__label { font-size: 10px; text-transform: uppercase; color: #64748b; }
.item-prices { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 8px; }
.item-actions { display: flex; flex-wrap: wrap; gap: 8px; }
.item-search-btn {
  border: 1px solid #1f4e79;
  border-radius: 10px;
  background: #1f4e79;
  color: #fff;
  padding: 8px 12px;
  font-size: 12px;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 7px;
}
.item-price-card { border: 1px solid #b7d2ef; border-radius: 10px; background: #e8f1fb; padding: 10px; display: flex; flex-direction: column; gap: 4px; }
.item-price-card span { font-size: 11px; text-transform: uppercase; color: #1f4e79; }
.item-price-card strong { font-size: 18px; color: #0f4c81; }
.item-related h2 { margin: 0 0 6px; font-size: 18px; }
.item-table-scroll { width: 100%; overflow: auto; }
.item-table { width: 100%; min-width: 760px; border-collapse: collapse; table-layout: fixed; }
.item-table th, .item-table td { border-bottom: 1px solid #e5eaf3; padding: 8px; font-size: 12px; text-align: left; }
.item-table th { font-size: 11px; text-transform: uppercase; color: #64748b; }
</style>
