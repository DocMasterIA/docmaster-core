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
