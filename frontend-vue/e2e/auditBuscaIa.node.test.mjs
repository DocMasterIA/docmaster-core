/**
 * Unit tests: parse + comparação termo×candidato + auditoria técnica.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { parseBrl, parseFaixaCell, normalizeScraped } from './helpers/scrapeBuscaIa.mjs';
import { compareTermToCandidate } from './helpers/compareItems.mjs';
import { stats, priceVsFaixa } from './helpers/priceAnalysis.mjs';
import { auditBuscaIa } from './helpers/auditBuscaIa.mjs';

test('parseBrl / faixa', () => {
  assert.equal(parseBrl('R$ 5,15'), 5.15);
  const f = parseFaixaCell('BASE R$ 6,19\nVAR 25%\nR$ 4,64 – R$ 7,74');
  assert.equal(f.base, 6.19);
  assert.equal(f.min, 4.64);
  assert.equal(f.max, 7.74);
});

test('compare: oxigenada vs boricada = mismatch', () => {
  const c = compareTermToCandidate(
    'ÁGUA OXIGENADA 10 VOLUMES',
    'AGUA BORICADA - Água buricada 3% - 100ml',
  );
  assert.equal(c.verdict, 'mismatch');
  assert.ok(c.familyConflict || c.missingCore.includes('oxigenada'));
});

test('compare: nylon vs fio dental = mismatch', () => {
  const c = compareTermToCandidate(
    'FIO NYLON N° 4.0 COR PRETA COM AGULHA 2,5 CM',
    'FIO DENTAL 100M FIO DENTAL, 100M',
  );
  assert.equal(c.verdict, 'mismatch');
});

test('compare: mesmo produto = match ou partial aceitável', () => {
  const c = compareTermToCandidate(
    'ÁLCOOL 70% FRASCO COM 1 LITRO',
    'Álcool etílico 70% 1L frasco',
  );
  assert.notEqual(c.verdict, 'mismatch');
  assert.ok(c.overlap >= 0.3);
});

test('priceVsFaixa e stats', () => {
  const vs = priceVsFaixa(1.92, { base: 6.19, min: 4.64, max: 7.74 });
  assert.equal(vs.dentro, false);
  assert.ok(vs.deltaBasePct < -60);
  const st = stats([5.15, 6.0, 8.23]);
  assert.equal(st.n, 3);
  assert.ok(st.cvPct > 0);
});

test('audit gera itemReports e mismatch crítico', () => {
  const data = normalizeScraped({
    groups: [{
      label: 'ÁGUA OXIGENADA 10 VOLUMES',
      mediaText: 'R$ -',
      rows: [
        {
          titulo: 'AGUA BORICADA 3%',
          valorText: 'R$ 5,00',
          faixaText: 'BASE R$ 6,00\nVAR 50%\nR$ 3,00 – R$ 9,00',
          scoreText: '54%',
          plataforma: 'PNCP',
          similaridade: true,
          processo: 'x',
        },
        {
          titulo: 'Água oxigenada 10 volumes 1L',
          valorText: 'R$ 6,10',
          faixaText: 'BASE R$ 6,00\nVAR 50%\nR$ 3,00 – R$ 9,00',
          scoreText: '80%',
          plataforma: 'PNCP',
          similaridade: false,
          processo: 'y',
        },
      ],
    }],
    progress: 'Busca automática concluída: 1 de 1',
    faixaGlobal: 'Faixa global: ±50%',
  });
  const audit = auditBuscaIa(data);
  assert.equal(audit.itemReports.length, 1);
  assert.ok(audit.summary.mismatches >= 1);
  assert.ok(audit.findings.some((f) => f.code === 'match_mismatch'));
  assert.match(audit.feedback, /Catálogo de mismatches|Resumo técnico|CV/);
  assert.ok(audit.ok === false);
});
