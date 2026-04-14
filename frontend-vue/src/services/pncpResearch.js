const API_BASE = import.meta.env.VITE_API_URL || 'https://api.docmasteria.com.br';

function extractErrorMessage(payload, status) {
  const raw = typeof payload === 'object' ? payload?.detail || payload?.error : payload;
  const msg = String(raw || '').trim();
  // Django 500 default HTML should not leak to UI.
  if (msg.startsWith('<!doctype html') || msg.startsWith('<html')) {
    if (status >= 500) return 'Erro interno no backend PNCP. Tente novamente em instantes.';
    return `Erro HTTP ${status}`;
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

export function addItemsToResearchSession(sessaoId, itens, signal) {
  return cotacaoRequest(`research/sessions/${encodeURIComponent(sessaoId)}/items`, {
    method: 'POST',
    body: { itens },
    signal,
  });
}

export function searchLocalItems(payload, signal) {
  return researchRequest('local-index/search-items', { method: 'POST', body: payload, signal });
}

export function getLocalIndexStats(signal) {
  return researchRequest('local-index/stats', { signal });
}

export function backfillLocalIndex(payload, signal) {
  return researchRequest('local-index/backfill', { method: 'POST', body: payload, signal });
}

/** PDF do relatório institucional da cotação (WeasyPrint no Django). */
export async function downloadCotacaoRelatorioPdf(sessaoId, tituloRelatorio, signal) {
  const res = await fetch(
    `${API_BASE}/api/pncp/cotacoes/research/sessions/${encodeURIComponent(sessaoId)}/relatorio/pdf`,
    {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ titulo_relatorio: tituloRelatorio }),
      signal,
    },
  );
  const ctype = (res.headers.get('content-type') || '').toLowerCase();
  if (!res.ok) {
    const payload = ctype.includes('application/json') ? await res.json() : await res.text();
    throw new Error(extractErrorMessage(payload, res.status));
  }
  return res.blob();
}
