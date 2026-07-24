/**
 * Auditoria técnica da Busca Inteligente:
 * - comparação termo × candidato
 * - análise estatística de preços vs BASE/VAR
 * - relatório acionável (não só contagem de warns)
 */

import { compareTermToCandidate } from './compareItems.mjs';
import { money, priceVsFaixa, round, stats } from './priceAnalysis.mjs';

function pct(n, d) {
  if (!d) return 0;
  return Math.round((1000 * n) / d) / 10;
}

/**
 * @param {import('./scrapeBuscaIa.mjs').normalizeScraped extends Function ? any : any} data
 */
export function auditBuscaIa(data, opts = {}) {
  const findings = [];
  const push = (severity, code, message, detail = {}) => {
    findings.push({ severity, code, message, ...detail });
  };

  const itemReports = [];
  const mismatchSamples = [];
  const groups = data.groups || [];

  if (/erro fatal|não autenticado|sessão expirada/i.test(data.searchError || '')) {
    push('critical', 'search_error', data.searchError);
  }
  if (data.lastFailure) push('warn', 'bulk_last_failure', data.lastFailure);

  const prog = String(data.progress || '');
  const doneMatch = prog.match(/(\d+)\s+de\s+(\d+)\s+item/i);
  if (doneMatch) {
    const done = Number(doneMatch[1]);
    const total = Number(doneMatch[2]);
    if (/parcial/i.test(prog) || done < total) {
      push('warn', 'bulk_incomplete', `Busca incompleta: ${done}/${total} itens.`, { done, total });
    }
  }

  const platCount = {};
  let foraFaixa = 0;
  let mismatches = 0;
  let partials = 0;
  let gruposSemPreco = 0;
  let gruposPoucos = 0;

  for (const g of groups) {
    const term = g.label || '';
    const quotes = [];

    for (const r of g.rows || []) {
      const plat = r.plataforma || 'desconhecida';
      platCount[plat] = (platCount[plat] || 0) + 1;

      const cmp = compareTermToCandidate(term, r.titulo || '');
      const vs = priceVsFaixa(r.valor, r.faixa);
      if (vs.dentro === false) {
        foraFaixa += 1;
        push('critical', 'preco_fora_faixa', `${money(r.valor)} fora de ${money(vs.min)}–${money(vs.max)} (${term})`, {
          item: term,
          valor: r.valor,
          ...vs,
          titulo: r.titulo,
          plataforma: plat,
        });
      }
      if (cmp.verdict === 'mismatch') {
        mismatches += 1;
        if (mismatchSamples.length < 40) {
          mismatchSamples.push({
            item: term,
            titulo: r.titulo,
            valor: r.valor,
            score: r.score,
            plataforma: plat,
            reasons: cmp.reasons,
            overlap: cmp.overlap,
            jaccard: cmp.jaccard,
            missingCore: cmp.missingCore,
            anchorsMissing: cmp.anchorsMissing,
          });
        }
        push('critical', 'match_mismatch', `Candidato incompatível com o termo: «${r.titulo}» ← «${term}»`, {
          item: term,
          titulo: r.titulo,
          reasons: cmp.reasons,
          overlap: cmp.overlap,
        });
      } else if (cmp.verdict === 'partial') {
        partials += 1;
        push('warn', 'match_partial', `Match parcial: «${r.titulo}» ← «${term}» (${cmp.reasons[0] || 'cobertura baixa'})`, {
          item: term,
          titulo: r.titulo,
          overlap: cmp.overlap,
        });
      }

      quotes.push({
        titulo: r.titulo,
        valor: r.valor,
        valorText: r.valorText,
        score: r.score,
        plataforma: plat,
        esfera: r.esfera,
        inciso: r.inciso,
        uf: r.uf,
        processo: r.processo,
        similaridadeUi: Boolean(r.similaridade),
        confiabilidade: r.confiabilidade,
        risco: r.risco,
        faixa: r.faixa,
        vsFaixa: vs,
        compare: {
          verdict: cmp.verdict,
          overlap: cmp.overlap,
          jaccard: cmp.jaccard,
          missingCore: cmp.missingCore,
          anchorsMissing: cmp.anchorsMissing,
          anchorsTerm: cmp.anchorsTerm,
          anchorsCand: cmp.anchorsCand,
          familyConflict: cmp.familyConflict,
          reasons: cmp.reasons,
        },
      });
    }

    if (!quotes.length) {
      gruposSemPreco += 1;
      push('warn', 'item_sem_cotacao', `Item sem cotações: ${term}`, { item: term });
    } else if (quotes.length < 3) {
      gruposPoucos += 1;
      push('warn', 'item_menos_de_3', `Item com só ${quotes.length} cotação(ões): ${term}`, {
        item: term,
        n: quotes.length,
      });
    }

    const priceStats = stats(quotes.map((q) => q.valor));
    const base = quotes.find((q) => q.faixa?.base != null)?.faixa.base
      ?? quotes[0]?.vsFaixa?.base
      ?? null;
    const varPct = quotes.find((q) => q.faixa?.varPct != null)?.faixa.varPct ?? null;
    const faixaMin = quotes.find((q) => q.faixa?.min != null)?.faixa.min ?? null;
    const faixaMax = quotes.find((q) => q.faixa?.max != null)?.faixa.max ?? null;

    // Distância média |valor-base|/base
    const deltas = quotes
      .map((q) => q.vsFaixa.deltaBasePct)
      .filter((d) => d != null);
    const meanAbsDelta = deltas.length
      ? round(deltas.reduce((a, b) => a + Math.abs(b), 0) / deltas.length, 2)
      : null;

    itemReports.push({
      term,
      mediaUi: g.media,
      nQuotes: quotes.length,
      base,
      varPct,
      faixaMin,
      faixaMax,
      priceStats,
      meanAbsDeltaPct: meanAbsDelta,
      matchSummary: {
        match: quotes.filter((q) => q.compare.verdict === 'match').length,
        partial: quotes.filter((q) => q.compare.verdict === 'partial').length,
        mismatch: quotes.filter((q) => q.compare.verdict === 'mismatch').length,
      },
      quotes,
    });
  }

  const critical = findings.filter((f) => f.severity === 'critical');
  const warn = findings.filter((f) => f.severity === 'warn');
  const info = findings.filter((f) => f.severity === 'info');

  const summary = {
    groups: groups.length,
    rows: itemReports.reduce((n, it) => n + it.nQuotes, 0),
    critical: critical.length,
    warn: warn.length,
    info: info.length,
    foraFaixa,
    mismatches,
    partials,
    gruposSemPreco,
    gruposPoucos,
    platforms: platCount,
    faixaGlobal: data.faixaGlobal || '',
    progress: data.progress || '',
    // métricas de preço agregadas
    itemsWithCvOver30: itemReports.filter((it) => (it.priceStats.cvPct || 0) > 30).length,
    itemsWithMismatch: itemReports.filter((it) => it.matchSummary.mismatch > 0).length,
    meanQuotesPerItem: groups.length
      ? round(itemReports.reduce((n, it) => n + it.nQuotes, 0) / groups.length, 2)
      : 0,
  };

  const feedback = buildTechnicalFeedback({
    data,
    summary,
    itemReports,
    mismatchSamples,
    critical,
    warn,
  });

  return {
    ok: critical.length === 0,
    summary,
    findings,
    itemReports,
    mismatchSamples,
    feedback,
    failOnCritical: opts.failOnCritical !== false,
  };
}

