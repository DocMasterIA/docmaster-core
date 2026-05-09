/**
 * Base URL da API Django nos `fetch` do browser.
 * - Dev (Vite): string vazia → mesmo origin + proxy `/api` → backend local.
 * - Produção: `VITE_API_URL` trimado, sem barra final; fallback https://api.docmasteria.com.br
 * - `VITE_API_USE_PAGE_ORIGIN=1` + `VITE_API_URL` vazio: em build de produção usa `window.location.origin`
 *   (útil quando o mesmo nginx serve o SPA e faz proxy de `/api` — evita cross-origin e net::ERR_FAILED).
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
  const usePage =
    String(import.meta.env.VITE_API_USE_PAGE_ORIGIN || '').trim() === '1' &&
    typeof window !== 'undefined' &&
    window.location?.origin;
  if (usePage) return String(window.location.origin).replace(/\/$/, '');
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

/** Mensagem quando o browser falha antes do HTTP (Chrome: net::ERR_FAILED / Failed to fetch). */
export function describeApiFetchNetworkFailure(apiUrl, shortLabel = 'API') {
  return [
    `Não foi possível contactar a ${shortLabel} (${apiUrl}).`,
    'Isto não é causado por opções de itens na tabela, numeração de processo ou flags de geração — o pedido nem chegou a responder em JSON.',
    'Verifique: HTTPS, certificado, VPN, extensão bloqueadora, e se o deploy usa o mesmo domínio com proxy /api/ (neste caso use build com VITE_API_URL vazio e VITE_API_USE_PAGE_ORIGIN=1).',
  ].join(' ');
}
