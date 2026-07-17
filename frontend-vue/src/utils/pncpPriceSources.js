import { listPriceSources } from '../services/pncpResearch';

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
];

/** Mescla catálogo da API com totais/readiness do /local-index/stats. */
export function mergeFontesWithLocalStats(fontes, localStats) {
  const por = Array.isArray(localStats?.por_plataforma) ? localStats.por_plataforma : [];
  return (fontes || []).map((f) => {
    const st = por.find((p) => p.id === f.id);
    if (!st) return { ...f };
    return {
      ...f,
      search_ready: st.search_ready != null ? Boolean(st.search_ready) : f.search_ready,
      total_itens: st.total_itens != null ? Number(st.total_itens) : f.total_itens,
      db_exists: st.db_exists != null ? Boolean(st.db_exists) : f.db_exists,
    };
  });
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

export function plataformaLabel(id, fontes = []) {
  const key = String(id || 'pncp').trim().toLowerCase();
  const hit = (fontes || []).find((f) => f.id === key);
  if (hit?.label) return hit.label;
  if (key === 'tce_rs') return 'TCE-RS (LicitaCon)';
  if (key === 'pncp') return 'PNCP';
  return key.toUpperCase();
}

export function plataformaBadgeShort(id) {
  const key = String(id || 'pncp').trim().toLowerCase();
  if (key === 'tce_rs') return 'TCE-RS';
  if (key === 'pncp') return 'PNCP';
  return key.toUpperCase();
}

export async function loadPriceSourcesCatalog() {
  try {
    const res = await listPriceSources();
    if (res?.ok && Array.isArray(res.fontes) && res.fontes.length) {
      return res.fontes.map((f) => ({ ...f }));
    }
  } catch (_) {
    /* offline / proxy */
  }
  return FALLBACK_FONTES.map((f) => ({ ...f }));
}

export function federatedItemPlataforma(it) {
  return String(it?.plataforma || 'pncp').trim().toLowerCase();
}

export function federatedItemProcessoRef(it) {
  const proc = it?.numero_pncp
    || it?.processo_id
    || it?.plataforma_item_id
    || it?.numero_processo
    || null;
  return proc ? String(proc).trim() : null;
}
