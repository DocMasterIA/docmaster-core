/**
 * Scrape / normalização da Busca Manual (item individual).
 */
import { parseBrl, parseFaixaCell } from './scrapeBuscaIa.mjs';

/** Extrai termo, resumo e linhas da tabela manual. */
export async function scrapeBuscaManualPage(page) {
  return page.evaluate(() => {
    const descricao = (
      document.querySelector('.manual-field--grow input')?.value
      || document.querySelector('label.manual-field input[type="text"]')?.value
      || ''
    ).trim();

    const metaAll = [...document.querySelectorAll('.manual-meta, .manual-summary-card')]
      .map((el) => (el.innerText || '').trim())
      .filter(Boolean);

    const summary = {};
    for (const card of document.querySelectorAll('.manual-summary-card')) {
      const label = (card.querySelector('span')?.innerText || '').trim();
      const value = (card.querySelector('strong')?.innerText || '').trim();
      if (label) summary[label] = value;
    }

    const searching = metaAll.some((t) => /Consultando índices/i.test(t));
    const searchError = metaAll.find((t) => /erro|falha/i.test(t)) || '';

    const rows = [];
    for (const tr of document.querySelectorAll('.manual-results-table tbody tr')) {
      const tds = [...tr.querySelectorAll('td')];
      if (tds.length < 9) continue;
      const cotTd = tds[2];
      rows.push({
        plataforma: (tds[1]?.querySelector('.manual-plat-badge')?.innerText || tds[1]?.innerText || '').trim(),
        titulo: (cotTd?.querySelector('.manual-cot-main')?.innerText || '').trim(),
        sub: (cotTd?.querySelector('.manual-cot-sub')?.innerText || '').trim(),
        similaridade: /similaridade/i.test(cotTd?.innerText || ''),
        quantidade: (tds[3]?.innerText || '').trim(),
        inciso: (tds[4]?.innerText || '').trim(),
        uf: (tds[5]?.innerText || '').trim().replace(/\s+/g, ' '),
        data: (tds[6]?.innerText || '').trim(),
        valorText: (tds[7]?.innerText || '').trim(),
        faixaText: (tds[8]?.innerText || '').trim(),
        confiabilidade: (tds[9]?.innerText || '').trim(),
        observacao: (tds[10]?.innerText || '').trim(),
      });
    }

    return {
      scrapedAt: new Date().toISOString(),
      url: location.href,
      descricao,
      summary,
      metaAll,
      searching,
      searchError,
      rowCount: rows.length,
      rows,
    };
  });
}

export function normalizeManualScraped(raw) {
  const rows = (raw.rows || []).map((r) => {
    const faixa = parseFaixaCell(r.faixaText);
    const valor = parseBrl(r.valorText);
    return {
      ...r,
      valor,
      faixa,
      foraFaixa:
        valor != null
        && faixa.min != null
        && faixa.max != null
        && (valor < faixa.min - 1e-9 || valor > faixa.max + 1e-9),
    };
  });
  return { ...raw, rows, rowCount: rows.length };
}
