import { computed, reactive, ref } from 'vue';
import {
  clearDeprecatedCargoPresetFields,
  TEXTO_PADRAO_ENDERECO_PROPOSTAS,
  TRATAMENTO_CARGO,
  TRATAMENTO_NOME,
} from '@/components/dispensa-art-75-ii/dispensaArt75iiShared.js';
import { normNomeTituloMultiline } from '@/utils/itemValorCampos.js';
import { emptyDa75DadosFixosPreset } from '@/utils/dadosFixosReset.js';
import { useOrgaoProfiles } from '@/composables/useOrgaoProfiles.js';

function normNomeTitulo(raw) {
  return normNomeTituloMultiline(raw);
}

export const GLOBAL_SLOT_FORM_PRESET_KEY = 'global_slots_preset_v1';

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
  'solicitacao_destinatario_tratamento_cargo',
  'solicitacao_responsavel_nome',
  'dfd_setor_requisitante',
  'dfd_responsavel_demanda',
  'dfd_email',
  'dfd_gestor_contratos',
  'dfd_fiscal_contratos',
  'dfd_assinatura_nome',
  'tr_endereco_entrega_propostas',
  'tr_email_recebimento_propostas',
  'tr_termo_responsavel_nome',
];

/**
 * @param {string} apiBase
 * @param {{ cabecalho: import('vue').Ref<string>; processoAtivo: import('vue').Ref<boolean>; processo: import('vue').Ref<string>; orgao: import('vue').Ref<string> }} parentRefs
 */
