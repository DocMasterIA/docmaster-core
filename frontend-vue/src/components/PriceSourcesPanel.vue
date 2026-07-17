<template>
  <section class="price-fontes-panel">
    <p class="price-fontes-panel__kicker">Fontes de preço</p>
    <h2 class="price-fontes-panel__title">Plataformas consultadas</h2>
    <p class="price-fontes-panel__hint">{{ hint }}</p>
    <p v-if="loading" class="price-fontes-panel__meta">Carregando fontes disponíveis…</p>
    <label
      v-for="fonte in fontesVisiveis"
      :key="fonte.id"
      class="price-fontes-item"
      :class="{ 'price-fontes-item--disabled': !fonteHabilitada(fonte) }"
    >
      <input
        v-model="model"
        type="checkbox"
        :value="fonte.id"
        :disabled="!fonteHabilitada(fonte)"
      />
      <span>
        {{ fonte.label }}
        <span v-if="fonte.total_itens > 0" class="price-fontes-item__count">
          ({{ Number(fonte.total_itens).toLocaleString('pt-BR') }} itens)
        </span>
        <span v-if="!fonteHabilitada(fonte)" class="price-fontes-item__off"> — índice indisponível</span>
        <span v-else-if="fonte.uf_scope" class="price-fontes-item__scope"> — escopo {{ fonte.uf_scope }}</span>
      </span>
    </label>
  </section>
</template>

<script setup>
import { computed } from 'vue';

const model = defineModel({ type: Array, default: () => ['pncp'] });

const props = defineProps({
  fontes: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  hint: {
    type: String,
    default:
      'Marque PNCP, TCE-RS ou ambos. A busca federada consulta os índices locais em paralelo.',
  },
});

const fontesVisiveis = computed(() => (props.fontes || []).filter((f) => f?.id));

function fonteHabilitada(fonte) {
  return fonte?.search_ready !== false;
}
</script>

<style scoped>
.price-fontes-panel {
  border: 1px solid #dbe4f0;
  border-radius: 12px;
  background: #fbfdff;
  padding: 12px 14px;
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.price-fontes-panel__kicker {
  margin: 0;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #3d6ea3;
}
.price-fontes-panel__title {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: #1a2f4a;
}
.price-fontes-panel__hint,
.price-fontes-panel__meta {
  margin: 0;
  font-size: 13px;
  color: #5a708a;
  line-height: 1.45;
}
.price-fontes-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 14px;
  margin-top: 4px;
  cursor: pointer;
}
.price-fontes-item--disabled {
  opacity: 0.65;
  cursor: not-allowed;
}
.price-fontes-item__off {
  color: #9a6b2e;
  font-size: 12px;
}
.price-fontes-item__scope,
.price-fontes-item__count {
  color: #5a708a;
  font-size: 12px;
}
</style>
