/** Códigos CD_TIPO_MODALIDADE (LicitaCon / TCE-RS) → rótulo legível. */

export const TCE_RS_MODALIDADE_LABELS = {
  PCE: 'Pregão Eletrônico',
  PCP: 'Pregão Presencial',
  PRD: 'Processo de Dispensa',
  PDE: 'Processo de Dispensa Eletrônica',
  PRI: 'Processo de Inexigibilidade',
  CCE: 'Concorrência Eletrônica',
  CPC: 'Concorrência',
  CPP: 'Concorrência Presencial',
  CCP: 'Concorrência Presencial',
  RPO: 'Adesão à Ata de Registro de Preços',
  CHP: 'Chamamento Público',
  LEE: 'Leilão Eletrônico',
  LEI: 'Leilão Presencial',
  RDE: 'RDC Eletrônico',
  RDP: 'RDC Presencial',
  CNS: 'Concurso',
  RIN: 'Regras Internacionais',
  ESE: 'Licitação Lei 13.303/16 Eletrônico',
  EST: 'Licitação Lei 13.303/16 Presencial',
};

export function pareceObservacaoTceComoModalidade(raw) {
  const s = String(raw || '').trim().toLowerCase();
  if (!s) return false;
  return (
    s.includes('tce-rs')
    || s.includes('tce_rs')
    || s.includes('licitacon')
    || s.startsWith('tce')
    || s.includes('proc.')
  );
}

export function codigoModalidadeTceFromKeys(...candidates) {
  for (const raw of candidates) {
    const s = String(raw || '').trim();
    if (!s) continue;
    const upper = s.toUpperCase();
    if (/^[A-Z]{2,4}$/.test(upper) && TCE_RS_MODALIDADE_LABELS[upper]) {
      return upper;
    }
    if (s.includes(':')) {
      const tail = s.split(':').pop().trim().toUpperCase();
      const code = tail.split(/[,;\s|/]+/)[0].trim();
      if (/^[A-Z]{2,4}$/.test(code) && TCE_RS_MODALIDADE_LABELS[code]) {
        return code;
      }
    }
    const re = /:([A-Z]{2,4})(?=[^A-Z]|$)/g;
    let m;
    while ((m = re.exec(upper)) !== null) {
      if (TCE_RS_MODALIDADE_LABELS[m[1]]) return m[1];
    }
  }
  return '';
}

function normalizeModalidadeLegivel(s) {
  return String(s || '')
    .trim()
    .replace(/\s*-\s*/g, ' ')
    .replace(/\s+/g, ' ')
    .slice(0, 120);
}

/**
 * Modalidade da licitação (Pregão Eletrônico, …), não confundir com Fonte (PNCP/TCE-RS).
 */
export function labelModalidadeFonte(it = {}, src = {}) {
  const source = src && typeof src === 'object' ? src : {};
  const candidates = [
    source.modalidade_nome,
    source.modalidadeNome,
    source.modalidade,
    it.modalidade,
  ];
  for (const cand of candidates) {
    const s = String(cand || '').trim();
    if (!s) continue;
    if (pareceObservacaoTceComoModalidade(s)) {
      const code = codigoModalidadeTceFromKeys(s);
      if (TCE_RS_MODALIDADE_LABELS[code]) return TCE_RS_MODALIDADE_LABELS[code];
      if (s.includes(',')) {
        const tail = s.split(',').pop().trim();
        if (tail && !pareceObservacaoTceComoModalidade(tail)) {
          return normalizeModalidadeLegivel(tail);
        }
      }
      continue;
    }
    const code = s.toUpperCase();
    if (TCE_RS_MODALIDADE_LABELS[code]) return TCE_RS_MODALIDADE_LABELS[code];
    if (s.length > 3 && !/^\d+$/.test(s)) return normalizeModalidadeLegivel(s);
  }
  const code = codigoModalidadeTceFromKeys(
    source.cd_tipo_modalidade,
    source.tipo_modalidade,
    source.modalidade_codigo,
    source.processo_id,
    source.plataforma_item_id,
    source.numero_processo,
    it.processo_id,
    it.plataforma_item_id,
    it.modalidade,
  );
  if (TCE_RS_MODALIDADE_LABELS[code]) return TCE_RS_MODALIDADE_LABELS[code];
  return code || 'N/D';
}
