// Em desenvolvimento, usa proxy do Vite (/api -> backend local) para evitar bater na API remota.
const API_BASE = import.meta.env.DEV ? '' : (import.meta.env.VITE_API_URL || 'https://api.docmasteria.com.br');

function flattenErrorDetail(raw) {
  if (raw == null || raw === '') return '';
  if (typeof raw === 'string') return raw.trim();
  if (typeof raw === 'number' || typeof raw === 'boolean') return String(raw);
  if (Array.isArray(raw)) {
    return raw
      .map((item) => {
        if (item == null) return '';
        if (typeof item === 'string') return item.trim();
        if (typeof item === 'object') {
          const loc = Array.isArray(item.loc)
            ? item.loc.filter((x) => x !== 'body').join('.')
            : '';
          const m = String(item.msg || item.message || item.detail || '').trim();
          if (loc && m) return `${loc}: ${m}`;
          return m || flattenErrorDetail(item);
        }
        return String(item);
      })
      .filter(Boolean)
      .join('; ');
  }
  if (typeof raw === 'object') {
    if (raw.msg || raw.message) return String(raw.msg || raw.message).trim();
    if (raw.detail != null && raw.detail !== raw) return flattenErrorDetail(raw.detail);
    if (raw.error != null && raw.error !== raw) return flattenErrorDetail(raw.error);
    try {
      return JSON.stringify(raw);
    } catch {
      return '';
    }
  }
  return String(raw).trim();
}

function extractErrorMessage(payload, status) {
  let p = payload;
  if (typeof p === 'string') {
    const t = p.trim();
    if (t.startsWith('{') || t.startsWith('[')) {
      try {
        p = JSON.parse(t);
      } catch {
        /* manter string */
      }
    }
  }
  const raw =
    typeof p === 'object' && p !== null ? (p.detail ?? p.error ?? p) : p;
  const msg = flattenErrorDetail(raw);
  const looksLikeHtml =
    /^<!doctype html/i.test(msg) || /^<html/i.test(msg) || /<body[\s>]/i.test(msg.slice(0, 400));
  // Gateway/Django HTML error page — não há JSON com detalhe.
  if (looksLikeHtml) {
    if (status >= 500) {
      if (status === 502 || status === 504) {
        return 'O proxy ou o gateway encerrou a ligação (502/504). Se estiver a gerar um PDF grande, peça ao administrador para desativar buffering no nginx (proxy_buffering off) ou aumentar timeouts para /api/.';
      }
      return 'Servidor ou proxy retornou erro temporário (sem detalhe). Tente novamente em instantes.';
    }
    return `Erro HTTP ${status}`;
  }
  if (status >= 500 && !msg) {
    return 'Erro temporário no servidor. Tente novamente em instantes.';
  }
  if (!msg || msg === '[object Object]') {
    return `Erro HTTP ${status || 'desconhecido'}`;
  }
  return msg;
}

/** Mensagem legível para UI a partir de Error / resposta API / Abort. */
export function formatResearchError(err) {
  if (err == null) return 'erro desconhecido';
  if (isClientTimeoutError(err)) {
    return 'A operação demorou demais (timeout). Tente de novo em instantes.';
  }
  if (isUserAbortError(err)) {
    return 'Operação cancelada.';
  }
  const status = Number(err?.status);
  if (status === 502 || status === 504) {
    return 'Serviço temporariamente indisponível (proxy). Tente de novo em instantes.';
  }
  if (status === 503) {
    return 'Serviço sobrecarregado. Tente de novo em instantes.';
  }
  if (isNetworkFetchError(err)) {
    return 'Falha de rede ao contactar o backend (conexão interrompida). Tente novamente em alguns segundos.';
  }
  const fromMsg = flattenErrorDetail(err?.message);
  if (fromMsg && fromMsg !== '[object Object]' && !/^failed to fetch$/i.test(fromMsg)) {
    return fromMsg;
  }
  const fromDetail = flattenErrorDetail(err?.detail ?? err?.error ?? err);
  if (fromDetail && fromDetail !== '[object Object]') return fromDetail;
  return 'erro desconhecido';
}

