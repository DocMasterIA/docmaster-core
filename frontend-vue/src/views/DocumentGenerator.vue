<template>
  <div class="doc-gen">
    <header class="gov-page-header">
      <h1 class="gov-page-title">Gerador de Documentos</h1>
      <p class="gov-page-subtitle">
        Crie documentos profissionais com conformidade governamental
      </p>
    </header>

    <div class="doc-gen__grid">
      <!-- Coluna esquerda: wizard -->
      <div class="doc-gen__main">
        <section class="gov-surface doc-gen__wizard">
          <div class="gov-surface__header">
            <div>
              <h2 class="gov-surface__title">Assistente de Criação</h2>
              <p class="gov-surface__subtitle">Guia executivo para documentação profissional</p>
            </div>
          </div>

          <form class="doc-gen__form" @submit.prevent="onSubmit">
            <div class="doc-gen__fields">
              <!-- Escolha do documento base: template ou arquivo -->
              <div class="gov-field doc-gen__field-template">
                <label class="gov-label">Documento Base</label>
                <div class="doc-gen__source-tabs">
                  <label class="doc-gen__tab">
                    <input v-model="sourceMode" type="radio" value="template" @change="onSourceChange('template')" />
                    <span>Template da biblioteca</span>
                  </label>
                  <label class="doc-gen__tab">
                    <input v-model="sourceMode" type="radio" value="file" @change="onSourceChange('file')" />
                    <span>Enviar meu .docx</span>
                  </label>
                  <label class="doc-gen__tab">
                    <input v-model="sourceMode" type="radio" value="llm" @change="onSourceChange('llm')" />
                    <span>Criar do zero (ETP, DFD, TR)</span>
                  </label>
                </div>

                <!-- Criar do zero com IA (LLM) -->
                <div v-show="sourceMode === 'llm'" class="doc-gen__llm-hint">
                  <p class="gov-text-soft">
                    <i class="fa-solid fa-wand-magic-sparkles" aria-hidden="true"></i>
                    A IA gera o documento completo a partir do seu prompt (ETP, DFD, Termo de Referência). Use o contexto do seu órgão e secretaria.
                  </p>
                </div>

                <!-- Template da biblioteca -->
                <div v-show="sourceMode === 'template'" class="doc-gen__search-wrap">
                  <input
                    id="template-search"
                    v-model="searchQuery"
                    type="text"
                    autocomplete="off"
                    placeholder="Selecione um documento base..."
                    class="gov-input doc-gen__search-input"
                    @focus="showTemplateDropdown = true; fetchTemplates('')"
                    @input="onSearchInput"
                    @keydown.down.prevent="focusNextResult"
                    @keydown.up.prevent="focusPrevResult"
                    @keydown.enter.prevent="selectFocusedResult"
                  />
                  <ul
                    v-show="showTemplateDropdown && (templateList.length > 0 || searchQuery === '')"
                    class="doc-gen__results"
                  >
                    <li
                      v-for="(t, idx) in templateList"
                      :key="t.id"
                      class="doc-gen__result-item"
                      :class="{ 'doc-gen__result-item--focused': focusedIndex === idx }"
                      @click="selectTemplate(t)"
                    >
                      <i class="doc-gen__result-icon fa-solid fa-file-lines" aria-hidden="true"></i>
                      <span class="doc-gen__result-name">{{ t.name }}</span>
                    </li>
                    <li v-if="templateList.length === 0 && searchQuery !== ''" class="doc-gen__result-item doc-gen__result-item--empty">
                      Nenhum template encontrado
                    </li>
                  </ul>
                  <p class="gov-text-soft gov-mt-sm">
                    <router-link to="/biblioteca" class="gov-link">Ver Biblioteca de Documentos</router-link>
                  </p>
                </div>

                <!-- Enviar meu .docx -->
                <div v-show="sourceMode === 'file'" class="doc-gen__upload-own">
                  <input
                    ref="docxFileInput"
                    type="file"
                    accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    class="doc-gen__file-input"
                    @change="onDocxFileSelect"
                  />
                  <button
                    v-if="!selectedDocxFile"
                    type="button"
                    class="gov-btn gov-btn--outline doc-gen__upload-btn"
                    @click="docxFileInput?.click()"
                  >
                    <i class="fa-solid fa-upload" aria-hidden="true"></i> Escolher arquivo .docx
                  </button>
                  <div v-else class="doc-gen__uploaded-file">
                    <i class="fa-solid fa-file-word doc-gen__uploaded-icon" aria-hidden="true"></i>
                    <span class="doc-gen__uploaded-name">{{ selectedDocxFile.name }}</span>
                    <button
                      type="button"
                      class="gov-btn gov-btn--outline gov-btn--sm doc-gen__uploaded-remove"
                      aria-label="Remover arquivo"
                      @click="clearDocxFile"
                    >
                      <i class="fa-solid fa-times" aria-hidden="true"></i>
                    </button>
                  </div>
                  <p class="gov-text-soft gov-mt-sm">O arquivo será enviado como base e a IA aplicará o prompt. Máx. 10 MB.</p>
                </div>
              </div>

              <!-- Prompt IA -->
              <div class="gov-field">
                <label class="gov-label" for="ia-prompt">
                  Prompt de Inteligência Artificial
                  <span class="gov-label__hint">(IA contextual inteligente)</span>
                </label>
                <div v-if="sourceMode === 'llm'" class="doc-gen__doc-type">
                  <label class="gov-label gov-label--inline">Tipo de documento</label>
                  <div class="doc-gen__doc-type-options">
                    <label class="doc-gen__doc-type-option">
                      <input v-model="docTypeMode" type="radio" value="auto" />
                      <span>Padrão (ETP / DFD / TR)</span>
                    </label>
                    <label class="doc-gen__doc-type-option">
                      <input v-model="docTypeMode" type="radio" value="tr_modelo" />
                      <span>TR com modelo fixo (slots IA)</span>
                    </label>
                  </div>
                </div>
                <textarea
                  id="ia-prompt"
                  v-model="iaPrompt"
                  name="ia_prompt"
                  class="gov-textarea"
                  rows="6"
                  :placeholder="sourceMode === 'llm' ? 'Ex: Gerar ETP para coleta seletiva de resíduos em 3 bairros' : 'Digite aqui o prompt que será enviado para a IA contextual inteligente...'"
                  required
                />
                <p class="gov-text-soft gov-mt-sm">
                  <i class="fa-solid fa-lightbulb" aria-hidden="true"></i> <strong>Dica:</strong> A IA contextual analisa seu prompt e aplica mudanças no documento.
                </p>
              </div>

              <!-- Botões -->
              <div class="doc-gen__actions">
                <button
                  type="submit"
                  class="gov-btn gov-btn--primary"
                  :disabled="isSubmitting || !hasDocumentBase || !iaPrompt.trim()"
                >
                  <span v-if="!isSubmitting"><i class="fa-solid fa-robot" aria-hidden="true"></i> Gerar com IA Contextual</span>
                  <span v-else class="doc-gen__spinner">Processando com IA...</span>
                </button>
                <template v-if="documentReady">
                  <a
                    v-if="documentDocxUrl"
                    :href="documentDocxUrl"
                    download="documento.docx"
                    class="gov-btn gov-btn--secondary"
                  >
                    <i class="fa-solid fa-file-word" aria-hidden="true"></i> Download DOCX
                  </a>
                  <a
                    v-if="documentPdfUrl"
                    :href="documentPdfUrl"
                    download="documento.pdf"
                    class="gov-btn gov-btn--secondary"
                  >
                    <i class="fa-solid fa-file-pdf" aria-hidden="true"></i> Download PDF
                  </a>
                </template>
              </div>
            </div>
          </form>

          <!-- Erro de geração -->
          <div v-if="generateError" class="doc-gen__error gov-surface">
            <p class="doc-gen__error-text">{{ generateError }}</p>
          </div>
          <!-- Mensagem de sucesso -->
          <div v-if="documentReady && successMessage" class="doc-gen__success gov-surface">
            <p class="doc-gen__success-title">Documento gerado com sucesso!</p>
            <p class="gov-text-soft">{{ successMessage }}</p>
          </div>
        </section>
      </div>

      <!-- Coluna direita: preview -->
      <aside class="doc-gen__aside">
        <section class="gov-surface doc-gen__preview-card">
          <div class="gov-surface__header">
            <div>
              <h2 class="gov-surface__title">Pré-visualização de Documento</h2>
              <p class="gov-surface__subtitle">Veja o modelo antes de gerar</p>
            </div>
          </div>
          <div class="doc-gen__preview-body">
            <h3 class="doc-gen__preview-heading">{{ previewHeading }}</h3>
            <p class="gov-text-soft">{{ previewSub }}</p>
            <div class="doc-gen__preview-excerpt">
              <template v-if="sourceMode === 'llm'">
                <p class="gov-text-soft">O documento será criado inteiramente pela IA com base no seu prompt. Sem necessidade de template prévio.</p>
              </template>
              <template v-else-if="sourceMode === 'file' && selectedDocxFile">
                <p class="gov-text-soft">Documento enviado: <strong>{{ selectedDocxFile.name }}</strong></p>
                <p class="gov-text-soft gov-text-sm">Pré-visualização em PDF não disponível para arquivo enviado. Gere o documento para baixar.</p>
              </template>
              <template v-else-if="selectedTemplate?.preview_image">
                <p class="gov-text-soft">Pré-visualização do documento:</p>
                <img :src="previewImageUrl" alt="Preview" class="doc-gen__preview-img" />
              </template>
              <template v-else>
                <p class="gov-text-soft">Nenhum documento base selecionado. Escolha um template, envie um .docx ou use "Criar do zero".</p>
              </template>
            </div>
            <div class="doc-gen__preview-actions">
              <button
                v-if="selectedTemplate?.id && sourceMode === 'template'"
                type="button"
                class="gov-btn gov-btn--primary gov-btn--sm"
                @click="openPdfModal"
              >
                Pré-visualizar
              </button>
              <router-link to="/biblioteca" class="gov-btn gov-btn--outline gov-btn--sm">Biblioteca</router-link>
            </div>
          </div>
        </section>
      </aside>
    </div>

    <!-- Modal PDF -->
    <div
      v-show="pdfModalOpen"
      class="doc-gen__modal"
      role="dialog"
      aria-modal="true"
      @click.self="closePdfModal"
    >
      <div class="doc-gen__modal-box">
        <div class="doc-gen__modal-header">
          <h3 class="doc-gen__modal-title">{{ pdfModalTitle }}</h3>
          <span class="doc-gen__modal-meta">{{ pdfModalMeta }}</span>
          <button type="button" class="gov-btn gov-btn--outline gov-btn--sm" @click="closePdfModal">
            Fechar
          </button>
        </div>
        <div class="doc-gen__modal-body">
          <div class="doc-gen__pdf-toolbar">
            <button type="button" class="gov-btn gov-btn--outline gov-btn--sm" :disabled="!pdfDoc || pdfPage <= 1" @click="prevPage">
              Anterior
            </button>
            <button type="button" class="gov-btn gov-btn--outline gov-btn--sm" :disabled="!pdfDoc || pdfPage >= pdfTotalPages" @click="nextPage">
              Próximo
            </button>
            <span class="doc-gen__pdf-pagenum">Página {{ pdfPage }} de {{ pdfTotalPages }}</span>
            <span class="doc-gen__pdf-goto">
              <input v-model.number="pdfGotoPage" type="number" min="1" :max="pdfTotalPages" class="gov-input doc-gen__goto-input" />
              <button type="button" class="gov-btn gov-btn--outline gov-btn--sm" @click="goToPage">Ir</button>
            </span>
          </div>
          <div class="doc-gen__pdf-canvas-wrap">
            <canvas ref="pdfCanvasEl" class="doc-gen__pdf-canvas"></canvas>
          </div>
          <aside class="doc-gen__pdf-thumbs">
            <h4 class="doc-gen__pdf-thumbs-title">Miniaturas</h4>
            <div ref="pdfThumbsEl" class="doc-gen__pdf-thumbs-list"></div>
          </aside>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRoute } from 'vue-router';

