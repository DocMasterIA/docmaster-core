<template>
  <component :is="wrapperTag" :class="rootClass">
    <h3 v-if="showTitle">Dotação orçamentária</h3>
    <div :class="bodyClass">
      <label :class="checkClass">
        <input v-model="dotacaoAtiva" type="checkbox" />
        Informar dotação orçamentária (opcional)
      </label>

      <template v-if="dotacaoAtiva">
        <div :class="profilesClass">
          <p v-if="isDa75" class="da75-subblock-title">Cadastros salvos</p>
          <div :class="profilesFieldsClass">
            <div :class="fieldClass">
              <label :class="labelClass">Dotação salva</label>
              <select
                :class="selectClass"
                :value="selectedProfileId"
                @change="onSelectProfile($event.target.value)"
              >
                <option value="">Selecione uma dotação salva</option>
                <option v-for="p in profiles" :key="p.id" :value="p.id">{{ p.name }}</option>
              </select>
            </div>
            <div :class="fieldClass">
              <label :class="labelClass">Nome do cadastro</label>
              <input
                v-model="profileName"
                :class="inputClass"
                placeholder="Ex.: Dotação Secretaria de Obras 2026"
              />
            </div>
          </div>
          <div :class="actionsClass">
            <button type="button" :class="btnNewClass" @click="onNewProfile">Novo cadastro</button>
            <button type="button" :class="btnSaveClass" @click="onSaveProfile">Salvar dotação</button>
            <button
              type="button"
              :class="btnDeleteClass"
              :disabled="!selectedProfileId"
              @click="onDeleteProfile"
            >
              Excluir cadastro
            </button>
          </div>
          <p v-if="saveHint" :class="hintClass">{{ saveHint }}</p>
        </div>

        <div :class="fieldClass">
          <label :class="labelClass">Dotação orçamentária</label>
          <textarea
            :class="textareaClass"
            :value="dotacao"
            :rows="isDa75 ? 4 : 3"
            :placeholder="placeholder"
            @input="onDotacaoInput($event)"
          />
        </div>
      </template>
    </div>
  </component>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useDotacaoOrcamentariaProfiles } from '@/composables/useDotacaoOrcamentariaProfiles.js';
import { PLACEHOLDER_DOTACAO } from '@/constants/dotacaoOrcamentaria.js';
import { primeiraMaiuscula } from '@/components/dispensa-art-75-ii/dispensaArt75iiShared.js';

const props = defineProps({
  apiBase: { type: String, required: true },
  /** da75 | ixp | fe */
  variant: { type: String, default: 'da75' },
  /** section (dispensa) ou article (inex) */
  wrapper: { type: String, default: 'section' },
  showTitle: { type: Boolean, default: true },
  placeholder: { type: String, default: PLACEHOLDER_DOTACAO },
  formatOnInput: { type: Boolean, default: true },
});

const dotacaoAtiva = defineModel('dotacaoAtiva', { type: Boolean, default: false });
const dotacao = defineModel('dotacao', { type: String, default: '' });

const {
  profiles,
  selectedProfileId,
  profileName,
  loadProfiles,
  loadProfile,
  newProfile,
  saveProfile,
  deleteProfile,
} = useDotacaoOrcamentariaProfiles(props.apiBase);

const saveMessage = ref('');

const saveHint = computed(() => {
  if (saveMessage.value) return saveMessage.value;
  if (!dotacaoAtiva.value) return '';
  return 'As dotações salvas ficam disponíveis em dispensa, inexigibilidade e demais módulos que usam este campo.';
});

const isDa75 = computed(() => props.variant === 'da75');

const wrapperTag = computed(() => (props.wrapper === 'article' ? 'article' : 'section'));

const rootClass = computed(() => {
  if (props.variant === 'ixp') return 'ixp-card';
  if (props.variant === 'fe') return 'fe-card';
  return 'da75-block';
});

