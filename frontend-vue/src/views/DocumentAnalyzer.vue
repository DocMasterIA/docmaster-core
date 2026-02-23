<template>
  <div class="doc-analyzer">
    <header class="gov-page-header">
      <h1 class="gov-page-title">Analisador de Documentos</h1>
      <p class="gov-page-subtitle">
        Envie documentos para análise com IA: conformidade, melhorias e recomendações
      </p>
    </header>

    <div class="doc-analyzer__grid">
      <!-- Coluna esquerda: upload e arquivos -->
      <section class="gov-surface doc-analyzer__upload">
        <div class="gov-surface__header">
          <div>
            <h2 class="gov-surface__title">Documentos para análise</h2>
            <p class="gov-surface__subtitle">PDF ou DOCX. Arraste ou selecione os arquivos.</p>
          </div>
        </div>

        <div
          class="doc-analyzer__dropzone"
          :class="{ 'doc-analyzer__dropzone--active': isDragging, 'doc-analyzer__dropzone--has-files': files.length > 0 }"
          @dragover.prevent="isDragging = true"
          @dragleave.prevent="isDragging = false"
          @drop.prevent="onDrop"
        >
          <input
            ref="fileInput"
            type="file"
            accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            multiple
            class="doc-analyzer__file-input"
            @change="onFileSelect"
          />
          <div class="doc-analyzer__dropzone-content">
            <i class="fa-solid fa-cloud-arrow-up doc-analyzer__dropzone-icon" aria-hidden="true"></i>
            <p class="doc-analyzer__dropzone-text">Arraste arquivos aqui ou clique para selecionar</p>
            <p class="gov-text-soft gov-text-sm">PDF e DOCX, até 10 MB por arquivo</p>
          </div>
        </div>

        <ul v-if="files.length > 0" class="doc-analyzer__file-list">
          <li v-for="(f, idx) in files" :key="f.id" class="doc-analyzer__file-item">
            <i class="fa-solid fa-file-lines doc-analyzer__file-icon" aria-hidden="true"></i>
            <span class="doc-analyzer__file-name" :title="f.file.name">{{ f.file.name }}</span>
            <span class="doc-analyzer__file-size">{{ formatSize(f.file.size) }}</span>
            <button
              type="button"
              class="gov-btn gov-btn--outline gov-btn--sm doc-analyzer__file-remove"
              aria-label="Remover arquivo"
              @click="removeFile(idx)"
            >
              <i class="fa-solid fa-times" aria-hidden="true"></i>
            </button>
          </li>
        </ul>

        <div class="doc-analyzer__actions">
          <button
            type="button"
            class="gov-btn gov-btn--primary"
            :disabled="files.length === 0 || isAnalyzing"
            @click="runAnalysis"
          >
            <span v-if="!isAnalyzing">
              <i class="fa-solid fa-wand-magic-sparkles" aria-hidden="true"></i> Analisar com IA
            </span>
            <span v-else class="doc-analyzer__spinner">
              <i class="fa-solid fa-spinner fa-spin" aria-hidden="true"></i> Analisando...
            </span>
          </button>
        </div>
      </section>

      <!-- Coluna direita: resultados -->
      <aside class="doc-analyzer__results-wrap">
        <section class="gov-surface doc-analyzer__results">
          <div class="gov-surface__header">
            <div>
              <h2 class="gov-surface__title">Resultado da análise</h2>
              <p class="gov-surface__subtitle">Conformidade, melhorias e sugestões da IA</p>
            </div>
          </div>

          <div v-if="!analysisDone && !isAnalyzing" class="doc-analyzer__results-empty">
            <i class="fa-solid fa-file-circle-question doc-analyzer__empty-icon" aria-hidden="true"></i>
            <p>Envie um ou mais documentos e clique em <strong>Analisar com IA</strong> para ver o resultado.</p>
          </div>

          <div v-else-if="isAnalyzing" class="doc-analyzer__results-loading">
            <i class="fa-solid fa-spinner fa-spin doc-analyzer__loading-icon" aria-hidden="true"></i>
            <p>Processando documento(s) com inteligência artificial...</p>
          </div>

          <div v-else class="doc-analyzer__results-body">
            <div v-if="analysisError" class="doc-analyzer__error">
              <i class="fa-solid fa-circle-exclamation" aria-hidden="true"></i>
              {{ analysisError }}
            </div>

            <template v-else>
              <!-- Resumo -->
              <div class="doc-analyzer__block">
                <h3 class="doc-analyzer__block-title">
                  <i class="fa-solid fa-file-circle-check doc-analyzer__block-icon doc-analyzer__block-icon--success" aria-hidden="true"></i>
                  Resumo da análise
                </h3>
                <p class="gov-text-soft gov-text-sm">
                  <strong>Tipo de documento:</strong> {{ result.document_type || 'não identificado' }}<br />
                  <strong>Conformidade geral:</strong>
                  <span v-if="result.conformidade_geral === true">Conforme</span>
                  <span v-else-if="result.conformidade_geral === false">Não conforme</span>
                  <span v-else>Indefinida</span>
                </p>
                <p v-if="result.observacoes" class="gov-text-soft gov-text-sm mt-2">
                  <strong>Observações:</strong> {{ result.observacoes }}
                </p>
              </div>

              <!-- Resumo executivo -->
              <div v-if="result.resumo_executivo" class="doc-analyzer__block">
                <h3 class="doc-analyzer__block-title">
                  <i class="fa-solid fa-file-lines doc-analyzer__block-icon" aria-hidden="true"></i>
                  Resumo executivo
                </h3>
                <p class="doc-analyzer__resumo-executivo gov-text-soft">{{ result.resumo_executivo }}</p>
              </div>

              <!-- Seções detectadas -->
              <div v-if="result.sections_detected && result.sections_detected.length" class="doc-analyzer__block">
                <h3 class="doc-analyzer__block-title">
                  <i class="fa-solid fa-list doc-analyzer__block-icon" aria-hidden="true"></i>
                  Seções detectadas
                </h3>
                <ul class="doc-analyzer__suggestion-list">
                  <li v-for="(s, i) in result.sections_detected" :key="i" class="doc-analyzer__suggestion-item">
                    {{ s }}
                  </li>
                </ul>
              </div>

              <!-- Pontos importantes -->
              <div v-if="result.pontos_importantes && result.pontos_importantes.length" class="doc-analyzer__block">
                <h3 class="doc-analyzer__block-title">
                  <i class="fa-solid fa-star doc-analyzer__block-icon doc-analyzer__block-icon--success" aria-hidden="true"></i>
                  Pontos importantes
                </h3>
                <ul class="doc-analyzer__suggestion-list">
                  <li v-for="(p, i) in result.pontos_importantes" :key="i" class="doc-analyzer__suggestion-item">
                    {{ p }}
                  </li>
                </ul>
              </div>

              <!-- Acertos -->
              <div v-if="result.acertos && result.acertos.length" class="doc-analyzer__block">
                <h3 class="doc-analyzer__block-title">
                  <i class="fa-solid fa-circle-check doc-analyzer__block-icon doc-analyzer__block-icon--success" aria-hidden="true"></i>
                  Acertos (em conformidade)
                </h3>
                <ul class="doc-analyzer__suggestion-list">
                  <li v-for="(a, i) in result.acertos" :key="i" class="doc-analyzer__suggestion-item">
                    {{ a }}
                  </li>
                </ul>
              </div>

              <!-- Ressalvas -->
              <div v-if="result.ressalvas && result.ressalvas.length" class="doc-analyzer__block">
                <h3 class="doc-analyzer__block-title">
                  <i class="fa-solid fa-triangle-exclamation doc-analyzer__block-icon doc-analyzer__block-icon--warning" aria-hidden="true"></i>
                  Ressalvas / Itens ambíguos
                </h3>
                <ul class="doc-analyzer__suggestion-list">
                  <li v-for="(r, i) in result.ressalvas" :key="i" class="doc-analyzer__suggestion-item">
                    {{ r }}
                  </li>
                </ul>
              </div>

              <!-- Erros -->
              <div v-if="result.erros && result.erros.length" class="doc-analyzer__block">
                <h3 class="doc-analyzer__block-title">
                  <i class="fa-solid fa-circle-xmark doc-analyzer__block-icon doc-analyzer__block-icon--danger" aria-hidden="true"></i>
                  Erros formais e não conformidades
                </h3>
                <ul class="doc-analyzer__suggestion-list">
                  <li v-for="(e, i) in result.erros" :key="i" class="doc-analyzer__suggestion-item">
                    {{ e }}
                  </li>
                </ul>
              </div>

              <!-- Riscos jurídicos -->
              <div v-if="result.riscos_juridicos && result.riscos_juridicos.length" class="doc-analyzer__block">
                <h3 class="doc-analyzer__block-title">
                  <i class="fa-solid fa-scale-balanced doc-analyzer__block-icon doc-analyzer__block-icon--warning" aria-hidden="true"></i>
                  Riscos jurídicos
                </h3>
                <ul class="doc-analyzer__suggestion-list">
                  <li v-for="(r, i) in result.riscos_juridicos" :key="i" class="doc-analyzer__suggestion-item">
                    {{ r }}
                  </li>
                </ul>
              </div>

              <!-- Sugestões de reescrita -->
              <div v-if="result.sugestoes_reescrita && result.sugestoes_reescrita.length" class="doc-analyzer__block">
                <h3 class="doc-analyzer__block-title">
                  <i class="fa-solid fa-pen-to-square doc-analyzer__block-icon" aria-hidden="true"></i>
                  Sugestões de reescrita
                </h3>
                <ul class="doc-analyzer__suggestion-list">
                  <li v-for="(s, i) in result.sugestoes_reescrita" :key="i" class="doc-analyzer__suggestion-item">
                    {{ s }}
                  </li>
                </ul>
              </div>
            </template>
          </div>
        </section>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onUnmounted } from 'vue';