export function useDispensaArt75IIDadosFixos(apiBase, parentRefs) {
  const { cabecalho, processoAtivo, processo, orgao } = parentRefs;

  const slotFieldOptions = reactive({});
  const orgaoProfilesApi = useOrgaoProfiles(() => apiBase);

  const fixoTratNome = ref('');
  const fixoNome = ref('');
  const fixoTratCargo = ref('');
  const fixoCargo = ref('');
  const fixoResponsavel = ref('');
  const fixoSetor = ref('');
  const fixoDemanda = ref('');
  const fixoEmail = ref('');
  const fixoGestor = ref('');
  const fixoFiscal = ref('');
  const fixoAssinatura = ref('');
  const fixoEnderecoEntrega = ref(TEXTO_PADRAO_ENDERECO_PROPOSTAS);
  const fixoEmailPropostas = ref('');
  const fixoTrResponsavelNome = ref('');

  const tratamentoNome = TRATAMENTO_NOME;
  const tratamentoCargo = TRATAMENTO_CARGO;

  /** Perfis salvos + histórico do catálogo + valor atual (texto livre no campo principal). */
  const mergedOrgaoOptions = computed(() => {
    const profiles = orgaoProfilesApi.orgaoOptionsFromProfiles.value || [];
    const catalog = Array.isArray(slotFieldOptions.orgao) ? slotFieldOptions.orgao : [];
    const current = String(orgao.value || '').trim();
    return [...new Set(
      [...profiles, ...catalog, current]
        .map((x) => String(x || '').trim())
        .filter(Boolean),
    )];
  });

  function collectPresetPayload() {
    return clearDeprecatedCargoPresetFields({
      cabecalho_documento: cabecalho.value,
      processo_ativo: false,
      processo_numero: '',
      orgao: orgao.value,
      solicitacao_tratamento_nome: fixoTratNome.value,
      solicitacao_destinatario_tratamento_cargo: fixoTratCargo.value,
      solicitacao_destinatario_nome: fixoNome.value,
      solicitacao_destinatario_cargo: fixoCargo.value,
      solicitacao_responsavel_nome: fixoResponsavel.value,
      dfd_setor_requisitante: fixoSetor.value,
      dfd_responsavel_demanda: fixoDemanda.value,
      dfd_email: fixoEmail.value,
      dfd_gestor_contratos: fixoGestor.value,
      dfd_fiscal_contratos: fixoFiscal.value,
      dfd_assinatura_nome: fixoAssinatura.value,
      tr_endereco_entrega_propostas: fixoEnderecoEntrega.value,
      tr_email_recebimento_propostas: fixoEmailPropostas.value,
      tr_termo_responsavel_nome: fixoTrResponsavelNome.value,
    });
  }

  function applyPresetPayload(data) {
    if (!data || typeof data !== 'object') return;
    if ('cabecalho_documento' in data) cabecalho.value = String(data.cabecalho_documento || '');
    if ('orgao' in data) orgao.value = normNomeTitulo(data.orgao);
    if ('solicitacao_tratamento_nome' in data) fixoTratNome.value = String(data.solicitacao_tratamento_nome || '');
    if ('solicitacao_destinatario_tratamento_cargo' in data) {
      fixoTratCargo.value = String(data.solicitacao_destinatario_tratamento_cargo || '');
    } else if ('solicitacao_tratamento_cargo' in data) {
      fixoTratCargo.value = String(data.solicitacao_tratamento_cargo || '');
    } else if ('senhor_senhora_genero' in data) {
      fixoTratCargo.value = String(data.senhor_senhora_genero || '');
    }
    if ('solicitacao_destinatario_nome' in data) fixoNome.value = normNomeTitulo(data.solicitacao_destinatario_nome);
    if ('solicitacao_destinatario_cargo' in data) fixoCargo.value = normNomeTitulo(data.solicitacao_destinatario_cargo);
    if ('solicitacao_responsavel_nome' in data) fixoResponsavel.value = normNomeTitulo(data.solicitacao_responsavel_nome);
    if ('dfd_setor_requisitante' in data) fixoSetor.value = normNomeTitulo(data.dfd_setor_requisitante);
    if ('dfd_responsavel_demanda' in data) fixoDemanda.value = normNomeTitulo(data.dfd_responsavel_demanda);
    if ('dfd_email' in data) fixoEmail.value = String(data.dfd_email || '');
    if ('dfd_gestor_contratos' in data) fixoGestor.value = normNomeTitulo(data.dfd_gestor_contratos);
    if ('dfd_fiscal_contratos' in data) fixoFiscal.value = normNomeTitulo(data.dfd_fiscal_contratos);
    if ('dfd_assinatura_nome' in data) fixoAssinatura.value = normNomeTitulo(data.dfd_assinatura_nome);
    if ('tr_endereco_entrega_propostas' in data) {
      const endereco = String(data.tr_endereco_entrega_propostas || '').trim();
      fixoEnderecoEntrega.value = endereco || TEXTO_PADRAO_ENDERECO_PROPOSTAS;
    }
    if ('tr_email_recebimento_propostas' in data) {
      fixoEmailPropostas.value = String(data.tr_email_recebimento_propostas || '');
    }
    if ('tr_termo_responsavel_nome' in data) fixoTrResponsavelNome.value = normNomeTitulo(data.tr_termo_responsavel_nome);
  }

  function buildCatalogEntries() {
    const pairs = [
      ['cabecalho_documento', cabecalho.value],
      ['orgao', orgao.value],
      ['solicitacao_destinatario_nome', fixoNome.value],
      ['solicitacao_destinatario_cargo', fixoCargo.value],
      ['solicitacao_destinatario_tratamento_cargo', fixoTratCargo.value],
      ['solicitacao_responsavel_nome', fixoResponsavel.value],
      ['dfd_setor_requisitante', fixoSetor.value],
      ['dfd_responsavel_demanda', fixoDemanda.value],
      ['dfd_email', fixoEmail.value],
      ['dfd_gestor_contratos', fixoGestor.value],
      ['dfd_fiscal_contratos', fixoFiscal.value],
      ['dfd_assinatura_nome', fixoAssinatura.value],
      ['tr_endereco_entrega_propostas', fixoEnderecoEntrega.value],
      ['tr_email_recebimento_propostas', fixoEmailPropostas.value],
      ['tr_termo_responsavel_nome', fixoTrResponsavelNome.value],
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
      applyPresetPayload(clearDeprecatedCargoPresetFields(payload?.data || {}));
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

  function clearDadosFixosFields() {
    applyPresetPayload(emptyDa75DadosFixosPreset({ cabecalho: cabecalho.value, orgao: '' }));
  }

  function loadOrgaoProfile(profileId) {
    orgaoProfilesApi.loadOrgaoProfile(profileId, (data) => {
      applyPresetPayload(clearDeprecatedCargoPresetFields(data || {}));
    });
  }

  function newOrgaoProfile() {
    orgaoProfilesApi.newOrgaoProfile(clearDadosFixosFields);
  }

  async function saveOrgaoProfile() {
    const nameRaw = String(orgaoProfilesApi.orgaoProfileName.value || '').trim();
    if (!nameRaw) return false;
    const data = collectPresetPayload();
    data.orgao = nameRaw;
    const ok = await orgaoProfilesApi.saveOrgaoProfile(nameRaw, data);
    if (!ok) return false;
    const orgaoValue = String(data.orgao || '').trim();
    if (orgaoValue) {
      const current = Array.isArray(slotFieldOptions.orgao) ? slotFieldOptions.orgao : [];
      if (!current.includes(orgaoValue)) slotFieldOptions.orgao = [...current, orgaoValue];
      void persistSlotEntries([{ field_key: 'orgao', value: orgaoValue }]);
    }
    return true;
  }

  async function deleteOrgaoProfile() {
    await orgaoProfilesApi.deleteOrgaoProfile();
  }

  return reactive({
    processo,
    orgao,
    orgaoProfiles: orgaoProfilesApi.orgaoProfiles,
    selectedOrgaoProfileId: orgaoProfilesApi.selectedOrgaoProfileId,
    orgaoProfileName: orgaoProfilesApi.orgaoProfileName,
    mergedOrgaoOptions,
    slotFieldOptions,
    tratamentoNome,
    tratamentoCargo,
    fixoTratNome,
    fixoNome,
    fixoTratCargo,
    fixoCargo,
    fixoResponsavel,
    fixoSetor,
    fixoDemanda,
    fixoEmail,
    fixoGestor,
    fixoFiscal,
    fixoAssinatura,
    fixoEnderecoEntrega,
    fixoEmailPropostas,
    fixoTrResponsavelNome,
    loadSlotCatalogSuggestions,
    loadUserGlobalPreset,
    loadOrgaoProfiles: orgaoProfilesApi.loadOrgaoProfiles,
    saveUserGlobalPreset,
    addFieldHistory,
    removeFieldHistory,
    canDeleteFieldHistory,
    loadOrgaoProfile,
    newOrgaoProfile,
    clearDadosFixosFields,
    saveOrgaoProfile,
    deleteOrgaoProfile,
  });
}
