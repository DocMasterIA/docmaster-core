/**
 * Monta payload para `recortes_geograficos` (PNCP local / IA).
 * @param {Array<{ uf?: string, municipio?: string }>} locais
 * @returns {Array<{ uf: string, municipio: string | null }>}
 */
export function buildRecortesGeograficosPayload(locais) {
  const out = [];
  const seen = new Set();
  for (const row of locais || []) {
    const uf = String(row?.uf || '')
      .trim()
      .toUpperCase();
    if (uf.length !== 2) continue;
    const mRaw = String(row?.municipio || '').trim();
    const municipio = mRaw || null;
    const key = `${uf}|${municipio || ''}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(municipio ? { uf, municipio } : { uf, municipio: null });
    if (out.length >= 30) break;
  }
  return out;
}

/**
 * @param {{ uf?: string, municipio?: string | null }} item
 * @param {ReturnType<buildRecortesGeograficosPayload>} recortes
 */
export function itemMatchesRecortesGeograficos(item, recortes) {
  if (!recortes?.length) return true;
  const iUf = String(item?.uf || '')
    .trim()
    .toUpperCase();
  const iMun = normalizeMunicipioKey(item?.municipio);
  return recortes.some((r) => {
    if (String(r.uf || '').toUpperCase() !== iUf) return false;
    if (!r.municipio) return true;
    return normalizeMunicipioKey(r.municipio) === iMun;
  });
}

function normalizeMunicipioKey(v) {
  return String(v ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}
