import { getApiBase } from './apiBase.js';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function defaultMaxAttempts() {
  const raw = String(
    import.meta.env.VITE_FILL_TR_SLOTS_RETRIES || import.meta.env.VITE_GERAR_TR_DFD_RETRIES || '',
  ).trim();
  const n = Number(raw);
  if (Number.isFinite(n) && n >= 1 && n <= 4) return Math.floor(n);
  // fill-tr-slots é o 1º passo (LLM lenta); 2 tentativas ajudam após timeout de proxy (~100s CF).
  return 2;
}

function backoffMs(attempt) {
  return Math.min(2400, 500 * 2 ** attempt);
}

function isTransientHttpStatus(status) {
  return [429, 502, 503, 520, 521, 522, 524].includes(status);
}

function errorMessageSuggestsRetry(msg) {
  const m = String(msg || '').toLowerCase();
  return /timeout|tempo limite|timed out|indispon|econnreset|connection reset|bad gateway|service unavailable|gateway timed|524|orquestração|llm/.test(
    m,
  );
}

export function buildFillTrSlotsUrl(apiBase) {
  const base = String(apiBase ?? getApiBase()).replace(/\/$/, '');
  const path = '/api/documentos/fill-tr-slots';
  if (base) return `${base}${path}`;
  if (typeof window !== 'undefined' && window.location?.origin) {
    return `${window.location.origin}${path}`;
  }
  return path;
}

/**
 * POST /api/documentos/fill-tr-slots com retries (proxy/Cloudflare cortam pedidos longos).
 */
export async function fetchFillTrSlotsWithRetry(apiBase, bodyObj, options = {}) {
  const maxAttempts = Math.max(1, Math.min(4, options.maxAttempts ?? defaultMaxAttempts()));
  const url = buildFillTrSlotsUrl(apiBase);
  const requestInit = {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(bodyObj),
    signal: options.signal,
  };

  let last = { ok: false, kind: 'unknown', errorMessage: 'Erro ao preencher objeto/justificativa.', status: 0, data: {} };

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    let res;
    try {
      res = await fetch(url, requestInit);
    } catch (netErr) {
      if (netErr?.name === 'AbortError') {
        return { ok: false, kind: 'abort', errorMessage: 'Pedido cancelado.', status: 0, data: {} };
      }
      last = {
        ok: false,
        kind: 'network',
        errorMessage: String(netErr?.message || netErr || 'Erro de rede'),
        status: 0,
        data: {},
      };
      if (attempt < maxAttempts - 1) {
        await sleep(backoffMs(attempt));
        continue;
      }
      return last;
    }

    const rawText = await res.text();
    let data = {};
    try {
      data = rawText ? JSON.parse(rawText) : {};
    } catch {
      const gateway = [502, 503, 504, 524].includes(res.status);
      last = {
        ok: false,
        kind: 'parse',
        errorMessage: gateway
          ? `HTTP ${res.status}: resposta não chegou em JSON (proxy/CDN pode ter cortado antes da IA terminar; Cloudflare grátis ~100s).`
          : `Resposta inválida (não é JSON). HTTP ${res.status}.`,
        status: res.status,
        data: {},
      };
      if (attempt < maxAttempts - 1 && isTransientHttpStatus(res.status)) {
        await sleep(backoffMs(attempt));
        continue;
      }
      return last;
    }

    if (res.ok && data.ok && data.slots && typeof data.slots === 'object') {
      return { ok: true, data, status: res.status };
    }

    const errMsg = data.error || data.detail || `Erro ${res.status}`;
    last = { ok: false, kind: 'api', errorMessage: errMsg, status: res.status, data };

    const retryable =
      attempt < maxAttempts - 1 &&
      (isTransientHttpStatus(res.status) || errorMessageSuggestsRetry(errMsg));

    if (retryable) {
      await sleep(backoffMs(attempt));
      continue;
    }

    return last;
  }

  return last;
}

export function describeFillTrSlotsNetworkFailure(apiUrl) {
  return (
    'Falha de rede em fill-tr-slots (objeto/justificativa pela IA). ' +
    'O browser não recebeu resposta HTTP válida — costuma ser timeout do proxy/CDN (~100s no Cloudflare grátis), não CORS. ' +
    'O sistema tenta de novo automaticamente; se persistir, aguarde e clique Gerar outra vez ou peça ao administrador timeouts maiores no nginx para /api/documentos/fill-tr-slots (ver deploy/nginx-gerar-tr-e-dfd-timeout.conf.example).\n\n' +
    `${apiUrl}`
  );
}
