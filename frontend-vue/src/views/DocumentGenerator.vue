<template>
  <div class="doc-gen" :class="{ 'doc-gen--rapida': isDispensaNewUi || isEtpLivreRoute }">
    <header class="doc-gen__page-header">
      <template v-if="isEtpLivreRoute">
        <h1 class="doc-gen__page-title">ETP Livre</h1>
        <p class="doc-gen__page-subtitle">
          Estudo Técnico Preliminar com IA contextual: documento base opcional da biblioteca e prompt livre para o objeto da contratação.
        </p>
      </template>
      <template v-else>
        <h1 class="doc-gen__page-title">Gerador de Documentos</h1>
        <p class="doc-gen__page-subtitle">
          Crie documentos profissionais com conformidade governamental
        </p>
      </template>
    </header>

    <div class="doc-gen__grid" :class="{ 'doc-gen__grid--single': !showSlotsCard }">
      <!-- Coluna esquerda: wizard -->
      <div class="doc-gen__main">
        <section class="gov-surface doc-gen__wizard" :class="{ 'doc-gen__wizard--etp': isEtpLivreRoute }">
          <div v-if="!isEtpLivreRoute" class="gov-surface__header">
            <div>
              <h2 class="gov-surface__title">Assistente de Criação</h2>
              <p class="gov-surface__subtitle">Guia executivo para documentação profissional</p>
            </div>
          </div>

          <form class="doc-gen__form" @submit.prevent="onSubmit">
            <div class="doc-gen__fields">
              <!-- Escolha do documento base: template ou arquivo -->
              <div v-if="!isInexigibilidadePreviewRoute" class="gov-field doc-gen__field-template">
                <label class="gov-label">Documento Base</label>
                <div class="doc-gen__llm-hint">
                  <p class="gov-text-soft">
                    <i class="fa-solid fa-wand-magic-sparkles" aria-hidden="true"></i>
                    <span v-if="docTypeMode === 'tr_modelo'">
                      Esta página gera <strong>TR, DFD e Solicitação / Ofício com modelo oficial (slots)</strong>. O modo é inferido automaticamente pela rota selecionada.
                    </span>
                    <span v-else>
                      Esta página gera <strong>ETP Livre (IA flexível)</strong>. O modo é inferido automaticamente pela rota selecionada.
                    </span>
                  </p>
                </div>

                <!-- Template da biblioteca (opcional, usado como cabeçalho/rodapé DOCX) -->
                <div class="doc-gen__search-wrap">
                  <input
                    id="template-search"
                    v-model="searchQuery"
                    type="text"
                    autocomplete="off"
                    placeholder="Selecionar base..."
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
                    <router-link to="/biblioteca" class="gov-link">Abrir biblioteca</router-link>
                  </p>
                </div>

              </div>

              <!-- Prompt IA -->
              <div v-if="!isInexigibilidadePreviewRoute" class="gov-field">
                <label class="gov-label" for="ia-prompt">
                  Prompt de Inteligência Artificial
                  <span class="gov-label__hint">(IA contextual inteligente)</span>
                </label>
                <textarea
                  id="ia-prompt"
                  v-model="iaPrompt"
                  name="ia_prompt"
                  class="gov-textarea"
                  rows="6"
                  placeholder="Ex: Gerar ETP para coleta seletiva de resíduos em 3 bairros"
                  required
                />
                <p class="gov-text-soft gov-mt-sm">
                  <i class="fa-solid fa-lightbulb" aria-hidden="true"></i> <strong>Dica:</strong> A IA contextual analisa seu prompt e aplica mudanças no documento.
                </p>
              </div>

              <!-- Botões -->
              <div class="doc-gen__actions">
                <button
                  v-if="showSlotsCard"
                  type="button"
                  class="gov-btn gov-btn--outline"
                  @click="slotDrawerOpen = true"
                >
                  Dados fixos
                </button>
                <button
                  type="submit"
                  class="gov-btn gov-btn--primary"
                  :disabled="isSubmitting || (!isInexigibilidadePreviewRoute && (!hasDocumentBase || !iaPrompt.trim()))"
                >
                  <span v-if="!isSubmitting"><i class="fa-solid fa-robot" aria-hidden="true"></i> {{ isInexigibilidadePreviewRoute ? 'Gerar Documento com IA' : 'Gerar com IA Contextual' }}</span>
                  <span v-else class="doc-gen__spinner" aria-live="polite">
                    <i class="fa-solid fa-spinner fa-spin" aria-hidden="true"></i>
                    Processando com IA…
                  </span>
                </button>
                <template v-if="documentReady">
                  <template v-if="docTypeMode === 'tr_modelo'">
                    <a
                      v-if="documentTrUrl"
                      :href="documentTrUrl"
                      :download="documentTrFilename"
                      class="gov-btn gov-btn--secondary"
                    >
                      <i class="fa-solid fa-file-word" aria-hidden="true"></i> Download TR (DOCX)
                    </a>
                    <a
                      v-if="documentDfdUrl"
                      :href="documentDfdUrl"
                      :download="documentDfdFilename"
                      class="gov-btn gov-btn--secondary"
                    >
                      <i class="fa-solid fa-file-word" aria-hidden="true"></i> Download DFD (DOCX)
                    </a>
                    <a
                      v-if="documentOficioUrl"
                      :href="documentOficioUrl"
                      :download="documentOficioFilename"
                      class="gov-btn gov-btn--secondary"
                    >
                      <i class="fa-solid fa-file-word" aria-hidden="true"></i> Download Solicitação/Ofício (DOCX)
                    </a>
                    <a
                      v-if="documentZipUrl"
                      :href="documentZipUrl"
                      :download="documentZipFilename"
                      class="gov-btn gov-btn--secondary"
                    >
                      <i class="fa-solid fa-file-archive" aria-hidden="true"></i> Download TR+DFD+Ofício (ZIP)
                    </a>
                  </template>
                  <template v-else>
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
                </template>
              </div>

              <div v-if="isSubmitting" class="doc-gen__loader-wrap" role="status" aria-live="polite">
                <svg class="doc-gen__pl" width="240" height="240" viewBox="0 0 240 240" aria-hidden="true">
                  <circle
                    class="doc-gen__pl-ring doc-gen__pl-ring--a"
                    cx="120"
                    cy="120"
                    r="105"
                    fill="none"
                    stroke-width="20"
                    stroke-dasharray="0 660"
                    stroke-dashoffset="-330"
                    stroke-linecap="round"
                  ></circle>
                  <circle
                    class="doc-gen__pl-ring doc-gen__pl-ring--b"
                    cx="120"
                    cy="120"
                    r="35"
                    fill="none"
                    stroke-width="20"
                    stroke-dasharray="0 220"
                    stroke-dashoffset="-110"
                    stroke-linecap="round"
                  ></circle>
                  <circle
                    class="doc-gen__pl-ring doc-gen__pl-ring--c"
                    cx="85"
                    cy="120"
                    r="70"
                    fill="none"
                    stroke-width="20"
                    stroke-dasharray="0 440"
                    stroke-linecap="round"
                  ></circle>
                  <circle
                    class="doc-gen__pl-ring doc-gen__pl-ring--d"
                    cx="155"
                    cy="120"
                    r="70"
                    fill="none"
                    stroke-width="20"
                    stroke-dasharray="0 440"
                    stroke-linecap="round"
                  ></circle>
                </svg>
                <p class="doc-gen__loader-text">Gerando documento com IA...</p>
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

      <!-- Coluna direita: dados para slots (TR / DFD / Solicitação Ofício — modelo oficial) -->
      <aside v-if="showSlotsCard" class="doc-gen__aside">
        <section class="gov-surface doc-gen__variables-card">
          <div class="gov-surface__header">
            <div>
              <h2 class="gov-surface__title">Dados do assistente (slots)</h2>
              <p class="gov-surface__subtitle">{{ slotCardFlowTitle }}</p>
            </div>
          </div>
          <div class="doc-gen__variables-body">
            <section class="doc-gen__live-summary">
              <div class="doc-gen__live-summary-head">
                <div>
                  <div class="doc-gen__live-summary-kicker">Resumo em tempo real</div>
                  <h3 class="doc-gen__live-summary-title">Painel do documento</h3>
                </div>
                <div class="doc-gen__live-summary-pill">{{ liveSummary.percent }}%</div>
              </div>
              <div class="doc-gen__live-summary-bar">
                <span class="doc-gen__live-summary-bar-fill" :style="{ width: `${liveSummary.percent}%` }"></span>
              </div>
              <p class="gov-text-soft gov-mt-sm">
                {{ liveSummary.filledFields }} de {{ liveSummary.totalFields }} campos preenchidos
              </p>
            </section>
            <p v-if="!isInexigibilidadePreviewRoute" class="gov-text-soft doc-gen__variables-desc">
              Preencha os campos com os valores que devem constar no documento (texto livre, lista sugerida ou registro na hora).
              Eles são enviados à IA e aos placeholders do modelo oficial quando aplicável.
            </p>
            <p class="gov-text-soft">
              Acesse os campos completos no botão <strong>Dados fixos</strong>.
            </p>
          </div>
        </section>
      </aside>
    </div>

    <div v-if="showSlotsCard && slotDrawerOpen" class="doc-gen__drawer-backdrop" @click="slotDrawerOpen = false"></div>
    <aside v-if="showSlotsCard" :class="['doc-gen__drawer', { 'doc-gen__drawer--open': slotDrawerOpen }]">
      <div class="doc-gen__drawer-head">
        <div>
          <div class="doc-gen__drawer-kicker">Configuração oculta</div>
          <h3 class="doc-gen__drawer-title">Dados fixos</h3>
        </div>
        <button type="button" class="doc-gen__drawer-close" @click="slotDrawerOpen = false">×</button>
      </div>
      <div class="doc-gen__drawer-body">
        <div
          v-for="section in selectedFlow.sections"
          :key="`drawer-${section.key}`"
          class="doc-gen__var-section"
        >
          <h3 class="doc-gen__var-heading">{{ section.title }}</h3>
          <div class="doc-gen__slot-grid">
            <template v-for="field in section.fields" :key="`drawer-${field.id}`">
              <h4 v-if="field.input === 'heading' && shouldRenderField(field)" class="doc-gen__slot-subheading">
                {{ field.label }}
              </h4>
              <div
                v-else-if="shouldRenderField(field)"
                class="gov-field doc-gen__slot-field"
                :class="{ 'doc-gen__slot-field--full': field.fullWidth }"
              >
                <label class="gov-label" :for="'drawer-slot-' + field.id">
                  {{ field.label }}
                  <span v-if="field.required" class="doc-gen__required" aria-hidden="true">*</span>
                </label>
                <textarea
                  v-if="field.input === 'textarea'"
                  :id="'drawer-slot-' + field.id"
                  v-model="slotForm[field.id]"
                  class="gov-textarea doc-gen__slot-input"
                  rows="3"
                />
                <select
                  v-else-if="field.input === 'select'"
                  :id="'drawer-slot-' + field.id"
                  v-model="slotForm[field.id]"
                  class="gov-input doc-gen__slot-input"
                >
                  <option value="">Selecione</option>
                  <option v-for="opt in field.options || []" :key="'drawer-select-' + field.id + '-' + opt" :value="opt">
                    {{ opt }}
                  </option>
                </select>
                <input
                  v-else-if="field.input === 'date'"
                  :id="'drawer-slot-' + field.id"
                  v-model="slotForm[field.id]"
                  type="date"
                  class="gov-input doc-gen__slot-input"
                  :disabled="isSlotFieldDisabled(field)"
                />
                <div v-else-if="field.input === 'email' || field.input === 'text'" class="doc-gen__combo-wrap">
                  <input
                    v-if="isCnpjSlotField(field)"
                    :id="'drawer-slot-' + field.id"
                    :value="slotForm[field.id]"
                    type="text"
                    class="gov-input doc-gen__slot-input"
                    autocomplete="off"
                    inputmode="numeric"
                    maxlength="18"
                    placeholder="00.000.000/0001-00"
                    @keydown="onCnpjInputKeydown"
                    @focus="openFieldSuggestions(field.id)"
                    @input="onCnpjDrawerInput(field, $event)"
                  />
                  <input
                    v-else
                    :id="'drawer-slot-' + field.id"
                    v-model="slotForm[field.id]"
                    :type="field.input === 'email' ? 'email' : 'text'"
                    class="gov-input doc-gen__slot-input"
                    :autocomplete="field.input === 'email' ? 'email' : 'off'"
                    :placeholder="field.placeholder || 'Selecione, digite ou adicione novo valor'"
                    @focus="openFieldSuggestions(field.id)"
                    @input="openFieldSuggestions(field.id)"
                  />
                  <button
                    type="button"
                    class="gov-btn gov-btn--outline gov-btn--sm doc-gen__combo-add"
                    @click="addFieldOption(field.id)"
                  >
                    + Adicionar
                  </button>
                  <button
                    type="button"
                    class="gov-btn gov-btn--outline gov-btn--sm doc-gen__combo-add"
                    :disabled="!canRemoveFieldOption(field.id)"
                    @click="removeFieldOption(field.id, slotForm[field.id])"
                  >
                    Excluir
                  </button>
                  <div
                    v-if="isFieldSuggestionsOpen(field.id)"
                    class="doc-gen__slot-suggestions"
                  >
                    <button
                      v-for="opt in getFieldSuggestions(field.id)"
                      :key="'drawer-' + field.id + '-opt-' + opt"
                      type="button"
                      class="doc-gen__slot-suggestion-item"
                      @click="selectFieldSuggestion(field.id, opt)"
                    >
                      <span class="doc-gen__slot-suggestion-label">{{ opt }}</span>
                      <span
                        class="doc-gen__slot-suggestion-remove"
                        title="Excluir valor"
                        @click.stop="removeFieldOption(field.id, opt)"
                      >×</span>
                    </button>
                  </div>
                </div>
                <div v-else-if="field.input === 'datalist'" class="doc-gen__combo-wrap">
                  <input
                    v-if="isCnpjSlotField(field)"
                    :id="'drawer-slot-' + field.id"
                    :value="slotForm[field.id]"
                    type="text"
                    class="gov-input doc-gen__slot-input"
                    autocomplete="off"
                    inputmode="numeric"
                    maxlength="18"
                    placeholder="00.000.000/0001-00"
                    @keydown="onCnpjInputKeydown"
                    @focus="openFieldSuggestions(field.id)"
                    @input="onCnpjDrawerInput(field, $event)"
                  />
                  <input
                    v-else
                    :id="'drawer-slot-' + field.id"
                    v-model="slotForm[field.id]"
                    class="gov-input doc-gen__slot-input"
                    :placeholder="field.placeholder || 'Escolha ou digite o cargo'"
                    @focus="openFieldSuggestions(field.id)"
                    @input="openFieldSuggestions(field.id)"
                  />
                  <button
                    type="button"
                    class="gov-btn gov-btn--outline gov-btn--sm doc-gen__combo-add"
                    @click="addFieldOption(field.id)"
                  >
                    + Adicionar
                  </button>
                  <button
                    type="button"
                    class="gov-btn gov-btn--outline gov-btn--sm doc-gen__combo-add"
                    :disabled="!canRemoveFieldOption(field.id)"
                    @click="removeFieldOption(field.id, slotForm[field.id])"
                  >
                    Excluir
                  </button>
                  <div
                    v-if="isFieldSuggestionsOpen(field.id)"
                    class="doc-gen__slot-suggestions"
                  >
                    <button
                      v-for="opt in getFieldSuggestions(field.id)"
                      :key="'drawer-' + field.id + '-opt-' + opt"
                      type="button"
                      class="doc-gen__slot-suggestion-item"
                      @click="selectFieldSuggestion(field.id, opt)"
                    >
                      <span class="doc-gen__slot-suggestion-label">{{ opt }}</span>
                      <span
                        class="doc-gen__slot-suggestion-remove"
                        title="Excluir valor"
                        @click.stop="removeFieldOption(field.id, opt)"
                      >×</span>
                    </button>
                  </div>
                </div>
                <label
                  v-else-if="field.input === 'checkbox'"
                  class="doc-gen__slot-checkbox-label"
                  :for="'drawer-slot-' + field.id"
                >
                  <input
                    :id="'drawer-slot-' + field.id"
                    v-model="slotForm[field.id]"
                    type="checkbox"
                    class="doc-gen__slot-checkbox"
                  />
                  <span>{{ field.checkboxHint || field.label }}</span>
                </label>
                <input
                  v-else
                  :id="'drawer-slot-' + field.id"
                  v-model="slotForm[field.id]"
                  type="text"
                  class="gov-input doc-gen__slot-input"
                />
              </div>
            </template>
          </div>
        </div>
      </div>
      <div class="doc-gen__drawer-foot">
        <button type="button" class="gov-btn gov-btn--primary" @click="slotDrawerOpen = false">
          Aplicar dados fixos
        </button>
      </div>
    </aside>

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
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import { buildGerarTrEDfdUrl, getApiBase } from '@/utils/apiBase.js';
import { describeGerarTrEDfdNetworkFailure, fetchGerarTrEDfdWithRetry } from '@/utils/fetchGerarTrEDfd.js';
import { formatCnpjBr, onCnpjInputKeydown } from '@/utils/cnpjFormat.js';

