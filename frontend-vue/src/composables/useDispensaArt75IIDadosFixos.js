import { computed, reactive, ref } from 'vue';
import {
  TEXTO_PADRAO_ENDERECO_PROPOSTAS,
  TRATAMENTO_CARGO,
  TRATAMENTO_NOME,
} from '@/components/dispensa-art-75-ii/dispensaArt75iiShared.js';
import { capitalizeFirstSignificantLetter } from '@/utils/itemValorCampos.js';

export const GLOBAL_SLOT_FORM_PRESET_KEY = 'global_slots_preset_v1';
const ORGAO_PROFILES_STORAGE_KEY = 'orgao_profiles_v1';

function catalogItemToString(x) {
  if (x == null) return '';
  if (typeof x === 'string') return x.trim();
  if (typeof x === 'number' || typeof x === 'boolean') return String(x).trim();
  if (typeof x === 'object') {
    if (x.value != null && typeof x.value !== 'object') return String(x.value).trim();
    if (typeof x.label === 'string') return x.label.trim();
  }
  return '';
}

/** Mesmas chaves do catálogo usadas em dispensa normal + campos do TR (Art. 75 II). */
export const DA75_FIXOS_CATALOG_KEYS = [
  'cabecalho_documento',
  'orgao',
  'solicitacao_destinatario_nome',
  'solicitacao_destinatario_cargo',
  'solicitacao_responsavel_nome',
  'solicitacao_responsavel_cargo',
  'dfd_setor_requisitante',
  'dfd_responsavel_demanda',
  'dfd_email',
  'dfd_gestor_contratos',
  'dfd_fiscal_contratos',
  'dfd_assinatura_nome',
  'dfd_assinatura_cargo',
  'tr_endereco_entrega_propostas',
  'tr_email_recebimento_propostas',
  'tr_termo_responsavel_nome',
  'tr_termo_responsavel_cargo',
];

/**
 * @param {string} apiBase
 * @param {{ cabecalho: import('vue').Ref<string>; processoAtivo: import('vue').Ref<boolean>; processo: import('vue').Ref<string>; orgao: import('vue').Ref<string> }} parentRefs
 */
