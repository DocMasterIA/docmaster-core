/**
 * Prefill da Busca Manual ao sair do detalhe do item (evita tela vazia se o GET da sessão falhar).
 */

function prefillKey(cotacaoId, itemId) {
  return `dm-manual-prefill:${cotacaoId}:${itemId}`;
}

export function stashManualSearchPrefill(cotacaoId, itemId, payload) {
  if (!cotacaoId || !itemId || !payload || typeof payload !== 'object') return;
  try {
    sessionStorage.setItem(
      prefillKey(cotacaoId, itemId),
      JSON.stringify({ ...payload, ts: Date.now() }),
    );
  } catch {
    /* quota / private mode */
  }
}

/** Lê e remove o prefill (one-shot). */
export function takeManualSearchPrefill(cotacaoId, itemId) {
  if (!cotacaoId || !itemId) return null;
  const key = prefillKey(cotacaoId, itemId);
  try {
    const raw = sessionStorage.getItem(key);
    if (!raw) return null;
    sessionStorage.removeItem(key);
    const data = JSON.parse(raw);
    if (!data || typeof data !== 'object') return null;
    if (data.ts && Date.now() - Number(data.ts) > 30 * 60 * 1000) return null;
    return data;
  } catch {
    return null;
  }
}