/** Proxy FastAPI: índice local, market-search, streams. */
function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isNetworkFetchError(err) {
  const name = String(err?.name || '');
  const msg = String(err?.message || err || '');
  return (
    name === 'TypeError'
    || name === 'TimeoutError'
    || /failed to fetch|networkerror|load failed|network error|err_failed|timed out|timeout/i.test(msg)
  );
}

function isClientTimeoutError(err) {
  if (!err) return false;
  if (String(err?.name || '') === 'TimeoutError') return true;
  const reason = err?.cause || err?.reason;
  if (reason && String(reason?.name || '') === 'TimeoutError') return true;
  const msg = String(err?.message || '');
  return /timed out|timeout|signal timed out|the operation was aborted due to timeout/i.test(msg);
}

/** Abort explícito do usuário / navegação — não confundir com timeout do AbortSignal.timeout. */
function isUserAbortError(err) {
  if (!err) return false;
  if (isClientTimeoutError(err)) return false;
  const name = String(err?.name || '');
  const msg = String(err?.message || '');
  return name === 'AbortError' || /aborted|abort|canceled|cancelled/i.test(msg);
}

function mergeAbortSignals(userSignal, timeoutMs) {
  const ms = Number(timeoutMs);
  if (!Number.isFinite(ms) || ms <= 0) {
    return userSignal || undefined;
  }
  const ac = new AbortController();
  let timer = null;
  const abort = () => {
    if (timer != null) clearTimeout(timer);
    if (!ac.signal.aborted) ac.abort();
  };
  if (userSignal) {
    if (userSignal.aborted) {
      abort();
      return ac.signal;
    }
    userSignal.addEventListener('abort', abort, { once: true });
  }
  if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') {
    const timeoutSignal = AbortSignal.timeout(ms);
    if (timeoutSignal.aborted) {
      abort();
      return ac.signal;
    }
    timeoutSignal.addEventListener('abort', abort, { once: true });
  } else {
    timer = setTimeout(abort, ms);
  }
  return ac.signal;
}

async function researchRequest(path, { method = 'GET', body, signal, timeoutMs } = {}) {
  const res = await fetch(`${API_BASE}/api/pncp-research/${path}`, {
    method,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
    body: body ? JSON.stringify(body) : undefined,
    signal: mergeAbortSignals(signal, timeoutMs),
  });

  const ctype = (res.headers.get('content-type') || '').toLowerCase();
  const payload = ctype.includes('application/json') ? await res.json() : await res.text();

  if (!res.ok) {
    const err = new Error(extractErrorMessage(payload, res.status));
    err.status = res.status;
    throw err;
  }
  return payload;
}

/** Resolve deep-links LicitaCon/PNCP no índice da plataforma (cotações sem url_origem). */
export async function resolvePlatformPortalUrls({
  plataforma = 'tce_rs',
  keys = [],
  signal,
} = {}) {
  const cleaned = [...new Set((keys || []).map((k) => String(k || '').trim()).filter(Boolean))];
  if (!cleaned.length) return { ok: true, urls: {} };
  return researchRequest('platform/portal-urls', {
    method: 'POST',
    body: { plataforma, keys: cleaned.slice(0, 200) },
    signal,
    timeoutMs: 30_000,
  });
}

/** Cotações / sessões persistidas no Django (ORM). */
async function cotacaoRequest(path, { method = 'GET', body, signal, timeoutMs } = {}) {
  const defaultTimeout = method === 'GET' ? 0 : 120_000;
  const res = await fetch(`${API_BASE}/api/pncp/cotacoes/${path}`, {
    method,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
    body: body ? JSON.stringify(body) : undefined,
    signal: mergeAbortSignals(signal, timeoutMs ?? defaultTimeout),
  });

  const ctype = (res.headers.get('content-type') || '').toLowerCase();
  const payload = ctype.includes('application/json') ? await res.json() : await res.text();

  if (!res.ok) {
    throw new Error(extractErrorMessage(payload, res.status));
  }
  return payload;
}

