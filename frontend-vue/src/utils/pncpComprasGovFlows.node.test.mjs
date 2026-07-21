/**
 * Fluxos Compras.gov no frontend: save meta, labels, falhas de salvabilidade.
 */
import test from 'node:test';
import assert from 'node:assert/strict';

import {
  isComprasGovPlatform,
  isTceRsPlatform,
  normalizePlataformaId,
  plataformaBadgeShort,
  plataformaFonteCurta,
  plataformaLabel,
  platformSaveMeta,
  pickDefaultFontes,
} from './pncpPriceSources.js';

import {
  canSalvarCotacaoPnCp,
  isComprasGovRow,
  resolveRowPlataforma,
} from './pncpPricing.js';

test('normalize e detecção compras_gov / tce', () => {
  assert.equal(normalizePlataformaId('compras-gov'), 'compras_gov');
  assert.equal(isComprasGovPlatform('compras_gov'), true);
  assert.equal(isComprasGovPlatform('compras-gov'), true);
  assert.equal(isComprasGovPlatform('pncp'), false);
  assert.equal(isTceRsPlatform('tce_rs'), true);
  assert.equal(isTceRsPlatform('compras_gov'), false);
});

test('labels e badge Compras.gov', () => {
  assert.equal(plataformaBadgeShort('compras_gov'), 'Compras.gov');
  assert.equal(plataformaFonteCurta('compras_gov'), 'Compras.gov');
  assert.match(plataformaLabel('compras_gov'), /Compras\.gov/);
});

test('platformSaveMeta compras_gov força inciso I / federal / governamentais', () => {
  const meta = platformSaveMeta('compras_gov', {
    inciso_classificacao: 'inciso_ii',
    esfera_administrativa: 'estadual',
    fonte: 'entes_publicos',
  });
  assert.equal(meta.inciso_classificacao, 'inciso_i');
  assert.equal(meta.esfera_administrativa, 'federal');
  assert.equal(meta.fonte, 'governamentais');
});

test('platformSaveMeta tce_rs continua inciso II', () => {
  const meta = platformSaveMeta('tce_rs');
  assert.equal(meta.inciso_classificacao, 'inciso_ii');
  assert.equal(meta.fonte, 'entes_publicos');
});

test('pickDefaultFontes ignora compras_gov sem search_ready', () => {
  const out = pickDefaultFontes([
    { id: 'pncp', search_ready: true },
    { id: 'compras_gov', search_ready: false },
    { id: 'tce_rs', search_ready: false },
  ]);
  assert.deepEqual(out, ['pncp']);
});

test('pickDefaultFontes inclui compras_gov quando ready', () => {
  const out = pickDefaultFontes([
    { id: 'pncp', search_ready: true },
    { id: 'compras_gov', search_ready: true },
  ]);
  assert.ok(out.includes('pncp'));
  assert.ok(out.includes('compras_gov'));
});

test('resolveRowPlataforma e isComprasGovRow', () => {
  const row = { sourceRaw: { plataforma: 'compras_gov', valor_unitario: 9 } };
  assert.equal(resolveRowPlataforma(row), 'compras_gov');
  assert.equal(isComprasGovRow(row), true);
});

test('compras_gov salva com CNPJ', () => {
  const row = {
    plataforma: 'compras_gov',
    sourceRaw: {
      plataforma: 'compras_gov',
      valor_unitario: 12,
      cnpj_fornecedor: '12345678000195',
      fornecedor_nome: 'FORN CG LTDA',
      plataforma_item_id: 'cg:1:1',
    },
  };
  assert.equal(canSalvarCotacaoPnCp(row), true);
});

test('compras_gov salva com processo + fornecedor sem CNPJ', () => {
  const row = {
    sourceRaw: {
      plataforma: 'compras_gov',
      valor_unitario: 12,
      plataforma_item_id: 'cg:compra:7',
      fornecedor: 'EMPRESA COMPRAS GOV LTDA',
    },
  };
  assert.equal(canSalvarCotacaoPnCp(row), true);
});

test('falha: compras_gov sem CNPJ e sem processo não salva', () => {
  const row = {
    sourceRaw: {
      plataforma: 'compras_gov',
      valor_unitario: 12,
      fornecedor: 'EMPRESA SEM ID LTDA',
    },
  };
  assert.equal(canSalvarCotacaoPnCp(row), false);
});

test('falha: compras_gov sem fornecedor identificável não salva', () => {
  const row = {
    sourceRaw: {
      plataforma: 'compras_gov',
      valor_unitario: 12,
      plataforma_item_id: 'cg:1:1',
      fornecedor: 'Não se aplica',
    },
  };
  assert.equal(canSalvarCotacaoPnCp(row), false);
});