const API_BASE = import.meta.env.VITE_API_URL || '';
const route = useRoute();

const useOwnFile = ref(false);
const selectedDocxFile = ref(null);
const docxFileInput = ref(null);

const searchQuery = ref('');
const showTemplateDropdown = ref(false);
const templateList = ref([]);
const selectedTemplate = ref(null);
const focusedIndex = ref(-1);
const searchDebounce = ref(null);

const iaPrompt = ref('');
const docTypeMode = ref('auto'); // 'auto' (generate-document), 'tr_modelo' (TR modelo fixo)
const sourceMode = ref('template'); // 'template' | 'file' | 'llm'
const isSubmitting = ref(false);
const documentReady = ref(false);
const documentDocxUrl = ref('');
const documentPdfUrl = ref('');
const successMessage = ref('');
const generateError = ref('');

const pdfModalOpen = ref(false);
const pdfModalTitle = ref('Preview');
const pdfModalMeta = ref('');
const pdfCanvasEl = ref(null);
const pdfThumbsEl = ref(null);
const pdfDoc = ref(null);
const pdfPage = ref(1);
const pdfTotalPages = ref(0);
const pdfGotoPage = ref(1);

const hasDocumentBase = computed(() => {
  if (sourceMode.value === 'llm') return true;
  if (sourceMode.value === 'file') return !!selectedDocxFile.value;
  return !!selectedTemplate.value?.id;
});