// Em dev: '' → proxy Vite `/api`
const API_BASE = getApiBase();
const route = useRoute();

/** Rotas `/geracao/dispensa-rapida/...` reutilizam pacotes e regras das rotas `DispensaArt75*`. */
const DISPENSA_RAPIDA_TO_LOGICAL = {
  DispensaRapidaArt75IObrasEngenharia: 'DispensaArt75IObrasEngenharia',
  DispensaRapidaArt75IManutencaoVeiculos: 'DispensaArt75IManutencaoVeiculos',
  DispensaRapidaArt75IICompras: 'DispensaArt75IICompras',
  DispensaRapidaArt75IIServicos: 'DispensaArt75IIServicos',
  DispensaRapidaArt75IIComprasServicosInclusos: 'DispensaArt75IIComprasServicosInclusos',
};

const dispensaLogicalRouteName = computed(
  () => DISPENSA_RAPIDA_TO_LOGICAL[route.name] || route.name,
);

const isDispensaNewUi = computed(() => {
  const name = String(route.name || '');
  const path = String(route.path || '');
  return (
    name.startsWith('DispensaArt75')
    || name.startsWith('DispensaRapida')
    || path.startsWith('/geracao/dispensa-art-75')
    || path.startsWith('/geracao/dispensa-rapida')
  );
});

const isInexigibilidadePreviewRoute = computed(
  () => route.name === 'InexigibilidadeArt74IManutencaoVeiculosPreview' || route.name === 'InexigibilidadeArt74IFornecedorExclusivoPreview',
);

const useOwnFile = ref(false);
const selectedDocxFile = ref(null);
const docxFileInput = ref(null);

const searchQuery = ref('');
const showTemplateDropdown = ref(false);
const templateList = ref([]);
const selectedTemplate = ref(null);
const focusedIndex = ref(-1);
const searchDebounce = ref(null);

const userPrefeituraId = ref(null);
const userIsSuperuser = ref(false);

async function fetchCurrentUser() {
  try {
    const res = await fetch(`${API_BASE}/api/me/`, { credentials: 'include' });
    if (!res.ok) return;
    const data = await res.json();
    userPrefeituraId.value = data.prefeitura_id || null;
    userIsSuperuser.value = !!data.is_superuser;
  } catch (e) {
    console.warn('fetchCurrentUser', e);
  }
}

function filterTemplatesByPrefeitura(list) {
  if (userIsSuperuser.value) return list;
  return list.filter((t) => !t.prefeitura || t.prefeitura.id === userPrefeituraId.value);
}

function canUseTemplateByPrefeitura(template) {
  if (!template) return false;
  if (userIsSuperuser.value) return true;
  if (!template.prefeitura) return true; // template global
  return String(template.prefeitura.id) === String(userPrefeituraId.value || '');
}

const iaPrompt = ref('');
const docTypeMode = ref('auto'); // 'auto' (generate-document), 'tr_modelo' (TR modelo fixo)
const sourceMode = ref('llm'); // modo único: criar do zero com IA
const isSubmitting = ref(false);
const documentReady = ref(false);
const documentDocxUrl = ref('');
const documentPdfUrl = ref('');
const documentTrUrl = ref('');
const documentDfdUrl = ref('');
const documentOficioUrl = ref('');
const documentZipUrl = ref('');
const documentTrFilename = ref('termo_referencia.docx');
const documentDfdFilename = ref('dfd.docx');
const documentOficioFilename = ref('oficio.docx');
const documentZipFilename = ref('tr_dfd_oficio.zip');
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
const suggestionOpenField = ref('');
const slotDrawerOpen = ref(false);
const slotStateSaveDebounce = ref(null);
const templatePresetSaveDebounce = ref(null);
const isHydratingSlotState = ref(false);
const GLOBAL_SLOT_FORM_PRESET_KEY = 'global_slots_preset_v1';
/** Chaves reservadas no preset global (backend) para cabeçalho/rodapé da Biblioteca. */
const LIBRARY_TEMPLATE_ID_KEY = '__library_template_id__';
const LIBRARY_TEMPLATE_NAME_KEY = '__library_template_name__';

