import { ref } from 'vue';
import { getApiBase } from '@/utils/apiBase.js';

/** Perfil do utilizador logado — partilhado entre router guard e App.vue. */
const user = ref(null);
const userLoading = ref(false);
let inflightPromise = null;

export function useSessionUser() {
  async function fetchMe({ force = false } = {}) {
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
          return null;
        }
        const ctype = (res.headers.get('content-type') || '').toLowerCase();
        if (!ctype.includes('application/json')) {
          user.value = null;
          return null;
        }
        const data = await res.json();
        if (data && typeof data === 'object') {
          user.value = data;
          return data;
        }
        user.value = null;
        return null;
      } catch (_) {
        user.value = null;
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
  }

  return { user, userLoading, fetchMe, clearUser };
}
