/**
 * Localidade do utilizador para placeholders (TR_CIDADE), (TR_CODIGO_UF) no modelo.
 * Reforço ao merge feito no rag_service a partir de context.usuario.
 */

/**
 * @param {string} apiBase
 * @returns {Promise<{ cidade: string; codigo_uf: string; cidade_estado: string } | null>}
 */
export async function fetchUsuarioLocalidadeParaTr(apiBase) {
  const base = String(apiBase || '').trim();
  if (!base) return null;
  try {
    const res = await fetch(`${base}/api/me/`, { credentials: 'include' });
    if (!res.ok) return null;
    const me = await res.json().catch(() => ({}));
    const cidade = String(me?.prefeitura_nome || '').trim();
    const codigo_uf = String(me?.prefeitura_uf || '').trim().toUpperCase();
    if (!cidade && !codigo_uf) return null;
    const cidade_estado = cidade && codigo_uf ? `${cidade} - ${codigo_uf}` : cidade || codigo_uf;
    return { cidade, codigo_uf, cidade_estado };
  } catch {
    return null;
  }
}

/**
 * @param {Record<string, unknown>} slots
 * @param {{ cidade?: string; codigo_uf?: string; cidade_estado?: string } | null} loc
 */
export function applyUsuarioLocalidadeToSlots(slots, loc) {
  if (!slots || !loc) return;
  if (loc.cidade && !String(slots.cidade || '').trim()) slots.cidade = loc.cidade;
  if (loc.codigo_uf && !String(slots.codigo_uf || '').trim()) slots.codigo_uf = loc.codigo_uf;
  if (loc.cidade_estado && !String(slots.cidade_estado || '').trim()) {
    slots.cidade_estado = loc.cidade_estado;
  }
}
