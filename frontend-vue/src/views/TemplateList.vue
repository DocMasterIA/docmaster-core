<template>
  <div class="tpl-list">
    <div class="tpl-list__top">
      <router-link to="/" class="gov-btn gov-btn--secondary gov-btn--sm">
        ← Voltar
      </router-link>
    </div>

    <header class="gov-page-header">
      <h1 class="gov-page-title">Biblioteca de Templates</h1>
      <p class="gov-page-subtitle">
        Encontre e visualize rapidamente os modelos disponíveis
      </p>
    </header>

    <!-- Filtros (placeholder – backend pode expor API depois) -->
    <div class="tpl-list__filters gov-surface gov-mb-md">
      <form class="tpl-list__filter-form" @submit.prevent="applyFilters">
        <div class="tpl-list__filter-row">
          <select v-model="filterEstado" class="gov-select tpl-list__select" name="estado">
            <option value="">Todos os Estados</option>
            <option v-for="e in estados" :key="e" :value="e">{{ e }}</option>
          </select>
          <select v-model="filterPrefeitura" class="gov-select tpl-list__select" name="prefeitura">
            <option value="">Todas Prefeituras</option>
            <option v-for="p in prefeituras" :key="p.id" :value="p.id">{{ p.nome_municipio }}</option>
          </select>
          <select v-model="filterSubtopico" class="gov-select tpl-list__select" name="subtopico">
            <option value="">Todos Subtópicos</option>
            <option v-for="s in subtopicos" :key="s.id" :value="s.id">{{ s.nome }}</option>
          </select>
          <button type="submit" class="gov-btn gov-btn--primary">Filtrar</button>
        </div>
      </form>
    </div>

    <!-- Busca local por nome -->
    <div class="gov-field gov-mb-md">
      <input
        v-model="searchQuery"
        type="text"
        class="gov-input tpl-list__search"
        placeholder="Pesquisar templates..."
      />
    </div>

    <!-- Grid de cards -->
    <div class="tpl-list__grid">
      <template v-for="tpl in filteredTemplates" :key="tpl.id">
        <div class="tpl-list__card">
          <h3 class="tpl-list__card-title">{{ tpl.name }}</h3>
          <div class="tpl-list__card-media">
            <img
              v-if="previewUrl(tpl)"
              :src="previewUrl(tpl)"
              :alt="tpl.name"
              class="tpl-list__card-img"
            />
            <div v-else class="tpl-list__card-placeholder">Sem Preview</div>
          </div>
          <div class="tpl-list__card-overlay">
            <button
              type="button"
              class="gov-btn gov-btn--primary gov-btn--sm"
              @click="openPdfModal(tpl)"
            >
              Pré-visualizar
            </button>
          </div>
        </div>
      </template>
    </div>

    <p v-if="filteredTemplates.length === 0" class="tpl-list__empty">
      Nenhum template encontrado
    </p>

    <!-- Modal PDF -->
    <div
      v-show="pdfModalOpen"
      class="tpl-list__modal"
      role="dialog"
      aria-modal="true"
      @click.self="closePdfModal"
    >
      <div class="tpl-list__modal-box">
        <div class="tpl-list__modal-header">
          <h3 class="tpl-list__modal-title">{{ pdfModalTitle }}</h3>
          <span class="tpl-list__modal-meta">{{ pdfModalMeta }}</span>
          <div class="tpl-list__modal-actions">
            <button
              type="button"
              class="gov-btn gov-btn--secondary gov-btn--sm"
              @click="usarComoBase"
            >
              Usar como base
            </button>
            <button type="button" class="gov-btn gov-btn--outline gov-btn--sm" @click="closePdfModal">
              Fechar
            </button>
          </div>
        </div>
        <div class="tpl-list__modal-body">
          <div class="tpl-list__pdf-toolbar">
            <button type="button" class="gov-btn gov-btn--outline gov-btn--sm" :disabled="!pdfDoc || pdfPage <= 1" @click="prevPage">
              Anterior
            </button>
            <button type="button" class="gov-btn gov-btn--outline gov-btn--sm" :disabled="!pdfDoc || pdfPage >= pdfTotalPages" @click="nextPage">
              Próximo
            </button>
            <span class="tpl-list__pdf-pagenum">Página {{ pdfPage }} de {{ pdfTotalPages }}</span>
            <span class="tpl-list__pdf-goto">
              <input v-model.number="pdfGotoPage" type="number" min="1" :max="pdfTotalPages" class="gov-input tpl-list__goto-input" />
              <button type="button" class="gov-btn gov-btn--outline gov-btn--sm" @click="goToPage">Ir</button>
            </span>
          </div>
          <div class="tpl-list__pdf-canvas-wrap">
            <canvas ref="pdfCanvasEl" class="tpl-list__pdf-canvas"></canvas>
          </div>
          <aside class="tpl-list__pdf-thumbs">
            <h4 class="tpl-list__pdf-thumbs-title">Miniaturas</h4>
            <div ref="pdfThumbsEl" class="tpl-list__pdf-thumbs-list"></div>
          </aside>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue';
