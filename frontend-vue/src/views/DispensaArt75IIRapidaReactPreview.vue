<template>
  <div class="react-preview-host" ref="rootEl"></div>
</template>

<script setup>
import React from 'react';
import { createRoot } from 'react-dom/client';
import { onBeforeUnmount, onMounted, ref } from 'vue';
import DispensaRapidaPage from '@repo/modulo_dispensa_art_75_ii_(DISPENSA RAPIDA).jsx';

const rootEl = ref(null);
let root = null;

onMounted(() => {
  if (!rootEl.value) return;
  root = createRoot(rootEl.value);
  root.render(React.createElement(DispensaRapidaPage));
});

onBeforeUnmount(() => {
  if (root) root.unmount();
  root = null;
});
</script>

<style scoped>
.react-preview-host {
  min-height: calc(100vh - 140px);
}
</style>
