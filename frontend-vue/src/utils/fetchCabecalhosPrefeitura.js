/**
 * Nomes de modelos DOCX da biblioteca (`/api/documentos_modelos/`) filtrados
 * pela prefeitura do usuário logado — mesma regra da dispensa normal (InexigibilidadeManutencaoVeiculosPreview).
 *
 * @param {string} apiBase ex.: import.meta.env.DEV ? '' : VITE_API_URL
 * @returns {Promise<string[]>}
 */
export async function fetchCabecalhosPrefeitura(apiBase) {
  let userPrefeituraId = null;
  try {
    const meRes = await fetch(`${apiBase}/api/me/`, { credentials: 'include' });
    if (meRes.ok) {
      const me = await meRes.json().catch(() => ({}));
      userPrefeituraId = me?.prefeitura_id != null ? String(me.prefeitura_id) : null;
    }
  } catch {
    // ignore
  }

  try {
    const res = await fetch(`${apiBase}/api/documentos_modelos/`, { credentials: 'include' });
    if (!res.ok) return [];
    const payload = await res.json().catch(() => ({}));
    const templates = Array.isArray(payload?.templates) ? payload.templates : [];
    const filtered = templates.filter((t) => {
      const tplPrefId = t?.prefeitura?.id != null ? String(t.prefeitura.id) : null;
      return !!userPrefeituraId && !!tplPrefId && tplPrefId === userPrefeituraId;
    });
    return [...new Set(filtered.map((t) => String(t?.name || '').trim()).filter(Boolean))];
  } catch {
    return [];
  }
}
