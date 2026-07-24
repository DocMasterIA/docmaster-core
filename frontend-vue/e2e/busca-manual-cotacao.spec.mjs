import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { cotacaoIdFromEnv, loginIfNeeded } from './helpers/auth.mjs';
import { scrapeBuscaManualPage, normalizeManualScraped } from './helpers/scrapeBuscaManual.mjs';
import { auditBuscaManual } from './helpers/auditBuscaManual.mjs';
import {
  enableAllReadyPriceSources,
  itemIdFilterFromEnv,
  loadCotacaoItems,
  maxItemsFromEnv,
  mergePlatCounts,
  summarizeFederatedResponse,
  waitManualPageReady,
  waitManualSearchSettled,
} from './helpers/manualSearchFlow.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ARTIFACTS = path.join(__dirname, '..', 'e2e-artifacts');

/**
 * E2E Busca Manual — cotação inteira, item a item:
 * para cada itemId → /busca-manual?itemId=…
 *
 * Env:
 *   PLAYWRIGHT_COTACAO_ID=138
 *   PLAYWRIGHT_ITEM_ID=31869          (opcional: só este item)
 *   PLAYWRIGHT_MANUAL_MAX_ITEMS=10    (opcional: limita N primeiros)
 *   PLAYWRIGHT_MANUAL_TIMEOUT_MS      (timeout por item, default 3 min)
 *   PLAYWRIGHT_MANUAL_FAIL_ON_MISMATCH=1
 */
test.describe('Auditoria Busca Manual (cotação item a item)', () => {
  test('percorre todos os itens na busca manual e gera feedback', async ({ page }) => {
    test.setTimeout(Number(process.env.PLAYWRIGHT_TEST_TIMEOUT_MS || 120 * 60 * 1000));

    const cotacaoId = cotacaoIdFromEnv('138');
    const perItemTimeout = Number(process.env.PLAYWRIGHT_MANUAL_TIMEOUT_MS || 3 * 60 * 1000);
    const failOnMismatch = String(process.env.PLAYWRIGHT_MANUAL_FAIL_ON_MISMATCH || '').trim() === '1';
    const onlyItemId = itemIdFilterFromEnv();
    const maxItems = maxItemsFromEnv();

    // Listener global: amostras por item (última resposta ok de cada busca)
    let currentItemApi = [];
    page.on('response', async (res) => {
      try {
        const url = res.url();
        if (!/market-search\/federated/.test(url)) return;
        if (res.status() !== 200) {
          currentItemApi.push({ url, status: res.status(), ok: false });
          return;
        }
        const json = await res.json().catch(() => null);
        if (!json || typeof json !== 'object') return;
        currentItemApi.push(summarizeFederatedResponse(json, { url, status: res.status() }));
      } catch {
        /* ignore */
      }
    });

    await loginIfNeeded(page, { redirectTo: `/pesquisador-pncp/cotacoes/${cotacaoId}` });
    await expect(page).not.toHaveURL(/\/login/);

    // Garante cookie de API: página da cotação carrega a sessão
    if (!page.url().includes(`/cotacoes/${cotacaoId}`)) {
      await page.goto(`/pesquisador-pncp/cotacoes/${cotacaoId}`, { waitUntil: 'domcontentloaded' });
    }
    await page.waitForTimeout(1_500);

    let items = await loadCotacaoItems(page, cotacaoId);
    if (onlyItemId) {
      items = items.filter((it) => String(it.id) === String(onlyItemId));
    }
    if (maxItems) {
      items = items.slice(0, maxItems);
    }
    expect(items.length, 'cotação deveria ter itens').toBeGreaterThan(0);

    const itemReports = [];
    let totalCritical = 0;
    let itensSemResultado = 0;
    let itensForaFaixa = 0;
    const platUiTotal = {};
    const fontesHitsTotal = {};

    console.log(`\n========== BUSCA MANUAL ITEM A ITEM (${items.length} itens, cotação ${cotacaoId}) ==========`);

    for (let i = 0; i < items.length; i += 1) {
      const item = items[i];
      const buscaPath = `/pesquisador-pncp/cotacoes/${cotacaoId}/busca-manual?itemId=${item.id}`;
      currentItemApi = [];

      console.log(`[${i + 1}/${items.length}] itemId=${item.id} — ${(item.descricao || '').slice(0, 70)}`);

      await page.goto(buscaPath, { waitUntil: 'domcontentloaded' });
      // h1 "Busca Manual…" é display:none no App.vue — não usar como gate
      await waitManualPageReady(page, { descricaoEsperada: item.descricao });

      // UI inicia só com PNCP; força todas as fontes ready e rebusca
      await enableAllReadyPriceSources(page);
      currentItemApi = [];
      await page.getByRole('button', { name: /^Buscar$/i }).click();
      await waitManualSearchSettled(page, perItemTimeout);

      const raw = await scrapeBuscaManualPage(page);
      const data = normalizeManualScraped(raw);
      data.apiSamples = currentItemApi.slice(-5);
      data.itemId = item.id;
      data.cotacaoId = cotacaoId;
      if (!data.descricao && item.descricao) {
        data.descricao = item.descricao;
      }

      const audit = auditBuscaManual(data, { failOnMismatch });
      const lastApi = [...(data.apiSamples || [])].reverse().find((s) => s.ok) || null;

      mergePlatCounts(platUiTotal, audit.summary.plataformas);
      if (lastApi?.fontes && typeof lastApi.fontes === 'object') {
        for (const [src, st] of Object.entries(lastApi.fontes)) {
          fontesHitsTotal[src] = (fontesHitsTotal[src] || 0) + Number(st?.hits || 0);
        }
      }

      if (audit.summary.resultadosUi === 0) itensSemResultado += 1;
      if (audit.summary.foraFaixa > 0) itensForaFaixa += 1;
      totalCritical += audit.summary.critical;

      itemReports.push({
        itemId: item.id,
        descricao: data.descricao || item.descricao,
        resultadosUi: audit.summary.resultadosUi,
        resultadosApi: audit.summary.resultadosApi,
        foraFaixa: audit.summary.foraFaixa,
        mismatches: audit.summary.mismatches,
        plataformas: audit.summary.plataformas,
        fontesApi: audit.summary.fontesApi,
        listaCompleta: audit.summary.listaCompleta,
        critical: audit.summary.critical,
        warn: audit.summary.warn,
      });
    }

    const summary = {
      cotacaoId,
      itensProcessados: itemReports.length,
      itensSemResultado,
      itensForaFaixa,
      totalCritical,
      plataformasUiTotal: platUiTotal,
      fontesHitsTotal,
    };

    const md = renderCotacaoManualMarkdown(summary, itemReports);
    fs.mkdirSync(ARTIFACTS, { recursive: true });
    const stamp = new Date().toISOString().replace(/[:.]/g, '-');
    const base = path.join(ARTIFACTS, `busca-manual-cotacao-${cotacaoId}-${stamp}`);
    fs.writeFileSync(`${base}.md`, md, 'utf8');
    fs.writeFileSync(`${base}.json`, JSON.stringify({ summary, itemReports }, null, 2), 'utf8');

    await test.info().attach('manual-cotacao-audit.md', { body: md, contentType: 'text/markdown' });
    await test.info().attach('manual-cotacao-summary.json', {
      body: JSON.stringify(summary, null, 2),
      contentType: 'application/json',
    });

    console.log('\n========== AUDITORIA BUSCA MANUAL (COTAÇÃO) ==========');
    console.log(md.slice(0, 2500));
    console.log(`\nRelatório: ${base}.md`);
    console.log('=====================================================\n');

    expect(itensSemResultado, `itens sem resultado na manual: ${itensSemResultado}`).toBe(0);
    expect(itensForaFaixa, `itens com preço fora da faixa: ${itensForaFaixa}`).toBe(0);
    expect(totalCritical, `críticos agregados — ver ${base}.md`).toBe(0);
  });
});

