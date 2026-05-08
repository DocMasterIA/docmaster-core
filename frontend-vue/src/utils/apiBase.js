/**
 * Base URL da API Django nos `fetch` do browser.
 * - Dev (Vite): string vazia → mesmo origin + proxy `/api` → backend local.
 * - Produção: `VITE_API_URL` trimado, sem barra final; fallback https://api.docmasteria.com.br
 * - Se a página for HTTPS e o env vier como http://..., força https para evitar mixed content (Chrome: net::ERR_FAILED).
 */
export function getApiBase() {
  const raw = String(import.meta.env.VITE_API_URL || '').trim().replace(/\/$/, '');
  if (raw) {
    if (
      !import.meta.env.DEV &&
      typeof window !== 'undefined' &&
      window.location?.protocol === 'https:' &&
      /^http:\/\//i.test(raw)
    ) {
      return raw.replace(/^http:/i, 'https:');
    }
    return raw;
  }
  if (import.meta.env.DEV) return '';
  return 'https://api.docmasteria.com.br';
}

/** URL absoluta usada no POST de geração TR+DFD (útil para mensagens de erro e logs). */
export function buildGerarTrEDfdUrl(apiBase) {
  const base = String(apiBase || '').replace(/\/$/, '');
  const path = '/api/documentos/gerar-tr-e-dfd';
  if (base) return `${base}${path}`;
  if (typeof window !== 'undefined' && window.location?.origin) {
    return `${window.location.origin}${path}`;
  }
  return path;
}