import { useRouter } from 'vue-router';

const API_BASE = import.meta.env.VITE_API_URL || '';
const router = useRouter();

/** Card mockado para testar o visualizador de PDF (sempre visível) */
const MOCK_TEMPLATE = {
  id: '__mock_demo__',
  name: 'Template de demonstração (mock)',
  preview_image: null,
};

const templates = ref([]);
const searchQuery = ref('');
const filterEstado = ref('');
const filterPrefeitura = ref('');
const filterSubtopico = ref('');
const estados = ref([]);
const prefeituras = ref([]);
const subtopicos = ref([]);

const pdfModalOpen = ref(false);
const pdfModalTitle = ref('Preview');
const pdfModalMeta = ref('');
const currentTemplateId = ref(null);
const currentTemplateName = ref('');
const pdfCanvasEl = ref(null);
const pdfThumbsEl = ref(null);
const pdfDoc = ref(null);
const pdfPage = ref(1);
const pdfTotalPages = ref(0);
const pdfGotoPage = ref(1);
let pdfBlobUrl = null;

const filteredTemplates = computed(() => {
  const q = searchQuery.value.toLowerCase().trim();
  const list = templates.value;
  const filtered = q ? list.filter((t) => (t.name || '').toLowerCase().includes(q)) : list;
  const mockMatches = !q || MOCK_TEMPLATE.name.toLowerCase().includes(q);
  return mockMatches ? [MOCK_TEMPLATE, ...filtered] : filtered;
});

function previewUrl(tpl) {
  const img = tpl.preview_image;
  if (!img) return '';
  return img.startsWith('http') ? img : `${API_BASE}${img}`;
}

async function loadTemplates() {
  try {
    const res = await fetch(`${API_BASE}/api/documentos_modelos/`, { credentials: 'include' });
    if (!res.ok) return;
    const data = await res.json();
    templates.value = data.templates || [];
  } catch (e) {
    console.warn('loadTemplates', e);
    templates.value = [];
  }
}

function applyFilters() {
  loadTemplates();
}

function openPdfModal(tpl) {
  currentTemplateId.value = tpl.id;
  currentTemplateName.value = tpl.name || 'Preview';
  pdfModalTitle.value = tpl.name || 'Preview';
  pdfModalMeta.value = 'Carregando preview...';
  pdfModalOpen.value = true;
  if (tpl.id === MOCK_TEMPLATE.id) {
    loadMockPdf();
  } else {
    loadTemplatePreviewPdf(tpl.id);
  }
}

function closePdfModal() {
  pdfModalOpen.value = false;
  pdfDoc.value = null;
  pdfPage.value = 1;
  pdfTotalPages.value = 0;
  pdfModalMeta.value = '';
  currentTemplateId.value = null;
  if (pdfBlobUrl) {
    URL.revokeObjectURL(pdfBlobUrl);
    pdfBlobUrl = null;
  }
  if (pdfThumbsEl.value) pdfThumbsEl.value.innerHTML = '';
}

