import { buildGerarTrEDfdUrl } from './apiBase.js';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function defaultMaxAttempts() {
  const raw = String(import.meta.env.VITE_GERAR_TR_DFD_RETRIES || '').trim();
  const n = Number(raw);
  if (Number.isFinite(n) && n >= 1 && n <= 4) return Math.floor(n);
  return 1;
}

function backoffMs(attempt) {
  return Math.min(2400, 350 * 2 ** attempt);
}

function isTransientHttpStatus(status) {
  // Sem 504: costuma ser «já esgotou o tempo» no backend; repetir só prolonga o travamento.
  return [429, 502, 503, 520, 521, 522, 524].includes(status);
}

function errorMessageSuggestsRetry(msg) {
  const m = String(msg || '').toLowerCase();
  return /timeout|tempo limite|timed out|indispon|econnreset|connection reset|bad gateway|service unavailable|gateway timed|524/.test(m);
}

/**
 * POST /api/documentos/gerar-tr-e-dfd com retries para falhas transitórias
 * (rede, proxy, rag_service ocupado).
 *
 * @param {string} apiBase - retorno de getApiBase()
 * @param {object} bodyObj - corpo JSON (já sanitizado se necessário)
 * @param {{ maxAttempts?: number, signal?: AbortSignal }} [options]
 * @returns {Promise<{ ok: true, data: object, status: number } | { ok: false, kind: string, errorMessage: string, status: number, data?: object }>}
 */
export async function fetchGerarTrEDfdWithRetry(apiBase, bodyObj, options = {}) {
  const maxAttempts = Math.max(1, Math.min(5, options.maxAttempts ?? defaultMaxAttempts()));
  const url = buildGerarTrEDfdUrl(apiBase);
  const requestInit = {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(bodyObj),
    signal: options.signal,
  };

  let last = { kind: 'unknown', errorMessage: 'Erro ao gerar documento.', status: 0, data: {} };

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    let res;
    try {
      res = await fetch(url, requestInit);
    } catch (netErr) {
      if (netErr?.name === 'AbortError') {
        return { ok: false, kind: 'abort', errorMessage: 'Pedido cancelado.', status: 0, data: {} };
      }
      last = {
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
    let parsed = false;
    try {
      data = rawText ? JSON.parse(rawText) : {};
      parsed = true;
    } catch {
      parsed = false;
    }

    if (!parsed) {
      last = {
        kind: 'parse',
        errorMessage: rawText.trim().startsWith('<')
          ? `Servidor devolveu HTML em vez de JSON (proxy ou erro ${res.status}).`
          : `Resposta inválida do servidor (não é JSON). HTTP ${res.status}.`,
        status: res.status,
        data: {},
      };
      if (attempt < maxAttempts - 1 && isTransientHttpStatus(res.status)) {
        await sleep(backoffMs(attempt));
        continue;
      }
      return last;
    }

    const hasDocs =
      Boolean(data.tr?.docx_base64) && Boolean(data.dfd?.docx_base64) && Boolean(data.oficio?.docx_base64);
    if (res.ok && data.ok && hasDocs) {
      return { ok: true, data, status: res.status };
    }

    const errMsg = data.error || data.detail || `Erro ${res.status}`;
    last = { kind: 'api', errorMessage: errMsg, status: res.status, data };

    const retryable =
      attempt < maxAttempts - 1 &&
      (isTransientHttpStatus(res.status) || (res.ok && !data.ok && errorMessageSuggestsRetry(errMsg)));

    if (retryable) {
      await sleep(backoffMs(attempt));
      continue;
    }

    return last;
  }

  return last;
}

export function describeGerarTrEDfdNetworkFailure(gerarUrl) {
  return `Falha de rede ao gerar o documento (ligação interrompida, firewall ou tempo limite). Com muitos itens o pedido pode demorar mais. Tente de novo em instantes ou reduza linhas vazias.\n\n${gerarUrl}`;
}
