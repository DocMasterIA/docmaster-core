<template>
  <section class="gov-page">
    <header class="gov-page__header">
      <h1 class="gov-page__title">Pesquisador de Dados PNCP</h1>
      <p class="gov-page__subtitle">
        Pesquise termos nas publicações e nos itens das contratações (via PNCP). É necessário estar logado.
      </p>
    </header>

    <div class="gov-surface gov-page__content">
      <form class="pncp-search" @submit.prevent="runSearch">
        <label class="gov-label" for="pncp-query">Termo de busca</label>
        <div class="pncp-search__row">
          <input
            id="pncp-query"
            v-model.trim="query"
            type="text"
            class="gov-input pncp-search__input"
            placeholder="Ex.: pneu, material esportivo, bambolê..."
            required
            :disabled="loading"
          />
          <button type="submit" class="gov-btn gov-btn--primary" :disabled="loading || !query">
            <i class="fa-solid fa-magnifying-glass" aria-hidden="true"></i>
            {{ loading ? 'Pesquisando…' : 'Pesquisar' }}
          </button>
        </div>

        <details class="pncp-advanced">
          <summary>Filtros opcionais</summary>
          <div class="pncp-advanced__grid">
            <label class="gov-label">
              UF
              <input v-model.trim="ufFilter" type="text" maxlength="2" class="gov-input" placeholder="Ex.: SP" :disabled="loading" />
            </label>
            <label class="gov-label">
              Máx. páginas (total)
              <input v-model.number="maxPaginas" type="number" min="1" max="60" class="gov-input" :disabled="loading" />
            </label>
            <label class="gov-label">
              Data inicial
              <input v-model="dataInicial" type="date" class="gov-input" :disabled="loading" />
            </label>
            <label class="gov-label">
              Data final
              <input v-model="dataFinal" type="date" class="gov-input" :disabled="loading" />
            </label>
          </div>
        </details>
      </form>

      <p v-if="errorMsg" class="pncp-error" role="alert">{{ errorMsg }}</p>
      <p v-if="loading && progressHint" class="pncp-progress">{{ progressHint }}</p>

      <div class="pncp-summary">
        <span class="pncp-summary__badge">{{ displayItems.length }} resultado(s)</span>
        <span v-if="finalStats" class="pncp-summary__hint">
          Páginas processadas: {{ finalStats.pages_processed ?? '—' }}
          <template v-if="finalStats.valor_medio != null">
            · Preço médio (amostra): {{ formatCurrency(finalStats.valor_medio) }}
          </template>
        </span>
      </div>

      <div class="pncp-grid">
        <article v-for="item in displayItems" :key="item.id" class="pncp-card">
          <h3 class="pncp-card__title">{{ item.title }}</h3>
          <p class="pncp-card__price">{{ formatCurrency(item.price) }}</p>

          <dl class="pncp-card__meta">
            <div class="pncp-card__meta-row">
              <dt>PNCP:</dt>
              <dd>{{ item.id }}</dd>
            </div>
            <div class="pncp-card__meta-row">
              <dt>Órgão:</dt>
              <dd>{{ item.orgao }}</dd>
            </div>
            <div class="pncp-card__meta-row">
              <dt>UF/Município:</dt>
              <dd>{{ item.uf }} — {{ item.municipio }}</dd>
            </div>
            <div class="pncp-card__meta-row">
              <dt>Modalidade:</dt>
              <dd>{{ item.modalidade }}</dd>
            </div>
            <div class="pncp-card__meta-row">
              <dt>Situação:</dt>
              <dd>{{ item.situacao }}</dd>
            </div>
          </dl>

          <details v-if="item.itensPncp?.length" class="pncp-card__itens">
            <summary>Itens da contratação ({{ item.itensPncp.length }})</summary>
            <ul class="pncp-item-lines">
              <li v-for="(row, idx) in mapLineItems(item.itensPncp)" :key="idx" class="pncp-item-line">
                <span v-if="row.badge" class="pncp-item-line__badge">{{ row.badge }}</span>
                <div class="pncp-item-line__body">
                  <p class="pncp-item-line__headline">{{ row.headline }}</p>
                  <p v-if="row.complemento" class="pncp-item-line__complemento">{{ row.complemento }}</p>
                  <div class="pncp-item-line__stats">
                    <span v-if="row.qtdLine" class="pncp-item-line__stat">{{ row.qtdLine }}</span>
                    <span v-if="row.unitLine" class="pncp-item-line__stat pncp-item-line__stat--money">
                      {{ row.unitLine }}
                    </span>
                  </div>
                </div>
              </li>
            </ul>
          </details>

          <footer class="pncp-card__footer">
            <span class="pncp-card__chip">{{ item.matchOrigem || '—' }}</span>
            <span class="pncp-card__date" :title="'Score: ' + item.score">
              {{ item.confirmadoItens === true ? 'Confirmado nos itens' : item.confirmadoItens === false ? 'Só objeto' : 'Sem tabela' }}
            </span>
          </footer>
        </article>
      </div>

      <p v-if="!loading && lastSearched && !displayItems.length && !errorMsg" class="pncp-empty">
        Nenhum resultado para "{{ lastSearched }}" com os filtros atuais.
      </p>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue';

