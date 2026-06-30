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
              <label :class="labelClass">Nome do cadastro</label>
              <input
                ref="profileNameInputRef"
                :value="profileName"
                :class="inputClass"
                placeholder="Ex.: Dotação Secretaria de Obras 2026"
                autocomplete="off"
                @input="onProfileNameInput"
              />
            </div>
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
          </div>
          <div :class="fieldClass">
            <label :class="labelClass">Dotação orçamentária</label>
            <textarea
              ref="dotacaoTextareaRef"
              v-model="dotacao"
              :class="textareaClass"
              :rows="isDa75 ? 4 : 3"
              :placeholder="placeholder"
            />
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
  /** false = preserva o texto multilinha (recomendado para dotação). */
  formatOnInput: { type: Boolean, default: false },
});

const dotacaoAtiva = defineModel('dotacaoAtiva', { type: Boolean, default: false });
const dotacao = defineModel('dotacao', { type: String, default: '' });

const {
  profiles,
  selectedProfileId,
  profileName,
  loadProfiles,
  profilePayload,
  newProfile,
  saveProfile,
  deleteProfile,
} = useDotacaoOrcamentariaProfiles(() => props.apiBase);

const saveMessage = ref('');
const profileNameInputRef = ref(null);
const dotacaoTextareaRef = ref(null);

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

function onProfileNameInput(event) {
  profileName.value = String(event?.target?.value ?? '');
}

function readProfileNameFromDom() {
  const el = profileNameInputRef.value;
  const dom = String(el?.value ?? '').trim();
  const state = String(profileName.value ?? '').trim();
  return dom || state;
}

function readDotacaoTexto() {
  const el = dotacaoTextareaRef.value;
  const dom = String(el?.value ?? '');
  const state = String(dotacao.value ?? '');
  const raw = (dom || state).trim();
  if (!raw) return '';
  return props.formatOnInput ? primeiraMaiuscula(raw).trim() : raw;
}

function syncDotacaoFromDom() {
  const texto = readDotacaoTexto();
  if (texto) dotacao.value = texto;
  return texto;
}

function applyProfileToFields(profileId, { forceText = false } = {}) {
  const payload = profilePayload(profileId);
  if (!payload) return false;
  selectedProfileId.value = String(profileId || '').trim();
  profileName.value = payload.name;
  const texto = String(payload.texto || '').trim();
  if (texto && (forceText || !String(dotacao.value || '').trim())) {
    dotacao.value = texto;
  }
  return Boolean(texto);
}

function syncSelectedProfileToDotacao({ forceText = false } = {}) {
  const id = String(selectedProfileId.value || '').trim();
  if (!id || !dotacaoAtiva.value) return;
  applyProfileToFields(id, { forceText });
}

async function onSelectProfile(id) {
  await loadProfiles();
  const applied = applyProfileToFields(id, { forceText: true });
  if (applied) {
    dotacaoAtiva.value = true;
    saveMessage.value = '';
  }
}

function onNewProfile() {
  newProfile();
  saveMessage.value = '';
}

async function onSaveProfile() {
  const name = readProfileNameFromDom();
  const texto = syncDotacaoFromDom();
  const result = await saveProfile(texto, { name });
  saveMessage.value = result.ok
    ? 'Dotação salva. Já pode reutilizar nos outros módulos.'
    : result.error || 'Não foi possível salvar o cadastro.';
}

async function onDeleteProfile() {
  await deleteProfile();
  saveMessage.value = '';
}

watch(dotacaoAtiva, async (active) => {
  if (!active) return;
  await loadProfiles();
  syncSelectedProfileToDotacao({ forceText: true });
});

watch(
  () => profiles.value,
  () => {
    syncSelectedProfileToDotacao();
  },
  { deep: true },
);

onMounted(async () => {
  await loadProfiles();
  syncSelectedProfileToDotacao({ forceText: true });
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