/** Sugestões para Função/Cargo (o usuário pode digitar outro valor). */
const CARGO_DATALIST_OPTIONS = [
  'Prefeito(a)',
  'Secretário(a) Municipal',
  'Diretor(a) de Departamento',
  'Coordenador(a)',
  'Chefe de Setor',
  'Procurador(a) do Município',
  'Fiscal de Contratos',
  'Gestor(a) de Contratos',
  'Outro (registrar no campo)',
];

const FLOW_CONFIG = {
  DispensaArt75IManutencaoVeiculos: {
    title: 'Assistente de Criação - Dispensa de Licitação - Art. 75, Inciso I - Manutenção de Veículos (Lei nº 14.133/2021)',
    sections: [
      {
        key: 'solicitacao',
        title: '1. Solicitação / Ofício',
        fields: [
          {
            id: 'solicitacao_destinatario_tratamento_nome',
            label: 'Tratamento',
            input: 'select',
            options: ['Ao senhor', 'A senhora'],
          },
          { id: 'solicitacao_destinatario_nome', label: '1.1 A quem é direcionada a solicitação — Nome', input: 'text' },
          {
            id: 'solicitacao_destinatario_tratamento_cargo',
            label: 'Tratamento',
            input: 'select',
            options: ['Senhor', 'Senhora'],
          },
          {
            id: 'solicitacao_destinatario_cargo',
            label: '1.2 A quem é direcionada a solicitação — Função / Cargo',
            input: 'datalist',
          },
          { id: '_h_solicitacao_responsavel', label: '1.3 Responsável pela solicitação', input: 'heading', fullWidth: true },
          { id: 'solicitacao_responsavel_nome', label: 'Nome do responsável', input: 'text' },
          {
            id: 'solicitacao_responsavel_cargo',
            label: 'Função / Cargo',
            input: 'datalist',
          },
        ],
      },
      {
        key: 'dfd',
        title: '2. DFD – Documento de Formalização da Demanda',
        fields: [
          {
            id: 'dfd_setor_requisitante',
            label: 'Setor requisitante (Unidade / Setor / Departamento)',
            input: 'text',
            required: true,
          },
          { id: 'dfd_responsavel_demanda', label: 'Responsável pela demanda', input: 'text', required: true },
          { id: 'dfd_email', label: 'E-mail', input: 'email', required: true },
          { id: 'dfd_gestor_contratos', label: 'Nome do(a) gestor(a) de contratos', input: 'text', required: true },
          { id: 'dfd_fiscal_contratos', label: 'Nome do(a) fiscal de contratos', input: 'text', required: true },
          { id: '_h_dfd_assinatura', label: '2.6 Responsável pela assinatura do DFD', input: 'heading', fullWidth: true },
          {
            id: 'dfd_assinatura_nome',
            label: 'Nome do responsável',
            input: 'text',
            required: true,
          },
          {
            id: 'dfd_assinatura_cargo',
            label: 'Função / Cargo',
            input: 'text',
            required: true,
          },
        ],
      },
    ],
  },
  DispensaArt75IObrasEngenharia: {
    title: 'Assistente de Criação - Dispensa de Licitação - Art. 75, Inciso I - Obras e Serviços de Engenharia',
    sections: [
      {
        key: 'base',
        title: 'Campos principais',
        fields: [
          { id: 'objeto_obra', label: 'Objeto da contratação', input: 'text' },
          { id: 'escopo_tecnico', label: 'Escopo técnico da obra/serviço', input: 'textarea', fullWidth: true },
          { id: 'responsavel_tecnico', label: 'Responsável técnico', input: 'text' },
        ],
      },
    ],
  },
  InexigibilidadeArt74IFornecedorExclusivoPreview: {
    title: 'Fornecedor Exclusivo Geral — Bens, Serviços e Soluções (Art. 74, I)',
    sections: [
      {
        key: 'dados_fixos',
        title: 'Dados fixos',
        fields: [
          { id: '_h_dados_basicos', label: 'Dados básicos', input: 'heading', fullWidth: true },
          { id: 'numero_processo', label: 'Informar número do processo (opcional)', input: 'text' },
          { id: 'orgao_unidade', label: 'Órgão/Unidade responsável pelo equipamento', input: 'text' },
          { id: '_h_objeto_especifico', label: 'Objeto específico', input: 'heading', fullWidth: true },
          { id: 'objeto_especifico', label: 'Selecione o objeto específico da contratação', input: 'text' },
          { id: '_h_dados_equipamento', label: 'Dados do equipamento', input: 'heading', fullWidth: true },
          { id: 'equipamento', label: 'Equipamento', input: 'text' },
          { id: 'marca', label: 'Marca', input: 'text' },
          { id: 'modelo', label: 'Modelo', input: 'text' },
        ],
      },
      {
        key: 'fornecedor',
        title: 'Fornecedor exclusivo',
        fields: [
          { id: 'fornecedor_nome', label: 'Razão social / Nome do fornecedor', input: 'text' },
          { id: 'fornecedor_cnpj', label: 'CNPJ', input: 'text' },
          { id: 'dotacao_orcamentaria', label: 'Informar dotação orçamentária (opcional)', input: 'textarea', fullWidth: true },
        ],
      },
      {
        key: 'itens',
        title: 'Itens e valores',
        fields: [
          { id: 'item_descricao', label: 'Descrição', input: 'text' },
          { id: 'item_quantidade', label: 'Quantidade', input: 'text' },
          { id: 'item_unidade', label: 'Unidade medida', input: 'text' },
          { id: 'item_valor_unitario', label: 'Valor unitário', input: 'text' },
          { id: 'item_valor_total', label: 'Valor total', input: 'text' },
          { id: 'valor_total_processo', label: 'Valor total do processo', input: 'text', fullWidth: true },
        ],
      },
      {
        key: 'fiscalizacao',
        title: 'Fiscalização',
        fields: [
          { id: 'fiscal_nome', label: 'Nome do fiscal de contratos', input: 'text' },
          { id: 'responsavel_tr_nome', label: 'Nome do responsável', input: 'text' },
          { id: 'responsavel_tr_cargo', label: 'Cargo/Função', input: 'text' },
          { id: 'modo_data', label: 'Modo da data', input: 'text' },
        ],
      },
    ],
  },
};

const TR_DFD_SLOTS_FLOW = FLOW_CONFIG.DispensaArt75IManutencaoVeiculos;

const DEFAULT_FLOW = {
  title: 'Assistente de Criação - Fluxo Geral de Geração de Documentos',
  sections: [
    {
      key: 'base',
      title: 'Campos principais',
      fields: [
        { id: 'objeto', label: 'Objeto da contratação', input: 'text' },
        { id: 'justificativa', label: 'Justificativa da necessidade', input: 'textarea', fullWidth: true },
        { id: 'setor_responsavel', label: 'Setor responsável', input: 'text' },
      ],
    },
  ],
};

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

/** Rota `/geracao/etp-livre` — mesma UI nova que dispensa rápida (`doc-gen--rapida`) + tema escuro. */
const isEtpLivreRoute = computed(() => route.name === 'EtpLivre');
const documentTypeHint = computed(() => (isEtpLivreRoute.value ? 'etp' : null));
const showSlotsCard = computed(() => !isEtpLivreRoute.value);

const selectedFlow = computed(() => TR_DFD_SLOTS_FLOW);

const liveSummary = computed(() => {
  const sections = selectedFlow.value.sections || [];
  const normalized = sections.map((section) => {
    const fields = (section.fields || []).filter((f) => f.input !== 'heading');
    const total = fields.length;
    const filled = fields.reduce((acc, field) => {
      const value = slotForm[field.id];
      if (field.input === 'checkbox') return acc + (value ? 1 : 0);
      const text = typeof value === 'string' ? value.trim() : value != null ? String(value).trim() : '';
      return acc + (text ? 1 : 0);
    }, 0);
    return { title: section.title, filled, total };
  });
  const totalFields = normalized.reduce((acc, sec) => acc + sec.total, 0);
  const filledFields = normalized.reduce((acc, sec) => acc + sec.filled, 0);
  const percent = totalFields ? Math.round((filledFields / totalFields) * 100) : 0;
  return { sections: normalized, totalFields, filledFields, percent };
});

const slotCardFlowTitle = computed(() => {
  const logical = dispensaLogicalRouteName.value;
  const routeFlowTitle = FLOW_CONFIG[logical]?.title;
  if (routeFlowTitle) return routeFlowTitle;

  const routeMetaTitle = typeof route.meta?.title === 'string' ? route.meta.title : '';
  if (routeMetaTitle) return `Assistente de Criação - ${routeMetaTitle}`;

  return DEFAULT_FLOW.title;
});

const SLOT_PACKAGE_BY_ROUTE = {
  DispensaArt75IManutencaoVeiculos: 'dispensa_75_i_manutencao_veiculos',
  DispensaArt75IObrasEngenharia: 'dispensa_75_i_obras_engenharia',
  DispensaArt75IICompras: 'dispensa_75_ii_compras',
  DispensaArt75IIServicos: 'dispensa_75_ii_servicos',
  DispensaArt75IIComprasServicosInclusos: 'dispensa_75_ii_compras_servicos_inclusos',
  InexigibilidadeArt74IFornecedorExclusivoPreview: 'inexigibilidade_74_i_fornecedor_exclusivo',
  InexigibilidadeArt74IManutencaoVeiculosPreview: 'inexigibilidade_74_i_manutencao_veiculos',
};

const SOL_OFICIO_FUNDAMENTO_LEGAL_BY_ROUTE = {
  DispensaArt75I: 'Art. 75, Inciso I, da Lei nº 14.133/2021',
  DispensaArt75IManutencaoVeiculos: 'Art. 75, Inciso I, da Lei nº 14.133/2021',
  DispensaArt75IObrasEngenharia: 'Art. 75, Inciso I, da Lei nº 14.133/2021',
  DispensaArt75II: 'Art. 75, Inciso II, da Lei nº 14.133/2021',
  DispensaArt75IICompras: 'Art. 75, Inciso II, da Lei nº 14.133/2021',
  DispensaArt75IIServicos: 'Art. 75, Inciso II, da Lei nº 14.133/2021',
  DispensaArt75IIComprasServicosInclusos: 'Art. 75, Inciso II, da Lei nº 14.133/2021',
  InexigibilidadeArt74I: 'Art. 74, Inciso I, da Lei nº 14.133/2021',
  InexigibilidadeArt74IManutencaoVeiculos: 'Art. 74, Inciso I, da Lei nº 14.133/2021',
  InexigibilidadeArt74IManutencaoVeiculosPreview: 'Art. 74, Inciso I, da Lei nº 14.133/2021',
  InexigibilidadeArt74IFornecedorExclusivo: 'Art. 74, Inciso I, da Lei nº 14.133/2021',
  InexigibilidadeArt74IFornecedorExclusivoPreview: 'Art. 74, Inciso I, da Lei nº 14.133/2021',
};