function usarComoBase() {
  if (!currentTemplateId.value || currentTemplateId.value === MOCK_TEMPLATE.id) return;
  closePdfModal();
  router.push({ path: '/', query: { template_id: currentTemplateId.value } });
}

const MOCK_PDF_URL = 'https://mozilla.github.io/pdf.js/web/compressed.tracemonkey-pldi-09.pdf';

async function loadMockPdf() {
  try {
    await loadPdf(MOCK_PDF_URL);
    pdfModalMeta.value = '';
  } catch (e) {
    console.error('loadMockPdf', e);
    pdfModalMeta.value = 'Erro ao carregar PDF de demonstração';
  }
}

async function loadTemplatePreviewPdf(templateId) {
  try {
    const res = await fetch(`${API_BASE}/api/documentos_modelos/${encodeURIComponent(templateId)}/pdf/`, { credentials: 'include' });
    const data = await res.json();
    if (!data?.ok || !data.pdf_url) throw new Error(data?.error || 'Preview indisponível');
    const pdfUrl = data.pdf_url.startsWith('http') ? data.pdf_url : `${API_BASE}${data.pdf_url}`;
    // Carrega o PDF via fetch (com credentials) e usa blob URL para evitar CORS no pdf.js
    const pdfRes = await fetch(pdfUrl, { credentials: 'include', mode: 'cors' });
    if (!pdfRes.ok) throw new Error('Falha ao baixar o PDF');
    const blob = await pdfRes.blob();
    if (pdfBlobUrl) URL.revokeObjectURL(pdfBlobUrl);
    pdfBlobUrl = URL.createObjectURL(blob);
    await nextTick();
    await loadPdf(pdfBlobUrl);
    pdfModalMeta.value = '';
  } catch (e) {
    console.error('loadTemplatePreviewPdf', e);
    pdfModalMeta.value = e?.message || 'Erro ao carregar preview';
  }
}

let pdfjsLib = null;
onMounted(() => {
  loadTemplates();
  if (window.pdfjsLib) {
    pdfjsLib = window.pdfjsLib;
    if (!pdfjsLib.GlobalWorkerOptions.workerSrc) {
      pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.9.179/pdf.worker.min.js';
    }
  }
});

async function loadPdf(url) {
  if (!pdfjsLib) {
    pdfModalMeta.value = 'Visualizador de PDF não carregado. Recarregue a página.';
    return;
  }
  if (!pdfCanvasEl.value) {
    pdfModalMeta.value = 'Aguarde...';
    await nextTick();
    if (!pdfCanvasEl.value) {
      pdfModalMeta.value = 'Erro ao preparar visualização.';
      return;
    }
  }
  pdfThumbsEl.value.innerHTML = '';
  try {
    const task = pdfjsLib.getDocument({ url });
    const doc = await task.promise;
    pdfDoc.value = doc;
    pdfTotalPages.value = doc.numPages;
    pdfPage.value = 1;
    pdfGotoPage.value = 1;
    await renderPdfPage(1);
    for (let p = 1; p <= doc.numPages; p++) {
      setTimeout(() => renderThumbnail(p), 50 * p);
    }
  } catch (e) {
    console.error('loadPdf', e);
    pdfModalMeta.value = 'Erro ao carregar PDF';
  }
}

async function renderPdfPage(pageNo) {
  if (!pdfDoc.value || !pdfCanvasEl.value) return;
  const page = await pdfDoc.value.getPage(pageNo);
  const viewport = page.getViewport({ scale: 1.25 });
  const canvas = pdfCanvasEl.value;
  const ctx = canvas.getContext('2d');
  canvas.width = 800;
  canvas.height = (800 / viewport.width) * viewport.height;
  await page.render({ canvasContext: ctx, viewport }).promise;
  pdfPage.value = pageNo;
  pdfGotoPage.value = pageNo;
}

