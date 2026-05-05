<template>
  <section class="gov-page">
    <header class="gov-page__header">
      <h1 class="gov-page__title">Preview de arquivo JSX</h1>
      <p class="gov-page__subtitle">
        Arquivo externo disponível no ambiente de desenvolvimento.
      </p>
    </header>

    <div class="gov-surface gov-page__content preview-wrap">
      <div class="preview-actions">
        <code class="preview-path">{{ sourcePath || '—' }}</code>
        <a v-if="devFsUrl" :href="devFsUrl" target="_blank" rel="noopener noreferrer" class="preview-link">
          Abrir arquivo bruto
        </a>
      </div>

      <p v-if="loadError" class="preview-error">{{ loadError }}</p>
      <pre v-else class="preview-code">{{ content }}</pre>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();
const content = ref('Carregando arquivo...');
const loadError = ref('');

const sourcePath = computed(() => String(route.meta?.sourcePath || '').trim());
const devFsUrl = computed(() => (sourcePath.value ? `/@fs${encodeURI(sourcePath.value)}` : ''));

onMounted(async () => {
  if (!devFsUrl.value) {
    loadError.value = 'Caminho do arquivo não configurado para este preview.';
    return;
  }
  try {
    const res = await fetch(devFsUrl.value, { credentials: 'same-origin' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    content.value = await res.text();
  } catch (err) {
    loadError.value = `Não foi possível abrir o arquivo no modo dev (${err?.message || 'erro desconhecido'}).`;
  }
});
</script>

<style scoped>
.preview-wrap {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 420px;
}

.preview-actions {
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
}

.preview-path {
  font-size: 12px;
  color: #334155;
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 6px 8px;
}

.preview-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #1f4e79;
  background: #1f4e79;
  color: #fff;
  text-decoration: none;
  border-radius: 8px;
  padding: 7px 10px;
  font-size: 12px;
  font-weight: 600;
}

.preview-code {
  margin: 0;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  background: #0f172a;
  color: #e2e8f0;
  padding: 12px;
  overflow: auto;
  font-size: 12px;
  line-height: 1.45;
  white-space: pre;
}

.preview-error {
  margin: 0;
  color: #b91c1c;
  font-size: 13px;
}
</style>