function resolveSolOficioFundamentoLegal(routeName) {
  const name = String(routeName || '').trim();
  if (!name) return '';
  if (SOL_OFICIO_FUNDAMENTO_LEGAL_BY_ROUTE[name]) return SOL_OFICIO_FUNDAMENTO_LEGAL_BY_ROUTE[name];
  if (name.startsWith('InexigibilidadeArt74I')) return 'Art. 74, Inciso I, da Lei nº 14.133/2021';
  if (name.startsWith('DispensaArt75I')) return 'Art. 75, Inciso I, da Lei nº 14.133/2021';
  if (name.startsWith('DispensaArt75II')) return 'Art. 75, Inciso II, da Lei nº 14.133/2021';
  return '';
}

const slotPackageKey = computed(() => {
  if (isEtpLivreRoute.value) return 'etp_livre';
  return SLOT_PACKAGE_BY_ROUTE[dispensaLogicalRouteName.value] || 'tr_dfd_generico';
});

/** Valores do formulário lateral (TR/DFD com slots). */
const slotForm = reactive({});
/** Opções por campo (selecionáveis via datalist), com suporte a adicionar novos valores. */
const slotFieldOptions = reactive({});

const SLOT_FIELD_PRESETS = {};

function addFieldOption(fieldId) {
  const raw = slotForm[fieldId];
  const value = typeof raw === 'string' ? raw.trim() : '';
  if (!value) return;
  if (!Array.isArray(slotFieldOptions[fieldId])) slotFieldOptions[fieldId] = [];
  if (!slotFieldOptions[fieldId].includes(value)) {
    slotFieldOptions[fieldId] = [...slotFieldOptions[fieldId], value];
  }
  persistSlotEntries([{ field_key: fieldId, value }]);
}

function getFieldSuggestions(fieldId) {
  const all = slotFieldOptions[fieldId] || [];
  const q = String(slotForm[fieldId] || '').trim().toLowerCase();
  if (!q) return all;
  return all.filter((x) => String(x).toLowerCase().includes(q));
}

function canRemoveFieldOption(fieldId) {
  const current = String(slotForm[fieldId] || '').trim();
  if (!current) return false;
  const list = Array.isArray(slotFieldOptions[fieldId]) ? slotFieldOptions[fieldId] : [];
  return list.includes(current);
}

function isCnpjSlotField(field) {
  const id = String(field?.id || '').toLowerCase();
  return id === 'fornecedor_cnpj' || id === 'cnpj_fornecedor' || id === 'cnpj' || id.endsWith('_cnpj');
}

function onCnpjDrawerInput(field, event) {
  const el = event?.target;
  if (!el) return;
  slotForm[field.id] = formatCnpjBr(el.value);
  openFieldSuggestions(field.id);
}

function openFieldSuggestions(fieldId) {
  suggestionOpenField.value = fieldId;
}

function isFieldSuggestionsOpen(fieldId) {
  return suggestionOpenField.value === fieldId;
}

function selectFieldSuggestion(fieldId, value) {
  slotForm[fieldId] = value;
  suggestionOpenField.value = '';
}

async function removeFieldOption(fieldId, value) {
  const list = Array.isArray(slotFieldOptions[fieldId]) ? slotFieldOptions[fieldId] : [];
  slotFieldOptions[fieldId] = list.filter((v) => v !== value);
  try {
    await fetch(`${API_BASE}/api/slots/catalog/delete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ field_key: fieldId, value }),
    });
  } catch (_e) {
    // silencioso
  }
}

async function persistSlotEntries(entries) {
  if (!Array.isArray(entries) || entries.length === 0) return;
  try {
    await fetch(`${API_BASE}/api/slots/catalog/upsert`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ entries }),
    });
  } catch (_e) {
    // silencioso: não deve interromper o fluxo principal de geração
  }
}

async function loadSlotCatalogSuggestions() {
  if (!showSlotsCard.value) return;
  const fieldIds = selectedFlow.value.sections
    .flatMap((section) => section.fields)
    .filter((field) => field.input === 'text' || field.input === 'email' || field.input === 'datalist')
    .map((field) => field.id);
  if (!fieldIds.length) return;

  try {
    const url = `${API_BASE}/api/slots/catalog/batch?fields=${encodeURIComponent(fieldIds.join(','))}&limit=25`;
    const res = await fetch(url, { credentials: 'include' });
    if (!res.ok) return;
    const data = await res.json().catch(() => ({}));
    const items = data?.items || {};
    for (const fieldId of fieldIds) {
      const current = Array.isArray(slotFieldOptions[fieldId]) ? slotFieldOptions[fieldId] : [];
      const incoming = Array.isArray(items[fieldId]) ? items[fieldId] : [];
      slotFieldOptions[fieldId] = [...new Set([...current, ...incoming])];
    }
  } catch (_e) {
    // silencioso: usa presets locais se API não estiver disponível
  }
}

function collectSlotFormStatePayload() {
  const data = {};
  for (const section of selectedFlow.value.sections) {
    for (const field of section.fields) {
      if (field.input === 'heading') continue;
      const raw = slotForm[field.id];
      if (field.input === 'checkbox') {
        data[field.id] = !!raw;
        continue;
      }
      data[field.id] = typeof raw === 'string' ? raw : (raw ?? '');
    }
  }
  return data;
}

/** Preset global: slots do assistente + template da biblioteca (merge no backend). */
function buildGlobalPresetPayload() {
  const data = showSlotsCard.value ? collectSlotFormStatePayload() : {};
  if (selectedTemplate.value?.id) {
    data[LIBRARY_TEMPLATE_ID_KEY] = String(selectedTemplate.value.id);
    data[LIBRARY_TEMPLATE_NAME_KEY] = String(selectedTemplate.value.name || '');
  } else {
    data[LIBRARY_TEMPLATE_ID_KEY] = '';
    data[LIBRARY_TEMPLATE_NAME_KEY] = '';
  }
  return data;
}

async function saveSlotFormState() {
  if (isHydratingSlotState.value) return;
  try {
    await fetch(`${API_BASE}/api/slots/form-state/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        slot_package_key: GLOBAL_SLOT_FORM_PRESET_KEY,
        data: buildGlobalPresetPayload(),
      }),
    });
  } catch (_e) {
    // silencioso
  }
}

async function loadSlotFormState() {
  isHydratingSlotState.value = true;
  try {
    const url = `${API_BASE}/api/slots/form-state?slot_package_key=${encodeURIComponent(GLOBAL_SLOT_FORM_PRESET_KEY)}`;
    const res = await fetch(url, { credentials: 'include' });
    if (!res.ok) return;
    const payload = await res.json().catch(() => ({}));
    const data = payload?.data || {};
    if (!data || typeof data !== 'object') return;

    const libId = data[LIBRARY_TEMPLATE_ID_KEY] || data._library_template_id;
    const libName = data[LIBRARY_TEMPLATE_NAME_KEY] || '';
    if (libId && String(libId).trim()) {
      const tid = String(libId).trim();
      selectedTemplate.value = { id: tid, name: libName, preview_image: null };
      searchQuery.value = libName || '';
      await fetchTemplateDetails(tid);
    } else {
      selectedTemplate.value = null;
      searchQuery.value = '';
    }

    if (!showSlotsCard.value) return;

    for (const section of selectedFlow.value.sections) {
      for (const field of section.fields) {
        if (field.input === 'heading') continue;
        if (!(field.id in data)) continue;
        const value = data[field.id];
        if (field.input === 'checkbox') {
          slotForm[field.id] = !!value;
        } else {
          slotForm[field.id] = value == null ? '' : String(value);
          if ((field.input === 'text' || field.input === 'email' || field.input === 'datalist') && slotForm[field.id]) {
            const current = Array.isArray(slotFieldOptions[field.id]) ? slotFieldOptions[field.id] : [];
            if (!current.includes(slotForm[field.id])) {
              slotFieldOptions[field.id] = [...current, slotForm[field.id]];
            }
          }
        }
      }
    }
  } catch (_e) {
    // silencioso
  } finally {
    isHydratingSlotState.value = false;
  }
}

function buildSlotEntriesFromForm() {
  const entries = [];
  for (const section of selectedFlow.value.sections) {
    for (const field of section.fields) {
      if (field.input === 'heading' || field.input === 'checkbox') continue;
      const value = String(slotForm[field.id] || '').trim();
      if (!value) continue;
      entries.push({ field_key: field.id, value });
    }
  }
  return entries;
}

function resetSlotFormAndSections() {
  Object.keys(slotForm).forEach((k) => {
    delete slotForm[k];
  });
  Object.keys(slotFieldOptions).forEach((k) => {
    delete slotFieldOptions[k];
  });
  for (const section of selectedFlow.value.sections) {
    for (const field of section.fields) {
      if (field.input === 'heading') continue;
      slotForm[field.id] = field.input === 'checkbox' ? false : '';
      if (field.input === 'text' || field.input === 'email' || field.input === 'datalist') {
        const isCargoField = field.input === 'datalist';
        const base = isCargoField ? CARGO_DATALIST_OPTIONS : (SLOT_FIELD_PRESETS[field.id] || []);
        slotFieldOptions[field.id] = [...base];
      }
    }
  }
}

function isSlotFieldDisabled(field) {
  if (!field || field.input !== 'date') return false;
  return field.id === 'tr_data_termo' && !!slotForm.tr_data_automatica;
}

function shouldRenderField(field) {
  if (!field) return true;
  // Campo exclusivo da rota de Obras e Serviços de Engenharia.
  if (field.id === 'tr_objeto_manual') return dispensaLogicalRouteName.value === 'DispensaArt75IObrasEngenharia';
  return true;
}

