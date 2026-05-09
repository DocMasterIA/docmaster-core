/**
 * Base URL da API Django nos `fetch` do browser.
 * - Dev (Vite): string vazia → mesmo origin + proxy `/api` → backend local.
 * - Produção com `VITE_API_URL` definido: usa esse host (ajusta http→https se a página for https).
 * - Produção com `VITE_API_URL` vazio: usa `window.location.origin` (nginx costuma expor `/api` no mesmo host do SPA;
 *   evita pedidos cross-origin para api.* e erros tipo Failed to fetch / net::ERR_FAILED).
 * - API só em subdomínio separado: defina `VITE_API_URL=https://api.docmasteria.com.br` no build.
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
  if (typeof window !== 'undefined' && window.location?.origin) {
    return String(window.location.origin).replace(/\/$/, '');
  }
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
  return `Não foi possível contactar ${shortLabel} (${apiUrl}). Verifique rede, HTTPS e se o build usa a mesma origem do site quando o Django está em /api (VITE_API_URL vazio); se a API for só em outro host, defina VITE_API_URL nesse build.`;
}