const previewHeading = computed(() => {
  if (sourceMode.value === 'llm') return docTypeMode.value === 'tr_modelo' ? 'Gerar Termo de Referência (modelo fixo)' : 'Gerar do zero com IA';
  if (sourceMode.value === 'file' && selectedDocxFile.value) return selectedDocxFile.value.name;
  return selectedTemplate.value?.name || 'Modelo de Documento';
});
const previewSub = computed(() => {
  if (sourceMode.value === 'llm') {
    return docTypeMode.value === 'tr_modelo'
      ? 'Termo de Referência baseado no modelo fixo oficial, com slots preenchidos pela IA.'
      : 'ETP, DFD ou Termo de Referência gerado via LLM com base no seu prompt.';
  }
  if (sourceMode.value === 'file' && selectedDocxFile.value) return 'Documento enviado — use o prompt e gere para baixar.';
  return selectedTemplate.value ? `Modelo de Documento - ${selectedTemplate.value.name}` : 'Selecione um template ou envie um .docx.';
});
const previewImageUrl = computed(() => {
  const img = selectedTemplate.value?.preview_image;
  if (!img) return '';
  return img.startsWith('http') ? img : `${API_BASE}${img}`;
});

async function fetchTemplates(q) {
  const url = `${API_BASE}/api/documentos_modelos/lista_10?q=${encodeURIComponent(q || '')}`;
  try {
    const res = await fetch(url, { credentials: 'include' });
    if (!res.ok) return;
    const data = await res.json();
    templateList.value = data.templates || [];
    focusedIndex.value = -1;
  } catch (e) {
    console.warn('fetchTemplates', e);
    templateList.value = [];
  }
}

