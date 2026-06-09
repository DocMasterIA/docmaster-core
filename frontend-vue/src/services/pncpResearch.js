// Em desenvolvimento, usa proxy do Vite (/api -> backend local) para evitar bater na API remota.
const API_BASE = import.meta.env.DEV ? '' : (import.meta.env.VITE_API_URL || 'https://api.docmasteria.com.br');

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
    typeof p === 'object' && p !== null ? p?.detail || p?.error : p;
  const msg = String(raw || '').trim();
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
  return msg || `Erro HTTP ${status}`;
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

function mergeAbortSignals(userSignal, timeoutMs) {
  const ms = Number(timeoutMs);
  if (!Number.isFinite(ms) || ms <= 0) {
    return userSignal || undefined;
  }
  let timeoutSignal = null;
  if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') {
    timeoutSignal = AbortSignal.timeout(ms);
  }
  if (!userSignal) return timeoutSignal || undefined;
  if (!timeoutSignal) return userSignal;
  const ac = new AbortController();
  const abort = () => {
    if (!ac.signal.aborted) ac.abort();
  };
  userSignal.addEventListener('abort', abort, { once: true });
  timeoutSignal.addEventListener('abort', abort, { once: true });
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

/** Cotações / sessões persistidas no Django (ORM). */
async function cotacaoRequest(path, { method = 'GET', body, signal } = {}) {
  const res = await fetch(`${API_BASE}/api/pncp/cotacoes/${path}`, {
    method,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
    body: body ? JSON.stringify(body) : undefined,
    signal,
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

export function getResearchSession(sessaoId, signal) {
  return cotacaoRequest(`research/sessions/${encodeURIComponent(sessaoId)}`, { signal });
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

export function searchLocalItems(payload, signal) {
  return researchRequest('local-index/search-items', { method: 'POST', body: payload, signal });
}

function isRetryableSearchError(err) {
  if (isNetworkFetchError(err)) return true;
  const status = Number(err?.status);
  return status === 502 || status === 504 || status === 503 || status === 429;
}

export function intelligentMarketSearch(payload, signal, options = {}) {
  const timeoutMs = options.timeoutMs ?? 120000;
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
        const aborted = String(err?.name || '') === 'AbortError'
          || /aborted|abort/i.test(String(err?.message || ''));
        if (aborted || !isRetryableSearchError(err)) {
          throw err;
        }
        if (i < maxAttempts - 1) {
          await sleep(900 * (i + 1));
        }
      }
    }
    throw lastErr || new Error('Falha de rede ao consultar busca inteligente.');
  })();
}

export function getLocalIndexStats(signal) {
  return researchRequest('local-index/stats', { signal });
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
  const t0 = Date.now();

  while (Date.now() - t0 < MAX_WAIT_MS) {
    if (signal?.aborted) {
      throw new DOMException('Aborted', 'AbortError');
    }
    let pollRes;
    try {
      pollRes = await fetch(pollUrl, { credentials: 'include', signal });
    } catch (err) {
      throw mapNetworkError(err, 'poll');
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
    if (pollData?.status === 'pending') {
      await sleep(POLL_MS);
      continue;
    }
    if (pollData?.status !== 'done' || !pollData?.file_url) {
      throw new Error('Resposta inesperada ao consultar o estado do PDF.');
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
