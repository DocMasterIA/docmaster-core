const FALLBACK_FONTES = [
  {
    id: 'pncp',
    label: 'PNCP (Portal Nacional de Contratações Públicas)',
    search_ready: true,
  },
  {
    id: 'tce_rs',
    label: 'TCE-RS (LicitaCon)',
    search_ready: false,
    uf_scope: 'RS',
  },
  {
    id: 'compras_gov',
    label: 'Compras.gov (Dados Abertos)',
    search_ready: false,
  },
  {
    id: 'notas_fiscais',
    label: 'Notas Fiscais (Portal da Transparência)',
    search_ready: false,
  },
];

/** Mescla catálogo da API com totais/readiness do /local-index/stats. */
export function mergeFontesWithLocalStats(fontes, localStats) {
  const por = Array.isArray(localStats?.por_plataforma) ? localStats.por_plataforma : [];
  return (fontes || []).map((f) => {
    const st = por.find((p) => p.id === f.id);
    if (!st) return { ...f };
    const total = st.total_itens != null ? Number(st.total_itens) : f.total_itens;
    let searchReady = f.search_ready;
    if (st.search_ready != null) {
      searchReady = Boolean(st.search_ready);
    } else if (Number.isFinite(total) && total > 0) {
      // PNCP legacy não envia search_ready — índice com itens = consultável.
      searchReady = true;
    }
    return {
      ...f,
      search_ready: searchReady,
      total_itens: total,
      db_exists: st.db_exists != null ? Boolean(st.db_exists) : f.db_exists,
    };
  });
}

/**
 * Quando /local-index/stats falha, não desabilitar fontes no catálogo:
 * a busca federada usa os .db locais e pode funcionar mesmo sem totais na UI.
 */
export function applyFontesWhenStatsUnavailable(fontes) {
  return (fontes || []).map((f) => ({
    ...f,
    search_ready: Boolean(f?.id),
    stats_degraded: true,
  }));
}

/** Evita mostrar «0 itens» quando stats ainda não carregou ou falhou. */
export function formatTotalItensIndexados(localStats, { loading = false, degraded = false } = {}) {
  if (loading) return '…';
  if (!localStats) return degraded ? '—' : '…';
  const todas = Number(localStats.total_itens_todas_fontes);
  if (Number.isFinite(todas) && todas > 0) return todas.toLocaleString('pt-BR');
  const pncp = Number(localStats.total_itens || 0);
  return pncp.toLocaleString('pt-BR');
}

export function pickDefaultFontes(fontes) {
  const ready = (fontes || [])
    .filter((f) => f?.id && f.search_ready !== false)
    .map((f) => f.id);
  const out = [];
  if (ready.includes('pncp')) out.push('pncp');
  else out.unshift('pncp');
  for (const id of ready) {
    if (!out.includes(id)) out.push(id);
  }
  return out.length ? out : ['pncp'];
}

export function normalizePlataformaId(id) {
  return String(id || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
    .toLowerCase()
    .replace(/-/g, '_');
}

export function isTceRsPlatform(id) {
  const key = normalizePlataformaId(id);
  return key === 'tce_rs' || key === 'licitacon';
}

export function isComprasGovPlatform(id) {
  const key = normalizePlataformaId(id);
  return key === 'compras_gov' || key === 'comprasgov';
}

export function isNotasFiscaisPlatform(id) {
  const key = normalizePlataformaId(id);
  return key === 'notas_fiscais' || key === 'notasfiscais' || key === 'nfe';
}

/**
 * Metadados de save por plataforma (inciso / esfera / bucket de fonte).
 * Fallbacks só entram quando a plataforma não tem regra própria.
 */
export function platformSaveMeta(plat, fallbacks = {}) {
  if (isTceRsPlatform(plat)) {
    return {
      inciso_classificacao: 'inciso_ii',
      esfera_administrativa: 'estadual',
      fonte: 'entes_publicos',
    };
  }
  if (isComprasGovPlatform(plat)) {
    return {
      inciso_classificacao: 'inciso_i',
      esfera_administrativa: 'federal',
      fonte: 'governamentais',
    };
  }
  if (isNotasFiscaisPlatform(plat)) {
    return {
      inciso_classificacao: 'inciso_v',
      esfera_administrativa: 'federal',
      fonte: 'notas_fiscais',
    };
  }
  const inciso = fallbacks.inciso_classificacao || fallbacks.inciso || null;
  let fonte = fallbacks.fonte || null;
  if (!fonte && inciso === 'inciso_i') fonte = 'governamentais';
  if (!fonte && inciso === 'inciso_ii') fonte = 'entes_publicos';
  if (!fonte && inciso === 'inciso_v') fonte = 'notas_fiscais';
  return {
    inciso_classificacao: inciso,
    esfera_administrativa: fallbacks.esfera_administrativa || fallbacks.esfera || null,
    fonte,
  };
}

export function plataformaLabel(id, fontes = []) {
  const key = normalizePlataformaId(id) || 'pncp';
  const hit = (fontes || []).find((f) => normalizePlataformaId(f.id) === key);
  if (hit?.label) return hit.label;
  if (isTceRsPlatform(key)) return 'TCE-RS (LicitaCon)';
  if (isComprasGovPlatform(key)) return 'Compras.gov (Dados Abertos)';
  if (isNotasFiscaisPlatform(key)) return 'Notas Fiscais (Portal da Transparência)';
  if (key === 'pncp') return 'PNCP';
  return key.toUpperCase();
}

export function plataformaBadgeShort(id) {
  const key = normalizePlataformaId(id) || 'pncp';
  if (isTceRsPlatform(key)) return 'TCE-RS';
  if (isComprasGovPlatform(key)) return 'Compras.gov';
  if (isNotasFiscaisPlatform(key)) return 'Notas Fiscais';
  if (key === 'pncp') return 'PNCP';
  return key.toUpperCase();
}

/** Rótulo curto da coluna Fonte (relatório / detalhe). */
export function plataformaFonteCurta(id) {
  const key = normalizePlataformaId(id) || 'pncp';
  if (isTceRsPlatform(key)) return 'TCE-RS';
  if (isComprasGovPlatform(key)) return 'Compras.gov';
  if (isNotasFiscaisPlatform(key)) return 'Notas Fiscais';
  if (key === 'pncp') return 'PNCP';
  return plataformaBadgeShort(key);
}

export async function loadPriceSourcesCatalog() {
  try {
    // Import dinâmico: evita puxar o client HTTP em testes Node dos helpers puros.
    const { listPriceSources } = await import('../services/pncpResearch.js');
    const res = await listPriceSources();
    if (res?.ok && Array.isArray(res.fontes) && res.fontes.length) {
      return res.fontes.map((f) => ({ ...f }));
    }
  } catch (_) {
    /* offline / proxy / ambiente sem bundler */
  }
  return FALLBACK_FONTES.map((f) => ({ ...f }));
}

export function federatedItemPlataforma(it) {
  return normalizePlataformaId(it?.plataforma || 'pncp') || 'pncp';
}

export function federatedItemProcessoRef(it) {
  const proc = it?.numero_pncp
    || it?.processo_id
    || it?.plataforma_item_id
    || it?.numero_processo
    || null;
  return proc ? String(proc).trim() : null;
}
