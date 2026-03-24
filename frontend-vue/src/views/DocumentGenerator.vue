<template>
  <div class="doc-gen">
    <header class="gov-page-header">
      <h1 class="gov-page-title">Gerador de Documentos</h1>
      <p class="gov-page-subtitle">
        Crie documentos profissionais com conformidade governamental
      </p>
    </header>

    <div class="doc-gen__grid" :class="{ 'doc-gen__grid--single': !showSlotsCard }">
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
                <div class="doc-gen__llm-hint">
                  <p class="gov-text-soft">
                    <i class="fa-solid fa-wand-magic-sparkles" aria-hidden="true"></i>
                    <span v-if="docTypeMode === 'tr_modelo'">
                      Esta página gera <strong>TR / DFD com modelo oficial (slots)</strong>. O modo é inferido automaticamente pela rota selecionada.
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

              </div>

              <!-- Prompt IA -->
              <div class="gov-field">
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
                  type="submit"
                  class="gov-btn gov-btn--primary"
                  :disabled="isSubmitting || !hasDocumentBase || !iaPrompt.trim()"
                >
                  <span v-if="!isSubmitting"><i class="fa-solid fa-robot" aria-hidden="true"></i> Gerar com IA Contextual</span>
                  <span v-else class="doc-gen__spinner">Processando com IA...</span>
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
                      v-if="documentZipUrl"
                      :href="documentZipUrl"
                      :download="documentZipFilename"
                      class="gov-btn gov-btn--secondary"
                    >
                      <i class="fa-solid fa-file-archive" aria-hidden="true"></i> Download TR+DFD (ZIP)
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

      <!-- Coluna direita: dados para slots (somente TR/DFD modelo oficial) -->
      <aside v-if="showSlotsCard" class="doc-gen__aside">
        <section class="gov-surface doc-gen__variables-card">
          <div class="gov-surface__header">
            <div>
              <h2 class="gov-surface__title">Dados do assistente (slots)</h2>
              <p class="gov-surface__subtitle">{{ slotCardFlowTitle }}</p>
            </div>
          </div>
          <div class="doc-gen__variables-body">
            <p class="gov-text-soft doc-gen__variables-desc">
              Preencha os campos com os valores que devem constar no documento (texto livre, lista sugerida ou registro na hora).
              Eles são enviados à IA e aos placeholders do modelo oficial quando aplicável.
            </p>
            <div
              v-for="section in selectedFlow.sections"
              :key="section.key"
              class="doc-gen__var-section"
            >
              <h3 class="doc-gen__var-heading">{{ section.title }}</h3>
              <div class="doc-gen__slot-grid">
                <template v-for="field in section.fields" :key="field.id">
                  <h4 v-if="field.input === 'heading' && shouldRenderField(field)" class="doc-gen__slot-subheading">
                    {{ field.label }}
                  </h4>
                  <div
                    v-else-if="shouldRenderField(field)"
                    class="gov-field doc-gen__slot-field"
                    :class="{ 'doc-gen__slot-field--full': field.fullWidth }"
                  >
                    <label class="gov-label" :for="'slot-' + field.id">
                      {{ field.label }}
                      <span v-if="field.required" class="doc-gen__required" aria-hidden="true">*</span>
                    </label>
                    <textarea
                      v-if="field.input === 'textarea'"
                      :id="'slot-' + field.id"
                      v-model="slotForm[field.id]"
                      class="gov-textarea doc-gen__slot-input"
                      rows="3"
                    />
                    <input
                      v-else-if="field.input === 'date'"
                      :id="'slot-' + field.id"
                      v-model="slotForm[field.id]"
                      type="date"
                      class="gov-input doc-gen__slot-input"
                      :disabled="isSlotFieldDisabled(field)"
                    />
                    <div v-else-if="field.input === 'email' || field.input === 'text'" class="doc-gen__combo-wrap">
                      <input
                        :id="'slot-' + field.id"
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
                      <div
                        v-if="isFieldSuggestionsOpen(field.id)"
                        class="doc-gen__slot-suggestions"
                      >
                        <button
                          v-for="opt in getFieldSuggestions(field.id)"
                          :key="field.id + '-opt-' + opt"
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
                        :id="'slot-' + field.id"
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
                      <div
                        v-if="isFieldSuggestionsOpen(field.id)"
                        class="doc-gen__slot-suggestions"
                      >
                        <button
                          v-for="opt in getFieldSuggestions(field.id)"
                          :key="field.id + '-opt-' + opt"
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
                      :for="'slot-' + field.id"
                    >
                      <input
                        :id="'slot-' + field.id"
                        v-model="slotForm[field.id]"
                        type="checkbox"
                        class="doc-gen__slot-checkbox"
                      />
                      <span>{{ field.checkboxHint || field.label }}</span>
                    </label>
                    <input
                      v-else
                      :id="'slot-' + field.id"
                      v-model="slotForm[field.id]"
                      type="text"
                      class="gov-input doc-gen__slot-input"
                    />
                  </div>
                </template>
              </div>
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
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue';
import { useRoute } from 'vue-router';