/** Mapeia campos do fluxo “Dispensa / DFD” para chaves aceitas em `slots_override` no backend. */
function buildTrSlotsOverride() {
  const f = slotForm;
  const o = {};
  {
    const rn = String(route.name || '');
    if (rn.startsWith('DispensaRapida')) o.dispensa_fluxo_ui = 'rapida';
    else if (rn.startsWith('DispensaArt75')) o.dispensa_fluxo_ui = 'normal';
  }
  const toBrDate = (iso) => {
    const v = String(iso || '').trim();
    if (!v) return '';
    const m = v.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!m) return v;
    return `${m[3]}/${m[2]}/${m[1]}`;
  };

  const fiscalNome = (f.dfd_fiscal_contratos || '').trim();
  if (fiscalNome) o.fiscal = { nome: fiscalNome };
  if (fiscalNome) o.dfd_fiscal_contratos = fiscalNome;

  const solDestNome = (f.solicitacao_destinatario_nome || '').trim();
  const solDestCargo = (f.solicitacao_destinatario_cargo || '').trim();
  const solDestTratNome = (f.solicitacao_destinatario_tratamento_nome || '').trim();
  const solDestTratCargo = (f.solicitacao_destinatario_tratamento_cargo || '').trim();
  const solRespNome = (f.solicitacao_responsavel_nome || '').trim();
  const solRespCargo = (f.solicitacao_responsavel_cargo || '').trim();
  if (solDestNome) o.sol_oficio_destinatario_nome = solDestNome;
  if (solDestCargo) o.sol_oficio_destinatario_cargo = solDestCargo;
  if (solDestTratNome) o.ao_senhor_genero = solDestTratNome;
  if (solDestTratCargo) o.senhor_senhora_genero = solDestTratCargo;
  if (solRespNome) o.sol_oficio_responsavel_nome = solRespNome;
  if (solRespCargo) o.sol_oficio_responsavel_cargo = solRespCargo;

  const itemDescricao = (f.item_descricao || '').trim();
  const itemQuantidade = (f.item_quantidade || '').trim();
  const itemUnidade = (f.item_unidade || '').trim();
  const itemValorUnitario = (f.item_valor_unitario || '').trim();
  const itemValorTotal = (f.item_valor_total || '').trim();
  const hasManualItem = [itemDescricao, itemQuantidade, itemUnidade, itemValorUnitario, itemValorTotal].some(Boolean);
  if (hasManualItem) {
    o.itens = [{
      descricao: itemDescricao,
      quantidade: itemQuantidade,
      unidade: itemUnidade,
      valor_unitario: itemValorUnitario,
      valor_total: itemValorTotal,
    }];
  }
  const trCargoAssinante = (f.tr_cargo_assinante || '').trim();
  if (trCargoAssinante) o.secretaria_usuario = trCargoAssinante;
  const setor = (f.dfd_setor_requisitante || '').trim();
  if (setor) o.dfd_setor_requisitante = setor;

  const respDemanda = (f.dfd_responsavel_demanda || '').trim();
  if (respDemanda) o.nome_usuario = respDemanda;
  if (respDemanda) o.dfd_responsavel_demanda = respDemanda;

  const dfdEmail = (f.dfd_email || '').trim();
  if (dfdEmail) o.dfd_email = dfdEmail;

  const dfdGestor = (f.dfd_gestor_contratos || '').trim();
  if (dfdGestor) o.dfd_gestor_contratos = dfdGestor;

  const dfdAssCargo = (f.dfd_assinatura_cargo || '').trim();
  if (dfdAssCargo) o.dfd_assinatura_cargo = dfdAssCargo;
  const dfdAssNome = (f.dfd_assinatura_nome || '').trim();
  if (dfdAssNome) o.dfd_assinatura_nome = dfdAssNome;

  const end = (f.tr_endereco_propostas || '').trim();
  const em = (f.tr_email_propostas || '').trim();
  if (end) o.endereco_entrega = end;
  if (em) o.email_envio_propostas = em;

  const dataManual = toBrDate(f.tr_data_termo);
  let dataTermo = '';
  if (f.tr_data_automatica) {
    const now = new Date();
    dataTermo = `${String(now.getDate()).padStart(2, '0')}/${String(now.getMonth() + 1).padStart(2, '0')}/${now.getFullYear()}`;
  } else if (dataManual) {
    dataTermo = dataManual;
  }
  if (f.tr_assinatura_digital) {
    dataTermo = 'datado e assinado digitalmente';
  }
  if (dataTermo) {
    o.data_termo = dataTermo;
  }

  const nomeAss = (f.tr_nome_assinante || '').trim();
  const cargoAss = (f.tr_cargo_assinante || '').trim();
  if (nomeAss) o.nome_assinante_termo = nomeAss;
  if (cargoAss) o.cargo_assinante_termo = cargoAss;

  const objetoManualTR = (f.tr_objeto_manual || '').trim();
  const objetoEscopo = (f.tr_objeto_escopo || '').trim();
  const objetoEntregas = (f.tr_objeto_entregas || '').trim();
  const objetoResultados = (f.tr_objeto_resultados || '').trim();
  if (dispensaLogicalRouteName.value === 'DispensaArt75IObrasEngenharia') {
    // Nesta rota o objeto é sempre manual (sem geração por IA).
    if (objetoManualTR) o.objeto = objetoManualTR;
  } else {
    const objeto = (f.objeto || f.objeto_obra || '').trim();
    if (objeto) o.objeto = objeto;
  }
  if (objetoEscopo) o.objeto_escopo = objetoEscopo;
  if (objetoEntregas) o.objeto_entregas = objetoEntregas;
  if (objetoResultados) o.objeto_resultados = objetoResultados;

  const justificativa = (f.justificativa || f.justificativa_inviabilidade || '').trim();
  if (justificativa) o.justificativa = justificativa;

  const setorResp = (f.setor_responsavel || '').trim();
  if (setorResp && !o.secretaria_usuario) o.secretaria_usuario = setorResp;
  if (setor && !o.secretaria_usuario) o.secretaria_usuario = setor;

  const fundamentoLegal = resolveSolOficioFundamentoLegal(dispensaLogicalRouteName.value);
  if (fundamentoLegal) o.sol_oficio_artigo_inciso = fundamentoLegal;

  return Object.keys(o).length ? o : null;
}

/** Texto extra anexado ao prompt para a IA considerar todos os campos preenchidos. */
function buildFormPromptAppendix() {
  const lines = [
    '### Dados informados no assistente (use de forma literal quando couber; não invente valores para itens já preenchidos abaixo):',
    '',
  ];
  let any = false;
  for (const section of selectedFlow.value.sections) {
    lines.push(`**${section.title}**`);
    for (const field of section.fields) {
      if (field.input === 'heading') {
        lines.push(`_(${field.label})_`);
        continue;
      }
      const v = slotForm[field.id];
      if (field.input === 'checkbox') {
        lines.push(`- ${field.checkboxHint || field.label}: ${v ? 'sim' : 'não'}`);
        any = true;
        continue;
      }
      const s = typeof v === 'string' ? v.trim() : v != null && v !== '' ? String(v) : '';
      if (s) {
        lines.push(`- ${field.label}: ${s}`);
        any = true;
      }
    }
    lines.push('');
  }
  if (!any) return '';
  return lines.join('\n');
}

