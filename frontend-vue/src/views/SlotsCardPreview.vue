<template>
  <div class="slots-preview">
    <header class="slots-preview__header">
      <h1 class="slots-preview__title">Preview de Card - TR/DFD</h1>
      <p class="slots-preview__subtitle">
        Página pública para testar somente o design do card (sem login e sem backend).
      </p>
    </header>

    <div class="slots-preview__layout">
      <section class="gov-surface slots-preview__generator">
        <div class="gov-surface__header">
          <div>
            <h2 class="gov-surface__title">Gerador de Documentos (preview)</h2>
            <p class="gov-surface__subtitle">Card de referência para comparar tamanho com o card de slots</p>
          </div>
        </div>
        <div class="slots-preview__generator-body">
          <div class="gov-field">
            <label class="gov-label">Tipo de documento</label>
            <div class="slots-preview__radios">
              <label><input type="radio" checked /> TR/DFD (modelo oficial)</label>
              <label><input type="radio" /> ETP (IA flexível)</label>
            </div>
          </div>
          <div class="gov-field">
            <label class="gov-label">Documento Base</label>
            <input class="gov-input" value="Modelo Oficial - TR e DFD" />
          </div>
          <div class="gov-field">
            <label class="gov-label">Prompt de Inteligência Artificial</label>
            <textarea class="gov-textarea" rows="10">Ex: Contratação de manutenção preventiva de frota municipal...</textarea>
          </div>
          <div class="slots-preview__actions">
            <button type="button" class="gov-btn gov-btn--primary">Gerar com IA</button>
            <button type="button" class="gov-btn gov-btn--outline">Download TR</button>
            <button type="button" class="gov-btn gov-btn--outline">Download DFD</button>
          </div>
        </div>
      </section>

      <section class="gov-surface slots-preview__card">
        <div class="gov-surface__header">
          <div>
            <h2 class="gov-surface__title">
              Assistente de Criação - Dispensa de Licitação - Art. 75, Inciso I (Lei n 14.133/2021)
            </h2>
            <p class="gov-surface__subtitle">Formulário de slots - Solicitação / DFD / TR</p>
          </div>
        </div>
        <div class="slots-preview__body">
          <div v-for="section in sections" :key="section.key" class="slots-preview__section">
            <h3 class="slots-preview__section-title">{{ section.title }}</h3>

            <div class="slots-preview__grid">
              <template v-for="field in section.fields" :key="field.id">
                <h4 v-if="field.input === 'heading'" class="slots-preview__subheading">
                  {{ field.label }}
                </h4>

                <div
                  v-else
                  class="gov-field slots-preview__field"
                  :class="{ 'slots-preview__field--full': field.fullWidth }"
                >
                  <label class="gov-label" :for="field.id">
                    {{ field.label }}
                    <span v-if="field.required" class="slots-preview__required">*</span>
                  </label>

                  <textarea
                    v-if="field.input === 'textarea'"
                    :id="field.id"
                    v-model="form[field.id]"
                    class="gov-textarea"
                    rows="3"
                  />

                  <input
                    v-else-if="field.input === 'date'"
                    :id="field.id"
                    v-model="form[field.id]"
                    type="date"
                    class="gov-input"
                  />

                  <div v-else-if="field.input === 'email' || field.input === 'text'" class="slots-preview__combo">
                    <input
                      :id="field.id"
                      v-model="form[field.id]"
                      :type="field.input === 'email' ? 'email' : 'text'"
                      class="gov-input"
                      :list="`field-dl-${field.id}`"
                      placeholder="Selecione, digite ou adicione novo valor"
                    />
                    <datalist :id="`field-dl-${field.id}`">
                      <option
                        v-for="opt in fieldOptions[field.id] || []"
                        :key="`${field.id}-${opt}`"
                        :value="opt"
                      />
                    </datalist>
                    <button type="button" class="gov-btn gov-btn--outline gov-btn--sm" @click="addFieldOption(field.id)">
                      + Adicionar
                    </button>
                  </div>

                  <div v-else-if="field.input === 'datalist'" class="slots-preview__combo">
                    <input
                      :id="field.id"
                      v-model="form[field.id]"
                      class="gov-input"
                      :list="`field-dl-${field.id}`"
                      placeholder="Digite o nome"
                    />
                    <datalist :id="`field-dl-${field.id}`">
                      <option
                        v-for="opt in fieldOptions[field.id] || []"
                        :key="`${field.id}-${opt}`"
                        :value="opt"
                      />
                    </datalist>
                    <button type="button" class="gov-btn gov-btn--outline gov-btn--sm" @click="addFieldOption(field.id)">
                      + Adicionar
                    </button>
                  </div>

                  <label v-else-if="field.input === 'checkbox'" class="slots-preview__checkbox">
                    <input :id="field.id" v-model="form[field.id]" type="checkbox" />
                    <span>{{ field.checkboxHint || field.label }}</span>
                  </label>

                  <input v-else :id="field.id" v-model="form[field.id]" type="text" class="gov-input" />
                </div>
              </template>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { reactive } from 'vue';