// Em dev: usar '' para que a requisição passe pelo proxy do Vite (evita 404 por chamar outro host/porta)
const API_BASE = import.meta.dev ? '' : (import.meta.env.VITE_API_URL || '');
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
const sourceMode = ref('llm'); // modo único: criar do zero com IA
const isSubmitting = ref(false);
const documentReady = ref(false);
const documentDocxUrl = ref('');
const documentPdfUrl = ref('');
const documentTrUrl = ref('');
const documentDfdUrl = ref('');
const documentZipUrl = ref('');
const documentTrFilename = ref('termo_referencia.docx');
const documentDfdFilename = ref('dfd.docx');
const documentZipFilename = ref('tr_dfd.zip');
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
          { id: 'solicitacao_destinatario_nome', label: '1.1 A quem é direcionada a solicitação — Nome', input: 'text' },
          {
            id: 'solicitacao_destinatario_cargo',
            label: '1.1 A quem é direcionada a solicitação — Função / Cargo',
            input: 'datalist',
          },
          { id: 'solicitacao_responsavel_nome', label: '1.2 Responsável pela solicitação — Nome', input: 'text' },
          {
            id: 'solicitacao_responsavel_cargo',
            label: '1.2 Responsável pela solicitação — Função / Cargo',
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
          {
            id: 'dfd_assinatura_cargo',
            label: 'Função / cargo do responsável pela assinatura da DFD',
            input: 'text',
            required: true,
          },
        ],
      },
      {
        key: 'tr',
        title: '3. Termo de Referência',
        fields: [
          {
            id: 'tr_objeto_manual',
            label: 'Objeto do TR (manual, sem geração por IA)',
            input: 'textarea',
            fullWidth: true,
          },
          {
            id: 'tr_endereco_propostas',
            label: 'Endereço presencial para envio ou entrega de propostas',
            input: 'text',
            fullWidth: true,
          },
          { id: 'tr_data_termo', label: 'Data do termo', input: 'date' },
          { id: 'tr_email_propostas', label: 'E-mail para recebimento de propostas', input: 'email' },
          {
            id: 'tr_assinatura_digital',
            label: 'Datado e assinado digitalmente',
            input: 'checkbox',
            checkboxHint: 'Datado e assinado digitalmente.',
          },
          {
            id: 'tr_data_automatica',
            label: 'Data automática',
            input: 'checkbox',
            checkboxHint: 'Inserir data atual automaticamente.',
          },
          { id: '_h_tr_assin', label: 'Assinatura do termo', input: 'heading', fullWidth: true },
          {
            id: 'tr_nome_assinante',
            label: 'Nome de quem assinará o Termo de Referência',
            input: 'text',
          },
          {
            id: 'tr_cargo_assinante',
            label: 'Função / cargo de quem assina o termo',
            input: 'datalist',
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
  InexigibilidadeArt74IShowArtistico: {
    title: 'Assistente de Criação - Inexigibilidade - Art. 74, Inciso I - Show Artístico',
    sections: [
      {
        key: 'base',
        title: 'Campos principais',
        fields: [
          { id: 'artista', label: 'Artista / atração', input: 'text' },
          { id: 'data_evento', label: 'Data do evento', input: 'date' },
          { id: 'justificativa_inviabilidade', label: 'Justificativa de inviabilidade de competição', input: 'textarea', fullWidth: true },
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

const isEtpLivreRoute = computed(() => route.name === 'EtpLivre');
const showSlotsCard = computed(() => !isEtpLivreRoute.value);

const selectedFlow = computed(() => TR_DFD_SLOTS_FLOW);

const slotCardFlowTitle = computed(() => {
  const routeFlowTitle = FLOW_CONFIG[route.name]?.title;
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
  InexigibilidadeArt74IShowArtistico: 'inexigibilidade_74_i_show_artistico',
};

const SOL_OFICIO_FUNDAMENTO_LEGAL_BY_ROUTE = {
  DispensaArt75IManutencaoVeiculos: 'Art. 75, Inciso I, da Lei nº 14.133/2021',
  DispensaArt75IObrasEngenharia: 'Art. 75, Inciso I, da Lei nº 14.133/2021',
  DispensaArt75IICompras: 'Art. 75, Inciso II, da Lei nº 14.133/2021',
  DispensaArt75IIServicos: 'Art. 75, Inciso II, da Lei nº 14.133/2021',
  DispensaArt75IIComprasServicosInclusos: 'Art. 75, Inciso II, da Lei nº 14.133/2021',
  InexigibilidadeArt74IShowArtistico: 'Art. 74, Inciso I, da Lei nº 14.133/2021',
};

const slotPackageKey = computed(() => {
  if (isEtpLivreRoute.value) return 'etp_livre';
  return SLOT_PACKAGE_BY_ROUTE[route.name] || 'tr_dfd_generico';
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
  if (field.id === 'tr_objeto_manual') return route.name === 'DispensaArt75IObrasEngenharia';
  return true;
}

/** Mapeia campos do fluxo “Dispensa / DFD” para chaves aceitas em `slots_override` no backend. */
function buildTrSlotsOverride() {
  const f = slotForm;
  const o = {};
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
  const solRespNome = (f.solicitacao_responsavel_nome || '').trim();
  const solRespCargo = (f.solicitacao_responsavel_cargo || '').trim();
  if (solDestNome) o.sol_oficio_destinatario_nome = solDestNome;
  if (solDestCargo) o.sol_oficio_destinatario_cargo = solDestCargo;
  if (solRespNome) o.sol_oficio_responsavel_nome = solRespNome;
  if (solRespCargo) o.sol_oficio_responsavel_cargo = solRespCargo;

  const setor = (f.dfd_setor_requisitante || '').trim();
  if (setor) o.secretaria_usuario = setor;
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
    dataTermo = dataTermo ? `${dataTermo}, datado e assinado digitalmente` : 'datado e assinado digitalmente';
  }
  if (dataTermo) {
    o.data_termo = dataTermo;
  }

  const nomeAss = (f.tr_nome_assinante || '').trim();
  const cargoAss = (f.tr_cargo_assinante || '').trim();
  if (nomeAss) o.nome_assinante_termo = nomeAss;
  if (cargoAss) o.cargo_assinante_termo = cargoAss;

  const objetoManualTR = (f.tr_objeto_manual || '').trim();
  if (route.name === 'DispensaArt75IObrasEngenharia') {
    // Nesta rota o objeto é sempre manual (sem geração por IA).
    if (objetoManualTR) o.objeto = objetoManualTR;
  } else {
    const objeto = (f.objeto || f.objeto_obra || '').trim();
    if (objeto) o.objeto = objeto;
  }

  const justificativa = (f.justificativa || f.justificativa_inviabilidade || '').trim();
  if (justificativa) o.justificativa = justificativa;

  const setorResp = (f.setor_responsavel || '').trim();
  if (setorResp && !o.secretaria_usuario) o.secretaria_usuario = setorResp;

  const fundamentoLegal = SOL_OFICIO_FUNDAMENTO_LEGAL_BY_ROUTE[route.name];
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
  if (!iaPrompt.value.trim()) return;
  if (docTypeMode.value === 'tr_modelo' && route.name === 'DispensaArt75IObrasEngenharia') {
    const manualObject = String(slotForm.tr_objeto_manual || '').trim();
    if (!manualObject) {
      generateError.value = 'Preencha o campo "Objeto do TR (manual, sem geração por IA)" para gerar nesta página.';
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
  if (documentZipUrl.value) {
    URL.revokeObjectURL(documentZipUrl.value);
    documentZipUrl.value = '';
  }
  documentTrFilename.value = 'termo_referencia.docx';
  documentDfdFilename.value = 'dfd.docx';
  documentZipFilename.value = 'tr_dfd.zip';

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
  const appendix = isTrDfd ? buildFormPromptAppendix() : '';
  const userPromptFinal = appendix ? `${basePrompt}\n\n${appendix}` : basePrompt;

  const payload = isTrDfd
    ? { user_prompt: userPromptFinal, slots_override: buildTrSlotsOverride(), slot_package_key: slotPackageKey.value }
    : {
        user_prompt: basePrompt,
        output: 'docx',
        slot_package_key: slotPackageKey.value,
      };
  if (selectedTemplate.value?.id) {
    payload.template_id = selectedTemplate.value.id;
  }

  const endpoint = isTrDfd
    ? `${API_BASE}/api/documentos/gerar-tr-e-dfd`
    : `${API_BASE}/api/documentos/gerar-via-llm`;

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

  // Modo TR/DFD (modelo oficial): resposta é sempre JSON com base64 dos arquivos
  if (docTypeMode.value === 'tr_modelo') {
    const rawText = await res.text();
    let data = {};
    try {
      data = rawText ? JSON.parse(rawText) : {};
    } catch (_e) {
      generateError.value = `Resposta inválida do servidor (não é JSON). Status: ${res.status}. Verifique se o backend respondeu corretamente.`;
      return;
    }

    if (!res.ok || !data.ok) {
      generateError.value =
        res.status === 500
          ? (data.error || data.detail || 'Erro 500 no servidor. Veja os logs do container backend.')
          : (data.error || data.detail || `Erro ${res.status}`);
      return;
    }

    if (!data.tr?.docx_base64 || !data.dfd?.docx_base64) {
      generateError.value = data.error || 'TR ou DFD não vieram na resposta. Tente novamente.';
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
      const zipUrl = data.zip?.zip_base64
        ? toBlobUrl(data.zip.zip_base64, 'application/zip')
        : '';
      // Revogar blobs antigos (se houver) antes de atribuir os novos, para todos os três botões ficarem consistentes
      if (documentTrUrl.value) URL.revokeObjectURL(documentTrUrl.value);
      if (documentDfdUrl.value) URL.revokeObjectURL(documentDfdUrl.value);
      if (documentZipUrl.value) URL.revokeObjectURL(documentZipUrl.value);
      documentTrUrl.value = trUrl;
      documentDfdUrl.value = dfdUrl;
      documentZipUrl.value = zipUrl;
      documentTrFilename.value = data.tr?.filename || 'termo_referencia.docx';
      documentDfdFilename.value = data.dfd?.filename || 'dfd.docx';
      documentZipFilename.value = data.zip?.filename || 'tr_dfd.zip';
    } catch (e) {
      generateError.value = `Falha ao processar arquivos: ${e?.message || 'dados inválidos'}. Tente novamente.`;
      return;
    }

    documentReady.value = true;
    successMessage.value = 'Termo de Referência e DFD gerados com sucesso. Baixe os arquivos abaixo.';
    persistSlotEntries(buildSlotEntriesFromForm());
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
onMounted(() => {
  document.addEventListener('click', clickOutside);
  docTypeMode.value = isEtpLivreRoute.value ? 'auto' : 'tr_modelo';
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
  resetSlotFormAndSections();
  loadSlotCatalogSuggestions();
});
onUnmounted(() => {
  document.removeEventListener('click', clickOutside);
  if (documentDocxUrl.value) URL.revokeObjectURL(documentDocxUrl.value);
  if (documentPdfUrl.value) URL.revokeObjectURL(documentPdfUrl.value);
  if (documentTrUrl.value) URL.revokeObjectURL(documentTrUrl.value);
  if (documentDfdUrl.value) URL.revokeObjectURL(documentDfdUrl.value);
  if (documentZipUrl.value) URL.revokeObjectURL(documentZipUrl.value);
});

watch(
  () => route.name,
  () => {
    docTypeMode.value = isEtpLivreRoute.value ? 'auto' : 'tr_modelo';
    resetSlotFormAndSections();
    loadSlotCatalogSuggestions();
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
  opacity: 0.9;
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
</style>
