import { reactive, ref } from 'vue';
import {
  TEXTO_PADRAO_ENDERECO_PROPOSTAS,
  TRATAMENTO_CARGO,
  TRATAMENTO_NOME,
} from '@/components/dispensa-art-75-ii/dispensaArt75iiShared.js';

export const GLOBAL_SLOT_FORM_PRESET_KEY = 'global_slots_preset_v1';

/** Mesmas chaves do catálogo usadas em dispensa normal + campos do TR (Art. 75 II). */
export const DA75_FIXOS_CATALOG_KEYS = [
  'cabecalho_documento',
  'processo_numero',
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
      processo_ativo: !!processoAtivo.value,
      processo_numero: processo.value,
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
    if ('processo_ativo' in data) processoAtivo.value = !!data.processo_ativo;
    if ('processo_numero' in data) processo.value = String(data.processo_numero || '');
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
      ['processo_numero', processo.value],
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
        slotFieldOptions[key] = [...new Set(incoming.map((x) => String(x || '').trim()).filter(Boolean))];
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

  return {
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
  };
}
