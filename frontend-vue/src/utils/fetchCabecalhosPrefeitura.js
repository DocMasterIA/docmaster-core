/**
 * Modelos DOCX da biblioteca (`/api/documentos_modelos/`) da prefeitura do utilizador,
 * com id para merge de cabeçalho/rodapé em `gerar-tr-e-dfd` (`template_id`).
 *
 * @param {string} apiBase ex.: import.meta.env.DEV ? '' : VITE_API_URL
 * @param {{ prefeituraId?: string|number|null }} [options]
 * @returns {Promise<Array<{ id: string; name: string }>>}
 */
export async function fetchCabecalhosPrefeitura(apiBase, { prefeituraId = null } = {}) {
  let userPrefeituraId = prefeituraId != null ? String(prefeituraId) : null;
  if (!userPrefeituraId) {
    try {
      const meRes = await fetch(`${apiBase}/api/me/`, { credentials: 'include' });
      if (meRes.ok) {
        const me = await meRes.json().catch(() => ({}));
        userPrefeituraId = me?.prefeitura_id != null ? String(me.prefeitura_id) : null;
      }
    } catch {
      // ignore
    }
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
    const seen = new Set();
    const out = [];
    for (const t of filtered) {
      const name = String(t?.name || '').trim();
      const id = t?.id != null ? String(t.id).trim() : '';
      if (!name || !id || seen.has(id)) continue;
      seen.add(id);
      out.push({ id, name });
    }
    out.sort((a, b) => a.name.localeCompare(b.name, 'pt', { sensitivity: 'base' }));
    return out;
  } catch {
    return [];
  }
}
