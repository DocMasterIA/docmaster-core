/** Localidade TCE/PNCP: não exibir código IBGE (7 dígitos) como município. */

export function pareceCodigoIbgeMunicipio(municipio) {
  const s = String(municipio || '').trim();
  if (!s) return false;
  const digits = s.replace(/\D/g, '');
  return digits.length === 7 && digits === s.replace(/\s/g, '');
}

/**
 * Espelha LicitaCon / PDF: «PM DE TIO HUGO» → «Tio Hugo».
 */
export function inferMunicipioFromOrgaoNome(orgao) {
  const raw = String(orgao || '').trim();
  if (!raw) return '';
  const head = raw.split(/\s+[—\-–]\s+/)[0].trim();
  const patterns = [
    /^(?:PM|CM)\s+DE\s+(.+)$/i,
    /^PREFEITURA(?:\s+MUNICIPAL)?\s+DE\s+(.+)$/i,
    /^C[ÂA]MARA(?:\s+MUNICIPAL)?\s+DE\s+(.+)$/i,
    /^FUNDO\s+MUNICIPAL\s+(?:DE\s+\w+\s+)?DE\s+(.+)$/i,
  ];
  let cidade = '';
  for (const pat of patterns) {
    const m = head.match(pat);
    if (m) {
      cidade = String(m[1] || '').trim();
      break;
    }
  }
  if (!cidade) return '';
  cidade = cidade.split(/[,/;|]/)[0].trim();
  if (!cidade || /^\d+$/.test(cidade)) return '';
  const small = new Set(['de', 'da', 'do', 'das', 'dos', 'e', 'a', 'o']);
  return cidade
    .split(/\s+/)
    .map((w, i) => {
      const wl = w.toLowerCase();
      if (i > 0 && small.has(wl)) return wl;
      return wl ? wl.charAt(0).toUpperCase() + wl.slice(1) : w;
    })
    .join(' ');
}

function pickFromSource(src, keys) {
  if (!src || typeof src !== 'object') return '';
  for (const k of keys) {
    const v = src[k];
    if (v != null && String(v).trim()) return String(v).trim();
  }
  const uo = src.unidadeOrgao || src.unidade_orgao;
  if (uo && typeof uo === 'object') {
    for (const k of keys) {
      const v = uo[k];
      if (v != null && String(v).trim()) return String(v).trim();
    }
  }
  return '';
}

/**
 * Resolve município + UF legíveis (ignora IBGE; infere cidade do órgão se preciso).
 * @returns {{ municipio: string, uf: string }}
 */
export function resolveMunicipioUf(it = {}, src = {}) {
  const source = src && typeof src === 'object' ? src : {};
  let mun = String(
    it.municipio
      || pickFromSource(source, ['municipio', 'municipioNome', 'municipio_nome', 'cidade'])
      || '',
  ).trim();
  let uf = String(
    it.uf
      || pickFromSource(source, ['uf', 'ufSigla', 'uf_sigla', 'siglaUf'])
      || '',
  ).trim().toUpperCase().slice(0, 2);

  if (pareceCodigoIbgeMunicipio(mun)) mun = '';

  if (!mun) {
    mun = inferMunicipioFromOrgaoNome(it.orgao || source.orgao || '') || '';
  }
  if (pareceCodigoIbgeMunicipio(mun)) mun = '';

  if (uf && !/^[A-Z]{2}$/.test(uf)) uf = '';
  return { municipio: mun, uf };
}

/** Ex.: «Tio Hugo/RS» ou «—». */
export function formatMunicipioUf(it = {}, src = {}, empty = '—') {
  const { municipio, uf } = resolveMunicipioUf(it, src);
  if (municipio && uf) return `${municipio}/${uf}`;
  return municipio || uf || empty;
}
