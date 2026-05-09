<script setup>
import { computed } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();

const heading = computed(() => {
  const s = route.meta?.geracaoHubSection;
  if (s === 'inexigibilidade') return 'Inexigibilidade';
  return 'Dispensa';
});
</script>

<template>
  <div class="geracao-hub">
    <div class="geracao-hub__card">
      <h2 class="geracao-hub__title">{{ heading }}</h2>
      <p class="geracao-hub__text">Selecione um fluxo no menu à esquerda para abrir o formulário.</p>
    </div>
  </div>
</template>

<style scoped>
.geracao-hub {
  min-height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 16px;
  box-sizing: border-box;
}
.geracao-hub__card {
  max-width: 28rem;
  text-align: center;
  border-radius: 14px;
  border: 1px solid #e2e8f0;
  background: #fff;
  padding: 28px 22px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
}
.dm-dark-theme .geracao-hub__card {
  border-color: rgba(148, 163, 184, 0.25);
  background: rgba(15, 23, 42, 0.55);
}
.geracao-hub__title {
  margin: 0 0 10px;
  font-size: 1.15rem;
  font-weight: 700;
  color: #0f172a;
}
.dm-dark-theme .geracao-hub__title {
  color: #f1f5f9;
}
.geracao-hub__text {
  margin: 0;
  font-size: 0.9rem;
  line-height: 1.45;
  color: #64748b;
}
.dm-dark-theme .geracao-hub__text {
  color: #94a3b8;
}
</style>
