import { computed, ref } from 'vue';
import { capitalizeNomeTituloPt } from '@/utils/itemValorCampos.js';
import {
  ORGAO_PROFILES_FORM_KEY,
  clearLegacyOrgaoProfilesLocalStorage,
} from '@/constants/orgaoProfiles.js';
import { resetOrgaoProfileSelection } from '@/utils/dadosFixosReset.js';

function normalizeProfile(p) {
  const trimmed = String(p?.name ?? '').trim();
  const name = trimmed ? capitalizeNomeTituloPt(trimmed) : '';
  const id = String(p?.id ?? '').trim() || String(Date.now());
  const data = p?.data && typeof p.data === 'object' ? p.data : {};
  if (!name) return null;
  return { id, name, data };
}

/**
 * Cadastros de órgão por usuário (API /api/slots/form-state), reutilizável em todos os módulos.
 * @param {import('vue').MaybeRefOrGetter<string>} apiBase
 */
export function useOrgaoProfiles(apiBase) {
  const baseRef = computed(() => {
    const raw = typeof apiBase === 'function' ? apiBase() : apiBase;
    return String(raw?.value ?? raw ?? '').trim();
  });

  const orgaoProfiles = ref([]);
  const selectedOrgaoProfileId = ref('');
  const orgaoProfileName = ref('');
  const loading = ref(false);
  let loaded = false;

  const orgaoOptionsFromProfiles = computed(() => {
    const values = orgaoProfiles.value
      .map((p) => String(p?.name || '').trim())
      .filter(Boolean);
    return [...new Set(values)];
  });
  const mergedOrgaoOptions = computed(() => orgaoOptionsFromProfiles.value);

  async function persistProfiles(list) {
    const base = baseRef.value;
    if (!base) return { ok: false, error: 'API indisponível' };
    try {
      const res = await fetch(`${base}/api/slots/form-state/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          slot_package_key: ORGAO_PROFILES_FORM_KEY,
          data: { profiles: list },
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        return { ok: false, error: body?.error || `Erro ao salvar (${res.status})` };
      }
      return { ok: true };
    } catch {
      return { ok: false, error: 'Falha de rede ao salvar cadastros de órgão.' };
    }
  }

  async function loadOrgaoProfiles(force = false) {
    const base = baseRef.value;
    if (!base) return;
    clearLegacyOrgaoProfilesLocalStorage();
    if (!force && loaded) return;
    loading.value = true;
    try {
      const url = `${base}/api/slots/form-state?slot_package_key=${encodeURIComponent(ORGAO_PROFILES_FORM_KEY)}`;
      const res = await fetch(url, { credentials: 'include' });
      if (res.ok) {
        const payload = await res.json().catch(() => ({}));
        const list = Array.isArray(payload?.data?.profiles) ? payload.data.profiles : [];
        orgaoProfiles.value = list.map(normalizeProfile).filter(Boolean);
        loaded = true;
      } else {
        orgaoProfiles.value = [];
      }
    } catch {
      orgaoProfiles.value = [];
    } finally {
      loading.value = false;
    }
  }

  function loadOrgaoProfile(profileId, applyPayload) {
    const id = String(profileId || '');
    selectedOrgaoProfileId.value = id;
    const hit = orgaoProfiles.value.find((p) => String(p.id) === id);
    if (!hit) return;
    const trimmed = String(hit.name || '').trim();
    orgaoProfileName.value = trimmed ? capitalizeNomeTituloPt(trimmed) : '';
    if (typeof applyPayload === 'function') {
      applyPayload(hit.data || {});
    }
  }

  function newOrgaoProfile(onClear) {
    resetOrgaoProfileSelection(selectedOrgaoProfileId, orgaoProfileName);
    if (typeof onClear === 'function') onClear();
  }

  /**
   * @param {string} name
   * @param {Record<string, unknown>} data
   * @returns {Promise<boolean>}
   */
  async function saveOrgaoProfile(name, data) {
    const trimmedName = String(name || '').trim();
    const profileName = trimmedName ? capitalizeNomeTituloPt(trimmedName) : '';
    if (!profileName) return false;
    orgaoProfileName.value = profileName;

    const list = [...orgaoProfiles.value];
    const idx = list.findIndex((p) => String(p.id) === String(selectedOrgaoProfileId.value || ''));
    if (idx >= 0) {
      list[idx] = { ...list[idx], name: profileName, data: { ...(data || {}) } };
    } else {
      const id = String(Date.now());
      list.push({ id, name: profileName, data: { ...(data || {}) } });
      selectedOrgaoProfileId.value = id;
    }
    orgaoProfiles.value = list;

    const persisted = await persistProfiles(list);
    return persisted.ok;
  }

  async function deleteOrgaoProfile() {
    const id = String(selectedOrgaoProfileId.value || '').trim();
    if (!id) return;
    const list = orgaoProfiles.value.filter((p) => String(p.id) !== id);
    orgaoProfiles.value = list;
    resetOrgaoProfileSelection(selectedOrgaoProfileId, orgaoProfileName);
    await persistProfiles(list);
  }

  return {
    orgaoProfiles,
    selectedOrgaoProfileId,
    orgaoProfileName,
    mergedOrgaoOptions,
    orgaoOptionsFromProfiles,
    loading,
    loadOrgaoProfiles,
    loadOrgaoProfile,
    newOrgaoProfile,
    saveOrgaoProfile,
    deleteOrgaoProfile,
    clearLegacyOrgaoProfilesLocalStorage,
  };
}