export function useDispensaArt75IIDadosFixos(apiBase, parentRefs) {
  const { cabecalho, processoAtivo, processo, orgao } = parentRefs;

  const slotFieldOptions = reactive({});
  const orgaoProfiles = ref([]);
  const selectedOrgaoProfileId = ref('');
  const orgaoProfileName = ref('');
  const orgaoOptionsFromProfiles = computed(() => {
    const values = orgaoProfiles.value
      .map((p) => String(p?.name || '').trim())
      .filter(Boolean);
    return [...new Set(values)];
  });
  const mergedOrgaoOptions = computed(() => orgaoOptionsFromProfiles.value);

  const fixoTratNome = ref('');
  const fixoNome = ref('');
  const fixoTratCargo = ref('');
  const fixoCargo = ref('');
  const fixoResponsavel = ref('');
  const fixoResponsavelCargo = ref('');
  const fixoSetor = ref('');
  const fixoDemanda = ref('');
  const fixoEmail = ref('');
  const fixoGestor = ref('');
  const fixoFiscal = ref('');
  const fixoAssinatura = ref('');
  const fixoAssinaturaCargo = ref('');
  const fixoEnderecoEntrega = ref(TEXTO_PADRAO_ENDERECO_PROPOSTAS);
  const fixoEmailPropostas = ref('');
  const fixoTrResponsavelNome = ref('');
  const fixoTrResponsavelCargo = ref('');

  const tratamentoNome = TRATAMENTO_NOME;
  const tratamentoCargo = TRATAMENTO_CARGO;

  function collectPresetPayload() {
    return {
      cabecalho_documento: cabecalho.value,
      // Processo (opcional) não entra no preset/perfil — só limpa merge antigo no servidor.
      processo_ativo: false,
      processo_numero: '',
      orgao: orgao.value,
      solicitacao_tratamento_nome: fixoTratNome.value,
      solicitacao_tratamento_cargo: fixoTratCargo.value,
      solicitacao_destinatario_nome: fixoNome.value,
      solicitacao_destinatario_cargo: fixoCargo.value,
      solicitacao_responsavel_nome: fixoResponsavel.value,
      solicitacao_responsavel_cargo: fixoResponsavelCargo.value,
      dfd_setor_requisitante: fixoSetor.value,
      dfd_responsavel_demanda: fixoDemanda.value,
      dfd_email: fixoEmail.value,
      dfd_gestor_contratos: fixoGestor.value,
      dfd_fiscal_contratos: fixoFiscal.value,
      dfd_assinatura_nome: fixoAssinatura.value,
      dfd_assinatura_cargo: fixoAssinaturaCargo.value,
      tr_endereco_entrega_propostas: fixoEnderecoEntrega.value,
      tr_email_recebimento_propostas: fixoEmailPropostas.value,
      tr_termo_responsavel_nome: fixoTrResponsavelNome.value,
      tr_termo_responsavel_cargo: fixoTrResponsavelCargo.value,
    };
  }

  function applyPresetPayload(data) {
    if (!data || typeof data !== 'object') return;
    if ('cabecalho_documento' in data) cabecalho.value = String(data.cabecalho_documento || '');
    if ('orgao' in data) orgao.value = String(data.orgao || '');
    if ('solicitacao_tratamento_nome' in data) fixoTratNome.value = String(data.solicitacao_tratamento_nome || '');
    if ('solicitacao_tratamento_cargo' in data) fixoTratCargo.value = String(data.solicitacao_tratamento_cargo || '');
    if ('solicitacao_destinatario_nome' in data) fixoNome.value = String(data.solicitacao_destinatario_nome || '');
    if ('solicitacao_destinatario_cargo' in data) fixoCargo.value = String(data.solicitacao_destinatario_cargo || '');
    if ('solicitacao_responsavel_nome' in data) fixoResponsavel.value = String(data.solicitacao_responsavel_nome || '');
    if ('solicitacao_responsavel_cargo' in data) fixoResponsavelCargo.value = String(data.solicitacao_responsavel_cargo || '');
    if ('dfd_setor_requisitante' in data) fixoSetor.value = String(data.dfd_setor_requisitante || '');
    if ('dfd_responsavel_demanda' in data) fixoDemanda.value = String(data.dfd_responsavel_demanda || '');
    if ('dfd_email' in data) fixoEmail.value = String(data.dfd_email || '');
    if ('dfd_gestor_contratos' in data) fixoGestor.value = String(data.dfd_gestor_contratos || '');
    if ('dfd_fiscal_contratos' in data) fixoFiscal.value = String(data.dfd_fiscal_contratos || '');
    if ('dfd_assinatura_nome' in data) fixoAssinatura.value = String(data.dfd_assinatura_nome || '');
    if ('dfd_assinatura_cargo' in data) fixoAssinaturaCargo.value = String(data.dfd_assinatura_cargo || '');
    if ('tr_endereco_entrega_propostas' in data) {
      fixoEnderecoEntrega.value = String(data.tr_endereco_entrega_propostas || '');
    }
    if ('tr_email_recebimento_propostas' in data) {
      fixoEmailPropostas.value = String(data.tr_email_recebimento_propostas || '');
    }
    if ('tr_termo_responsavel_nome' in data) fixoTrResponsavelNome.value = String(data.tr_termo_responsavel_nome || '');
    if ('tr_termo_responsavel_cargo' in data) {
      fixoTrResponsavelCargo.value = String(data.tr_termo_responsavel_cargo || '');
    }
  }

  function buildCatalogEntries() {
    const pairs = [
      ['cabecalho_documento', cabecalho.value],
      ['orgao', orgao.value],
      ['solicitacao_destinatario_nome', fixoNome.value],
      ['solicitacao_destinatario_cargo', fixoCargo.value],
      ['solicitacao_responsavel_nome', fixoResponsavel.value],
      ['solicitacao_responsavel_cargo', fixoResponsavelCargo.value],
      ['dfd_setor_requisitante', fixoSetor.value],
      ['dfd_responsavel_demanda', fixoDemanda.value],
      ['dfd_email', fixoEmail.value],
      ['dfd_gestor_contratos', fixoGestor.value],
      ['dfd_fiscal_contratos', fixoFiscal.value],
      ['dfd_assinatura_nome', fixoAssinatura.value],
      ['dfd_assinatura_cargo', fixoAssinaturaCargo.value],
      ['tr_endereco_entrega_propostas', fixoEnderecoEntrega.value],
      ['tr_email_recebimento_propostas', fixoEmailPropostas.value],
      ['tr_termo_responsavel_nome', fixoTrResponsavelNome.value],
      ['tr_termo_responsavel_cargo', fixoTrResponsavelCargo.value],
    ];
    return pairs
      .map(([field_key, value]) => ({ field_key, value: String(value || '').trim() }))
      .filter((e) => e.value);
  }

  async function persistSlotEntries(entries) {
    if (!Array.isArray(entries) || entries.length === 0) return;
    try {
      await fetch(`${apiBase}/api/slots/catalog/upsert`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ entries }),
      });
    } catch {
      // silencioso
    }
  }

  async function removeCatalogEntry(fieldKey, value) {
    const v = String(value || '').trim();
    if (!v) return;
    try {
      await fetch(`${apiBase}/api/slots/catalog/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ field_key: fieldKey, value: v }),
      });
    } catch {
      // silencioso
    }
  }

  async function addFieldHistory(fieldKey, rawValue) {
    const value = String(rawValue || '').trim();
    if (!value) return;
    const current = Array.isArray(slotFieldOptions[fieldKey]) ? slotFieldOptions[fieldKey] : [];
    if (!current.includes(value)) slotFieldOptions[fieldKey] = [...current, value];
    await persistSlotEntries([{ field_key: fieldKey, value }]);
  }

  function canDeleteFieldHistory(fieldKey, rawValue) {
    const value = String(rawValue || '').trim();
    if (!value) return false;
    const current = Array.isArray(slotFieldOptions[fieldKey]) ? slotFieldOptions[fieldKey] : [];
    return current.includes(value);
  }

  async function removeFieldHistory(fieldKey, rawValue) {
    const value = String(rawValue || '').trim();
    if (!value) return;
    const current = Array.isArray(slotFieldOptions[fieldKey]) ? slotFieldOptions[fieldKey] : [];
    slotFieldOptions[fieldKey] = current.filter((x) => x !== value);
    await removeCatalogEntry(fieldKey, value);
  }

  async function loadSlotCatalogSuggestions() {
    try {
      const url = `${apiBase}/api/slots/catalog/batch?fields=${encodeURIComponent(DA75_FIXOS_CATALOG_KEYS.join(','))}&limit=25`;
      const res = await fetch(url, { credentials: 'include' });
      if (!res.ok) return;
      const payload = await res.json().catch(() => ({}));
      const map = payload?.items || {};
      DA75_FIXOS_CATALOG_KEYS.forEach((key) => {
        const incoming = Array.isArray(map[key]) ? map[key] : [];
        slotFieldOptions[key] = [...new Set(incoming.map(catalogItemToString).filter(Boolean))];
      });
    } catch {
      // silencioso
    }
  }

  async function loadUserGlobalPreset() {
    try {
      const url = `${apiBase}/api/slots/form-state?slot_package_key=${encodeURIComponent(GLOBAL_SLOT_FORM_PRESET_KEY)}`;
      const res = await fetch(url, { credentials: 'include' });
      if (!res.ok) return;
      const payload = await res.json().catch(() => ({}));
      applyPresetPayload(payload?.data || {});
    } catch {
      // silencioso
    }
  }

  async function saveUserGlobalPreset() {
    try {
      await fetch(`${apiBase}/api/slots/form-state/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          slot_package_key: GLOBAL_SLOT_FORM_PRESET_KEY,
          data: collectPresetPayload(),
        }),
      });
      await persistSlotEntries(buildCatalogEntries());
    } catch {
      // silencioso
    }
  }

  function loadOrgaoProfiles() {
    try {
      const raw = localStorage.getItem(ORGAO_PROFILES_STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      const list = Array.isArray(parsed) ? parsed : [];
      let dirty = false;
      orgaoProfiles.value = list.map((p) => {
        const trimmed = String(p?.name ?? '').trim();
        const n = trimmed ? capitalizeFirstSignificantLetter(trimmed) : '';
        if (n !== trimmed) dirty = true;
        return { ...p, name: n };
      });
      if (dirty) persistOrgaoProfiles();
    } catch {
      orgaoProfiles.value = [];
    }
  }

  function persistOrgaoProfiles() {
    try {
      localStorage.setItem(ORGAO_PROFILES_STORAGE_KEY, JSON.stringify(orgaoProfiles.value));
    } catch {
      // silencioso
    }
  }

  function createOrgaoProfilePayload() {
    return collectPresetPayload();
  }

  function loadOrgaoProfile(profileId) {
    const id = String(profileId || '');
    selectedOrgaoProfileId.value = id;
    const hit = orgaoProfiles.value.find((p) => String(p.id) === id);
    if (!hit) return;
    const trimmed = String(hit.name || '').trim();
    orgaoProfileName.value = trimmed ? capitalizeFirstSignificantLetter(trimmed) : '';
    applyPresetPayload(hit.data || {});
  }

  function newOrgaoProfile() {
    selectedOrgaoProfileId.value = '';
    orgaoProfileName.value = '';
  }

  function saveOrgaoProfile() {
    const nameRaw = String(orgaoProfileName.value || '').trim();
    const name = nameRaw ? capitalizeFirstSignificantLetter(nameRaw) : '';
    if (!name) return false;
    orgaoProfileName.value = name;
    const data = createOrgaoProfilePayload();
    data.orgao = name;
    const orgaoValue = String(data?.orgao || '').trim();
    const existingIdx = orgaoProfiles.value.findIndex((p) => String(p.id) === String(selectedOrgaoProfileId.value || ''));
    if (existingIdx >= 0) {
      orgaoProfiles.value[existingIdx] = {
        ...orgaoProfiles.value[existingIdx],
        name,
        data,
      };
    } else {
      const id = String(Date.now());
      orgaoProfiles.value.push({ id, name, data });
      selectedOrgaoProfileId.value = id;
    }
    persistOrgaoProfiles();
    if (orgaoValue) {
      const current = Array.isArray(slotFieldOptions.orgao) ? slotFieldOptions.orgao : [];
      if (!current.includes(orgaoValue)) slotFieldOptions.orgao = [...current, orgaoValue];
      void persistSlotEntries([{ field_key: 'orgao', value: orgaoValue }]);
    }
    return true;
  }

  function deleteOrgaoProfile() {
    const id = String(selectedOrgaoProfileId.value || '');
    if (!id) return;
    orgaoProfiles.value = orgaoProfiles.value.filter((p) => String(p.id) !== id);
    persistOrgaoProfiles();
    selectedOrgaoProfileId.value = '';
    orgaoProfileName.value = '';
  }

  loadOrgaoProfiles();

  // `reactive` para refs aninhadas serem desempacotadas em templates (ex.: drawer com `:ctx="dadosFixos"`).
  // Sem isso, `v-model="ctx.fixoNome"` recebe o objeto Ref e o input mostra "[object Object]".
  return reactive({
    processo,
    orgao,
    orgaoProfiles,
    selectedOrgaoProfileId,
    orgaoProfileName,
    mergedOrgaoOptions,
    slotFieldOptions,
    tratamentoNome,
    tratamentoCargo,
    fixoTratNome,
    fixoNome,
    fixoTratCargo,
    fixoCargo,
    fixoResponsavel,
    fixoResponsavelCargo,
    fixoSetor,
    fixoDemanda,
    fixoEmail,
    fixoGestor,
    fixoFiscal,
    fixoAssinatura,
    fixoAssinaturaCargo,
    fixoEnderecoEntrega,
    fixoEmailPropostas,
    fixoTrResponsavelNome,
    fixoTrResponsavelCargo,
    loadSlotCatalogSuggestions,
    loadUserGlobalPreset,
    saveUserGlobalPreset,
    addFieldHistory,
    removeFieldHistory,
    canDeleteFieldHistory,
    loadOrgaoProfile,
    newOrgaoProfile,
    saveOrgaoProfile,
    deleteOrgaoProfile,
  });
}
