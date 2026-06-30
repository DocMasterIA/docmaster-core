import { computed, ref } from 'vue';
import {
  DOTACAO_ORCAMENTARIA_CATALOG_KEY,
  DOTACAO_PROFILES_FORM_KEY,
} from '@/constants/dotacaoOrcamentaria.js';

const SESSION_USER_KEY = 'docmaster.session_user_v1';

/** Perfis em memória — chave `${apiBase}::${userId}` (nunca só apiBase). */
const profilesByCacheKey = ref({});

function readSessionUserId() {
  try {
    const raw = sessionStorage.getItem(SESSION_USER_KEY);
    if (!raw) return '';
    const parsed = JSON.parse(raw);
    return String(parsed?.data?.id ?? '').trim();
  } catch {
    return '';
  }
}

function profilesCacheKey(apiBase, userId = '') {
  const base = String(apiBase || '').trim();
  if (!base) return '';
  const uid = String(userId || readSessionUserId() || '').trim() || 'anonymous';
  return `${base}::${uid}`;
}

/** Limpa cache ao trocar de usuário (logout / login). */
export function clearDotacaoOrcamentariaProfilesCache() {
  profilesByCacheKey.value = {};
  loadedCacheKeys.clear();
}

function normalizeProfile(p) {
  const name = String(p?.name ?? '').trim();
  const texto = String(p?.texto ?? p?.text ?? p?.value ?? '').trim();
  const id = String(p?.id ?? '').trim() || crypto.randomUUID();
  if (!name && !texto) return null;
  return { id, name: name || 'Sem nome', texto };
}

function profilesForCacheKey(cacheKey) {
  const key = String(cacheKey || '').trim();
  if (!key) return [];
  const bucket = profilesByCacheKey.value[key];
  return Array.isArray(bucket) ? bucket : [];
}

function setProfilesForCacheKey(cacheKey, list) {
  const key = String(cacheKey || '').trim();
  if (!key) return;
  profilesByCacheKey.value = {
    ...profilesByCacheKey.value,
    [key]: list,
  };
}