/** Dados do usuário logado (mesmo formato que `/api/me/` GET). */
export async function fetchCurrentUser(signal) {
  const res = await fetch(`${API_BASE}/api/me/`, { credentials: 'include', signal });
  if (!res.ok) return null;
  return res.json();
}

export function listResearchSessions(limit = 100, signal) {
  return cotacaoRequest(`research/sessions?limit=${encodeURIComponent(limit)}`, { signal });
}

export function listFornecedoresCadastrados(limit = 100, signal) {
  return cotacaoRequest(`fornecedores?limit=${encodeURIComponent(limit)}`, { signal });
}

export function saveFornecedorCadastrado(fornecedor, signal) {
  return cotacaoRequest('fornecedores', {
    method: 'POST',
    body: { fornecedor },
    signal,
  });
}

export function createResearchSession(payload, signal) {
  return cotacaoRequest('research/sessions', {
    method: 'POST',
    body: payload,
    signal,
  });
}

export function getResearchSession(sessaoId, { signal, relatorio = false, timeoutMs = 180_000 } = {}) {
  const q = relatorio ? '?relatorio=1' : '';
  return cotacaoRequest(`research/sessions/${encodeURIComponent(sessaoId)}${q}`, { signal, timeoutMs });
}

/**
 * Carrega sessão com retries em falhas transitórias (502/504/rede/timeout).
 * Usado na página da cotação, onde o GET às vezes falha sob carga.
 */
export async function getResearchSessionResilient(sessaoId, options = {}) {
  const maxAttempts = Math.max(1, Math.min(4, Number(options.maxAttempts) || 3));
  const timeoutMs = options.timeoutMs ?? (options.relatorio ? 180_000 : 120_000);
  let lastErr = null;
  for (let i = 0; i < maxAttempts; i += 1) {
    try {
      return await getResearchSession(sessaoId, {
        signal: options.signal,
        relatorio: options.relatorio,
        timeoutMs,
      });
    } catch (err) {
      lastErr = err;
      if (isUserAbortError(err) || !isRetryableSearchError(err) || i >= maxAttempts - 1) {
        throw err;
      }
      await sleep(Math.min(2400, 500 * (i + 1)));
    }
  }
  throw lastErr || new Error('Falha ao carregar sessão.');
}

/** Lista paginada e leve de itens para busca inteligente em lote (centenas de itens). */
export function getResearchSessionItemsSearchContext(
  sessaoId,
  { offset = 0, limit = 250, somenteIncompletos = true, signal } = {},
) {
  const q = new URLSearchParams({
    offset: String(Math.max(0, Number(offset) || 0)),
    limit: String(Math.max(1, Math.min(500, Number(limit) || 250))),
    somente_incompletos: somenteIncompletos ? '1' : '0',
  });
  return cotacaoRequest(
    `research/sessions/${encodeURIComponent(sessaoId)}/items/search-context?${q}`,
    { signal },
  );
}

export async function fetchAllItemsForBulkSearch(
  sessaoId,
  { somenteIncompletos = true, signal, onPage } = {},
) {
  const PAGE = 250;
  let offset = 0;
  const all = [];
  let sessao = null;
  let stats = null;
  let pageInfo = null;
  for (;;) {
    const page = await getResearchSessionItemsSearchContext(sessaoId, {
      offset,
      limit: PAGE,
      somenteIncompletos,
      signal,
    });
    if (!page?.ok) {
      throw new Error(page?.error || page?.detail || 'Falha ao carregar itens da cotação.');
    }
    sessao = page.sessao || sessao;
    stats = page.stats || stats;
    pageInfo = page.page || pageInfo;
    const chunk = Array.isArray(page.itens) ? page.itens : [];
    all.push(...chunk);
    if (typeof onPage === 'function') {
      onPage({ loaded: all.length, stats, page: page.page });
    }
    if (!page?.page?.has_more || chunk.length === 0) break;
    offset += chunk.length;
  }
  return { sessao, itens: all, stats, page: pageInfo };
}