function onSearchInput() {
  clearTimeout(searchDebounce.value);
  searchDebounce.value = setTimeout(() => {
    fetchTemplates(searchQuery.value);
  }, 160);
}

function selectTemplate(t) {
  selectedTemplate.value = t;
  searchQuery.value = t.name;
  showTemplateDropdown.value = false;
  fetchTemplateDetails(t.id);
}

async function fetchTemplateDetails(id) {
  try {
    const res = await fetch(`${API_BASE}/api/documentos_modelos/?id=${encodeURIComponent(id)}`, { credentials: 'include' });
    if (!res.ok) return;
    const data = await res.json();
    const t = data.template || data.templates?.[0];
    if (t) selectedTemplate.value = { id: t.id, name: t.name, preview_image: t.preview_image };
  } catch (e) {
    console.debug('fetchTemplateDetails', e);
  }
}

function focusNextResult() {
  if (templateList.value.length === 0) return;
  focusedIndex.value = Math.min(focusedIndex.value + 1, templateList.value.length - 1);
}

function focusPrevResult() {
  focusedIndex.value = Math.max(focusedIndex.value - 1, 0);
}

function selectFocusedResult() {
  if (focusedIndex.value >= 0 && templateList.value[focusedIndex.value]) {
    selectTemplate(templateList.value[focusedIndex.value]);
  } else if (templateList.value.length > 0) {
    selectTemplate(templateList.value[0]);
  }
}

