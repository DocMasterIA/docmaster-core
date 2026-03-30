<template>
  <section class="gov-page">
    <header class="gov-page__header">
      <h1 class="gov-page__title">Pesquisador de Dados PNCP</h1>
      <p class="gov-page__subtitle">
        Pesquise itens e visualize referências de preços e contratações públicas.
      </p>
    </header>

    <div class="gov-surface gov-page__content">
      <form class="pncp-search" @submit.prevent>
        <label class="gov-label" for="pncp-query">Pesquisar item no PNCP</label>
        <div class="pncp-search__row">
          <input
            id="pncp-query"
            v-model.trim="query"
            type="text"
            class="gov-input pncp-search__input"
            placeholder="Ex.: pavimentação asfáltica, pneus aro 16, medicamentos..."
          />
          <button type="button" class="gov-btn gov-btn--primary" @click="query = query">
            <i class="fa-solid fa-magnifying-glass" aria-hidden="true"></i>
            Pesquisar
          </button>
        </div>
      </form>

      <div class="pncp-summary">
        <span class="pncp-summary__badge">{{ filteredItems.length }} itens encontrados</span>
        <span class="pncp-summary__hint">Mockup inicial - integração em tempo real em desenvolvimento.</span>
      </div>

      <div class="pncp-grid">
        <article v-for="item in filteredItems" :key="item.id" class="pncp-card">
          <h3 class="pncp-card__title">{{ item.title }}</h3>
          <p class="pncp-card__price">{{ formatCurrency(item.price) }}</p>

          <dl class="pncp-card__meta">
            <div class="pncp-card__meta-row">
              <dt>Órgão:</dt>
              <dd>{{ item.orgao }}</dd>
            </div>
            <div class="pncp-card__meta-row">
              <dt>UF/Município:</dt>
              <dd>{{ item.uf }} - {{ item.municipio }}</dd>
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

          <footer class="pncp-card__footer">
            <span class="pncp-card__chip">{{ item.tema }}</span>
            <span class="pncp-card__date">{{ item.dataRef }}</span>
          </footer>
        </article>
      </div>

      <p v-if="!filteredItems.length" class="pncp-empty">
        Nenhum item encontrado para "{{ query }}".
      </p>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue';

const query = ref('');

const mockItems = ref([
  {
    id: 'pncp-001',
    title: 'Pavimentação asfáltica CBUQ em vias urbanas',
    price: 1845200.5,
    orgao: 'Prefeitura Municipal de Itajaí',
    uf: 'SC',
    municipio: 'Itajaí',
    modalidade: 'Dispensa',
    situacao: 'Homologada',
    tema: 'obras_engenharia',
    dataRef: '22/03/2026',
  },
  {
    id: 'pncp-002',
    title: 'Aquisição de pneus e serviços de balanceamento',
    price: 326780.0,
    orgao: 'Prefeitura Municipal de Joinville',
    uf: 'SC',
    municipio: 'Joinville',
    modalidade: 'Pregão',
    situacao: 'Em disputa',
    tema: 'frota_pneus',
    dataRef: '21/03/2026',
  },
  {
    id: 'pncp-003',
    title: 'Fornecimento de medicamentos da atenção básica',
    price: 912450.9,
    orgao: 'Prefeitura Municipal de Blumenau',
    uf: 'SC',
    municipio: 'Blumenau',
    modalidade: 'Pregão',
    situacao: 'Adjudicada',
    tema: 'saude_medicamentos_insumos',
    dataRef: '19/03/2026',
  },
  {
    id: 'pncp-004',
    title: 'Serviços de limpeza predial continuada',
    price: 1274300.0,
    orgao: 'Prefeitura Municipal de Florianópolis',
    uf: 'SC',
    municipio: 'Florianópolis',
    modalidade: 'Dispensa',
    situacao: 'Publicada',
    tema: 'servicos_limpeza',
    dataRef: '18/03/2026',
  },
]);

const filteredItems = computed(() => {
  const q = query.value.toLowerCase().trim();
  if (!q) return mockItems.value;
  return mockItems.value.filter((item) => {
    const haystack = [
      item.title,
      item.orgao,
      item.uf,
      item.municipio,
      item.modalidade,
      item.situacao,
      item.tema,
    ]
      .join(' ')
      .toLowerCase();
    return haystack.includes(q);
  });
});

function formatCurrency(value) {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    maximumFractionDigits: 2,
  }).format(Number(value || 0));
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
}

.pncp-search__input {
  flex: 1;
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

.pncp-card__footer {
  margin-top: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pncp-card__chip {
  font-size: 11px;
  padding: 3px 8px;
  border: 1px solid #cfd8e3;
  border-radius: 999px;
  background: #f6f9fc;
}

.pncp-card__date {
  font-size: 12px;
  color: var(--color-text-soft);
}

.pncp-empty {
  margin: 0;
  color: var(--color-text-soft);
}
</style>