export function updateResearchSession(sessaoId, payload, signal) {
  return cotacaoRequest(`research/sessions/${encodeURIComponent(sessaoId)}/update`, {
    method: 'POST',
    body: payload,
    signal,
  });
}

export function deleteResearchSession(sessaoId, signal) {
  return cotacaoRequest(`research/sessions/${encodeURIComponent(sessaoId)}`, {
    method: 'DELETE',
    signal,
  });
}

export function addItemsToResearchSession(sessaoId, itens, signal) {
  return cotacaoRequest(`research/sessions/${encodeURIComponent(sessaoId)}/items`, {
    method: 'POST',
    body: { itens },
    signal,
  });
}

export function getItemCotacoesFromResearchSession(sessaoId, itemId, signal) {
  return cotacaoRequest(
    `research/sessions/${encodeURIComponent(sessaoId)}/items/${encodeURIComponent(itemId)}/cotacoes`,
    { signal },
  );
}

export function addCotacoesToItemInResearchSession(sessaoId, itemId, cotacoes, signal) {
  return cotacaoRequest(
    `research/sessions/${encodeURIComponent(sessaoId)}/items/${encodeURIComponent(itemId)}/cotacoes`,
    {
      method: 'POST',
      body: { cotacoes },
      signal,
    },
  );
}

export function updateCotacaoInItemResearchSession(sessaoId, itemId, cotacaoId, cotacao, signal) {
  return cotacaoRequest(
    `research/sessions/${encodeURIComponent(sessaoId)}/items/${encodeURIComponent(itemId)}/cotacoes/${encodeURIComponent(cotacaoId)}/update`,
    {
      method: 'POST',
      body: { cotacao },
      signal,
    },
  );
}

/** Remove uma cotação de preço ligada ao item (qualquer fonte: PNCP, manual, direta, domínio amplo, etc.). */
export function deleteCotacaoFromItemResearchSession(sessaoId, itemId, cotacaoId, signal) {
  return cotacaoRequest(
    `research/sessions/${encodeURIComponent(sessaoId)}/items/${encodeURIComponent(itemId)}/cotacoes/${encodeURIComponent(cotacaoId)}/delete`,
    {
      method: 'POST',
      body: {},
      signal,
    },
  );
}

export function deleteItemsFromResearchSession(sessaoId, itemIds, signal) {
  return cotacaoRequest(`research/sessions/${encodeURIComponent(sessaoId)}/items/delete`, {
    method: 'POST',
    body: { item_ids: itemIds },
    signal,
  });
}

/** Atualiza metadados do item (ex.: valor base da faixa regional). Variação % é só na sessão. */
export function updateResearchSessionItem(sessaoId, itemId, payload, signal) {
  return cotacaoRequest(
    `research/sessions/${encodeURIComponent(sessaoId)}/items/${encodeURIComponent(itemId)}/update`,
    {
      method: 'POST',
      body: payload,
      signal,
    },
  );
}

export async function importItemsSpreadsheetToResearchSession(sessaoId, file, columnMap = {}, signal) {
  const form = new FormData();
  form.append('arquivo', file);
  form.append('column_map', JSON.stringify(columnMap || {}));

  const res = await fetch(
    `${API_BASE}/api/pncp/cotacoes/research/sessions/${encodeURIComponent(sessaoId)}/items/import`,
    {
      method: 'POST',
      credentials: 'include',
      body: form,
      signal,
    },
  );

  const ctype = (res.headers.get('content-type') || '').toLowerCase();
  const payload = ctype.includes('application/json') ? await res.json() : await res.text();
  if (!res.ok) throw new Error(extractErrorMessage(payload, res.status));
  return payload;
}