function buildTechnicalFeedback(ctx) {
  const lines = [];
  const s = ctx.summary;
  lines.push('## Resumo técnico');
  lines.push('');
  lines.push('| Métrica | Valor |');
  lines.push('|---------|------:|');
  lines.push(`| Itens (grupos UI) | ${s.groups} |`);
  lines.push(`| Cotações analisadas | ${s.rows} |`);
  lines.push(`| Média cotações/item | ${s.meanQuotesPerItem} |`);
  lines.push(`| Fora da faixa BASE±VAR | ${s.foraFaixa} |`);
  lines.push(`| Mismatch termo×candidato | ${s.mismatches} |`);
  lines.push(`| Match parcial | ${s.partials} |`);
  lines.push(`| Itens com CV preço > 30% | ${s.itemsWithCvOver30} |`);
  lines.push(`| Itens com ≥1 mismatch | ${s.itemsWithMismatch} |`);
  lines.push(`| Itens < 3 cotações | ${s.gruposPoucos} |`);
  lines.push(`| Plataformas | ${JSON.stringify(s.platforms)} |`);
  lines.push('');
  if (s.faixaGlobal) lines.push(`Faixa global: ${s.faixaGlobal.replace(/\n/g, ' ')}`);
  if (s.progress) lines.push(`Progresso: ${s.progress}`);
  lines.push('');

  lines.push('## Catálogo de mismatches (termo ≠ produto pego)');
  lines.push('');
  if (!ctx.mismatchSamples.length) {
    lines.push('_Nenhum mismatch lexical/família detectado pela heurística do auditor._');
  } else {
    lines.push('| Item (termo) | Candidato pego | Preço | Score | Overlap | Motivo |');
    lines.push('|---|---|---:|---:|---:|---|');
    for (const m of ctx.mismatchSamples.slice(0, 25)) {
      lines.push(
        `| ${esc(m.item)} | ${esc(m.titulo)} | ${money(m.valor)} | ${m.score ?? '—'}% | ${pct(m.overlap, 1)}% | ${esc((m.reasons || []).join('; '))} |`,
      );
    }
  }
  lines.push('');

  lines.push('## Análise de preços por item (amostra pior CV / mismatch)');
  lines.push('');
  const ranked = [...ctx.itemReports]
    .filter((it) => it.nQuotes > 0)
    .sort((a, b) => {
      const scoreA = (a.matchSummary.mismatch * 10) + (a.priceStats.cvPct || 0);
      const scoreB = (b.matchSummary.mismatch * 10) + (b.priceStats.cvPct || 0);
      return scoreB - scoreA;
    })
    .slice(0, 15);

  for (const it of ranked) {
    lines.push(`### ${it.term}`);
    lines.push('');
    lines.push(
      `- BASE ${money(it.base)} · VAR ${it.varPct ?? '—'}% · faixa ${money(it.faixaMin)}–${money(it.faixaMax)}`,
    );
    lines.push(
      `- n=${it.priceStats.n} · min ${money(it.priceStats.min)} · mediana ${money(it.priceStats.median)} · `
      + `média ${money(it.priceStats.mean)} · max ${money(it.priceStats.max)} · `
      + `σ ${money(it.priceStats.stdev)} · **CV ${it.priceStats.cvPct ?? '—'}%** · `
      + `max/min ×${it.priceStats.ratioMaxMin ?? '—'} · |Δ| médio vs BASE ${it.meanAbsDeltaPct ?? '—'}%`,
    );
    lines.push(
      `- Match: ${it.matchSummary.match} ok / ${it.matchSummary.partial} parcial / **${it.matchSummary.mismatch} mismatch**`,
    );
    lines.push('');
    lines.push('| # | Preço | Δ BASE | Pos. faixa | Score | Plat. | Verdict | Candidato | Motivos |');
    lines.push('|--:|---:|---:|---:|---:|---|---|---|---|');
    it.quotes.forEach((q, i) => {
      lines.push(
        `| ${i + 1} | ${money(q.valor)} | ${fmtDelta(q.vsFaixa.deltaBasePct)} | ${fmtPos(q.vsFaixa.posFaixa)} | `
        + `${q.score ?? '—'}% | ${esc(q.plataforma)} | **${q.compare.verdict}** | ${esc(q.titulo)} | `
        + `${esc((q.compare.reasons || []).slice(0, 2).join('; ') || '—')} |`,
      );
    });
    lines.push('');
  }

  lines.push('## Interpretação para o researcher');
  lines.push('');
  if (s.mismatches > 0) {
    lines.push(
      `1. **${s.mismatches} hits lexicalmente incompatíveis** chegaram ao top da UI. `
      + 'Isso é evidência de falha de filtragem (spec/category/literal), não de faixa. '
      + 'O preço pode estar “dentro da VAR” e mesmo assim ser o produto errado — a cotação fica enviesada.',
    );
  } else {
    lines.push('1. Sem mismatches heurísticos graves nesta amostra.');
  }
  if (s.itemsWithCvOver30 > 0) {
    lines.push(
      `2. **${s.itemsWithCvOver30} itens com CV > 30%** no grupo: dispersão alta costuma acompanhar mix de produtos/embalagens. `
      + 'Cruzar com a coluna Verdict (mismatch/partial) antes de aceitar média.',
    );
  }
  if (s.foraFaixa === 0) {
    lines.push('3. Gate BASE±VAR: nenhum preço fora da faixa na UI nesta rodada.');
  } else {
    lines.push(`3. Gate BASE±VAR: **${s.foraFaixa}** preço(s) fora — regressão do hard-enforce.`);
  }
  lines.push(
    `4. Mix de fontes: ${JSON.stringify(s.platforms)} — se Compras.gov/TCE quase não aparecem, o top-3 está enviesado ao PNCP.`,
  );
  lines.push('');

  const verdict = ctx.critical.length
    ? `**Veredito:** FALHA — ${ctx.critical.length} crítico(s) (mismatch e/ou fora da faixa), ${ctx.warn.length} aviso(s).`
    : ctx.warn.length
      ? `**Veredito:** OK com ressalvas — 0 críticos, ${ctx.warn.length} aviso(s).`
      : '**Veredito:** OK.';
  lines.push(verdict);
  return lines.join('\n');
}