const RAW_API_BASE = import.meta.dev ? '' : (import.meta.env.VITE_API_URL || '');
const API_BASE = String(RAW_API_BASE).replace(/\/+$/, '');

const query = ref('');
const ufFilter = ref('');
const maxPaginas = ref(15);
const dataInicial = ref('');
const dataFinal = ref('');

const loading = ref(false);
const errorMsg = ref(null);
const progressHint = ref('');
const lastSearched = ref('');

/** @type {import('vue').Ref<Array<ReturnType<typeof mapApiItem>>>} */
const items = ref([]);
const finalStats = ref(null);

const displayItems = computed(() =>
  [...items.value].sort((a, b) => (b.score || 0) - (a.score || 0)),
);

function toPnDate(htmlDate) {
  if (!htmlDate) return null;
  return String(htmlDate).replaceAll('-', '');
}

function mapApiItem(raw) {
  return {
    id: raw.numero_pncp || '',
    title: raw.objeto_resumido || '—',
    price: raw.valor_global ?? 0,
    orgao: raw.orgao || '—',
    uf: raw.uf || '—',
    municipio: raw.municipio || '—',
    modalidade: raw.modalidade || '—',
    situacao: raw.situacao || '—',
    matchOrigem: raw.match_origem || '',
    confirmadoItens: raw.confirmado_nos_itens,
    itensPncp: Array.isArray(raw.itens_pncp) ? raw.itens_pncp : [],
    score: raw.score_relevancia ?? 0,
  };
}

function formatCurrency(value) {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    maximumFractionDigits: 2,
  }).format(Number(value || 0));
}

/**
 * Separa descrição típica PNCP: especificação do produto vs. trecho legal/serviços (após ", com ...").
 */
function splitItemDescricao(descricao) {
  const s = String(descricao || '').trim();
  if (!s) return { headline: '—', complemento: '' };
  const m = s.match(/^(.+?),\s*(com\s+.+)$/is);
  if (m) return { headline: m[1].trim(), complemento: m[2].trim() };
  return { headline: s, complemento: '' };
}

/**
 * @param {Record<string, unknown>} li
 */
function lineItemParts(li) {
  const { headline, complemento } = splitItemDescricao(li.descricao);
  const badge = li.numeroItem != null ? `#${li.numeroItem}` : '';
  const unid = String(li.unidadeMedida || '').trim();
  const qtdLine =
    li.quantidade != null ? `Quantidade: ${li.quantidade}${unid ? ` ${unid}` : ''}` : '';
  const unitLine =
    li.valorUnitarioEstimado != null ? `Valor unitário: ${formatCurrency(li.valorUnitarioEstimado)}` : '';
  return { badge, headline, complemento, qtdLine, unitLine };
}