const sections = [
  {
    key: 'solicitacao',
    title: '1. Solicitação / Ofício',
    fields: [
      { id: 'solicitacao_destinatario_nome', label: '1.1 A quem é direcionada a solicitação? Nome', input: 'text' },
      { id: 'solicitacao_responsavel_nome', label: '1.2 Responsável pela Solicitação? Nome', input: 'textarea', fullWidth: true },
    ],
  },
  {
    key: 'dfd',
    title: '2. DFD - Documento de Formalização da Demanda',
    fields: [
      { id: 'dfd_setor', label: 'Setor Requisitante (Unidade / Setor / Departamento)', input: 'text', required: true },
      { id: 'dfd_responsavel', label: 'Responsável pela Demanda', input: 'text', required: true },
      { id: 'dfd_email', label: 'E-mail', input: 'email', required: true },
      { id: 'dfd_gestor', label: 'Nome do(a) Gestor(a) de Contratos', input: 'text', required: true },
      { id: 'dfd_fiscal', label: 'Nome do(a) Fiscal de Contratos', input: 'text', required: true },
      { id: 'dfd_assinatura_nome', label: 'Nome do responsável pela assinatura da DFD', input: 'textarea', fullWidth: true, required: true },
    ],
  },
  {
    key: 'tr',
    title: '3. Termo de Referência',
    fields: [
      { id: 'tr_endereco', label: 'Endereço presencial para envio ou entrega de propostas', input: 'text', fullWidth: true },
      { id: 'tr_data', label: 'Data do Termo', input: 'date' },
      { id: 'tr_email', label: 'E-mail para recebimento de propostas', input: 'email' },
      { id: 'tr_assinatura_digital', label: 'Datado e assinado digitalmente', input: 'checkbox', checkboxHint: 'Datado e assinado digitalmente.' },
      { id: 'tr_data_automatica', label: 'Inserir data atual automaticamente', input: 'checkbox', checkboxHint: 'Inserir data atual automaticamente.' },
      { id: 'tr_heading', label: 'Assinatura do Termo', input: 'heading', fullWidth: true },
      { id: 'tr_nome_assinante', label: 'Nome de quem assinará o Termo de Referência', input: 'textarea', fullWidth: true },
    ],
  },
];

const form = reactive({});
const fieldOptions = reactive({});
const FIELD_PRESETS = {
  solicitacao_destinatario_nome: ['João da Silva', 'Maria Oliveira'],
  solicitacao_responsavel_nome: ['Ana Souza', 'Carlos Pereira'],
  dfd_setor: ['Secretaria de Administração', 'Secretaria de Saúde'],
  dfd_responsavel: ['Coordenadoria de Compras', 'Diretoria Administrativa'],
  dfd_email: ['compras@prefeitura.gov.br', 'licitacao@prefeitura.gov.br'],
  dfd_gestor: ['Mariana Costa', 'Rafael Mendes'],
  dfd_fiscal: ['Patrícia Lima', 'Bruno Almeida'],
  tr_endereco: ['Rua Principal, 123 - Centro', 'Av. Brasil, 450 - Setor Administrativo'],
  tr_email: ['propostas@prefeitura.gov.br', 'licitacao@prefeitura.gov.br'],
  tr_nome_assinante: ['Secretário(a) Municipal', 'Diretor(a) Administrativo(a)'],
};