async function fetchTemplates(q) {
  const url = `${API_BASE}/api/documentos_modelos/lista_10?q=${encodeURIComponent(q || '')}&only_user_prefeitura=1`;
  try {
    const res = await fetch(url, { credentials: 'include' });
    if (!res.ok) return;
    const data = await res.json();
    templateList.value = filterTemplatesByPrefeitura(data.templates || []);
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
  if (!canUseTemplateByPrefeitura(t)) {
    generateError.value = 'Este template pertence a outra prefeitura e não pode ser utilizado.';
    return;
  }
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
    if (!t) return;
    if (!canUseTemplateByPrefeitura(t)) {
      selectedTemplate.value = null;
      searchQuery.value = '';
      generateError.value = 'Template bloqueado: ele não pertence à sua prefeitura.';
      return;
    }
    selectedTemplate.value = {
      id: t.id,
      name: t.name,
      preview_image: t.preview_image,
      prefeitura: t.prefeitura || null,
    };
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
  if (!e.target.closest('.doc-gen__combo-wrap')) {
    suggestionOpenField.value = '';
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
  if (isInexigibilidadePreviewRoute.value && !iaPrompt.value.trim()) {
    iaPrompt.value = `Gerar documento com base nos dados preenchidos para ${slotCardFlowTitle.value}.`;
  }
  if (!iaPrompt.value.trim()) return;
  if (docTypeMode.value === 'tr_modelo' && dispensaLogicalRouteName.value === 'DispensaArt75IObrasEngenharia') {
    if (!Object.prototype.hasOwnProperty.call(slotForm, 'tr_objeto_manual')) {
      isSubmitting.value = false;
      generateError.value = 'Preencha os dados fixos no modal para gerar o documento.';
      return;
    }
    const manualObject = String(slotForm.tr_objeto_manual || '').trim();
    if (!manualObject) {
      generateError.value = 'Preencha o campo "Objeto do TR (manual, sem geração por IA)" para gerar nesta página.';
      return;
    }
  }
  if (docTypeMode.value === 'tr_modelo' && String(route.name || '').startsWith('DispensaArt75')) {
    const hasAnyItem = [
      slotForm.item_descricao,
      slotForm.item_quantidade,
      slotForm.item_unidade,
      slotForm.item_valor_unitario,
      slotForm.item_valor_total,
    ].some((v) => String(v || '').trim());
    if (!hasAnyItem) {
      generateError.value = 'Na dispensa normal, adicione os itens manualmente antes de gerar o documento.';
      return;
    }
  }
  isSubmitting.value = true;
  documentReady.value = false;
  generateError.value = '';
  // Revogar blobs antigos antes de limpar, para não deixar links inválidos e evitar vazamento
  if (documentDocxUrl.value) {
    URL.revokeObjectURL(documentDocxUrl.value);
    documentDocxUrl.value = '';
  }
  if (documentPdfUrl.value) {
    URL.revokeObjectURL(documentPdfUrl.value);
    documentPdfUrl.value = '';
  }
  if (documentTrUrl.value) {
    URL.revokeObjectURL(documentTrUrl.value);
    documentTrUrl.value = '';
  }
  if (documentDfdUrl.value) {
    URL.revokeObjectURL(documentDfdUrl.value);
    documentDfdUrl.value = '';
  }
  if (documentOficioUrl.value) {
    URL.revokeObjectURL(documentOficioUrl.value);
    documentOficioUrl.value = '';
  }
  if (documentZipUrl.value) {
    URL.revokeObjectURL(documentZipUrl.value);
    documentZipUrl.value = '';
  }
  documentTrFilename.value = 'termo_referencia.docx';
  documentDfdFilename.value = 'dfd.docx';
  documentOficioFilename.value = 'oficio.docx';
  documentZipFilename.value = 'tr_dfd_oficio.zip';

  try {
    await submitViaLLM();
  } catch (e) {
    generateError.value = e.message || 'Erro ao gerar documento';
  } finally {
    isSubmitting.value = false;
  }
}

async function submitViaLLM() {
  const isTrDfd = docTypeMode.value === 'tr_modelo';
  const basePrompt = iaPrompt.value.trim();
  // TR/DFD já envia os dados estruturados em slots_override; anexar todo o formulário
  // no user_prompt duplica contexto e aumenta muito latência/token no Ollama local.
  const appendix = '';
  const userPromptFinal = appendix ? `${basePrompt}\n\n${appendix}` : basePrompt;

  const payload = isTrDfd
    ? { user_prompt: userPromptFinal, slots_override: buildTrSlotsOverride(), slot_package_key: slotPackageKey.value }
    : {
        user_prompt: basePrompt,
        output: 'docx',
        slot_package_key: slotPackageKey.value,
        ...(documentTypeHint.value ? { document_type_hint: documentTypeHint.value } : {}),
      };
  if (selectedTemplate.value?.id) {
    if (!canUseTemplateByPrefeitura(selectedTemplate.value)) {
      generateError.value = 'Template bloqueado: ele não pertence à sua prefeitura.';
      return;
    }
    payload.template_id = selectedTemplate.value.id;
  }

  // Modo TR/DFD (modelo oficial): resposta é sempre JSON com base64 dos arquivos
  if (isTrDfd) {
    const gerarUrl = buildGerarTrEDfdUrl(API_BASE);
    const result = await fetchGerarTrEDfdWithRetry(API_BASE, payload);
    if (!result.ok) {
      if (result.kind === 'network') {
        const msg = String(result.errorMessage || '');
        generateError.value = /fetch|network|failed|load|aborted|timed out|timeout/i.test(msg)
          ? describeGerarTrEDfdNetworkFailure(gerarUrl)
          : msg || describeGerarTrEDfdNetworkFailure(gerarUrl);
      } else {
        generateError.value =
          result.status === 500
            ? result.data?.error || result.data?.detail || result.errorMessage || 'Erro 500 no servidor. Veja os logs do container backend.'
            : result.errorMessage;
      }
      return;
    }
    const data = result.data;
    if (!data.tr?.docx_base64 || !data.dfd?.docx_base64 || !data.oficio?.docx_base64) {
      generateError.value = data.error || 'TR, DFD ou Solicitação/Ofício não vieram na resposta. Tente novamente.';
      return;
    }

    const toBlobUrl = (base64, mimeType) => {
      if (!base64) return '';
      const binary = atob(base64);
      const len = binary.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i += 1) {
        bytes[i] = binary.charCodeAt(i);
      }
      return URL.createObjectURL(new Blob([bytes], { type: mimeType }));
    };

    try {
      const trUrl = toBlobUrl(
        data.tr.docx_base64,
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      );
      const dfdUrl = toBlobUrl(
        data.dfd.docx_base64,
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      );
      const oficioUrl = toBlobUrl(
        data.oficio.docx_base64,
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      );
      const zipUrl = data.zip?.zip_base64
        ? toBlobUrl(data.zip.zip_base64, 'application/zip')
        : '';
      // Revogar blobs antigos (se houver) antes de atribuir os novos, para todos os três botões ficarem consistentes
      if (documentTrUrl.value) URL.revokeObjectURL(documentTrUrl.value);
      if (documentDfdUrl.value) URL.revokeObjectURL(documentDfdUrl.value);
      if (documentOficioUrl.value) URL.revokeObjectURL(documentOficioUrl.value);
      if (documentZipUrl.value) URL.revokeObjectURL(documentZipUrl.value);
      documentTrUrl.value = trUrl;
      documentDfdUrl.value = dfdUrl;
      documentOficioUrl.value = oficioUrl;
      documentZipUrl.value = zipUrl;
      documentTrFilename.value = data.tr?.filename || 'termo_referencia.docx';
      documentDfdFilename.value = data.dfd?.filename || 'dfd.docx';
      documentOficioFilename.value = data.oficio?.filename || 'oficio.docx';
      documentZipFilename.value = data.zip?.filename || 'tr_dfd_oficio.zip';
    } catch (e) {
      generateError.value = `Falha ao processar arquivos: ${e?.message || 'dados inválidos'}. Tente novamente.`;
      return;
    }

    documentReady.value = true;
    successMessage.value = 'Termo de Referência, DFD e Solicitação/Ofício gerados com sucesso. Baixe os arquivos abaixo.';
    persistSlotEntries(buildSlotEntriesFromForm());
    return;
  }

  const endpoint = `${API_BASE}/api/documentos/gerar-via-llm`;

  const res = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(payload),
  });

  const contentType = (res.headers.get('content-type') || '').toLowerCase();

  if (res.status === 404) {
    generateError.value =
      'Rota não encontrada (404). Confira se o backend está rodando (docker compose up -d backend) e reconstruído com o código atual (docker compose build --no-cache backend). Em dev, o front usa o proxy do Vite para /api.';
    return;
  }

  // Demais modos: fluxo original (DOCX único)
  if (!res.ok) {
    const rawErr = await res.text();
    let err = {};
    try {
      err = contentType.includes('json') && rawErr ? JSON.parse(rawErr) : {};
    } catch (_e) {
      err = {};
    }
    generateError.value =
      res.status === 500
        ? (err.error || err.detail || 'Erro 500 no servidor. Veja os logs do container backend.')
        : (err.error || err.detail || `Erro ${res.status}`);
    return;
  }

  // Pedimos DOCX: resposta 200 pode ser o arquivo (Content-Type pode vir oculto por CORS em respostas attachment)
  const looksLikeDocx =
    contentType.includes('application/vnd.openxmlformats') ||
    contentType.includes('octet-stream');
  const notJson = !contentType.includes('application/json');

  if (looksLikeDocx || (payload.output === 'docx' && notJson)) {
    const blob = await res.blob();
    documentDocxUrl.value = URL.createObjectURL(blob);
    documentPdfUrl.value = '';
    documentReady.value = true;
    successMessage.value = 'Documento gerado pela IA. Baixe o DOCX abaixo.';
    persistSlotEntries(buildSlotEntriesFromForm());
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
onMounted(async () => {
  fetchCurrentUser();
  document.addEventListener('click', clickOutside);
  docTypeMode.value = isEtpLivreRoute.value ? 'auto' : 'tr_modelo';
  if (window.pdfjsLib) {
    pdfjsLib = window.pdfjsLib;
    if (!pdfjsLib.GlobalWorkerOptions.workerSrc) {
      pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.9.179/pdf.worker.min.js';
    }
  }
  resetSlotFormAndSections();
  loadSlotCatalogSuggestions();
  await loadSlotFormState();
  const qTemplate = route.query.template_id;
  if (qTemplate) {
    await fetchTemplateDetails(String(qTemplate));
    if (selectedTemplate.value) searchQuery.value = selectedTemplate.value.name;
  }
});
onUnmounted(() => {
  document.removeEventListener('click', clickOutside);
  clearTimeout(slotStateSaveDebounce.value);
  clearTimeout(templatePresetSaveDebounce.value);
  if (documentDocxUrl.value) URL.revokeObjectURL(documentDocxUrl.value);
  if (documentPdfUrl.value) URL.revokeObjectURL(documentPdfUrl.value);
  if (documentTrUrl.value) URL.revokeObjectURL(documentTrUrl.value);
  if (documentDfdUrl.value) URL.revokeObjectURL(documentDfdUrl.value);
  if (documentOficioUrl.value) URL.revokeObjectURL(documentOficioUrl.value);
  if (documentZipUrl.value) URL.revokeObjectURL(documentZipUrl.value);
});

watch(
  () => route.name,
  async () => {
    slotDrawerOpen.value = false;
    docTypeMode.value = isEtpLivreRoute.value ? 'auto' : 'tr_modelo';
    resetSlotFormAndSections();
    loadSlotCatalogSuggestions();
    await loadSlotFormState();
  },
);

watch(isEtpLivreRoute, (isEtp) => {
  docTypeMode.value = isEtp ? 'auto' : 'tr_modelo';
});

watch(
  () => slotForm.tr_data_automatica,
  (enabled) => {
    if (enabled) slotForm.tr_data_termo = '';
  },
);

watch(
  slotForm,
  () => {
    if (!showSlotsCard.value || isHydratingSlotState.value) return;
    clearTimeout(slotStateSaveDebounce.value);
    slotStateSaveDebounce.value = setTimeout(() => {
      saveSlotFormState();
    }, 500);
  },
  { deep: true },
);

watch(
  () => selectedTemplate.value?.id,
  () => {
    if (isHydratingSlotState.value) return;
    clearTimeout(templatePresetSaveDebounce.value);
    templatePresetSaveDebounce.value = setTimeout(() => {
      saveSlotFormState();
    }, 400);
  },
);

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
.doc-gen {
  width: 100%;
  max-width: 100%;
  overflow-x: hidden;
}
.doc-gen__grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 16px;
  align-items: start;
}
.doc-gen__grid--single {
  grid-template-columns: 1fr;
}
@media (max-width: 960px) {
  .doc-gen__grid {
    grid-template-columns: 1fr;
  }
}
.doc-gen__page-header {
  display: block;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 8px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
}
.doc-gen__page-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
  line-height: 1.35;
}
.doc-gen__page-subtitle {
  margin: 6px 0 0;
  font-size: 12px;
  color: #64748b;
}
/* O shell já mostra contexto global; no modo dispensa/ETP o cabeçalho local é oculto para evitar card vazio/duplicado. */
.doc-gen.doc-gen--rapida .doc-gen__page-header {
  display: none;
}
.dm-dark .doc-gen__page-header,
.dm-dark-theme .doc-gen__page-header {
  background: #0f172a;
  border-color: #334155;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.35);
}
.dm-dark .doc-gen__page-title,
.dm-dark-theme .doc-gen__page-title {
  color: #f1f5f9;
}
.dm-dark .doc-gen__page-subtitle,
.dm-dark-theme .doc-gen__page-subtitle {
  color: #94a3b8;
}
.doc-gen__main {
  min-width: 0;
}
.doc-gen__wizard {
  padding: 20px 24px;
  height: 72vh;
  max-height: 72vh;
  overflow-y: auto;
  overflow-x: hidden;
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
  display: inline-flex;
  align-items: center;
  gap: 8px;
  opacity: 0.95;
}
.doc-gen__spinner .fa-spinner {
  flex-shrink: 0;
}
.doc-gen__loader-wrap {
  margin-top: 14px;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: #f4f9fe;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
}
.doc-gen__loader-text {
  margin: 0;
  font-size: 12px;
  color: var(--color-primary-dark);
  font-weight: 600;
}
.doc-gen__pl {
  width: 5.4em;
  height: 5.4em;
}
.doc-gen__pl-ring {
  animation: docGenRingA 2s linear infinite;
}
.doc-gen__pl-ring--a {
  stroke: #0d6efd;
}
.doc-gen__pl-ring--b {
  animation-name: docGenRingB;
  stroke: #2a8cff;
}
.doc-gen__pl-ring--c {
  animation-name: docGenRingC;
  stroke: #1b74e4;
}
.doc-gen__pl-ring--d {
  animation-name: docGenRingD;
  stroke: #59a8ff;
}
@keyframes docGenRingA {
  from, 4% {
    stroke-dasharray: 0 660;
    stroke-width: 20;
    stroke-dashoffset: -330;
  }
  12% {
    stroke-dasharray: 60 600;
    stroke-width: 30;
    stroke-dashoffset: -335;
  }
  32% {
    stroke-dasharray: 60 600;
    stroke-width: 30;
    stroke-dashoffset: -595;
  }
  40%, 54% {
    stroke-dasharray: 0 660;
    stroke-width: 20;
    stroke-dashoffset: -660;
  }
  62% {
    stroke-dasharray: 60 600;
    stroke-width: 30;
    stroke-dashoffset: -665;
  }
  82% {
    stroke-dasharray: 60 600;
    stroke-width: 30;
    stroke-dashoffset: -925;
  }
  90%, to {
    stroke-dasharray: 0 660;
    stroke-width: 20;
    stroke-dashoffset: -990;
  }
}
@keyframes docGenRingB {
  from, 12% {
    stroke-dasharray: 0 220;
    stroke-width: 20;
    stroke-dashoffset: -110;
  }
  20% {
    stroke-dasharray: 20 200;
    stroke-width: 30;
    stroke-dashoffset: -115;
  }
  40% {
    stroke-dasharray: 20 200;
    stroke-width: 30;
    stroke-dashoffset: -195;
  }
  48%, 62% {
    stroke-dasharray: 0 220;
    stroke-width: 20;
    stroke-dashoffset: -220;
  }
  70% {
    stroke-dasharray: 20 200;
    stroke-width: 30;
    stroke-dashoffset: -225;
  }
  90% {
    stroke-dasharray: 20 200;
    stroke-width: 30;
    stroke-dashoffset: -305;
  }
  98%, to {
    stroke-dasharray: 0 220;
    stroke-width: 20;
    stroke-dashoffset: -330;
  }
}
@keyframes docGenRingC {
  from {
    stroke-dasharray: 0 440;
    stroke-width: 20;
    stroke-dashoffset: 0;
  }
  8% {
    stroke-dasharray: 40 400;
    stroke-width: 30;
    stroke-dashoffset: -5;
  }
  28% {
    stroke-dasharray: 40 400;
    stroke-width: 30;
    stroke-dashoffset: -175;
  }
  36%, 58% {
    stroke-dasharray: 0 440;
    stroke-width: 20;
    stroke-dashoffset: -220;
  }
  66% {
    stroke-dasharray: 40 400;
    stroke-width: 30;
    stroke-dashoffset: -225;
  }
  86% {
    stroke-dasharray: 40 400;
    stroke-width: 30;
    stroke-dashoffset: -395;
  }
  94%, to {
    stroke-dasharray: 0 440;
    stroke-width: 20;
    stroke-dashoffset: -440;
  }
}
@keyframes docGenRingD {
  from, 8% {
    stroke-dasharray: 0 440;
    stroke-width: 20;
    stroke-dashoffset: 0;
  }
  16% {
    stroke-dasharray: 40 400;
    stroke-width: 30;
    stroke-dashoffset: -5;
  }
  36% {
    stroke-dasharray: 40 400;
    stroke-width: 30;
    stroke-dashoffset: -175;
  }
  44%, 50% {
    stroke-dasharray: 0 440;
    stroke-width: 20;
    stroke-dashoffset: -220;
  }
  58% {
    stroke-dasharray: 40 400;
    stroke-width: 30;
    stroke-dashoffset: -225;
  }
  78% {
    stroke-dasharray: 40 400;
    stroke-width: 30;
    stroke-dashoffset: -395;
  }
  86%, to {
    stroke-dasharray: 0 440;
    stroke-width: 20;
    stroke-dashoffset: -440;
  }
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
.doc-gen__variables-card {
  padding: 14px 12px;
  height: 72vh;
  max-height: 72vh;
  overflow: hidden;
}
.doc-gen__variables-body {
  margin-top: 6px;
  height: calc(100% - 62px);
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 2px;
}
.doc-gen__variables-desc {
  margin: 0 0 8px;
  font-size: 12px;
}
.doc-gen__var-section {
  margin-top: 8px;
  padding: 8px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: #fafbfd;
}
.doc-gen__var-heading {
  margin: 0 0 6px;
  font-size: 12px;
  font-weight: 600;
}
.doc-gen__slot-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
  align-items: start;
}
.doc-gen__slot-field--full {
  grid-column: 1 / -1;
}
.doc-gen__slot-subheading {
  margin: 6px 0 2px;
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text);
  grid-column: 1 / -1;
}
.doc-gen__slot-field {
  margin: 0;
  min-width: 0;
}
.doc-gen__slot-field .gov-label {
  font-size: 11px;
  line-height: 1.3;
  margin-bottom: 3px;
}
.doc-gen__slot-input {
  width: 100%;
  font-size: 12px;
  padding: 6px 8px;
  min-width: 0;
}
.doc-gen__required {
  color: #c62828;
  margin-left: 2px;
}
.doc-gen__slot-checkbox-label {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12px;
  cursor: pointer;
  line-height: 1.35;
}
.doc-gen__slot-checkbox {
  margin-top: 2px;
  flex-shrink: 0;
  accent-color: var(--color-primary);
}
.doc-gen__datalist-wrap {
  width: 100%;
}
.doc-gen__combo-wrap {
  display: flex;
  gap: 4px;
  align-items: stretch;
  min-width: 0;
  position: relative;
}
.doc-gen__combo-wrap .doc-gen__slot-input {
  flex: 1;
}
.doc-gen__combo-add {
  white-space: nowrap;
  padding: 5px 8px;
  font-size: 11px;
}
.doc-gen__slot-suggestions {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  z-index: 40;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  max-height: 260px;
  overflow-y: auto;
  overflow-x: hidden;
  box-shadow: 0 6px 14px rgba(0, 0, 0, 0.12);
}
.doc-gen__slot-suggestion-item {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  border: none;
  background: transparent;
  text-align: left;
  padding: 6px 8px;
  cursor: pointer;
}
.doc-gen__slot-suggestion-item:hover {
  background: #edf5fc;
}
.doc-gen__slot-suggestion-label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
}
.doc-gen__slot-suggestion-remove {
  color: #c62828;
  font-size: 14px;
  line-height: 1;
  font-weight: 700;
  padding: 0 4px;
}
@media (max-width: 960px) {
  .doc-gen__wizard,
  .doc-gen__variables-card {
    height: auto;
    max-height: none;
  }
  .doc-gen__variables-body {
    height: auto;
    overflow: visible;
  }
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
.doc-gen__live-summary {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px;
  background: #fff;
  margin-bottom: 12px;
}
.doc-gen__live-summary-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.doc-gen__live-summary-kicker {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #64748b;
  font-weight: 600;
}
.doc-gen__live-summary-title {
  margin: 2px 0 0;
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}
.doc-gen__live-summary-pill {
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  color: #0369a1;
  font-size: 12px;
  font-weight: 700;
  border-radius: 999px;
  padding: 2px 10px;
}
.doc-gen__live-summary-bar {
  margin-top: 10px;
  width: 100%;
  height: 8px;
  border-radius: 999px;
  background: #f1f5f9;
  overflow: hidden;
}
.doc-gen__live-summary-bar-fill {
  display: block;
  height: 100%;
  width: 0;
  border-radius: 999px;
  background: #0ea5e9;
  transition: width .2s ease;
}

.doc-gen__drawer-backdrop {
  position: fixed;
  inset: 0;
  z-index: 40;
  background: rgba(15, 23, 42, 0.2);
}
.doc-gen__drawer {
  position: fixed;
  right: 0;
  top: 0;
  z-index: 50;
  height: 100%;
  width: 100%;
  max-width: 960px;
  transform: translateX(100%);
  transition: transform .3s ease;
  border-left: 1px solid #e2e8f0;
  background: #fff;
  box-shadow: -8px 0 28px rgba(15, 23, 42, 0.2);
  display: flex;
  flex-direction: column;
}
.doc-gen__drawer--open {
  transform: translateX(0);
}
.doc-gen__drawer-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  border-bottom: 1px solid #e2e8f0;
  padding: 16px 20px;
}
.doc-gen__drawer-kicker {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #64748b;
}
.doc-gen__drawer-title {
  margin: 2px 0 0;
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}
.doc-gen__drawer-close {
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #64748b;
  border-radius: 12px;
  width: 36px;
  height: 36px;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
}
.doc-gen__drawer-close:hover {
  background: #f8fafc;
}
.doc-gen__drawer-body {
  flex: 1;
  overflow-y: auto;
  padding: 18px 20px;
}
.doc-gen__drawer-foot {
  border-top: 1px solid #e2e8f0;
  padding: 14px 20px;
}
.doc-gen__drawer-foot .gov-btn {
  width: 100%;
}