async function renderThumbnail(pageNo) {
  if (!pdfDoc.value || !pdfThumbsEl.value) return;
  try {
    const page = await pdfDoc.value.getPage(pageNo);
    const viewport = page.getViewport({ scale: 0.18 });
    const canvas = document.createElement('canvas');
    canvas.width = viewport.width;
    canvas.height = viewport.height;
    const ctx = canvas.getContext('2d');
    await page.render({ canvasContext: ctx, viewport }).promise;
    const wrap = document.createElement('div');
    wrap.className = 'tpl-list__thumb';
    wrap.title = `Ir para página ${pageNo}`;
    wrap.appendChild(canvas);
    wrap.addEventListener('click', () => {
      pdfPage.value = pageNo;
      renderPdfPage(pageNo);
    });
    pdfThumbsEl.value.appendChild(wrap);
  } catch (e) {
    console.warn('thumbnail', e);
  }
}

function prevPage() {
  if (!pdfDoc.value || pdfPage.value <= 1) return;
  renderPdfPage(pdfPage.value - 1);
}

function nextPage() {
  if (!pdfDoc.value || pdfPage.value >= pdfTotalPages.value) return;
  renderPdfPage(pdfPage.value + 1);
}

function goToPage() {
  const v = parseInt(pdfGotoPage.value, 10);
  if (isNaN(v) || v < 1 || v > pdfTotalPages.value) return;
  renderPdfPage(v);
}
</script>

<style scoped>
.tpl-list__top {
  margin-bottom: 16px;
}
.tpl-list__filters {
  padding: 16px 20px;
}
.tpl-list__filter-form {
  margin: 0;
}
.tpl-list__filter-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}
.tpl-list__select {
  min-width: 160px;
  padding: 8px 10px;
}
.tpl-list__search {
  width: 100%;
  max-width: 400px;
  padding: 10px 12px;
}
.tpl-list__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 24px;
}
.tpl-list__card {
  position: relative;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  overflow: hidden;
  background: var(--color-bg);
}
.tpl-list__card-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
  padding: 8px 10px;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.tpl-list__card-media {
  aspect-ratio: 3/4;
  background: #e6ecf3;
}
.tpl-list__card-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: blur(3px);
}
.tpl-list__card-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-soft);
  font-size: 12px;
  font-weight: 600;
}
.tpl-list__card-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding: 16px;
  opacity: 0;
  transition: opacity 0.2s;
}
.tpl-list__card:hover .tpl-list__card-overlay {
  opacity: 1;
}
.tpl-list__empty {
  text-align: center;
  color: var(--color-text-soft);
  font-size: 16px;
  margin: 32px 0;
}
.tpl-list__modal {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.6);
}
.tpl-list__modal-box {
  width: 90%;
  max-width: 900px;
  max-height: 90vh;
  background: var(--color-bg);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.tpl-list__modal-header {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-border);
}
.tpl-list__modal-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
}
.tpl-list__modal-meta {
  font-size: 12px;
  color: var(--color-text-soft);
}
.tpl-list__modal-actions {
  margin-left: auto;
  display: flex;
  gap: 8px;
}
.tpl-list__modal-body {
  display: flex;
  flex: 1;
  gap: 16px;
  padding: 16px;
  overflow: hidden;
}
.tpl-list__pdf-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.tpl-list__pdf-pagenum {
  font-size: 12px;
  color: var(--color-text-soft);
  margin-left: 8px;
}
.tpl-list__pdf-goto {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 4px;
}
.tpl-list__goto-input {
  width: 56px;
  padding: 4px 6px;
}
.tpl-list__pdf-canvas-wrap {
  flex: 1;
  min-height: 400px;
  overflow: auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
}
.tpl-list__pdf-canvas {
  max-width: 100%;
  display: block;
}
.tpl-list__pdf-thumbs {
  width: 140px;
  flex-shrink: 0;
  overflow-y: auto;
}
.tpl-list__pdf-thumbs-title {
  font-size: 12px;
  font-weight: 600;
  margin: 0 0 8px;
}
.tpl-list__pdf-thumbs-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.tpl-list__thumb {
  cursor: pointer;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  overflow: hidden;
}
.tpl-list__thumb:hover {
  border-color: var(--color-primary);
}
</style>