async function persistProfiles(apiBase, profiles) {
  const base = String(apiBase || '').trim();
  if (!base) return { ok: false, error: 'API indisponível' };
  try {
    const res = await fetch(`${base}/api/slots/form-state/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        slot_package_key: DOTACAO_PROFILES_FORM_KEY,
        data: { profiles },
      }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return { ok: false, error: body?.error || `Erro ao salvar (${res.status})` };
    }
    return { ok: true };
  } catch {
    return { ok: false, error: 'Falha de rede ao salvar o cadastro.' };
  }
}

async function upsertCatalogValue(apiBase, texto) {
  const value = String(texto || '').trim();
  if (!value) return;
  const base = String(apiBase || '').trim();
  if (!base) return;
  try {
    await fetch(`${base}/api/slots/catalog/upsert`, {
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

const loadedCacheKeys = new Set();

/**
 * Perfis de dotação orçamentária (servidor + catálogo), reutilizáveis em todos os módulos TR/DFD.
 * Estado de edição (nome selecionado, id) é por instância do componente.
 * @param {import('vue').MaybeRefOrGetter<string>} apiBase
 */
export function useDotacaoOrcamentariaProfiles(apiBase) {
  const baseRef = computed(() => {
    const raw = typeof apiBase === 'function' ? apiBase() : apiBase;
    return String(raw?.value ?? raw ?? '').trim();
  });

  const cacheKeyRef = computed(() => profilesCacheKey(baseRef.value));

  const profiles = computed(() => profilesForCacheKey(cacheKeyRef.value));
  const selectedProfileId = ref('');
  const profileName = ref('');
  const loading = ref(false);

  async function loadProfiles(force = false) {
    const base = baseRef.value;
    const cacheKey = cacheKeyRef.value;
    if (!base || !cacheKey) return;
    if (!force && loadedCacheKeys.has(cacheKey)) return;
    loading.value = true;
    try {
      const url = `${base}/api/slots/form-state?slot_package_key=${encodeURIComponent(DOTACAO_PROFILES_FORM_KEY)}`;
      const res = await fetch(url, { credentials: 'include' });
      if (res.ok) {
        const payload = await res.json().catch(() => ({}));
        const list = Array.isArray(payload?.data?.profiles) ? payload.data.profiles : [];
        setProfilesForCacheKey(cacheKey, list.map(normalizeProfile).filter(Boolean));
        loadedCacheKeys.add(cacheKey);
      }
    } catch {
      setProfilesForCacheKey(cacheKey, []);
    } finally {
      loading.value = false;
    }
  }

  function findProfile(profileId) {
    const id = String(profileId || '').trim();
    if (!id) return null;
    return profiles.value.find((p) => String(p.id) === id) || null;
  }

  /** @returns {{ name: string, texto: string } | null} */
  function profilePayload(profileId) {
    const hit = findProfile(profileId);
    if (!hit) return null;
    return { name: hit.name, texto: hit.texto };
  }

  function loadProfile(profileId) {
    const id = String(profileId || '').trim();
    selectedProfileId.value = id;
    if (!id) {
      profileName.value = '';
      return null;
    }
    const payload = profilePayload(id);
    if (!payload) {
      profileName.value = '';
      return null;
    }
    profileName.value = payload.name;
    return payload.texto;
  }

  function newProfile() {
    selectedProfileId.value = '';
    profileName.value = '';
  }

  /**
   * @param {string} texto — conteúdo do textarea
   * @param {{ name?: string }} [opts]
   * @returns {Promise<{ ok: boolean, error?: string, field?: 'name' | 'texto' }>}
   */
  async function saveProfile(texto, opts = {}) {
    const base = baseRef.value;
    const name = String(opts.name ?? profileName.value ?? '').trim();
    const body = String(texto ?? '').trim();

    if (!name) {
      return { ok: false, field: 'name', error: 'Informe o nome do cadastro no campo «Nome do cadastro».' };
    }
    if (!body) {
      return {
        ok: false,
        field: 'texto',
        error: 'Informe o texto da dotação no campo «Dotação orçamentária».',
      };
    }

    profileName.value = name;
    const data = { name, texto: body };
    const cacheKey = cacheKeyRef.value;
    const list = [...profilesForCacheKey(cacheKey)];
    const idx = list.findIndex((p) => String(p.id) === String(selectedProfileId.value || ''));
    if (idx >= 0) {
      list[idx] = { ...list[idx], ...data };
    } else {
      const id = crypto.randomUUID();
      list.push({ id, ...data });
      selectedProfileId.value = id;
    }
    setProfilesForCacheKey(cacheKey, list);

    const persisted = await persistProfiles(base, list);
    if (!persisted.ok) {
      return { ok: false, error: persisted.error || 'Não foi possível salvar no servidor.' };
    }
    await upsertCatalogValue(base, body);
    return { ok: true };
  }

  async function deleteProfile() {
    const base = baseRef.value;
    const id = String(selectedProfileId.value || '').trim();
    if (!id) return { ok: false, error: 'Nenhum cadastro selecionado.' };
    const cacheKey = cacheKeyRef.value;
    const list = profilesForCacheKey(cacheKey).filter((p) => String(p.id) !== id);
    setProfilesForCacheKey(cacheKey, list);
    selectedProfileId.value = '';
    profileName.value = '';
    const persisted = await persistProfiles(base, list);
    if (!persisted.ok) {
      return { ok: false, error: persisted.error || 'Não foi possível excluir no servidor.' };
    }
    return { ok: true };
  }

  return {
    profiles,
    selectedProfileId,
    profileName,
    loading,
    loadProfiles,
    loadProfile,
    profilePayload,
    newProfile,
    saveProfile,
    deleteProfile,
    upsertCatalogValue: (texto) => upsertCatalogValue(baseRef.value, texto),
  };
}
