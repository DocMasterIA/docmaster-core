/**
 * Monta payload para `recortes_geograficos` (PNCP local / IA).
 * Cada linha pode ter `municipios: string[]` (várias cidades na mesma UF) ou
 * o formato legado `municipio: string` (uma cidade). Sem município = UF inteira.
 * @param {Array<{ uf?: string, municipio?: string, municipios?: string[] }>} linhas
 * @returns {Array<{ uf: string, municipio: string | null }>}
 */
export function buildRecortesGeograficosPayload(linhas) {
  const out = [];
  const seen = new Set();
  for (const row of linhas || []) {
    const uf = String(row?.uf || '')
      .trim()
      .toUpperCase();
    if (uf.length !== 2) continue;

    const arr = Array.isArray(row?.municipios)
      ? row.municipios.map((m) => String(m || '').trim()).filter(Boolean)
      : [];
    const legacy = String(row?.municipio || '').trim();

    if (arr.length > 0) {
      for (const mRaw of arr) {
        const municipio = mRaw;
        const key = `${uf}|${municipio}`;
        if (seen.has(key)) continue;
        seen.add(key);
        out.push({ uf, municipio });
        if (out.length >= 30) return out;
      }
    } else if (legacy) {
      const key = `${uf}|${legacy}`;
      if (seen.has(key)) continue;
      seen.add(key);
      out.push({ uf, municipio: legacy });
      if (out.length >= 30) return out;
    } else {
      const key = `${uf}|`;
      if (seen.has(key)) continue;
      seen.add(key);
      out.push({ uf, municipio: null });
      if (out.length >= 30) return out;
    }
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
