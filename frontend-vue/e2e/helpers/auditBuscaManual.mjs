/**
 * Auditoria da Busca Manual (um item): fontes, faixa, amostra lexical.
 */
import { compareTermToCandidate } from './compareItems.mjs';
import { money } from './priceAnalysis.mjs';

/**
 * @param {object} data normalizeManualScraped + apiSamples
 * @param {{ failOnMismatch?: boolean }} opts
 */
export function auditBuscaManual(data, opts = {}) {
  const failOnMismatch = Boolean(opts.failOnMismatch);
  const findings = [];
  const push = (severity, code, message, detail = {}) => {
    findings.push({ severity, code, message, ...detail });
  };

  const term = String(data.descricao || '').trim();
  const rows = data.rows || [];
  const platCount = {};
  let foraFaixa = 0;
  let mismatches = 0;
  let partials = 0;
  const mismatchSamples = [];

  if (/erro|falha/i.test(data.searchError || '')) {
    push('critical', 'search_error', data.searchError);
  }
  if (!term) {
    push('critical', 'sem_termo', 'Campo descrição vazio — itemId pode não ter carregado a cotação.');
  }
  if (rows.length === 0) {
    push('critical', 'sem_resultados', 'Busca manual retornou 0 linhas na UI.');
  }

  for (const r of rows) {
    const plat = r.plataforma || 'desconhecida';
    platCount[plat] = (platCount[plat] || 0) + 1;

    if (r.foraFaixa) {
      foraFaixa += 1;
      push('critical', 'preco_fora_faixa', `${money(r.valor)} fora da faixa (${term})`, {
        titulo: r.titulo,
        valor: r.valor,
        plataforma: plat,
      });
    }

    if (term) {
      const cmp = compareTermToCandidate(term, r.titulo || '');
      if (cmp.verdict === 'mismatch') {
        mismatches += 1;
        if (mismatchSamples.length < 30) {
          mismatchSamples.push({
            titulo: r.titulo,
            valor: r.valor,
            plataforma: plat,
            reasons: cmp.reasons,
            overlap: cmp.overlap,
          });
        }
        if (failOnMismatch) {
          push('critical', 'mismatch', `Mismatch: ${r.titulo}`, { plataforma: plat, reasons: cmp.reasons });
        } else {
          push('warn', 'mismatch', `Mismatch (lista ampla): ${r.titulo}`, { plataforma: plat });
        }
      } else if (cmp.verdict === 'partial') {
        partials += 1;
      }
    }
  }

  const api = Array.isArray(data.apiSamples) ? data.apiSamples : [];
  const lastOk = [...api].reverse().find((s) => s.ok && s.nItens != null);
  if (lastOk && lastOk.listaCompleta === false) {
    push('warn', 'sem_lista_completa', 'Última resposta federada sem lista_completa=true.');
  }
  if (lastOk?.fontes && typeof lastOk.fontes === 'object') {
    const fontesZeradas = Object.entries(lastOk.fontes)
      .filter(([, st]) => st && Number(st.hits || 0) === 0 && !st.skipped)
      .map(([k]) => k);
    if (fontesZeradas.length) {
      push('warn', 'fonte_zero_hits', `Fontes com 0 hits: ${fontesZeradas.join(', ')}`, { fontes: lastOk.fontes });
    }
  }

  const critical = findings.filter((f) => f.severity === 'critical').length;
  const warn = findings.filter((f) => f.severity === 'warn').length;

  const summary = {
    termo: term,
    resultadosUi: rows.length,
    resultadosApi: lastOk?.nItens ?? null,
    foraFaixa,
    mismatches,
    partials,
    plataformas: platCount,
    fontesApi: lastOk?.fontes || null,
    listaCompleta: lastOk?.listaCompleta ?? null,
    critical,
    warn,
  };

  const feedback = renderManualFeedback(summary, mismatchSamples, findings);
  return { summary, findings, mismatchSamples, feedback, critical, warn };
}

function renderManualFeedback(summary, mismatchSamples, findings) {
  const lines = [
    '## Resumo — Busca Manual (item)',
    '',
    `| Métrica | Valor |`,
    `|---------|------:|`,
    `| Termo | ${summary.termo || '—'} |`,
    `| Resultados UI | ${summary.resultadosUi} |`,
    `| Resultados API | ${summary.resultadosApi ?? '—'} |`,
    `| lista_completa | ${summary.listaCompleta ?? '—'} |`,
    `| Fora da faixa | ${summary.foraFaixa} |`,
    `| Mismatch (amostra lexical) | ${summary.mismatches} |`,
    `| Match parcial | ${summary.partials} |`,
    `| Plataformas UI | ${JSON.stringify(summary.plataformas)} |`,
    `| Fontes API (hits) | ${JSON.stringify(summary.fontesApi)} |`,
    '',
  ];

  if (mismatchSamples.length) {
    lines.push('## Amostra mismatches (lista ampla — esperado ter ruído)');
    lines.push('');
    lines.push('| Plataforma | Preço | Candidato | Motivo |');
    lines.push('|---|---:|---|---|');
    for (const m of mismatchSamples.slice(0, 15)) {
      const reason = (m.reasons || []).join('; ').replace(/\|/g, '/');
      lines.push(
        `| ${m.plataforma || '—'} | ${money(m.valor)} | ${(m.titulo || '').slice(0, 80)} | ${reason.slice(0, 120)} |`,
      );
    }
    lines.push('');
  }

  const crits = findings.filter((f) => f.severity === 'critical');
  if (crits.length) {
    lines.push('## Críticos');
    lines.push('');
    for (const f of crits) lines.push(`- **${f.code}**: ${f.message}`);
    lines.push('');
  }

  lines.push('## Interpretação');
  lines.push('');
  lines.push(
    '1. Manual usa `lista_completa` — lista larga multi-fonte; mismatch lexical é esperado em volume.',
  );
  lines.push(
    '2. União de fontes: olhar `Fontes API (hits)` e `Plataformas UI` (PNCP / TCE-RS / Compras.gov).',
  );
  lines.push('3. Gate de faixa: `Fora da faixa` deve ser 0 quando BASE+VAR estão ativos.');
  lines.push('');
  lines.push(
    `**Veredito:** ${summary.critical > 0 ? 'FALHA' : 'OK (critérios manuais)'} — ${summary.critical} crítico(s), ${summary.warn} aviso(s).`,
  );
  return lines.join('\n');
}

export function renderManualAuditMarkdown(audit, data) {
  return [
    '# Auditoria — Busca Manual (item)',
    '',
    `- URL: ${data.url || '—'}`,
    `- Capturado: ${data.scrapedAt || '—'}`,
    `- itemId: ${data.itemId ?? '—'}`,
    `- cotacaoId: ${data.cotacaoId ?? '—'}`,
    '',
    audit.feedback,
  ].join('\n');
}
