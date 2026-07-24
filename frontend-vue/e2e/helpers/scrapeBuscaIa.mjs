/**
 * Parse helpers (pt-BR) para auditoria da Busca IA.
 */

export function parseBrl(text) {
  if (text == null) return null;
  const s = String(text).replace(/\s/g, ' ').trim();
  if (!s || s === '-' || s === '—' || /n\/?d/i.test(s)) return null;
  // "R$ 5,15" | "5.15" | "1.234,56"
  const m = s.replace(/R\$\s*/gi, '').match(/-?\d{1,3}(?:\.\d{3})*,\d+|-?\d+[.,]\d+|-?\d+/);
  if (!m) return null;
  let raw = m[0];
  if (raw.includes(',') && raw.includes('.')) {
    raw = raw.replace(/\./g, '').replace(',', '.');
  } else if (raw.includes(',')) {
    raw = raw.replace(',', '.');
  }
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

export function parseFaixaCell(text) {
  const blob = String(text || '');
  const base = parseBrl((blob.match(/BASE\s*(R\$\s*[\d.,]+)/i) || [])[1]);
  const varPct = (() => {
    const m = blob.match(/VAR\s*([\d.,]+)\s*%/i);
    if (!m) return null;
    const n = Number(String(m[1]).replace(',', '.'));
    return Number.isFinite(n) ? n : null;
  })();
  const range = blob.match(/(R\$\s*[\d.,]+)\s*[–-]\s*(R\$\s*[\d.,]+)/);
  const min = range ? parseBrl(range[1]) : null;
  const max = range ? parseBrl(range[2]) : null;
  return { base, varPct, min, max, raw: blob.trim() };
}

export function parseScorePercent(text) {
  const m = String(text || '').match(/([\d.,]+)\s*%?/);
  if (!m) return null;
  const n = Number(String(m[1]).replace(',', '.'));
  return Number.isFinite(n) ? n : null;
}

/** Extrai grupos/linhas da página Busca Inteligente. */
export async function scrapeBuscaIaPage(page) {
  return page.evaluate(() => {
    const metaAll = [...document.querySelectorAll('.bia-meta, .bia-faixa-banner')]
      .map((el) => (el.innerText || '').trim())
      .filter(Boolean);

    const groups = [];
    for (const card of document.querySelectorAll('.bia-group-card')) {
      const titleEl = card.querySelector('.bia-group-title');
      const title = (titleEl?.innerText || '').replace(/\s+/g, ' ').trim();
      const mediaMatch = title.match(/Média escolhida:\s*(.+)$/i);
      const label = title.replace(/\s*·\s*Média escolhida:.*$/i, '').trim();
      const hint = (card.querySelector('.bia-meta')?.innerText || '').trim();
      const rows = [];
      for (const tr of card.querySelectorAll('tbody tr')) {
        const tds = [...tr.querySelectorAll('td')];
        if (tds.length < 12) continue;
        const main = tds[1];
        rows.push({
          titulo: (main.querySelector('.bia-main')?.innerText || '').trim(),
          interpretacaoIa: (main.querySelector('.bia-ia-hint')?.innerText || '').trim(),
          orgaoCidade: (main.querySelectorAll('.bia-sub')[0]?.innerText || '').trim(),
          modalidadeStatus: (main.querySelectorAll('.bia-sub')[1]?.innerText || '').trim(),
          similaridade: /similaridade/i.test(main.innerText || ''),
          plataforma: (main.querySelector('.bia-plat-badge')?.innerText || '').trim(),
          esfera: (tds[2]?.innerText || '').trim(),
          inciso: (tds[3]?.innerText || '').trim(),
          quantidade: (tds[4]?.innerText || '').trim(),
          uf: (tds[5]?.innerText || '').trim().replace(/\s+/g, ' '),
          data: (tds[6]?.innerText || '').trim(),
          valorText: (tds[7]?.innerText || '').trim(),
          faixaText: (tds[8]?.innerText || '').trim(),
          confiabilidade: (tds[9]?.innerText || '').trim(),
          risco: (tds[10]?.innerText || '').trim(),
          scoreText: (tds[11]?.innerText || '').trim(),
          processo: (tds[12]?.innerText || '').trim(),
        });
      }
      groups.push({
        label,
        mediaText: mediaMatch ? mediaMatch[1].trim() : '',
        hint,
        rows,
      });
    }

    const progress = metaAll.find((t) => /Busca automática/i.test(t)) || '';
    const faixaGlobal = metaAll.find((t) => /Faixa global/i.test(t)) || '';
    const lastFailure = metaAll.find((t) => /Última falha/i.test(t)) || '';
    const searchError = metaAll.find((t) => /erro|falha ao/i.test(t) && !/falha\(s\)/i.test(t)) || '';

    return {
      scrapedAt: new Date().toISOString(),
      url: location.href,
      metaAll,
      progress,
      faixaGlobal,
      lastFailure,
      searchError,
      groupCount: groups.length,
      rowCount: groups.reduce((n, g) => n + g.rows.length, 0),
      groups,
    };
  });
}

export function normalizeScraped(raw) {
  const groups = (raw.groups || []).map((g) => {
    const rows = (g.rows || []).map((r) => {
      const faixa = parseFaixaCell(r.faixaText);
      const valor = parseBrl(r.valorText);
      const score = parseScorePercent(r.scoreText);
      return {
        ...r,
        valor,
        score,
        faixa,
        foraFaixa:
          valor != null
          && faixa.min != null
          && faixa.max != null
          && (valor < faixa.min - 1e-9 || valor > faixa.max + 1e-9),
      };
    });
    return {
      ...g,
      media: parseBrl(g.mediaText),
      rows,
    };
  });
  return { ...raw, groups };
}
