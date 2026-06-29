/** Fechamento normativo do objeto no TR — espelha rag_service/app/tr_objeto_fechamento.py */

export const TR_FECHAMENTO_PADRAO =
  ', conforme quantidades e demais condições estabelecidas neste Termo de Referência';

/** @deprecated use TR_FECHAMENTO_PADRAO */
export const TR_FECHAMENTO_AQUISICAO = TR_FECHAMENTO_PADRAO;

const RE_TR_FECHAMENTO_ANY =
  /,?\s*conforme\s+(?:quantidades(?:\s+e(?:\s+quantitativos?)?)?|requisitos\s+t[eé]cnicos|especifica[cç][oõ]es\s+t[eé]cnicas(?:,?\s*quantitativos?\s+e)?)\s+demais\s+condi[çc][oõ]es\s+estabelecidas\s+(?:neste|no)\s+termo\s+de\s+refer[eê]ncia\.?/gi;

const RE_EM_QUANTIDADE =
  /,?\s*em\s+quantidade\s+conforme\s+estipulado\s+(?:neste|no)\s+termo\s+de\s+refer[eê]ncia\.?/gi;

/** Garante o fechamento normativo único com «neste Termo de Referência». */
export function ensureTrObjetoFechamento(text) {
  let t = String(text || '').trim();
  if (!t) return t;

  if (RE_TR_FECHAMENTO_ANY.test(t) || RE_EM_QUANTIDADE.test(t)) {
    t = t.replace(RE_EM_QUANTIDADE, '').replace(RE_TR_FECHAMENTO_ANY, '');
    t = t.replace(/\s{2,}/g, ' ').replace(/[.,;:]+$/, '').trim();
    RE_TR_FECHAMENTO_ANY.lastIndex = 0;
    RE_EM_QUANTIDADE.lastIndex = 0;
  }

  const base = t.replace(/[.,;:]+$/, '').trim();
  if (!base) return String(text || '').trim();
  return `${base}${TR_FECHAMENTO_PADRAO}.`;
}
