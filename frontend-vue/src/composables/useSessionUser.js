import { ref } from 'vue';
import { getApiBase } from '@/utils/apiBase.js';

/** Perfil do utilizador logado — partilhado entre router guard e App.vue. */
const user = ref(null);
const userLoading = ref(false);
let inflightPromise = null;
/** Evita /api/me/ em cada navegação enquanto busca PNCP ocupa workers do Django. */
let lastFetchedAt = 0;
const ME_CACHE_MS = 5 * 60 * 1000;

export function useSessionUser() {
  async function fetchMe({ force = false } = {}) {
    const now = Date.now();
    if (
      !force
      && user.value
      && lastFetchedAt > 0
      && now - lastFetchedAt < ME_CACHE_MS
    ) {
      return user.value;
    }
    if (inflightPromise && !force) {
      return inflightPromise;
    }
    userLoading.value = true;
    inflightPromise = (async () => {
      try {
        const res = await fetch(`${getApiBase()}/api/me/`, {
          method: 'GET',
          credentials: 'include',
        });
        if (res.status !== 200) {
          user.value = null;
          lastFetchedAt = 0;
          return null;
        }
        const ctype = (res.headers.get('content-type') || '').toLowerCase();
        if (!ctype.includes('application/json')) {
          user.value = null;
          lastFetchedAt = 0;
          return null;
        }
        const data = await res.json();
        if (data && typeof data === 'object') {
          user.value = data;
          lastFetchedAt = Date.now();
          return data;
        }
        user.value = null;
        lastFetchedAt = 0;
        return null;
      } catch (_) {
        // Mantém sessão em cache se rede falhar momentaneamente (busca PNCP a saturar API).
        if (user.value && lastFetchedAt > 0) {
          return user.value;
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
  }

  return { user, userLoading, fetchMe, clearUser };
}