function clickOutside(e) {
  if (!e.target.closest('.doc-gen__search-wrap') && !e.target.closest('.doc-gen__results')) {
    showTemplateDropdown.value = false;
  }
}

function onSourceChange(mode) {
  if (mode === 'llm' || mode === 'file') {
    selectedTemplate.value = null;
    searchQuery.value = '';
    showTemplateDropdown.value = false;
  }
  if (mode === 'template' || mode === 'llm') {
    selectedDocxFile.value = null;
    if (docxFileInput.value) docxFileInput.value.value = '';
  }
}

function onDocxFileSelect(e) {
  const file = e.target.files?.[0];
  if (!file) return;
  const name = (file.name || '').toLowerCase();
  if (!name.endsWith('.docx')) {
    alert('Selecione um arquivo .docx');
    e.target.value = '';
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    alert('Arquivo deve ter no máximo 10 MB.');
    e.target.value = '';
    return;
  }
  selectedDocxFile.value = file;
}

function clearDocxFile() {
  selectedDocxFile.value = null;
  if (docxFileInput.value) docxFileInput.value.value = '';
}

async function onSubmit() {
  if (!hasDocumentBase.value || !iaPrompt.value.trim()) return;
  isSubmitting.value = true;
  documentReady.value = false;
  documentDocxUrl.value = '';
  documentPdfUrl.value = '';
  generateError.value = '';

  try {
    if (sourceMode.value === 'llm') {
      await submitViaLLM();
      return;
    }
    await submitViaTemplate();
  } catch (e) {
    generateError.value = e.message || 'Erro ao gerar documento';
  } finally {
    isSubmitting.value = false;
  }
}

async function submitViaLLM() {
  const payload = {
    user_prompt: iaPrompt.value.trim(),
    output: 'docx',
  };
  if (selectedTemplate.value?.id && docTypeMode.value === 'auto') {
    payload.template_id = selectedTemplate.value.id;
  }

  const endpoint =
    docTypeMode.value === 'tr_modelo'
      ? `${API_BASE}/api/documentos/gerar-tr-modelo`
      : `${API_BASE}/api/documentos/gerar-via-llm`;

  const res = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(payload),
  });

  const contentType = res.headers.get('content-type') || '';
  if (!res.ok) {
    const err = contentType.includes('json')
      ? await res.json().catch(() => ({}))
      : {};
    generateError.value = err.error || err.detail || `Erro ${res.status}`;
    return;
  }

  if (contentType.includes('application/vnd.openxmlformats') || contentType.includes('octet-stream')) {
    const blob = await res.blob();
    documentDocxUrl.value = URL.createObjectURL(blob);
    documentPdfUrl.value = '';
    documentReady.value = true;
    successMessage.value = 'Documento gerado pela IA. Baixe o DOCX abaixo.';
  } else {
    const data = await res.json().catch(() => ({}));
    if (data.ok && data.docx_path) {
      generateError.value = 'Resposta inesperada: DOCX não retornado. Tente novamente.';
    } else {
      generateError.value = data.error || data.detail || 'Erro na geração';
    }
  }
}

