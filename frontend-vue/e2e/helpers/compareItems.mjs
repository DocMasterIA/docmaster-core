/**
 * Comparação lexical/técnica termo da cotação × título do candidato PNCP.
 * Não substitui o researcher — serve para auditoria E2E explicar *por que* o hit é duvidoso.
 */

const STOP = new Set([
  'de', 'da', 'do', 'das', 'dos', 'e', 'ou', 'com', 'para', 'em', 'no', 'na', 'nos', 'nas',
  'um', 'uma', 'uns', 'umas', 'c', 'x', 'ml', 'mg', 'g', 'kg', 'un', 'und', 'unidade',
  'unidades', 'frasco', 'cx', 'caixa', 'pct', 'pacote', 'tipo', 'modelo',
]);

/** Famílias mutuamente excludentes (se termo tem A e candidato tem B → mismatch). */
const FAMILY_GROUPS = [
  ['oxigenada', 'boricada', 'destilada', 'aguarras', 'sanitaria'],
  ['nylon', 'seda', 'vicryl', 'catgut', 'algodao', 'dental'],
  ['gel', 'liquido', 'solucao', 'xarope', 'comprimido', 'capsula', 'injetavel'],
  ['microporosa', 'isolante', 'crepe', 'esparadrapo'],
];

export function normalizeText(s) {
  return String(s || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9%.,/\s-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

export function tokenize(s) {
  const n = normalizeText(s);
  const parts = n.split(/[\s,/|-]+/).filter(Boolean);
  return parts.filter((t) => t.length >= 2 && !STOP.has(t));
}

/** Âncoras numéricas / de especificação (ex.: 70%, 10 volumes, n 4.0, 50mg). */
export function extractAnchors(s) {
  const raw = String(s || '');
  const n = normalizeText(raw);
  const anchors = new Set();

  for (const m of raw.matchAll(/(\d+[.,]?\d*)\s*%/g)) anchors.add(`${m[1].replace(',', '.')}%`);
  // "70 VOLUME" / "70, PRODUTO" comum em editais de álcool
  for (const m of n.matchAll(/\b(\d+[.,]?\d*)\s*volume(?:s|\.|\,|\s)/g)) {
    const v = m[1].replace(',', '.');
    if (!anchors.has(`${v}volumes`)) anchors.add(`${v}%`);
  }
  for (const m of n.matchAll(/(\d+[.,]?\d*)\s*mg(?:\s*\/\s*ml)?/g)) anchors.add(`${m[1].replace(',', '.')}mg`);
  for (const m of n.matchAll(/(\d+[.,]?\d*)\s*ml\b/g)) anchors.add(`${m[1].replace(',', '.')}ml`);
  for (const m of n.matchAll(/(\d+)\s*volumes?\b/g)) anchors.add(`${m[1]}volumes`);
  for (const m of n.matchAll(/\bn[°º.]?\s*(\d+[.,]?\d*)/g)) anchors.add(`n${m[1].replace(',', '.')}`);
  for (const m of n.matchAll(/\b(?:no|nro|numero)\s*(\d+[.,]?\d*)\b/g)) anchors.add(`n${m[1].replace(',', '.')}`);
  for (const m of n.matchAll(/(\d+[.,]?\d*)\s*x\s*(\d+[.,]?\d*)\s*(cm|mm|m)\b/g)) {
    anchors.add(`${m[1].replace(',', '.')}x${m[2].replace(',', '.')}${m[3]}`);
  }
  for (const m of n.matchAll(/c\s*\/?\s*(\d+)\b/g)) anchors.add(`c${m[1]}`);

  return [...anchors];
}

function familyHits(tokens) {
  const set = new Set(tokens);
  const hits = [];
  for (const group of FAMILY_GROUPS) {
    const found = group.filter((f) => set.has(f) || [...set].some((t) => t.includes(f)));
    if (found.length) hits.push({ group, found });
  }
  return hits;
}

/**
 * Compara termo do item da cotação com o título do preço encontrado.
 * @returns {{
 *   overlap: number,
 *   jaccard: number,
 *   termTokens: string[],
 *   candTokens: string[],
 *   missingCore: string[],
 *   extraNoise: string[],
 *   anchorsTerm: string[],
 *   anchorsCand: string[],
 *   anchorsMissing: string[],
 *   familyConflict: null|{ term: string[], cand: string[] },
 *   verdict: 'match'|'partial'|'mismatch',
 *   reasons: string[],
 * }}
 */
export function compareTermToCandidate(termLabel, candidateTitle) {
  const termTokens = tokenize(termLabel);
  const candTokens = tokenize(candidateTitle);
  const termSet = new Set(termTokens);
  const candSet = new Set(candTokens);

  const inter = termTokens.filter((t) => candSet.has(t));
  const unionSize = new Set([...termTokens, ...candTokens]).size || 1;
  const jaccard = inter.length / unionSize;
  const overlap = termTokens.length ? inter.length / termTokens.length : 0;

  // Tokens "core": os mais longos / específicos do termo (len>=4 ou com dígito)
  const core = termTokens.filter((t) => t.length >= 4 || /\d/.test(t));
  const missingCore = core.filter((t) => !candSet.has(t) && ![...candSet].some((c) => c.includes(t) || t.includes(c)));

  const anchorsTerm = extractAnchors(termLabel);
  const anchorsCand = extractAnchors(candidateTitle);
  const anchorsMissing = anchorsTerm.filter((a) => {
    const key = a.replace(/[^0-9a-z.%]/g, '');
    return !anchorsCand.some((b) => b.replace(/[^0-9a-z.%]/g, '') === key);
  });

  const famTerm = familyHits(termTokens);
  const famCand = familyHits(candTokens);
  let familyConflict = null;
  for (const ft of famTerm) {
    for (const fc of famCand) {
      if (ft.group === fc.group) {
        const onlyTerm = ft.found.filter((x) => !fc.found.includes(x));
        const onlyCand = fc.found.filter((x) => !ft.found.includes(x));
        if (onlyTerm.length && onlyCand.length) {
          familyConflict = { term: onlyTerm, cand: onlyCand, group: ft.group };
        }
      }
    }
  }
  // Conflito cross-group: termo oxigenada vs cand boricada (mesmo grupo já coberto)

  const reasons = [];
  if (familyConflict) {
    reasons.push(
      `família conflitante: termo[${familyConflict.term.join(',')}] vs candidato[${familyConflict.cand.join(',')}]`,
    );
  }
  if (missingCore.length) {
    reasons.push(`faltam âncoras lexicais do termo: ${missingCore.slice(0, 6).join(', ')}`);
  }
  if (anchorsMissing.length) {
    reasons.push(`faltam specs numéricas: ${anchorsMissing.join(', ')}`);
  }
  if (overlap < 0.35) {
    reasons.push(`baixa cobertura de tokens (${(overlap * 100).toFixed(0)}%)`);
  }

  let verdict = 'match';
  if (familyConflict || (missingCore.length >= 2 && overlap < 0.5) || (anchorsMissing.length && overlap < 0.45)) {
    verdict = 'mismatch';
  } else if (missingCore.length || anchorsMissing.length || overlap < 0.6 || jaccard < 0.35) {
    verdict = 'partial';
  }

  // Ruído extra óbvio
  const extraNoise = candTokens.filter((t) => !termSet.has(t) && t.length >= 5).slice(0, 8);

  return {
    overlap: Math.round(overlap * 1000) / 1000,
    jaccard: Math.round(jaccard * 1000) / 1000,
    termTokens,
    candTokens,
    missingCore,
    extraNoise,
    anchorsTerm,
    anchorsCand,
    anchorsMissing,
    familyConflict,
    verdict,
    reasons,
  };
}
