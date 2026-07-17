/** URLs públicas de processo: PNCP e plataformas (ex.: TCE-RS LicitaCon). */

const PNCP_PORTAL_BASE = 'https://pncp.gov.br/app/editais';

/** Busca genérica do LicitaCon — não aponta para um processo (não usar como link de item). */
const TCE_RS_LICITACON_BUSCA_RE = /f\?p=50500:19:/i;

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
    if (!/^https?:\/\//i.test(u)) continue;
    // Descarta a página de busca genérica (:19:) — não abre o processo.
    if (TCE_RS_LICITACON_BUSCA_RE.test(u)) continue;
    return u;
  }
  return '';
}

function cotacaoSource(cotacao) {
  return cotacao?.source && typeof cotacao.source === 'object' ? cotacao.source : {};
}

/** Camadas onde o payload de busca/save costuma guardar metadados (incl. source aninhado). */
function cotacaoMetaLayers(cotacao) {
  const src = cotacaoSource(cotacao);
  const nested = src.source && typeof src.source === 'object' ? src.source : {};
  const raw = src.sourceRaw && typeof src.sourceRaw === 'object' ? src.sourceRaw : {};
  const topRaw =
    cotacao?.sourceRaw && typeof cotacao.sourceRaw === 'object' ? cotacao.sourceRaw : {};
  return [cotacao, src, nested, raw, topRaw].filter((x) => x && typeof x === 'object');
}

export function resolveCotacaoPlataforma(cotacao) {
  for (const layer of cotacaoMetaLayers(cotacao)) {
    const plat = String(layer.plataforma || layer.platform_id || '').trim().toLowerCase();
    if (plat) return plat;
  }
  return 'pncp';
}

function isTceRsPlataforma(plat) {
  return plat === 'tce_rs' || plat === 'tce-rs' || plat === 'licitacon';
}

/** Deep-link LicitaCon do processo (LINK_LICITACON_CIDADAO). Sem fallback genérico. */
function buildTceRsPortalUrl(cotacao) {
  const layers = cotacaoMetaLayers(cotacao);
  return pickHttpUrl(
    ...layers.flatMap((layer) => [
      layer.url_origem,
      layer.link_licitacon_cidadao,
      layer.linkLicitaconCidadao,
      layer.LINK_LICITACON_CIDADAO,
      layer.portal_url,
      layer.link_portal,
    ]),
  );
}

/**
 * Monta link para o processo no portal PNCP a partir de uma cotação de preço (PncpCotacaoItemCotacao).
 * @param {Record<string, unknown>|null|undefined} cotacao
 * @returns {string}
 */
export function buildPncpPortalProcessoUrl(cotacao) {
  const src = cotacaoSource(cotacao);
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

/** Link do portal da fonte (PNCP ou TCE-RS LicitaCon). */
export function buildFontePortalProcessoUrl(cotacao) {
  const plat = resolveCotacaoPlataforma(cotacao);
  if (isTceRsPlataforma(plat)) {
    return buildTceRsPortalUrl(cotacao);
  }

  const pncpUrl = buildPncpPortalProcessoUrl(cotacao);
  if (pncpUrl) return pncpUrl;

  // TCE salvo sem plataforma explícita, mas com deep-link LicitaCon.
  return buildTceRsPortalUrl(cotacao);
}

export function pncpProcessoDisplayLabel(cotacao) {
  const src = cotacaoSource(cotacao);
  return String(
    cotacao?.numero_pncp || src.numero_pncp || src.numeroControlePNCP || '',
  ).trim();
}

export function fontePortalProcessoDisplayLabel(cotacao) {
  const plat = resolveCotacaoPlataforma(cotacao);
  if (isTceRsPlataforma(plat) || /portal\.tce\.rs\.gov\.br/i.test(buildTceRsPortalUrl(cotacao))) {
    for (const layer of cotacaoMetaLayers(cotacao)) {
      const label = String(
        layer.numero_processo
        || layer.processo_id
        || layer.plataforma_item_id
        || layer.numero_pncp
        || '',
      ).trim();
      if (label) return label;
    }
    return '';
  }
  return pncpProcessoDisplayLabel(cotacao);
}

/** Texto do CTA: «Ver no PNCP» / «Ver no TCE-RS». */
export function fontePortalCtaLabel(cotacao) {
  const plat = resolveCotacaoPlataforma(cotacao);
  if (isTceRsPlataforma(plat)) return 'Ver no TCE-RS';
  const url = buildFontePortalProcessoUrl(cotacao);
  if (/portal\.tce\.rs\.gov\.br/i.test(url)) return 'Ver no TCE-RS';
  return 'Ver no PNCP';
}

export function fontePortalFieldLabel(cotacao) {
  const plat = resolveCotacaoPlataforma(cotacao);
  if (isTceRsPlataforma(plat)) return 'Processo TCE-RS';
  const url = buildFontePortalProcessoUrl(cotacao);
  if (/portal\.tce\.rs\.gov\.br/i.test(url)) return 'Processo TCE-RS';
  return 'Processo PNCP';
}

export function fontePortalTitle(cotacao) {
  const label = fontePortalProcessoDisplayLabel(cotacao);
  const url = buildFontePortalProcessoUrl(cotacao);
  const isTce =
    isTceRsPlataforma(resolveCotacaoPlataforma(cotacao))
    || /portal\.tce\.rs\.gov\.br/i.test(url);
  const portal = isTce ? 'portal TCE-RS (LicitaCon)' : 'portal PNCP';
  return label ? `Abrir processo ${label} no ${portal}` : `Abrir no ${portal}`;
}

/** Chaves para resolver URL no índice TCE quando a cotação não trouxe url_origem. */
export function tceRsPortalLookupKeys(cotacao) {
  const keys = [];
  const seen = new Set();
  for (const layer of cotacaoMetaLayers(cotacao)) {
    for (const k of ['processo_id', 'plataforma_item_id', 'numero_processo']) {
      const v = String(layer[k] || '').trim();
      if (!v || seen.has(v)) continue;
      seen.add(v);
      keys.push(v);
    }
  }
  return keys;
}