async function submitViaTemplate() {
  let templateId = selectedTemplate.value?.id;

  if (sourceMode.value === 'file' && selectedDocxFile.value) {
    const formData = new FormData();
    formData.append('template_file', selectedDocxFile.value);
    formData.append('name', selectedDocxFile.value.name.replace(/\.docx$/i, ''));
    const resUpload = await fetch(`${API_BASE}/api/documentos_modelos/enviar`, {
      method: 'POST',
      credentials: 'include',
      body: formData,
    });
    const dataUpload = await resUpload.json().catch(() => ({}));
    if (!resUpload.ok || !dataUpload.template_id) {
      generateError.value = dataUpload.error || `Erro ao enviar arquivo (${resUpload.status})`;
      return;
    }
    templateId = dataUpload.template_id;
  }

  const payload = { template_id: templateId, values: { prompt: iaPrompt.value.trim() } };
  const opts = { method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include' };

  const resDocx = await fetch(`${API_BASE}/api/documentos_modelos/gerar`, {
    ...opts,
    body: JSON.stringify({ ...payload, output: 'docx' }),
  });
  if (!resDocx.ok) {
    const err = await resDocx.json().catch(() => ({}));
    generateError.value = err.error || `Erro ${resDocx.status}`;
    return;
  }
  const resPdf = await fetch(`${API_BASE}/api/documentos_modelos/gerar`, {
    ...opts,
    body: JSON.stringify({ ...payload, output: 'pdf' }),
  });
  if (!resPdf.ok) {
    const err = await resPdf.json().catch(() => ({}));
    generateError.value = err.error || `Erro ${resPdf.status}`;
    return;
  }

  const blobDocx = await resDocx.blob();
  const blobPdf = await resPdf.blob();
  documentDocxUrl.value = URL.createObjectURL(blobDocx);
  documentPdfUrl.value = URL.createObjectURL(blobPdf);
  documentReady.value = true;
  successMessage.value = 'Seu documento foi processado e está pronto para download.';
}

function openPdfModal() {
  if (!selectedTemplate.value?.id) return;
  pdfModalTitle.value = selectedTemplate.value.name || 'Preview';
  pdfModalMeta.value = 'Carregando preview...';
  pdfModalOpen.value = true;
  loadTemplatePreviewPdf(selectedTemplate.value.id);
}

function closePdfModal() {
  pdfModalOpen.value = false;
  pdfDoc.value = null;
  pdfPage.value = 1;
  pdfTotalPages.value = 0;
  pdfModalMeta.value = '';
  if (pdfThumbsEl.value) pdfThumbsEl.value.innerHTML = '';
}

async function loadTemplatePreviewPdf(templateId) {
  try {
    const res = await fetch(`${API_BASE}/api/documentos_modelos/${encodeURIComponent(templateId)}/pdf/`, { credentials: 'include' });
    const data = await res.json();
    if (!data?.ok || !data.pdf_url) throw new Error(data?.error || 'Preview indisponível');
    const url = data.pdf_url.startsWith('http') ? data.pdf_url : `${API_BASE}${data.pdf_url}`;
    await loadPdf(url);
    pdfModalMeta.value = '';
  } catch (e) {
    console.error('loadTemplatePreviewPdf', e);
    pdfModalMeta.value = 'Erro ao carregar preview';
  }
}

let pdfjsLib = null;
onMounted(() => {
  document.addEventListener('click', clickOutside);
  const templateId = route.query.template_id;
  if (templateId) {
    fetchTemplateDetails(templateId).then(() => {
      if (selectedTemplate.value) searchQuery.value = selectedTemplate.value.name;
    });
  }
  if (window.pdfjsLib) {
    pdfjsLib = window.pdfjsLib;
    if (!pdfjsLib.GlobalWorkerOptions.workerSrc) {
      pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.9.179/pdf.worker.min.js';
    }
  }
});
onUnmounted(() => {
  document.removeEventListener('click', clickOutside);
  if (documentDocxUrl.value) URL.revokeObjectURL(documentDocxUrl.value);
  if (documentPdfUrl.value) URL.revokeObjectURL(documentPdfUrl.value);
});

async function loadPdf(url) {
  if (!pdfjsLib || !pdfCanvasEl.value) return;
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
    wrap.className = 'doc-gen__thumb';
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
.doc-gen__grid {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 24px;
}
@media (max-width: 960px) {
  .doc-gen__grid {
    grid-template-columns: 1fr;
  }
}
.doc-gen__main {
  min-width: 0;
}
.doc-gen__wizard {
  padding: 20px 24px;
}
.doc-gen__form {
  margin-top: 8px;
}
.doc-gen__fields {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.doc-gen__field-template {
  position: relative;
}
.doc-gen__source-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.doc-gen__tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background: var(--color-bg);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}
.doc-gen__tab input {
  margin: 0;
}
.doc-gen__tab:has(input:checked) {
  border-color: var(--color-primary);
  background: #e5f3fa;
  color: var(--color-primary-dark);
}
.doc-gen__llm-hint {
  padding: 12px 16px;
  background: #e5f3fa;
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-md);
}
.doc-gen__llm-hint .fa-wand-magic-sparkles {
  margin-right: 6px;
  color: var(--color-primary);
}
.doc-gen__upload-own {
  position: relative;
}
.doc-gen__file-input {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  pointer-events: none;
}
.doc-gen__upload-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.doc-gen__uploaded-file {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: var(--color-bg-soft);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 13px;
}
.doc-gen__uploaded-icon {
  color: var(--color-primary);
  flex-shrink: 0;
}
.doc-gen__uploaded-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.doc-gen__uploaded-remove {
  padding: 4px 8px;
  min-width: auto;
}
.doc-gen__search-wrap {
  position: relative;
}
.doc-gen__search-input {
  width: 100%;
  padding: 10px 12px;
}
.doc-gen__results {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  margin: 4px 0 0;
  padding: 4px 0;
  list-style: none;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  max-height: 240px;
  overflow-y: auto;
  z-index: 50;
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}
.doc-gen__result-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 13px;
}
.doc-gen__result-item:hover,
.doc-gen__result-item--focused {
  background: #e5f3fa;
}
.doc-gen__result-item--empty {
  cursor: default;
  color: var(--color-text-soft);
}
.doc-gen__result-icon {
  font-size: 16px;
}
.doc-gen .fa-lightbulb,
.doc-gen .fa-robot,
.doc-gen .fa-file-word,
.doc-gen .fa-file-pdf {
  margin-right: 6px;
}
.doc-gen__result-name {
  font-weight: 600;
  color: var(--color-primary-dark);
}
.doc-gen__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}
.doc-gen__spinner {
  opacity: 0.9;
}
.doc-gen__success {
  margin-top: 20px;
  padding: 16px 20px;
  background: #e0f1ed;
  border: 1px solid var(--color-success);
  border-radius: var(--radius-lg);
}
.doc-gen__success-title {
  font-weight: 600;
  color: var(--color-success);
  margin: 0 0 4px;
}
.doc-gen__error {
  margin-top: 16px;
  padding: 12px 16px;
  background: #f6e0de;
  border: 1px solid var(--color-danger);
  border-radius: var(--radius-lg);
}
.doc-gen__error-text {
  margin: 0;
  color: var(--color-danger);
  font-size: 13px;
}
.gov-label__hint {
  font-weight: normal;
  color: var(--color-text-soft);
}
.gov-mt-sm {
  margin-top: 8px;
}
.doc-gen__aside {
  min-width: 0;
}
.doc-gen__preview-card {
  padding: 20px 24px;
}
.doc-gen__preview-heading {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 4px;
}
.doc-gen__preview-excerpt {
  margin-top: 12px;
}
.doc-gen__preview-img {
  width: 100%;
  max-height: 200px;
  object-fit: contain;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}
