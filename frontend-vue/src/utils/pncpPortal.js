/** URL pública do processo no portal PNCP (https://pncp.gov.br/app/editais/{cnpj}/{ano}/{seq}). */

const PNCP_PORTAL_BASE = 'https://pncp.gov.br/app/editais';

export function extractCnpjOrgaoFromNumeroPncp(numeroPncp) {
  const raw = String(numeroPncp || '').trim();
  if (!raw) return '';
  const head = raw.includes('-') ? raw.split('-', 1)[0] : raw;
  const digits = head.replace(/\D/g, '');
  return digits.length === 14 ? digits : '';
}

export function parseAnoSeqFromNumeroPncp(numeroPncp) {
  const s = String(numeroPncp || '').trim();
  if (!s) return { ano: null, sequencial: null };

  const slash = s.match(/-(\d+)\/(\d{4})\s*$/);
  if (slash) {
    const sequencial = Number.parseInt(slash[1], 10);
    const ano = Number.parseInt(slash[2], 10);
    if (Number.isFinite(ano) && ano >= 1990 && ano <= 2100 && Number.isFinite(sequencial) && sequencial > 0) {
      return { ano, sequencial };
    }
    return { ano: null, sequencial: null };
  }

  const parts = s.split('-').map((p) => p.trim()).filter(Boolean);
  if (parts.length < 4) return { ano: null, sequencial: null };
  const ano = Number.parseInt(parts[parts.length - 2], 10);
  const sequencial = Number.parseInt(parts[parts.length - 1], 10);
  if (!Number.isFinite(ano) || ano < 1990 || ano > 2100 || !Number.isFinite(sequencial) || sequencial <= 0) {
    return { ano: null, sequencial: null };
  }
  return { ano, sequencial };
}

function pickHttpUrl(...candidates) {
  for (const v of candidates) {
    const u = String(v || '').trim();
    if (/^https?:\/\//i.test(u)) return u;
  }
  return '';
}

/**
 * Monta link para o processo no portal PNCP a partir de uma cotação de preço (PncpCotacaoItemCotacao).
 * @param {Record<string, unknown>|null|undefined} cotacao
 * @returns {string}
 */
export function buildPncpPortalProcessoUrl(cotacao) {
  const src = cotacao?.source && typeof cotacao.source === 'object' ? cotacao.source : {};
  const fromSource = pickHttpUrl(
    src.linkSistemaOrigem,
    src.linkProcessoEletronico,
    src.url_pncp,
    src.link_pncp,
    src.linkPncp,
    src.link_portal_pncp,
  );
  if (fromSource) return fromSource;

  const numeroPncp = String(
    cotacao?.numero_pncp || src.numero_pncp || src.numeroControlePNCP || '',
  ).trim();
  const cnpj = extractCnpjOrgaoFromNumeroPncp(numeroPncp);
  if (!cnpj) return '';

  let ano = cotacao?.ano_compra ?? src.anoCompra ?? src.ano_compra;
  let sequencial = cotacao?.sequencial_compra ?? src.sequencialCompra ?? src.sequencial_compra;

  if (ano == null || sequencial == null) {
    const parsed = parseAnoSeqFromNumeroPncp(numeroPncp);
    if (ano == null) ano = parsed.ano;
    if (sequencial == null) sequencial = parsed.sequencial;
  }

  const anoN = Number.parseInt(String(ano ?? ''), 10);
  const seqN = Number.parseInt(String(sequencial ?? ''), 10);
  if (!Number.isFinite(anoN) || !Number.isFinite(seqN) || seqN <= 0) return '';

  return `${PNCP_PORTAL_BASE}/${cnpj}/${anoN}/${seqN}`;
}

export function pncpProcessoDisplayLabel(cotacao) {
  const src = cotacao?.source && typeof cotacao.source === 'object' ? cotacao.source : {};
  return String(
    cotacao?.numero_pncp || src.numero_pncp || src.numeroControlePNCP || '',
  ).trim();
}
