<template>
  <section class="gov-page mod-placeholder">
    <header class="gov-page__header">
      <h1 class="gov-page__title">{{ title }}</h1>
      <p class="gov-page__subtitle">{{ subtitle }}</p>
    </header>
    <div class="gov-surface gov-page__content mod-placeholder__surface" aria-hidden="true" />
  </section>
</template>

<script setup>
import { computed } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();
const title = computed(() => String(route.meta?.title || 'Módulo'));
const subtitle = computed(() =>
  String(route.meta?.subtitle || 'Esta área ainda não possui telas implementadas; o roteamento está preparado para evolução futura.'),
);
</script>

<style scoped>
.gov-page.mod-placeholder {
  min-height: 0;
}

.mod-placeholder__surface {
  min-height: 42vh;
  border-style: dashed;
  opacity: 0.85;
}
</style>