const bodyClass = computed(() => {
  if (props.variant === 'ixp') return 'ixp-body';
  if (props.variant === 'fe') return 'fe-body';
  return 'da75-block__body da75-stack';
});

const checkClass = computed(() => {
  if (props.variant === 'ixp') return 'ixp-check';
  if (props.variant === 'fe') return 'fe-check';
  return 'da75-check';
});

const fieldClass = computed(() => {
  if (props.variant === 'ixp') return 'ixp-field';
  if (props.variant === 'fe') return 'fe-field';
  return 'da75-field';
});

const labelClass = computed(() => {
  if (props.variant === 'da75') return 'da75-label';
  return '';
});

const selectClass = computed(() => {
  if (props.variant === 'da75') return 'da75-select da75-select--sm';
  return '';
});

const inputClass = computed(() => {
  if (props.variant === 'da75') return 'da75-input da75-input--sm';
  return '';
});

const textareaClass = computed(() => (props.variant === 'da75' ? 'da75-textarea' : ''));

const profilesClass = computed(() => {
  if (props.variant === 'da75') return 'da75-dotacao-catalog';
  return 'dotacao-profiles';
});

const profilesFieldsClass = computed(() => (props.variant === 'da75' ? 'da75-stack' : 'dotacao-profiles-fields'));

const actionsClass = computed(() => {
  if (props.variant === 'ixp') return 'ixp-inline-actions ixp-orgao-profile-actions';
  if (props.variant === 'fe') return 'fe-inline-actions dotacao-profile-actions';
  return 'da75-dotacao-catalog__actions';
});

const btnNewClass = computed(() => {
  if (props.variant === 'ixp') return 'ixp-btn-secondary ixp-btn-xs';
  if (props.variant === 'fe') return 'fe-btn-secondary fe-btn-xs';
  return 'da75-btn da75-btn--xs';
});

const btnSaveClass = computed(() => {
  if (props.variant === 'ixp') return 'ixp-btn-secondary ixp-btn-xs ixp-orgao-btn-save';
  if (props.variant === 'fe') return 'fe-btn-secondary fe-btn-xs';
  return 'da75-btn da75-btn--xs da75-btn--primary';
});

const btnDeleteClass = computed(() => {
  if (props.variant === 'ixp') return 'ixp-btn-secondary ixp-btn-xs ixp-orgao-btn-delete';
  if (props.variant === 'fe') return 'fe-btn-secondary fe-btn-xs';
  return 'da75-btn da75-btn--xs da75-btn--danger';
});

const hintClass = computed(() => {
  if (props.variant === 'da75') return 'da75-helper da75-dotacao-catalog__hint';
  return 'gov-text-soft';
});

function onDotacaoInput(event) {
  const raw = String(event?.target?.value ?? '');
  dotacao.value = props.formatOnInput ? primeiraMaiuscula(raw) : raw;
}

function onSelectProfile(id) {
  const texto = loadProfile(id);
  if (texto != null) {
    dotacaoAtiva.value = true;
    dotacao.value = texto;
    saveMessage.value = '';
  }
}

function onNewProfile() {
  newProfile();
  saveMessage.value = '';
}

async function onSaveProfile() {
  const ok = await saveProfile(dotacao.value);
  saveMessage.value = ok
    ? 'Dotação salva. Já pode reutilizar nos outros módulos.'
    : 'Informe o nome do cadastro e o texto da dotação antes de salvar.';
}

async function onDeleteProfile() {
  await deleteProfile();
  saveMessage.value = '';
}

watch(dotacaoAtiva, (v) => {
  if (!v) dotacao.value = '';
});

onMounted(() => {
  loadProfiles();
});
</script>

<style scoped>
.dotacao-profiles,
.dotacao-profiles-fields {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  margin-top: 0.75rem;
}

.dotacao-profile-actions,
.fe-inline-actions.dotacao-profile-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}
</style>
