/**
 * Base URL da API Django nos `fetch` do browser.
 * - Dev (Vite): string vazia → mesmo origin + proxy `/api` → backend local.
 * - Produção com `VITE_API_URL` definido: usa esse host (ajusta http→https se a página for https).
 * - Produção com `VITE_API_URL` vazio: fallback `https://api.docmasteria.com.br` (SPA estático em outro host
 *   sem proxy /api devolve HTML em /api/me → quebra JSON; não usar origem da página nesse caso).
 * - Mesmo host + nginx com `/api` → Django: `VITE_API_URL` vazio e `VITE_API_USE_PAGE_ORIGIN=1` no build
 *   (não use PAGE_ORIGIN se o SPA está noutro domínio que a API, ex.: docmaster.com.br → api.docmasteria.com.br).
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
  const origin =
    typeof window !== 'undefined' && window.location?.origin ? window.location.origin : '';
  const crossHost =
    origin &&
    apiUrl &&
    !apiUrl.startsWith(origin) &&
    /^https?:\/\//i.test(String(apiUrl));
  const corsHint = crossHost
    ? ` Origem ${origin} ≠ host da API: net::ERR_FAILED costuma ser rede, TLS, firewall, extensão ou proxy — não é necessariamente CORS (CORS na consola traz mensagem explícita a bloquear leitura da resposta). Se for CORS, o Django tem de enviar Access-Control-Allow-Origin para esse origin (credentials exigem correspondência exata); docmasteria/docmaster já estão nos defaults do backend e há regex para subdomínios.`
    : '';
  const viteHint =
    ' VITE_API_USE_PAGE_ORIGIN=1 só quando o mesmo site serve o SPA e o proxy /api para o Django; com API noutro host use VITE_API_URL=https://… (API).';
  return `Não foi possível contactar ${shortLabel} (${apiUrl}). Verifique rede, HTTPS e extensões.${corsHint}${viteHint}`;
}