function mapLineItems(list) {
  if (!Array.isArray(list) || !list.length) return [];
  return list.map((li) => lineItemParts(li));
}

/** Resposta de erro do proxy/Django/FastAPI (detail string ou lista Pydantic). */
async function readErrorMessage(res) {
  const fallback = res.statusText || `HTTP ${res.status}`;
  let text = '';
  try {
    text = await res.text();
  } catch {
    return fallback;
  }
  if (!text.trim()) return fallback;
  try {
    const j = JSON.parse(text);
    const d = j.detail ?? j.error ?? j.message;
    if (typeof d === 'string') return d;
    if (Array.isArray(d)) {
      const parts = d.map((x) => {
        if (typeof x === 'string') return x;
        if (x && typeof x.msg === 'string') return x.msg;
        return JSON.stringify(x);
      });
      return parts.join('; ') || fallback;
    }
    if (d != null) return String(d);
  } catch {
    /* not JSON */
  }
  return text.trim().slice(0, 800) || fallback;
}

function applyStreamEvent(ev, byKey, pageEventsRef) {
  if (ev.type === 'page') {
    pageEventsRef.count += 1;
    progressHint.value = `Processando publicações… (${pageEventsRef.count} lote(s) recebido(s))`;
    for (const it of ev.items || []) {
      const m = mapApiItem(it);
      if (m.id) byKey.set(m.id, m);
    }
    items.value = Array.from(byKey.values());
  } else if (ev.type === 'final') {
    finalStats.value = ev.stats || null;
    const list = ev.itens || [];
    for (const it of list) {
      const m = mapApiItem(it);
      if (m.id) byKey.set(m.id, m);
    }
    items.value = Array.from(byKey.values());
  } else if (ev.type === 'error') {
    throw new Error(ev.detail || 'Erro na pesquisa PNCP.');
  }
}

function tryApplyNdjsonLine(line, byKey, pageEventsRef) {
  const s = line.trim();
  if (!s) return;
  let ev;
  try {
    ev = JSON.parse(s);
  } catch {
    return;
  }
  applyStreamEvent(ev, byKey, pageEventsRef);
}

