/** URLs públicas de processo: PNCP e plataformas (ex.: TCE-RS LicitaCon). */

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

const TCE_RS_LICITACON_BUSCA =
  'https://portal.tce.rs.gov.br/aplicprod/f?p=50500:19:::NO:::';

function buildTceRsPortalUrl(cotacao) {
  const layers = cotacaoMetaLayers(cotacao);
  const direct = pickHttpUrl(
    ...layers.flatMap((layer) => [
      layer.url_origem,
      layer.link_licitacon_cidadao,
      layer.linkLicitaconCidadao,
      layer.LINK_LICITACON_CIDADAO,
      layer.link_portal,
      layer.link,
    ]),
  );
  if (direct) return direct;
  // Sem deep-link no índice: abre a busca pública do LicitaCon Cidadão.
  return TCE_RS_LICITACON_BUSCA;
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
  if (plat === 'tce_rs' || plat === 'tce-rs' || plat === 'licitacon') {
    return buildTceRsPortalUrl(cotacao);
  }

  const pncpUrl = buildPncpPortalProcessoUrl(cotacao);
  if (pncpUrl) return pncpUrl;

  // Itens TCE salvos sem plataforma explícita ainda podem ter o link LicitaCon.
  const layers = cotacaoMetaLayers(cotacao);
  return pickHttpUrl(
    ...layers.flatMap((layer) => [
      layer.url_origem,
      layer.link_licitacon_cidadao,
      layer.linkLicitaconCidadao,
      layer.LINK_LICITACON_CIDADAO,
    ]),
  );
}

export function pncpProcessoDisplayLabel(cotacao) {
  const src = cotacaoSource(cotacao);
  return String(
    cotacao?.numero_pncp || src.numero_pncp || src.numeroControlePNCP || '',
  ).trim();
}

export function fontePortalProcessoDisplayLabel(cotacao) {
  const plat = resolveCotacaoPlataforma(cotacao);
  if (plat === 'tce_rs') {
    for (const layer of cotacaoMetaLayers(cotacao)) {
      const label = String(
        layer.processo_id
        || layer.plataforma_item_id
        || layer.numero_processo
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
  if (plat === 'tce_rs' || plat === 'tce-rs' || plat === 'licitacon') return 'Ver no TCE-RS';
  const url = buildFontePortalProcessoUrl(cotacao);
  if (/portal\.tce\.rs\.gov\.br/i.test(url)) return 'Ver no TCE-RS';
  return 'Ver no PNCP';
}

export function fontePortalFieldLabel(cotacao) {
  const plat = resolveCotacaoPlataforma(cotacao);
  if (plat === 'tce_rs' || plat === 'tce-rs' || plat === 'licitacon') return 'Processo TCE-RS';
  const url = buildFontePortalProcessoUrl(cotacao);
  if (/portal\.tce\.rs\.gov\.br/i.test(url)) return 'Processo TCE-RS';
  return 'Processo PNCP';
}

export function fontePortalTitle(cotacao) {
  const label = fontePortalProcessoDisplayLabel(cotacao);
  const isTce =
    ['tce_rs', 'tce-rs', 'licitacon'].includes(resolveCotacaoPlataforma(cotacao))
    || /portal\.tce\.rs\.gov\.br/i.test(buildFontePortalProcessoUrl(cotacao));
  const portal = isTce ? 'portal TCE-RS (LicitaCon)' : 'portal PNCP';
  return label ? `Abrir processo ${label} no ${portal}` : `Abrir no ${portal}`;
}