function renderCotacaoManualMarkdown(summary, itemReports) {
  const lines = [
    '# Auditoria — Busca Manual (cotação, item a item)',
    '',
    `- Cotação: ${summary.cotacaoId}`,
    `- Itens processados: ${summary.itensProcessados}`,
    '',
    '## Resumo',
    '',
    '| Métrica | Valor |',
    '|---------|------:|',
    `| Itens processados | ${summary.itensProcessados} |`,
    `| Itens sem resultado | ${summary.itensSemResultado} |`,
    `| Itens com fora da faixa | ${summary.itensForaFaixa} |`,
    `| Críticos (soma) | ${summary.totalCritical} |`,
    `| Plataformas UI (soma linhas) | ${JSON.stringify(summary.plataformasUiTotal)} |`,
    `| Fontes API hits (soma) | ${JSON.stringify(summary.fontesHitsTotal)} |`,
    '',
    '## Por item',
    '',
    '| # | itemId | Resultados | Fora faixa | Mismatch* | Plataformas UI | Fontes API hits | Crit | Termo |',
    '|--:|--:|--:|--:|--:|---|---|--:|---|',
  ];

  itemReports.forEach((r, idx) => {
    const fontesHits = r.fontesApi
      ? Object.fromEntries(
        Object.entries(r.fontesApi).map(([k, st]) => [k, Number(st?.hits || 0)]),
      )
      : {};
    lines.push(
      `| ${idx + 1} | ${r.itemId} | ${r.resultadosUi} | ${r.foraFaixa} | ${r.mismatches} | `
      + `${JSON.stringify(r.plataformas)} | ${JSON.stringify(fontesHits)} | ${r.critical} | `
      + `${(r.descricao || '').slice(0, 60).replace(/\|/g, '/')} |`,
    );
  });

  lines.push('');
  lines.push('\\* Mismatch lexical na lista ampla é aviso (não falha o item), salvo `PLAYWRIGHT_MANUAL_FAIL_ON_MISMATCH=1`.');
  lines.push('');
  lines.push('## Interpretação');
  lines.push('');
  lines.push('1. Cada item passou pela **busca manual individual** (`lista_completa`).');
  lines.push('2. União de fontes: ver coluna Fontes API hits (pncp / tce_rs / compras_gov).');
  lines.push('3. Critérios de falha da suíte: item sem resultado, fora da faixa, ou critical>0.');
  lines.push('');
  const ok = summary.itensSemResultado === 0 && summary.itensForaFaixa === 0 && summary.totalCritical === 0;
  lines.push(`**Veredito:** ${ok ? 'OK' : 'FALHA'}.`);
  return lines.join('\n');
}