export async function uploadSupplierPdfToResearchSession(sessaoId, files, signal) {
  const form = new FormData();
  const list = Array.isArray(files) ? files : [files];
  for (const f of list) {
    if (f) form.append('arquivo', f);
  }
  const res = await fetch(
    `${API_BASE}/api/pncp/cotacoes/research/sessions/${encodeURIComponent(sessaoId)}/attachments/supplier-pdf`,
    {
      method: 'POST',
      credentials: 'include',
      body: form,
      signal,
    },
  );
  const ctype = (res.headers.get('content-type') || '').toLowerCase();
  const payload = ctype.includes('application/json') ? await res.json() : await res.text();
  if (!res.ok) throw new Error(extractErrorMessage(payload, res.status));
  return payload;
}

export async function downloadResearchSessionExcel(sessaoId, fields = null, signal) {
  const hasBody = fields && typeof fields === 'object';
  const res = await fetch(
    `${API_BASE}/api/pncp/cotacoes/research/sessions/${encodeURIComponent(sessaoId)}/export/xlsx`,
    {
      method: hasBody ? 'POST' : 'GET',
      credentials: 'include',
      headers: hasBody ? { 'Content-Type': 'application/json' } : undefined,
      body: hasBody ? JSON.stringify(fields) : undefined,
      signal,
    },
  );
  const ctype = (res.headers.get('content-type') || '').toLowerCase();
  if (!res.ok) {
    const payload = ctype.includes('application/json') ? await res.json() : await res.text();
    throw new Error(extractErrorMessage(payload, res.status));
  }
  const blob = await res.blob();
  const cd = res.headers.get('content-disposition') || '';
  const filename = parseFilenameFromContentDisposition(cd) || '';
  return { blob, filename };
}

export function searchLocalItems(payload, signal) {
  return researchRequest('local-index/search-items', { method: 'POST', body: payload, signal });
}

function isRetryableSearchError(err) {
  if (isClientTimeoutError(err)) return true;
  if (isNetworkFetchError(err)) return true;
  const status = Number(err?.status);
  return status === 502 || status === 504 || status === 503 || status === 429;
}

export function intelligentMarketSearch(payload, signal, options = {}) {
  const timeoutMs = options.timeoutMs ?? 180000;
  const maxAttempts = Math.max(1, Math.min(5, Number(options.maxAttempts) || 3));

  const attemptOnce = () =>
    researchRequest('market-search/intelligent', {
      method: 'POST',
      body: payload,
      signal,
      timeoutMs,
    }).catch(async (err) => {
      const msg = String(err?.message || '');
      if (msg.includes('Not Found') || msg.includes('404')) {
        return researchRequest('market-search', { method: 'POST', body: payload, signal, timeoutMs });
      }
      throw err;
    });

  return (async () => {
    let lastErr = null;
    for (let i = 0; i < maxAttempts; i += 1) {
      try {
        return await attemptOnce();
      } catch (err) {
        lastErr = err;
        if (isUserAbortError(err) || !isRetryableSearchError(err)) {
          throw err;
        }
        if (i < maxAttempts - 1) {
          const base = Number(options.retryDelayMs) > 0 ? Number(options.retryDelayMs) : 700;
          await sleep(base * (i + 1));
        }
      }
    }
    throw lastErr || new Error('Falha de rede ao consultar busca inteligente.');
  })();
}

/** Busca federada multi-fonte (Parte 0). Fallback para intelligent se endpoint indisponível. */
export function federatedMarketSearch(payload, signal, options = {}) {
  const fontesN = Array.isArray(payload?.fontes_habilitadas) ? payload.fontes_habilitadas.length : 1;
  const defaultTimeout = fontesN > 1 ? 200000 : 180000;
  const timeoutMs = options.timeoutMs ?? defaultTimeout;
  const maxAttempts = Math.max(1, Math.min(5, Number(options.maxAttempts) || 3));
  const body = {
    ...payload,
    fontes_habilitadas: payload.fontes_habilitadas?.length
      ? payload.fontes_habilitadas
      : ['pncp'],
  };

  const attemptOnce = () =>
    researchRequest('market-search/federated', {
      method: 'POST',
      body,
      signal,
      timeoutMs,
    }).catch((err) => {
      const status = Number(err?.status);
      if (status === 404 || status === 501) {
        return intelligentMarketSearch(payload, signal, options);
      }
      throw err;
    });

  return (async () => {
    let lastErr = null;
    for (let i = 0; i < maxAttempts; i += 1) {
      try {
        return await attemptOnce();
      } catch (err) {
        lastErr = err;
        if (isUserAbortError(err) || !isRetryableSearchError(err)) {
          throw err;
        }
        if (i < maxAttempts - 1) {
          const base = Number(options.retryDelayMs) > 0 ? Number(options.retryDelayMs) : 900;
          await sleep(base * (i + 1));
        }
      }
    }
    throw lastErr || new Error('Falha de rede ao consultar busca federada.');
  })();
}