function addFieldOption(fieldId) {
  const value = String(form[fieldId] || '').trim();
  if (!value) return;
  if (!Array.isArray(fieldOptions[fieldId])) fieldOptions[fieldId] = [];
  if (!fieldOptions[fieldId].includes(value)) {
    fieldOptions[fieldId] = [...fieldOptions[fieldId], value];
  }
}

for (const section of sections) {
  for (const field of section.fields) {
    if (field.input === 'heading') continue;
    form[field.id] = field.input === 'checkbox' ? false : '';
    if (field.input === 'text' || field.input === 'email' || field.input === 'datalist') {
      const base = FIELD_PRESETS[field.id] || [];
      fieldOptions[field.id] = [...base];
    }
  }
}
</script>

<style scoped>
.slots-preview {
  max-width: 1320px;
  margin: 0 auto;
  padding: 14px;
}
.slots-preview__header {
  margin-bottom: 8px;
}
.slots-preview__title {
  margin: 0 0 2px;
  font-size: 20px;
}
.slots-preview__subtitle {
  margin: 0;
  font-size: 12px;
  color: var(--color-text-soft);
}
.slots-preview__layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 14px;
  min-height: 72vh;
}
.slots-preview__generator,
.slots-preview__card {
  padding: 12px 14px;
  height: 72vh;
  max-height: 72vh;
  overflow: hidden;
}
.slots-preview__generator-body,
.slots-preview__body {
  margin-top: 6px;
  overflow-y: auto;
  overflow-x: hidden;
  height: calc(100% - 64px);
  padding-right: 2px;
}
.slots-preview__section {
  margin-top: 8px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 8px;
  background: #fafbfd;
}
.slots-preview__section-title {
  margin: 0 0 6px;
  font-size: 13px;
}
.slots-preview__grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px 8px;
}
.slots-preview__field--full,
.slots-preview__subheading {
  grid-column: 1 / -1;
}
.slots-preview__subheading {
  margin: 4px 0 1px;
  font-size: 11px;
}
.slots-preview__field {
  margin: 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: stretch;
}
.slots-preview__field .gov-label {
  font-size: 11px;
  line-height: 1.2;
  margin-bottom: 3px;
}
.slots-preview__combo {
  display: flex;
  align-items: stretch;
  gap: 4px;
  min-width: 0;
}
.slots-preview__combo .gov-input {
  flex: 1;
  min-width: 0;
}
.slots-preview__combo .gov-btn {
  align-self: stretch;
}
.slots-preview__radios {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  font-size: 12px;
}
.slots-preview__actions {
  margin-top: 10px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.slots-preview__checkbox {
  display: inline-flex;
  gap: 6px;
  font-size: 11px;
  align-items: flex-start;
}
.slots-preview__required {
  color: #c62828;
  margin-left: 2px;
}
.slots-preview :deep(.gov-input),
.slots-preview :deep(.gov-textarea) {
  font-size: 12px;
  padding: 6px 8px;
  min-width: 0;
}
.slots-preview :deep(.gov-btn) {
  padding: 5px 8px;
  font-size: 11px;
}
@media (max-width: 1120px) {
  .slots-preview__layout {
    grid-template-columns: 1fr;
    min-height: unset;
  }
  .slots-preview__generator,
  .slots-preview__card {
    height: auto;
    max-height: unset;
  }
  .slots-preview__generator-body,
  .slots-preview__body {
    height: auto;
    overflow: visible;
  }
}
</style>
