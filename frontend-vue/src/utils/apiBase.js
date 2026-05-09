/**
 * Base URL da API Django nos `fetch` do browser.
 * - Dev (Vite): string vazia → mesmo origin + proxy `/api` → backend local.
 * - Produção com `VITE_API_URL` definido: usa esse host (ajusta http→https se a página for https).
 * - Produção com `VITE_API_URL` vazio: fallback `https://api.docmasteria.com.br` (SPA estático em outro host
 *   sem proxy /api devolve HTML em /api/me → quebra JSON; não usar origem da página nesse caso).
 * - Mesmo host + nginx com `/api` → Django: `VITE_API_URL` vazio e `VITE_API_USE_PAGE_ORIGIN=1` no build.
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
  const usePageOrigin =
    String(import.meta.env.VITE_API_USE_PAGE_ORIGIN || '').trim() === '1' &&
    typeof window !== 'undefined' &&
    window.location?.origin;
  if (usePageOrigin) return String(window.location.origin).replace(/\/$/, '');
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

/** Mensagem curta quando o fetch falha no browser (ex.: Failed to fetch / CORS). */
export function describeApiFetchNetworkFailure(apiUrl, shortLabel = 'API') {
  return `Não foi possível contactar ${shortLabel} (${apiUrl}). Verifique rede, HTTPS e CORS. Se o Django está no mesmo domínio com proxy /api, use no build VITE_API_USE_PAGE_ORIGIN=1 e VITE_API_URL vazio; caso contrário defina VITE_API_URL com o host da API.`;
}
