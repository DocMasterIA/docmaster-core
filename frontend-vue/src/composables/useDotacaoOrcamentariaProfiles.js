import { ref } from 'vue';
import {
  DOTACAO_ORCAMENTARIA_CATALOG_KEY,
  DOTACAO_PROFILES_FORM_KEY,
} from '@/constants/dotacaoOrcamentaria.js';

/** Estado partilhado entre dispensa, inexigibilidade e outros módulos. */
const profiles = ref([]);
const selectedProfileId = ref('');
const profileName = ref('');
const loading = ref(false);
let loadedForApiBase = '';

function normalizeProfile(p) {
  const name = String(p?.name ?? '').trim();
  const texto = String(p?.texto ?? p?.text ?? p?.value ?? '').trim();
  const id = String(p?.id ?? '').trim() || crypto.randomUUID();
  if (!name && !texto) return null;
  return { id, name: name || 'Sem nome', texto };
}

async function persistProfiles(apiBase) {
  await fetch(`${apiBase}/api/slots/form-state/save`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({
      slot_package_key: DOTACAO_PROFILES_FORM_KEY,
      data: { profiles: profiles.value },
    }),
  });
}

async function upsertCatalogValue(apiBase, texto) {
  const value = String(texto || '').trim();
  if (!value) return;
  try {
    await fetch(`${apiBase}/api/slots/catalog/upsert`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        entries: [{ field_key: DOTACAO_ORCAMENTARIA_CATALOG_KEY, value }],
      }),
    });
  } catch {
    // silencioso
  }
}

/**
 * Perfis de dotação orçamentária (servidor + catálogo), reutilizáveis em todos os módulos TR/DFD.
 * @param {string} apiBase
 */
export function useDotacaoOrcamentariaProfiles(apiBase) {
  async function loadProfiles(force = false) {
    const base = String(apiBase || '').trim();
    if (!base) return;
    if (!force && loadedForApiBase === base) return;
    loading.value = true;
    try {
      const url = `${base}/api/slots/form-state?slot_package_key=${encodeURIComponent(DOTACAO_PROFILES_FORM_KEY)}`;
      const res = await fetch(url, { credentials: 'include' });
      if (res.ok) {
        const payload = await res.json().catch(() => ({}));
        const list = Array.isArray(payload?.data?.profiles) ? payload.data.profiles : [];
        profiles.value = list.map(normalizeProfile).filter(Boolean);
        loadedForApiBase = base;
      }
    } catch {
      profiles.value = [];
    } finally {
      loading.value = false;
    }
  }

  function loadProfile(profileId) {
    const id = String(profileId || '');
    selectedProfileId.value = id;
    const hit = profiles.value.find((p) => String(p.id) === id);
    if (!hit) return null;
    profileName.value = hit.name;
    return hit.texto;
  }

  function newProfile() {
    selectedProfileId.value = '';
    profileName.value = '';
  }

  /**
   * @param {string} texto — conteúdo actual do textarea
   * @returns {boolean}
   */
  async function saveProfile(texto) {
    const name = String(profileName.value || '').trim();
    const body = String(texto || '').trim();
    if (!name) return false;
    if (!body) return false;

    const data = { name, texto: body };
    const idx = profiles.value.findIndex((p) => String(p.id) === String(selectedProfileId.value || ''));
    if (idx >= 0) {
      profiles.value[idx] = { ...profiles.value[idx], ...data };
    } else {
      const id = crypto.randomUUID();
      profiles.value.push({ id, ...data });
      selectedProfileId.value = id;
    }
    await persistProfiles(apiBase);
    await upsertCatalogValue(apiBase, body);
    return true;
  }

  async function deleteProfile() {
    const id = String(selectedProfileId.value || '');
    if (!id) return false;
    profiles.value = profiles.value.filter((p) => String(p.id) !== id);
    selectedProfileId.value = '';
    profileName.value = '';
    await persistProfiles(apiBase);
    return true;
  }

  return {
    profiles,
    selectedProfileId,
    profileName,
    loading,
    loadProfiles,
    loadProfile,
    newProfile,
    saveProfile,
    deleteProfile,
    upsertCatalogValue,
  };
}
