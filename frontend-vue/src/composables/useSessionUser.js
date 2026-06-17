import { ref } from 'vue';
import { getApiBase } from '@/utils/apiBase.js';

const SESSION_USER_KEY = 'docmaster.session_user_v1';

/** Perfil do utilizador logado — partilhado entre router guard e App.vue. */
const user = ref(null);
const userLoading = ref(false);
let inflightPromise = null;
/** Evita /api/me/ em cada navegação enquanto busca PNCP ocupa workers do Django. */
let lastFetchedAt = 0;
const ME_CACHE_MS = 5 * 60 * 1000;
const ME_FETCH_TIMEOUT_MS = 8000;

function readStoredUser() {
  try {
    const raw = sessionStorage.getItem(SESSION_USER_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed?.data || typeof parsed.fetchedAt !== 'number') return null;
    if (Date.now() - parsed.fetchedAt > ME_CACHE_MS) return null;
    return parsed.data;
  } catch (_) {
    return null;
  }
}

function writeStoredUser(data) {
  try {
    if (!data) {
      sessionStorage.removeItem(SESSION_USER_KEY);
      return;
    }
    sessionStorage.setItem(
      SESSION_USER_KEY,
      JSON.stringify({ data, fetchedAt: Date.now() }),
    );
  } catch (_) {
    /* quota / private mode */
  }
}

function hydrateUserFromStorage() {
  if (user.value) return;
  const stored = readStoredUser();
  if (stored) {
    user.value = stored;
    lastFetchedAt = Date.now();
  }
}

hydrateUserFromStorage();

function hasCachedUser() {
  return Boolean(
    user.value
    && lastFetchedAt > 0
    && Date.now() - lastFetchedAt < ME_CACHE_MS,
  );
}

function isTransientMeStatus(status) {
  return status === 502 || status === 503 || status === 504 || status === 429;
}

export function useSessionUser() {
  async function fetchMe({ force = false } = {}) {
    if (!force && hasCachedUser()) {
      return user.value;
    }
    // Não bloquear navegação num /api/me/ pendente se já temos perfil em cache.
    if (inflightPromise && !force && user.value && lastFetchedAt > 0) {
      return user.value;
    }
    if (inflightPromise && !force) {
      return inflightPromise;
    }
    userLoading.value = true;
    inflightPromise = (async () => {
      try {
        const signal = typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function'
          ? AbortSignal.timeout(ME_FETCH_TIMEOUT_MS)
          : undefined;
        const res = await fetch(`${getApiBase()}/api/me/`, {
          method: 'GET',
          credentials: 'include',
          signal,
        });
        if (res.status !== 200) {
          if (isTransientMeStatus(res.status) && user.value && lastFetchedAt > 0) {
            return user.value;
          }
          user.value = null;
          lastFetchedAt = 0;
          writeStoredUser(null);
          return null;
        }
        const ctype = (res.headers.get('content-type') || '').toLowerCase();
        if (!ctype.includes('application/json')) {
          if (user.value && lastFetchedAt > 0) return user.value;
          user.value = null;
          lastFetchedAt = 0;
          writeStoredUser(null);
          return null;
        }
        const data = await res.json();
        if (data && typeof data === 'object') {
          user.value = data;
          lastFetchedAt = Date.now();
          writeStoredUser(data);
          return data;
        }
        user.value = null;
        lastFetchedAt = 0;
        writeStoredUser(null);
        return null;
      } catch (_) {
        // Mantém sessão em cache se rede falhar momentaneamente (busca PNCP a saturar API).
        if (user.value && lastFetchedAt > 0) {
          return user.value;
        }
        const stored = readStoredUser();
        if (stored) {
          user.value = stored;
          lastFetchedAt = Date.now();
          return stored;
        }
        user.value = null;
        lastFetchedAt = 0;
        return null;
      } finally {
        userLoading.value = false;
        inflightPromise = null;
      }
    })();
    return inflightPromise;
  }

  function clearUser() {
    user.value = null;
    lastFetchedAt = 0;
    writeStoredUser(null);
  }

  return { user, userLoading, fetchMe, clearUser, hasCachedUser };
}
