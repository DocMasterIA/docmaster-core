/** Fechamento normativo do objeto no TR — espelha rag_service/app/tr_objeto_fechamento.py */

export const TR_FECHAMENTO_AQUISICAO =
  ', conforme quantidades e demais condições estabelecidas neste Termo de Referência';

export const TR_FECHAMENTO_CONTRATACAO =
  ', conforme requisitos técnicos e demais condições estabelecidas neste Termo de Referência';

const RE_TR_FECHAMENTO_ANY =
  /,?\s*conforme\s+(?:quantidades(?:\s+e(?:\s+quantitativos?)?)?|requisitos\s+t[eé]cnicos|especifica[cç][oõ]es\s+t[eé]cnicas(?:,?\s*quantitativos?\s+e)?)\s+demais\s+condi[çc][oõ]es\s+estabelecidas\s+(?:neste|no)\s+termo\s+de\s+refer[eê]ncia\.?/gi;

const RE_EM_QUANTIDADE =
  /,?\s*em\s+quantidade\s+conforme\s+estipulado\s+(?:neste|no)\s+termo\s+de\s+refer[eê]ncia\.?/gi;

function objetoIsAquisicao(text) {
  const low = String(text || '').toLowerCase();
  const serviceHints = [
    'serviço',
    'servicos',
    'prestação',
    'prestacao',
    'manutenção',
    'manutencao',
    'execução',
    'execucao',
    'obra',
    'engenharia',
    'locação',
    'locacao',
  ];
  const hasService = serviceHints.some((h) => low.includes(h));
  const hasGoods = /\b(aquisi(?:c|ç)[aã]o|fornecimento|material|produto|insumo|equipamento)\b/i.test(low);
  if (hasService && !hasGoods) return false;
  if (hasGoods && !hasService) return true;
  return /\b(aquisi(?:c|ç)[aã]o|fornecimento)\b/i.test(low);
}

/** Garante fechamento com «neste Termo de Referência» (padrão TR). */
export function ensureTrObjetoFechamento(text) {
  let t = String(text || '').trim();
  if (!t) return t;

  const fechamento = objetoIsAquisicao(t) ? TR_FECHAMENTO_AQUISICAO : TR_FECHAMENTO_CONTRATACAO;

  if (RE_TR_FECHAMENTO_ANY.test(t) || RE_EM_QUANTIDADE.test(t)) {
    t = t.replace(RE_EM_QUANTIDADE, '').replace(RE_TR_FECHAMENTO_ANY, '');
    t = t.replace(/\s{2,}/g, ' ').replace(/[.,;:]+$/, '').trim();
    RE_TR_FECHAMENTO_ANY.lastIndex = 0;
    RE_EM_QUANTIDADE.lastIndex = 0;
  }

  const base = t.replace(/[.,;:]+$/, '').trim();
  if (!base) return String(text || '').trim();
  return `${base}${fechamento}.`;
}