export function listPriceSources() {
  return researchRequest('price-sources', { method: 'GET' });
}

export function getLocalIndexStats(signal, options = {}) {
  const timeoutMs = options.timeoutMs ?? 120_000;
  return researchRequest('local-index/stats', { signal, timeoutMs });
}

/** Stats do índice com retry — evita UI «0 itens» por falha transitória de rede/proxy. */
export async function getLocalIndexStatsResilient(options = {}) {
  const maxAttempts = Math.max(1, Math.min(5, Number(options.maxAttempts) || 3));
  const timeoutMs = options.timeoutMs ?? 120_000;
  let lastErr = null;
  for (let i = 0; i < maxAttempts; i += 1) {
    try {
      return await getLocalIndexStats(undefined, { timeoutMs });
    } catch (err) {
      lastErr = err;
      if (i < maxAttempts - 1) {
        await sleep(Math.min(2400, 700 * (i + 1)));
      }
    }
  }
  throw lastErr || new Error('Falha ao carregar estatísticas do índice local.');
}

export function backfillLocalIndex(payload, signal) {
  return researchRequest('local-index/backfill', { method: 'POST', body: payload, signal });
}

function mapNetworkError(err, context) {
  const msg = String(err?.message || err || '');
  if (/failed to fetch|networkerror|load failed/i.test(msg)) {
    if (context === 'start') {
      return new Error(
        'Não foi possível iniciar a geração do PDF (rede ou servidor indisponível). Tente novamente em instantes.',
      );
    }
    if (context === 'poll') {
      return new Error(
        'A conexão caiu ao aguardar o PDF. O servidor pode ainda estar a gerar — feche e abra o relatório e tente «Gerar e baixar» outra vez.',
      );
    }
    return new Error(
      'O download do PDF foi interrompido (rede). Tente novamente; se o relatório for muito grande, aguarde e volte a gerar.',
    );
  }
  return err;
}

function parseFilenameFromContentDisposition(cd) {
  let filename = '';
  const utf8Match = cd.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    filename = decodeURIComponent(utf8Match[1]);
  } else {
    const plainMatch = cd.match(/filename="?([^";]+)"?/i);
    if (plainMatch?.[1]) filename = plainMatch[1];
  }
  return filename;
}

/**
 * PDF do relatório (WeasyPrint no Django).
 * Usa POST …/relatorio/pdf/start (202) e polling em …/pdf/jobs/<id> para evitar timeout de proxy na geração longa.
 */