/* UI de dispensa isolada do tema legado */
.doc-gen.doc-gen--rapida,
.doc-gen.doc-gen--rapida * {
  box-sizing: border-box;
}
.doc-gen.doc-gen--rapida {
  color: #0f172a;
}
.doc-gen.doc-gen--rapida :deep(.gov-page-header),
.doc-gen.doc-gen--rapida :deep(.gov-page-title),
.doc-gen.doc-gen--rapida :deep(.gov-page-subtitle),
.doc-gen.doc-gen--rapida :deep(.gov-surface),
.doc-gen.doc-gen--rapida :deep(.gov-surface__header),
.doc-gen.doc-gen--rapida :deep(.gov-surface__title),
.doc-gen.doc-gen--rapida :deep(.gov-surface__subtitle),
.doc-gen.doc-gen--rapida :deep(.gov-label),
.doc-gen.doc-gen--rapida :deep(.gov-label__hint),
.doc-gen.doc-gen--rapida :deep(.gov-input),
.doc-gen.doc-gen--rapida :deep(.gov-textarea),
.doc-gen.doc-gen--rapida :deep(.gov-btn),
.doc-gen.doc-gen--rapida :deep(.gov-btn--primary),
.doc-gen.doc-gen--rapida :deep(.gov-btn--secondary),
.doc-gen.doc-gen--rapida :deep(.gov-btn--outline),
.doc-gen.doc-gen--rapida :deep(.gov-text-soft),
.doc-gen.doc-gen--rapida :deep(.gov-link) {
  all: unset;
}
.doc-gen.doc-gen--rapida :deep(.gov-page-header) {
  display: block;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 8px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
}
.doc-gen.doc-gen--rapida :deep(.gov-page-title) {
  display: block;
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
  line-height: 1.35;
}
.doc-gen.doc-gen--rapida :deep(.gov-page-subtitle) {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  color: #64748b;
}
.doc-gen.doc-gen--rapida :deep(.doc-gen__grid) {
  gap: 16px;
}
.doc-gen.doc-gen--rapida :deep(.doc-gen__wizard),
.doc-gen.doc-gen--rapida :deep(.doc-gen__variables-card) {
  border-radius: 16px;
  border: 1px solid #e2e8f0;
  background: #fff;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
}
.doc-gen.doc-gen--rapida :deep(.doc-gen__wizard.doc-gen__wizard--etp) {
  max-height: none;
  height: auto;
  min-height: min(72vh, 720px);
}
.doc-gen.doc-gen--rapida :deep(.doc-gen__variables-card) {
  position: sticky;
  top: 12px;
}
.doc-gen.doc-gen--rapida :deep(.gov-surface__header) {
  display: block;
  border-bottom: 1px solid #e2e8f0;
  margin-bottom: 8px;
  padding-bottom: 12px;
}
.doc-gen.doc-gen--rapida :deep(.gov-surface__title) {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}
.doc-gen.doc-gen--rapida :deep(.gov-surface__subtitle) {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: #94a3b8;
}
.doc-gen.doc-gen--rapida :deep(.gov-label) {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: #475569;
}
.doc-gen.doc-gen--rapida :deep(.gov-label__hint) {
  font-size: 11px;
  color: #94a3b8;
}
.doc-gen.doc-gen--rapida :deep(.gov-input),
.doc-gen.doc-gen--rapida :deep(.gov-textarea),
.doc-gen.doc-gen--rapida :deep(.doc-gen__search-input) {
  display: block;
  width: 100%;
  margin-top: 4px;
  border-radius: 12px;
  border: 1px solid #cbd5e1;
  background: #fff;
  padding: 10px 12px;
  font-size: 14px;
  color: #1e293b;
  outline: none;
  transition: border-color .15s ease, box-shadow .15s ease;
}
.doc-gen.doc-gen--rapida :deep(.gov-input:focus),
.doc-gen.doc-gen--rapida :deep(.gov-textarea:focus),
.doc-gen.doc-gen--rapida :deep(.doc-gen__search-input:focus) {
  border-color: #38bdf8;
  box-shadow: 0 0 0 3px rgba(125, 211, 252, .35);
}
.doc-gen.doc-gen--rapida :deep(.gov-btn),
.doc-gen.doc-gen--rapida :deep(.gov-btn--primary),
.doc-gen.doc-gen--rapida :deep(.gov-btn--secondary),
.doc-gen.doc-gen--rapida :deep(.gov-btn--outline) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 12px;
  border: 1px solid transparent;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
}
.doc-gen.doc-gen--rapida :deep(.gov-btn--primary) {
  background: #0f172a;
  color: #fff;
  border-color: #0f172a;
}
.doc-gen.doc-gen--rapida :deep(.gov-btn--primary:hover:not(:disabled)) {
  background: #1e293b;
  border-color: #1e293b;
}
.doc-gen.doc-gen--rapida :deep(.gov-btn--secondary),
.doc-gen.doc-gen--rapida :deep(.gov-btn--outline) {
  background: #fff;
  color: #334155;
  border-color: #cbd5e1;
}
.doc-gen.doc-gen--rapida :deep(.gov-btn--secondary:hover:not(:disabled)),
.doc-gen.doc-gen--rapida :deep(.gov-btn--outline:hover:not(:disabled)) {
  background: #f8fafc;
}
.doc-gen.doc-gen--rapida :deep(.gov-text-soft) {
  display: block;
  font-size: 12px;
  color: #94a3b8;
}
.doc-gen.doc-gen--rapida :deep(.gov-link) {
  color: #0f172a;
  font-weight: 600;
  text-decoration: none;
}
.doc-gen.doc-gen--rapida :deep(.doc-gen__llm-hint) {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
}
.doc-gen.doc-gen--rapida :deep(.doc-gen__results) {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(15, 23, 42, .08);
}
.doc-gen.doc-gen--rapida :deep(.doc-gen__result-item:hover),
.doc-gen.doc-gen--rapida :deep(.doc-gen__result-item--focused) {
  background: #f8fafc;
}
.doc-gen.doc-gen--rapida :deep(.doc-gen__result-name) {
  color: #0f172a;
  font-weight: 600;
}
.doc-gen.doc-gen--rapida :deep(.doc-gen__result-item--empty) {
  color: #94a3b8;
}
.doc-gen.doc-gen--rapida :deep(.doc-gen__error) {
  display: block;
  margin-top: 16px;
  padding: 14px 16px;
  border-radius: 12px;
  border: 1px solid #fecaca;
  background: #fef2f2;
}
.doc-gen.doc-gen--rapida :deep(.doc-gen__error-text) {
  display: block;
  margin: 0;
  font-size: 13px;
  color: #b91c1c;
  line-height: 1.45;
}
.doc-gen.doc-gen--rapida :deep(.doc-gen__success) {
  display: block;
  margin-top: 16px;
  padding: 14px 16px;
  border-radius: 12px;
  border: 1px solid #86efac;
  background: #f0fdf4;
}
.doc-gen.doc-gen--rapida :deep(.doc-gen__success-title) {
  display: block;
  margin: 0 0 6px;
  font-size: 14px;
  font-weight: 600;
  color: #166534;
}
.doc-gen.doc-gen--rapida :deep(.doc-gen__loader-wrap) {
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
}
.doc-gen.doc-gen--rapida :deep(.doc-gen__loader-text) {
  color: #334155;
}
.doc-gen.doc-gen--rapida :deep(.doc-gen__var-heading),
.doc-gen.doc-gen--rapida :deep(.doc-gen__slot-subheading) {
  color: #334155;
}