async function runSearch() {
  const termo = query.value.trim();
  if (!termo || loading.value) return;

  const diEarly = toPnDate(dataInicial.value);
  const dfEarly = toPnDate(dataFinal.value);
  if (diEarly && dfEarly && diEarly > dfEarly) {
    errorMsg.value = 'Data inicial não pode ser posterior à data final.';
    return;
  }

  errorMsg.value = null;
  finalStats.value = null;
  items.value = [];
  lastSearched.value = termo;
  loading.value = true;
  progressHint.value = 'Enviando pesquisa…';

  const body = {
    termo_busca: termo,
    pagina: 1,
    tamanho_pagina: 50,
    max_paginas: Math.min(60, Math.max(1, Number(maxPaginas.value) || 15)),
  };
  const di = diEarly;
  const df = dfEarly;
  if (di) body.data_inicial = di;
  if (df) body.data_final = df;
  const u = ufFilter.value.trim().toUpperCase();
  if (u.length === 2) body.uf = u;

  const byKey = new Map();
  const pageEventsRef = { count: 0 };

  try {
    const res = await fetch(`${API_BASE}/api/pncp-research/market-search/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/x-ndjson, application/json' },
      credentials: 'include',
      body: JSON.stringify(body),
    });

    if (res.status === 401) {
      errorMsg.value = 'Faça login para usar o pesquisador PNCP.';
      return;
    }

    if (!res.ok) {
      throw new Error(await readErrorMessage(res));
    }

    const ct = res.headers.get('Content-Type') || '';
    if (!ct.includes('ndjson') && ct.includes('json')) {
      const data = await res.json();
      if (data.detail && !data.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail));
      const list = data.itens || [];
      items.value = list.map(mapApiItem);
      finalStats.value = data.stats || null;
      return;
    }

    const reader = res.body?.getReader();
    if (!reader) throw new Error('Stream não suportado pelo navegador.');

    const dec = new TextDecoder();
    let buf = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const lines = buf.split('\n');
      buf = lines.pop() || '';
      for (const line of lines) {
        tryApplyNdjsonLine(line, byKey, pageEventsRef);
      }
    }
    tryApplyNdjsonLine(buf, byKey, pageEventsRef);
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
    progressHint.value = '';
  }
}
</script>

<style scoped>
.gov-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.gov-page__title {
  margin: 0;
  font-size: 24px;
}

.gov-page__subtitle {
  margin: 6px 0 0;
  color: var(--color-text-soft);
}

.gov-page__content {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.pncp-search {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pncp-search__row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.pncp-search__input {
  flex: 1;
  min-width: 200px;
}

.pncp-advanced {
  margin-top: 6px;
  font-size: 13px;
}

.pncp-advanced summary {
  cursor: pointer;
  color: var(--color-text-soft);
}

.pncp-advanced__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 10px;
  margin-top: 10px;
}

.pncp-error {
  margin: 0;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: #fde8e8;
  border: 1px solid #e8a4a4;
  color: #8a1f1f;
}

.pncp-progress {
  margin: 0;
  font-size: 13px;
  color: var(--color-text-soft);
}

.pncp-summary {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.pncp-summary__badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  background: #e6f0fa;
  border: 1px solid #b7d2ef;
  color: #1f4e79;
  font-size: 12px;
  font-weight: 600;
}

.pncp-summary__hint {
  color: var(--color-text-soft);
  font-size: 12px;
}

.pncp-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 10px;
}

.pncp-card {
  border: 1px solid #d6dde8;
  border-radius: var(--radius-md);
  background: #fff;
  padding: 12px;
}

.pncp-card__title {
  margin: 0 0 4px;
  font-size: 15px;
  line-height: 1.35;
  color: var(--color-text);
}

.pncp-card__price {
  margin: 0 0 8px;
  color: #0f5e3a;
  font-size: 18px;
  font-weight: 700;
}

.pncp-card__meta {
  margin: 0;
}

.pncp-card__meta-row {
  display: grid;
  grid-template-columns: 110px 1fr;
  gap: 6px;
  margin-bottom: 3px;
}

.pncp-card__meta-row dt {
  font-weight: 600;
  color: var(--color-text-soft);
}

.pncp-card__meta-row dd {
  margin: 0;
}

.pncp-card__itens {
  margin-top: 10px;
  font-size: 12px;
}

.pncp-item-lines {
  margin: 8px 0 0;
  padding: 0;
  list-style: none;
}

.pncp-item-line {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 10px 0;
  border-bottom: 1px solid #e8edf4;
}

.pncp-item-line:last-child {
  border-bottom: none;
}

.pncp-item-line__badge {
  flex: 0 0 auto;
  font-weight: 700;
  font-size: 11px;
  line-height: 1.4;
  color: #1f4e79;
  background: #e8f1fb;
  padding: 3px 7px;
  border-radius: 6px;
  margin-top: 2px;
}

.pncp-item-line__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.pncp-item-line__headline {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  line-height: 1.4;
  color: var(--color-text);
}

.pncp-item-line__complemento {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
  color: var(--color-text-soft);
}

.pncp-item-line__stats {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 14px;
  margin-top: 2px;
}

.pncp-item-line__stat {
  font-size: 12px;
  color: var(--color-text-soft);
}

.pncp-item-line__stat--money {
  font-weight: 600;
  color: #0f5e3a;
}

.pncp-card__footer {
  margin-top: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.pncp-card__chip {
  font-size: 11px;
  padding: 3px 8px;
  border: 1px solid #cfd8e3;
  border-radius: 999px;
  background: #f6f9fc;
}

.pncp-card__date {
  font-size: 11px;
  color: var(--color-text-soft);
  text-align: right;
}

.pncp-empty {
  margin: 0;
  color: var(--color-text-soft);
}
</style>