export async function downloadCotacaoRelatorioPdf(
  sessaoId,
  tituloRelatorio,
  signal,
  incluirAnexosFornecedor = true,
) {
  const bodyJson = {
    titulo_relatorio: tituloRelatorio,
    incluir_anexos_fornecedor: Boolean(incluirAnexosFornecedor),
  };

  const startOpts = {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(bodyJson),
  };
  if (signal) startOpts.signal = signal;

  let startRes;
  try {
    startRes = await fetch(
      `${API_BASE}/api/pncp/cotacoes/research/sessions/${encodeURIComponent(sessaoId)}/relatorio/pdf/start`,
      startOpts,
    );
  } catch (err) {
    throw mapNetworkError(err, 'start');
  }

  let startPayload;
  const startCtype = (startRes.headers.get('content-type') || '').toLowerCase();
  try {
    startPayload = startCtype.includes('application/json') ? await startRes.json() : await startRes.text();
  } catch (err) {
    throw mapNetworkError(err, 'start');
  }
  if (!startRes.ok) {
    throw new Error(extractErrorMessage(startPayload, startRes.status));
  }
  if (startRes.status !== 202 || !startPayload?.poll_path || !startPayload?.job_id) {
    throw new Error('Resposta inesperada ao iniciar geração do PDF.');
  }

  const pollUrl = `${API_BASE}${startPayload.poll_path}`;
  const POLL_MS = 1500;
  const MAX_WAIT_MS = 40 * 60 * 1000;
  const POLL_NETWORK_RETRIES = 12;
  const t0 = Date.now();

  while (Date.now() - t0 < MAX_WAIT_MS) {
    if (signal?.aborted) {
      throw new DOMException('Aborted', 'AbortError');
    }
    let pollRes;
    let pollNetworkRetries = 0;
    while (true) {
      try {
        pollRes = await fetch(pollUrl, { credentials: 'include', signal });
        break;
      } catch (err) {
        if (isNetworkFetchError(err) && pollNetworkRetries < POLL_NETWORK_RETRIES) {
          pollNetworkRetries += 1;
          await sleep(POLL_MS * Math.min(4, pollNetworkRetries));
          continue;
        }
        throw mapNetworkError(err, 'poll');
      }
    }
    const pollCtype = (pollRes.headers.get('content-type') || '').toLowerCase();

    if (pollRes.status === 202) {
      await sleep(POLL_MS);
      continue;
    }

    if (!pollRes.ok) {
      const payload = pollCtype.includes('application/json')
        ? await pollRes.json()
        : await pollRes.text();
      throw new Error(extractErrorMessage(payload, pollRes.status));
    }

    if (!pollCtype.includes('application/json')) {
      const payload = await pollRes.text();
      throw new Error(extractErrorMessage(payload, pollRes.status));
    }

    const pollData = await pollRes.json();
    if (pollData?.status === 'error') {
      throw new Error(
        pollData.detail || pollData.error || 'Erro ao gerar o PDF no servidor.',
      );
    }
    if (pollData?.status === 'pending' || pollData?.status === 'processing') {
      await sleep(POLL_MS);
      continue;
    }
    if (pollData?.status !== 'done' || !pollData?.file_url) {
      throw new Error(
        pollData?.detail || pollData?.error || 'Resposta inesperada ao consultar o estado do PDF.',
      );
    }

    const fileUrl = `${API_BASE}${pollData.file_url}`;
    let fileRes;
    try {
      fileRes = await fetch(fileUrl, { credentials: 'include', signal });
    } catch (err) {
      throw mapNetworkError(err, 'blob');
    }
    const fileCtype = (fileRes.headers.get('content-type') || '').toLowerCase();
    if (!fileRes.ok) {
      const payload = fileCtype.includes('application/json')
        ? await fileRes.json()
        : await fileRes.text();
      throw new Error(extractErrorMessage(payload, fileRes.status));
    }
    if (!fileCtype.includes('application/pdf') && !fileCtype.includes('octet-stream')) {
      const payload = fileCtype.includes('application/json')
        ? await fileRes.json()
        : await fileRes.text();
      throw new Error(extractErrorMessage(payload, fileRes.status));
    }

    let blob;
    try {
      blob = await fileRes.blob();
    } catch (err) {
      throw mapNetworkError(err, 'blob');
    }
    const cd = fileRes.headers.get('content-disposition') || '';
    const headerName = parseFilenameFromContentDisposition(cd);
    const filename = headerName || String(pollData.filename || '').trim() || '';
    return { blob, filename };
  }

  throw new Error(
    'O relatório demorou mais do que o esperado a ficar pronto. Tente gerar de novo; se for uma cotação muito grande, contacte o suporte.',
  );
}