/* Tema escuro: UI nova (dispensa rápida + ETP livre) */
.dm-dark .doc-gen.doc-gen--rapida,
.dm-dark-theme .doc-gen.doc-gen--rapida {
  color: #e2e8f0;
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.gov-page-header),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.gov-page-header) {
  background: #0f172a;
  border-color: #334155;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.35);
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.gov-page-title),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.gov-page-title) {
  color: #f1f5f9;
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.gov-page-subtitle),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.gov-page-subtitle) {
  color: #94a3b8;
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.doc-gen__wizard),
.dm-dark .doc-gen.doc-gen--rapida :deep(.doc-gen__variables-card),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.doc-gen__wizard),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.doc-gen__variables-card) {
  background: #0f172a;
  border-color: #334155;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.35);
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.gov-surface__header),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.gov-surface__header) {
  border-color: #334155;
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.gov-surface__title),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.gov-surface__title) {
  color: #e2e8f0;
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.gov-surface__subtitle),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.gov-surface__subtitle) {
  color: #94a3b8;
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.gov-label),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.gov-label) {
  color: #cbd5e1;
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.gov-label__hint),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.gov-label__hint) {
  color: #94a3b8;
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.gov-input),
.dm-dark .doc-gen.doc-gen--rapida :deep(.gov-textarea),
.dm-dark .doc-gen.doc-gen--rapida :deep(.doc-gen__search-input),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.gov-input),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.gov-textarea),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.doc-gen__search-input) {
  background: #0b1222;
  border-color: #334155;
  color: #e2e8f0;
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.gov-input::placeholder),
.dm-dark .doc-gen.doc-gen--rapida :deep(.gov-textarea::placeholder),
.dm-dark .doc-gen.doc-gen--rapida :deep(.doc-gen__search-input::placeholder),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.gov-input::placeholder),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.gov-textarea::placeholder),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.doc-gen__search-input::placeholder) {
  color: #64748b;
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.gov-input:focus),
.dm-dark .doc-gen.doc-gen--rapida :deep(.gov-textarea:focus),
.dm-dark .doc-gen.doc-gen--rapida :deep(.doc-gen__search-input:focus),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.gov-input:focus),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.gov-textarea:focus),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.doc-gen__search-input:focus) {
  border-color: #38bdf8;
  box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.22);
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.gov-btn--primary),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.gov-btn--primary) {
  background: #38bdf8;
  color: #0f172a;
  border-color: #38bdf8;
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.gov-btn--primary:hover:not(:disabled)),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.gov-btn--primary:hover:not(:disabled)) {
  background: #7dd3fc;
  border-color: #7dd3fc;
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.gov-btn--secondary),
.dm-dark .doc-gen.doc-gen--rapida :deep(.gov-btn--outline),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.gov-btn--secondary),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.gov-btn--outline) {
  background: #0b1222;
  color: #e2e8f0;
  border-color: #334155;
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.gov-btn--secondary:hover:not(:disabled)),
.dm-dark .doc-gen.doc-gen--rapida :deep(.gov-btn--outline:hover:not(:disabled)),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.gov-btn--secondary:hover:not(:disabled)),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.gov-btn--outline:hover:not(:disabled)) {
  background: #1e293b;
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.gov-text-soft),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.gov-text-soft) {
  color: #94a3b8;
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.gov-link),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.gov-link) {
  color: #7dd3fc;
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.doc-gen__llm-hint),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.doc-gen__llm-hint) {
  background: #082f49;
  border-color: #0ea5e9;
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.doc-gen__llm-hint strong),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.doc-gen__llm-hint strong) {
  color: #e2e8f0;
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.doc-gen__results),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.doc-gen__results) {
  background: #0f172a;
  border-color: #334155;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.45);
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.doc-gen__result-item:hover),
.dm-dark .doc-gen.doc-gen--rapida :deep(.doc-gen__result-item--focused),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.doc-gen__result-item:hover),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.doc-gen__result-item--focused) {
  background: #1e293b;
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.doc-gen__result-name),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.doc-gen__result-name) {
  color: #e2e8f0;
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.doc-gen__result-item--empty),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.doc-gen__result-item--empty) {
  color: #64748b;
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.doc-gen__result-icon),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.doc-gen__result-icon) {
  color: #38bdf8;
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.doc-gen__error),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.doc-gen__error) {
  border-color: #9f1239;
  background: #3f1d2e;
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.doc-gen__error-text),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.doc-gen__error-text) {
  color: #fecdd3;
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.doc-gen__success),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.doc-gen__success) {
  border-color: #166534;
  background: #052e16;
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.doc-gen__success-title),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.doc-gen__success-title) {
  color: #bbf7d0;
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.doc-gen__loader-wrap),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.doc-gen__loader-wrap) {
  background: #082f49;
  border-color: #0ea5e9;
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.doc-gen__loader-text),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.doc-gen__loader-text) {
  color: #bae6fd;
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.doc-gen__pl-ring--a),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.doc-gen__pl-ring--a) {
  stroke: #38bdf8;
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.doc-gen__pl-ring--b),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.doc-gen__pl-ring--b) {
  stroke: #7dd3fc;
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.doc-gen__pl-ring--c),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.doc-gen__pl-ring--c) {
  stroke: #0ea5e9;
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.doc-gen__pl-ring--d),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.doc-gen__pl-ring--d) {
  stroke: #bae6fd;
}
.dm-dark .doc-gen.doc-gen--rapida :deep(.doc-gen__var-heading),
.dm-dark .doc-gen.doc-gen--rapida :deep(.doc-gen__slot-subheading),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.doc-gen__var-heading),
.dm-dark-theme .doc-gen.doc-gen--rapida :deep(.doc-gen__slot-subheading) {
  color: #cbd5e1;
}
</style>