.doc-gen__preview-actions {
  margin-top: 16px;
  display: flex;
  gap: 8px;
}
.doc-gen__modal {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0,0,0,0.6);
}
.doc-gen__modal-box {
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
.doc-gen__modal-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-border);
}
.doc-gen__modal-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
}
.doc-gen__modal-meta {
  font-size: 12px;
  color: var(--color-text-soft);
}
.doc-gen__modal-body {
  display: flex;
  flex: 1;
  gap: 16px;
  padding: 16px;
  overflow: hidden;
}
.doc-gen__pdf-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.doc-gen__pdf-pagenum {
  font-size: 12px;
  color: var(--color-text-soft);
  margin-left: 8px;
}
.doc-gen__pdf-goto {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 4px;
}
.doc-gen__goto-input {
  width: 56px;
  padding: 4px 6px;
}
.doc-gen__pdf-canvas-wrap {
  flex: 1;
  min-height: 400px;
  overflow: auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
}
.doc-gen__pdf-canvas {
  max-width: 100%;
  display: block;
}
.doc-gen__pdf-thumbs {
  width: 140px;
  flex-shrink: 0;
  overflow-y: auto;
}
.doc-gen__pdf-thumbs-title {
  font-size: 12px;
  font-weight: 600;
  margin: 0 0 8px;
}
.doc-gen__pdf-thumbs-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.doc-gen__thumb {
  cursor: pointer;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  overflow: hidden;
}
.doc-gen__thumb:hover {
  border-color: var(--color-primary);
}
</style>