function esc(s) {
  return String(s || '').replace(/\|/g, '/').replace(/\n/g, ' ');
}

function fmtDelta(d) {
  if (d == null) return '—';
  const sign = d > 0 ? '+' : '';
  return `${sign}${d}%`;
}

function fmtPos(p) {
  if (p == null) return '—';
  return `${Math.round(p * 100)}%`;
}

export function renderAuditMarkdown(audit, data) {
  const lines = [];
  lines.push('# Auditoria técnica — Busca IA');
  lines.push('');
  lines.push(`- URL: ${data.url || ''}`);
  lines.push(`- Capturado: ${data.scrapedAt || ''}`);
  lines.push(
    `- Grupos: ${audit.summary.groups} · Linhas: ${audit.summary.rows} · `
    + `Critical: ${audit.summary.critical} · Warn: ${audit.summary.warn}`,
  );
  lines.push('');
  lines.push(audit.feedback);
  lines.push('');
  lines.push('## Anexo — todos os itens (compacto)');
  lines.push('');
  lines.push('| Item | n | BASE | min–max | CV% | mismatch | Δmédio|');
  lines.push('|---|--:|---:|---|---:|---:|---:|');
  for (const it of audit.itemReports || []) {
    lines.push(
      `| ${esc(it.term)} | ${it.nQuotes} | ${money(it.base)} | `
      + `${money(it.priceStats.min)}–${money(it.priceStats.max)} | `
      + `${it.priceStats.cvPct ?? '—'} | ${it.matchSummary.mismatch} | ${it.meanAbsDeltaPct ?? '—'}% |`,
    );
  }
  lines.push('');
  return lines.join('\n');
}