const API_BASE = import.meta.env.VITE_API_URL || '';

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB
const ACCEPT_TYPES = ['.pdf', '.docx', 'application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];

const fileInput = ref(null);
const isDragging = ref(false);
const files = ref([]);
const fileId = ref(0);
const isAnalyzing = ref(false);
const analysisDone = ref(false);
const analysisError = ref('');

// Estrutura compatível com AnalyzeDocumentResponse do rag_service
const result = reactive({
  document_type: '',
  sections_detected: [],
  pontos_importantes: [],
  acertos: [],
  ressalvas: [],
  erros: [],
  riscos_juridicos: [],
  sugestoes_reescrita: [],
  conformidade_geral: null,
  observacoes: '',
  resumo_executivo: '',
});

function acceptFile(file) {
  const ext = (file.name || '').toLowerCase();
  const type = file.type || '';
  const ok = ACCEPT_TYPES.some((t) => t.startsWith('.') ? ext.endsWith(t) : type === t);
  if (!ok) return false;
  if (file.size > MAX_FILE_SIZE) return false;
  return true;
}

function onDrop(e) {
  isDragging.value = false;
  const items = e.dataTransfer?.files;
  if (!items?.length) return;
  addFiles(Array.from(items));
}

function onFileSelect(e) {
  const items = e.target.files;
  if (!items?.length) return;
  addFiles(Array.from(items));
  e.target.value = '';
}

function addFiles(list) {
  const added = list.filter((file) => acceptFile(file)).map((file) => ({ id: ++fileId.value, file }));
  const rejected = list.filter((f) => !acceptFile(f));
  if (rejected.length) {
    const names = rejected.map((f) => f.name).join(', ');
    alert(`Arquivo(s) ignorado(s) (tipo ou tamanho): ${names}. Use PDF ou DOCX, até 10 MB.`);
  }
  files.value = [...files.value, ...added];
}

function removeFile(index) {
  files.value = files.value.filter((_, i) => i !== index);
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** Resposta mockada até existir API de análise no backend */
function mapApiResponse(payload) {
  result.document_type = payload.document_type || '';
  result.sections_detected = payload.sections_detected || [];
  result.pontos_importantes = payload.pontos_importantes || [];
  result.acertos = payload.acertos || [];
  result.ressalvas = payload.ressalvas || [];
  result.erros = payload.erros || [];
  result.riscos_juridicos = payload.riscos_juridicos || [];
  result.sugestoes_reescrita = payload.sugestoes_reescrita || [];
  result.conformidade_geral = payload.conformidade_geral ?? null;
  result.observacoes = payload.observacoes || '';
  result.resumo_executivo = payload.resumo_executivo || '';
}

async function runAnalysis() {
  if (files.value.length === 0) return;
  isAnalyzing.value = true;
  analysisDone.value = false;
  analysisError.value = '';
  result.document_type = '';
  result.sections_detected = [];
  result.pontos_importantes = [];
  result.acertos = [];
  result.ressalvas = [];
  result.erros = [];
  result.riscos_juridicos = [];
  result.sugestoes_reescrita = [];
  result.conformidade_geral = null;
  result.observacoes = '';
  result.resumo_executivo = '';

  try {
    const formData = new FormData();
    // Por enquanto, enviamos apenas o primeiro arquivo para análise
    const primary = files.value[0]?.file;
    if (!primary) {
      throw new Error('Nenhum arquivo válido para análise.');
    }
    formData.append('file', primary);

    const res = await fetch(`${API_BASE}/api/analise-documentos/`, {
      method: 'POST',
      body: formData,
      credentials: 'include',
    });

    if (!res.ok) {
      let msg = `Erro na análise (HTTP ${res.status})`;
      try {
        const data = await res.json();
        msg = data.detail || data.error || msg;
      } catch (e) {
        // ignore parse error, keep msg
      }
      throw new Error(msg);
    }

    const data = await res.json();
    if (!data.ok) {
      throw new Error(data.error || 'Falha na análise do documento.');
    }

    mapApiResponse(data);
    analysisDone.value = true;
  } catch (e) {
    analysisError.value = e.message || 'Erro ao analisar documentos. Tente novamente.';
  } finally {
    isAnalyzing.value = false;
  }
}

onUnmounted(() => {
  isDragging.value = false;
});
</script>

<style scoped>
.doc-analyzer__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}
@media (max-width: 960px) {
  .doc-analyzer__grid {
    grid-template-columns: 1fr;
  }
}
.doc-analyzer__upload {
  padding: 20px 24px;
}
.doc-analyzer__dropzone {
  position: relative;
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-lg);
  padding: 32px 24px;
  text-align: center;
  background: var(--color-bg-soft);
  transition: border-color 0.2s, background 0.2s;
}
.doc-analyzer__dropzone:hover,
.doc-analyzer__dropzone--active {
  border-color: var(--color-primary);
  background: #e5f3fa;
}
.doc-analyzer__dropzone--has-files {
  padding: 20px;
}
.doc-analyzer__file-input {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  cursor: pointer;
}
.doc-analyzer__dropzone-content {
  pointer-events: none;
}
.doc-analyzer__dropzone-icon {
  font-size: 36px;
  color: var(--color-primary);
  margin-bottom: 8px;
}
.doc-analyzer__dropzone-text {
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 4px;
}
.doc-analyzer__file-list {
  list-style: none;
  padding: 0;
  margin: 16px 0 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.doc-analyzer__file-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: var(--color-bg-soft);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 13px;
}
.doc-analyzer__file-icon {
  color: var(--color-primary);
  flex-shrink: 0;
}
.doc-analyzer__file-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.doc-analyzer__file-size {
  color: var(--color-text-soft);
  font-size: 12px;
}
.doc-analyzer__file-remove {
  padding: 4px 8px;
  min-width: auto;
}
.doc-analyzer__actions {
  margin-top: 20px;
}
.doc-analyzer__spinner {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.doc-analyzer__results-wrap {
  min-width: 0;
}
.doc-analyzer__results {
  padding: 20px 24px;
  min-height: 320px;
}
.doc-analyzer__results-empty,
.doc-analyzer__results-loading {
  text-align: center;
  padding: 48px 24px;
  color: var(--color-text-soft);
}
.doc-analyzer__empty-icon,
.doc-analyzer__loading-icon {
  font-size: 48px;
  color: var(--color-border-strong);
  margin-bottom: 16px;
  display: block;
}
.doc-analyzer__results-body {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.doc-analyzer__error {
  padding: 12px 16px;
  background: #f6e0de;
  border: 1px solid var(--color-danger);
  border-radius: var(--radius-md);
  color: var(--color-danger);
  display: flex;
  align-items: center;
  gap: 8px;
}
.doc-analyzer__block-title {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.doc-analyzer__block-icon {
  font-size: 16px;
}
.doc-analyzer__block-icon--success {
  color: var(--color-success);
}
.doc-analyzer__block-icon--warning {
  color: #b45309;
}
.doc-analyzer__check-list,
.doc-analyzer__suggestion-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.doc-analyzer__check-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 0;
  font-size: 13px;
}
.doc-analyzer__check-item i.fa-check {
  color: var(--color-success);
  flex-shrink: 0;
  margin-top: 2px;
}
.doc-analyzer__check-item i.fa-xmark {
  color: var(--color-danger);
  flex-shrink: 0;
  margin-top: 2px;
}
.doc-analyzer__suggestion-item {
  padding: 8px 0;
  padding-left: 20px;
  position: relative;
  font-size: 13px;
  border-bottom: 1px solid var(--color-border);
}
.doc-analyzer__suggestion-item:last-child {
  border-bottom: none;
}
.doc-analyzer__suggestion-item::before {
  content: '•';
  position: absolute;
  left: 0;
  color: var(--color-primary);
  font-weight: bold;
}
.doc-analyzer__observacoes {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  color: var(--color-text);
}
.gov-text-sm {
  font-size: 12px;
}
</style>
