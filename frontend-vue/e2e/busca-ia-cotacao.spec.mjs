import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { cotacaoIdFromEnv, loginIfNeeded } from './helpers/auth.mjs';
import { scrapeBuscaIaPage, normalizeScraped } from './helpers/scrapeBuscaIa.mjs';
import { auditBuscaIa, renderAuditMarkdown } from './helpers/auditBuscaIa.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ARTIFACTS = path.join(__dirname, '..', 'e2e-artifacts');

/**
 * Auditoria E2E da Busca Inteligente:
 * 1) login
 * 2) dispara busca IA (autostart + rebuscar)
 * 3) espera conclusão do bulk
 * 4) coleta preços/faixas/scores da UI
 * 5) analisa inconsistências e grava relatório de feedback
 *
 * Default: cotação 138 (~52 itens). 137 (~700) via PLAYWRIGHT_COTACAO_ID.
 */
test.describe('Auditoria Busca IA', () => {
  test('executa busca, audita preços e gera feedback', async ({ page }) => {
    const cotacaoId = cotacaoIdFromEnv('138');
    const buscaPath = `/pesquisador-pncp/cotacoes/${cotacaoId}/busca-inteligente?autostart=1&rebuscar=1`;

    const apiSamples = [];
    page.on('response', async (res) => {
      try {
        const url = res.url();
        if (!/market-search\/(federated|intelligent)/.test(url)) return;
        if (res.status() !== 200) {
          apiSamples.push({ url, status: res.status(), ok: false });
          return;
        }
        const json = await res.json().catch(() => null);
        if (!json || typeof json !== 'object') return;
        const itens = Array.isArray(json.itens) ? json.itens : [];
        apiSamples.push({
          url,
          status: res.status(),
          ok: Boolean(json.ok),
          nItens: itens.length,
          termo: json.filtros?.termo_busca || json.termo_busca || null,
          faixaMin: json.filtros?.faixa_regional_min ?? null,
          faixaMax: json.filtros?.faixa_regional_max ?? null,
          funil: json.stats?.funil_busca || json.funil_busca || null,
          precos: itens.slice(0, 5).map((it) => ({
            descricao: it.descricao_item || it.objeto_resumido,
            vu: it.valor_unitario_homologado ?? it.valor_unitario,
            plataforma: it.plataforma,
            score: it.score_aprovacao,
          })),
        });
      } catch {
        /* ignore parse errors */
      }
    });

    await loginIfNeeded(page, { redirectTo: buscaPath });
    if (!page.url().includes('/busca-inteligente')) {
      await page.goto(buscaPath, { waitUntil: 'domcontentloaded' });
    }

    await expect(page).not.toHaveURL(/\/login/);
    await expect(page.getByText(/Pesquisa de Precos/i).first()).toBeVisible({ timeout: 60_000 });

    // Espera progresso iniciar (ou já concluído se cache rápido)
    await expect(
      page.getByText(/Busca automática|cotações sugeridas|Consultando índices/i).first(),
    ).toBeVisible({ timeout: 180_000 });

    // Espera conclusão do bulk (ou timeout do teste)
    await expect
      .poll(async () => {
        const txt = await page.locator('.bia-meta').allInnerTexts();
        const blob = txt.join('\n');
        if (/Busca automática concluída/i.test(blob)) return 'done';
        if (/Busca concluída/i.test(blob)) return 'done';
        // ainda andamento
        if (/em andamento/i.test(blob)) return 'running';
        if (/Busca automática parcial/i.test(blob)) {
          const m = blob.match(/parcial:\s*(\d+)\s+de\s+(\d+)/i);
          if (m && Number(m[1]) >= Number(m[2])) return 'done';
        }
        return 'running';
      }, {
        timeout: Number(process.env.PLAYWRIGHT_BULK_TIMEOUT_MS || 40 * 60 * 1000),
        intervals: [5_000, 10_000, 15_000],
      })
      .toBe('done');

    // Scroll para carregar todos os grupos no DOM
    for (let i = 0; i < 20; i += 1) {
      await page.mouse.wheel(0, 4000);
      await page.waitForTimeout(200);
    }
    await page.evaluate(() => window.scrollTo(0, 0));

    const raw = await scrapeBuscaIaPage(page);
    const data = normalizeScraped(raw);
    data.apiSamples = apiSamples.slice(-80);

    const audit = auditBuscaIa(data, { failOnCritical: true });
    const md = renderAuditMarkdown(audit, data);

    fs.mkdirSync(ARTIFACTS, { recursive: true });
    const stamp = new Date().toISOString().replace(/[:.]/g, '-');
    const base = path.join(ARTIFACTS, `busca-ia-audit-${cotacaoId}-${stamp}`);
    fs.writeFileSync(`${base}.md`, md, 'utf8');
    fs.writeFileSync(`${base}.json`, JSON.stringify({
      summary: audit.summary,
      findings: audit.findings,
      itemReports: audit.itemReports,
      mismatchSamples: audit.mismatchSamples,
      scrapedMeta: {
        url: data.url,
        scrapedAt: data.scrapedAt,
        progress: data.progress,
        faixaGlobal: data.faixaGlobal,
        apiSamples: data.apiSamples || [],
      },
    }, null, 2), 'utf8');

    // Anexa ao relatório Playwright
    await test.info().attach('audit-report.md', { body: md, contentType: 'text/markdown' });
    await test.info().attach('audit-summary.json', {
      body: JSON.stringify(audit.summary, null, 2),
      contentType: 'application/json',
    });

    console.log('\n========== AUDITORIA BUSCA IA ==========');
    console.log(audit.feedback);
    console.log(`Relatório: ${base}.md`);
    console.log('========================================\n');

    expect(data.groupCount, 'esperava grupos de itens na UI').toBeGreaterThan(0);
    expect(
      audit.summary.critical,
      `críticos (mismatch e/ou fora da faixa) — ver ${base}.md\n` + audit.feedback,
    ).toBe(0);
  });
});
