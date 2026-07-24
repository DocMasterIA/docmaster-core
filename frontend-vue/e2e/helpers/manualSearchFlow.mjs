/**
 * Helpers compartilhados da Busca Manual E2E (item a item).
 */
import { expect } from '@playwright/test';

export function itemIdFilterFromEnv() {
  const raw = String(process.env.PLAYWRIGHT_ITEM_ID || '').trim();
  return raw || null;
}

export function maxItemsFromEnv() {
  const n = Number(process.env.PLAYWRIGHT_MANUAL_MAX_ITEMS || 0);
  return Number.isFinite(n) && n > 0 ? Math.floor(n) : null;
}

/**
 * Lista itens da cotação via API (mesma sessão cookie do browser).
 */
export async function loadCotacaoItems(page, cotacaoId) {
  const items = await page.evaluate(async (id) => {
    const candidates = [];
    try {
      const meta = document.querySelector('meta[name="api-base"]');
      if (meta?.content) candidates.push(String(meta.content).replace(/\/$/, ''));
    } catch {
      /* ignore */
    }
    candidates.push('https://api.docmasteria.com.br', '');

    const seen = new Set();
    for (const base of candidates) {
      if (seen.has(base)) continue;
      seen.add(base);
      try {
        const url = `${base}/api/pncp/cotacoes/research/sessions/${encodeURIComponent(id)}`;
        const res = await fetch(url, { credentials: 'include' });
        if (!res.ok) continue;
        const data = await res.json();
        const itens = Array.isArray(data?.itens) ? data.itens : [];
        if (!itens.length) continue;
        return itens
          .map((it) => ({
            id: Number(it?.id),
            descricao: String(it?.descricao_item || it?.descricao || '').trim(),
          }))
          .filter((x) => Number.isFinite(x.id) && x.id > 0);
      } catch {
        /* tenta próximo base */
      }
    }
    return [];
  }, String(cotacaoId));

  if (!items.length) {
    throw new Error(
      `Não foi possível listar itens da cotação ${cotacaoId} via API (cookie/sessão).`,
    );
  }
  return items;
}

/**
 * Página pronta (o h1 "Busca Manual…" fica display:none no shell App.vue).
 * Usa controles visíveis da UI manual.
 */
export async function waitManualPageReady(page, { descricaoEsperada = null, timeout = 60_000 } = {}) {
  await expect(page.getByRole('button', { name: /^Buscar$/i })).toBeVisible({ timeout });
  await expect(page.getByRole('link', { name: /Voltar à busca compacta/i })).toBeVisible({ timeout });
  await expect(page.getByRole('heading', { name: /Plataformas consultadas/i })).toBeVisible({ timeout });

  if (descricaoEsperada) {
    const needle = String(descricaoEsperada).trim().slice(0, 40);
    await expect
      .poll(async () => {
        const val = await page.locator('.manual-field--grow input').inputValue().catch(() => '');
        return val.includes(needle) || val.length > 8;
      }, { timeout, intervals: [400, 800, 1_500] })
      .toBeTruthy();
  }
}

/** Marca todas as fontes com checkbox habilitado (união multi-fonte). */
export async function enableAllReadyPriceSources(page) {
  const boxes = page.locator('.price-fontes-panel input[type="checkbox"]:not([disabled])');
  const n = await boxes.count();
  for (let i = 0; i < n; i += 1) {
    const box = boxes.nth(i);
    if (!(await box.isChecked().catch(() => false))) {
      await box.check({ force: true });
    }
  }
  return n;
}

/** Espera auto-busca manual terminar (ou empty/error). */
export async function waitManualSearchSettled(page, timeoutMs) {
  try {
    await expect
      .poll(async () => {
        const searching = await page.locator('.manual-meta', { hasText: /Consultando índices/i }).count();
        const n = await page.locator('.manual-results-table tbody tr').count();
        const err = await page.locator('.manual-meta--error').count();
        if (err > 0) return 'error';
        if (searching > 0) return 'running';
        if (n > 0) return 'done';
        const card = await page.locator('.manual-summary-card', { hasText: /Resultados/i }).innerText().catch(() => '');
        if (/Resultados\s*0\b/i.test(card) && searching === 0) return 'empty';
        return 'waiting';
      }, { timeout: Math.min(45_000, timeoutMs), intervals: [800, 1_500, 2_500] })
      .toMatch(/done|empty|error/);
  } catch {
    const btn = page.getByRole('button', { name: /^Buscar$/i });
    if (await btn.isVisible().catch(() => false)) {
      await btn.click();
    }
  }

  await expect
    .poll(async () => {
      const searching = await page.locator('.manual-meta', { hasText: /Consultando índices/i }).count();
      if (searching > 0) return 'running';
      const n = await page.locator('.manual-results-table tbody tr').count();
      if (n > 0) return 'done';
      const err = await page.locator('.manual-meta--error').innerText().catch(() => '');
      if (err) return `error:${err.slice(0, 160)}`;
      const card = await page.locator('.manual-summary-card', { hasText: /Resultados/i }).innerText().catch(() => '');
      if (/Resultados\s*0\b/i.test(card)) return 'empty';
      return 'waiting';
    }, { timeout: timeoutMs, intervals: [1_500, 3_000, 5_000] })
    .toMatch(/^done|^empty|^error/);
}

export function summarizeFederatedResponse(json, resMeta = {}) {
  const itens = Array.isArray(json?.itens) ? json.itens : [];
  const fontes = json?.stats?.fontes || null;
  const plataformasItens = {};
  for (const it of itens) {
    const p = String(it.plataforma || 'desconhecida');
    plataformasItens[p] = (plataformasItens[p] || 0) + 1;
  }
  return {
    ...resMeta,
    ok: Boolean(json?.ok),
    nItens: itens.length,
    termo: json?.filtros?.termo_busca || null,
    listaCompleta: Boolean(json?.filtros?.lista_completa ?? json?.stats?.lista_completa),
    fontes,
    plataformasItens,
    faixaMin: json?.filtros?.faixa_regional_min ?? null,
    faixaMax: json?.filtros?.faixa_regional_max ?? null,
  };
}

export function mergePlatCounts(into, from) {
  for (const [k, v] of Object.entries(from || {})) {
    into[k] = (into[k] || 0) + Number(v || 0);
  }
  return into;
}
