// Em desenvolvimento, usa proxy do Vite (/api -> backend local) para evitar bater na API remota.
const API_BASE = import.meta.dev ? '' : (import.meta.env.VITE_API_URL || 'https://api.docmasteria.com.br');

function extractErrorMessage(payload, status) {
  const raw =
    typeof payload === 'object' && payload !== null ? payload?.detail || payload?.error : payload;
  const msg = String(raw || '').trim();
  const looksLikeHtml =
    /^<!doctype html/i.test(msg) || /^<html/i.test(msg) || /<body[\s>]/i.test(msg.slice(0, 400));
  // Gateway/Django HTML error page — não há JSON com detalhe.
  if (looksLikeHtml) {
    if (status >= 500)
      return 'Servidor ou proxy retornou erro temporário (sem detalhe). Tente novamente em instantes.';
    return `Erro HTTP ${status}`;
  }
  if (status >= 500 && !msg) {
    return 'Erro temporário no servidor. Tente novamente em instantes.';
  }
  return msg || `Erro HTTP ${status}`;
}

/** Proxy FastAPI: índice local, market-search, streams. */
async function researchRequest(path, { method = 'GET', body, signal } = {}) {
  const res = await fetch(`${API_BASE}/api/pncp-research/${path}`, {
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

export function intelligentMarketSearch(payload, signal) {
  return researchRequest('market-search/intelligent', { method: 'POST', body: payload, signal }).catch(async (err) => {
    const msg = String(err?.message || '');
    // Fallback de compatibilidade: ambiente antigo sem endpoint inteligente ainda publicado.
    if (msg.includes('Not Found') || msg.includes('404')) {
      return researchRequest('market-search', { method: 'POST', body: payload, signal });
    }
    throw err;
  });
}

export function getLocalIndexStats(signal) {
  return researchRequest('local-index/stats', { signal });
}

export function backfillLocalIndex(payload, signal) {
  return researchRequest('local-index/backfill', { method: 'POST', body: payload, signal });
}

const PDF_FETCH_TIMEOUT_MS = 600000; // 10 min — geração pode demorar em cotações com muitos itens
const PDF_MAX_ATTEMPTS = 2;
const PDF_RETRY_BASE_MS = 2500;

function mergePdfFetchSignal(userSignal) {
  if (typeof AbortSignal === 'undefined' || typeof AbortSignal.timeout !== 'function') {
    return userSignal;
  }
  try {
    const deadline = AbortSignal.timeout(PDF_FETCH_TIMEOUT_MS);
    if (!userSignal) return deadline;
    if (typeof AbortSignal.any === 'function') {
      return AbortSignal.any([userSignal, deadline]);
    }
  } catch {
    return userSignal;
  }
  return userSignal;
}

function sleep(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function isPdfNetworkFailureMessage(msg) {
  return /failed to fetch|networkerror|load failed|aborted|tempo esgotou|sobrecarregado|interrompido/i.test(
    String(msg || ''),
  );
}

/** PDF do relatório institucional da cotação (WeasyPrint no Django). */
export async function downloadCotacaoRelatorioPdf(sessaoId, tituloRelatorio, signal) {
  let lastErr;
  for (let attempt = 1; attempt <= PDF_MAX_ATTEMPTS; attempt += 1) {
    if (signal?.aborted) {
      const e = new Error('Operação cancelada.');
      e.name = 'AbortError';
      throw e;
    }
    const fetchSignal = mergePdfFetchSignal(signal);
    const fetchOpts = {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        titulo_relatorio: tituloRelatorio,
        incluir_anexos_fornecedor: false,
      }),
    };
    if (fetchSignal) fetchOpts.signal = fetchSignal;

    let res;
    try {
      res = await fetch(
        `${API_BASE}/api/pncp/cotacoes/research/sessions/${encodeURIComponent(sessaoId)}/relatorio/pdf`,
        fetchOpts,
      );
    } catch (err) {
      lastErr = err;
      const msg = String(err?.message || err || '');
      const retryable = isPdfNetworkFailureMessage(msg) && attempt < PDF_MAX_ATTEMPTS && !signal?.aborted;
      if (retryable) {
        await sleep(PDF_RETRY_BASE_MS * attempt);
        continue;
      }
      if (/failed to fetch|networkerror|load failed|aborted/i.test(msg)) {
        throw new Error(
          'A conexão com o servidor caiu ou o tempo esgotou ao gerar o PDF. Tente novamente em instantes; se persistir, o servidor pode estar sobrecarregado.',
        );
      }
      throw err;
    }

    const ctype = (res.headers.get('content-type') || '').toLowerCase();
    if (!res.ok) {
      const payload = ctype.includes('application/json') ? await res.json() : await res.text();
      throw new Error(extractErrorMessage(payload, res.status));
    }

    let blob;
    try {
      blob = await res.blob();
    } catch (err) {
      lastErr = err;
      const msg = String(err?.message || err || '');
      const retryable = isPdfNetworkFailureMessage(msg) && attempt < PDF_MAX_ATTEMPTS && !signal?.aborted;
      if (retryable) {
        await sleep(PDF_RETRY_BASE_MS * attempt);
        continue;
      }
      if (/failed to fetch|networkerror|load failed|aborted/i.test(msg)) {
        throw new Error(
          'O download do PDF foi interrompido (rede ou tempo esgotado). Tente novamente; se o relatório for muito grande, aguarde alguns segundos e gere de novo.',
        );
      }
      throw err;
    }

    const cd = res.headers.get('content-disposition') || '';
    let filename = '';
    const utf8Match = cd.match(/filename\*=UTF-8''([^;]+)/i);
    if (utf8Match?.[1]) {
      filename = decodeURIComponent(utf8Match[1]);
    } else {
      const plainMatch = cd.match(/filename="?([^";]+)"?/i);
      if (plainMatch?.[1]) filename = plainMatch[1];
    }
    return { blob, filename };
  }
  throw lastErr || new Error('Falha ao gerar o PDF.');
}
