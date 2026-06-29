/** Pacote SlotFormState no backend — um registro por usuário (owner). */
export const ORGAO_PROFILES_FORM_KEY = 'orgao_profiles_v1';

/** Chave antiga em localStorage (sem isolamento por usuário) — só para limpeza. */
export const LEGACY_ORGAO_PROFILES_LS_KEY = 'orgao_profiles_v1';

export function clearLegacyOrgaoProfilesLocalStorage() {
  try {
    localStorage.removeItem(LEGACY_ORGAO_PROFILES_LS_KEY);
  } catch {
    // silencioso
  }
}
