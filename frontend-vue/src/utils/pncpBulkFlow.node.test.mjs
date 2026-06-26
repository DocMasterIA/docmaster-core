import test from 'node:test';
import assert from 'node:assert/strict';

import {
  hasValidPnCpFornecedorParaBusca,
  passesPnCpSearchDisplayGate,
  hasDisplayPnCpPrecoPositivo,
  hasCnpjFornecedorSalvar,
  canSalvarCotacaoPnCp,
  extractCnpjFornecedorSalvar,
} from './pncpPricing.js';

test('rejeita fornecedor Não se aplica na busca', () => {
  const row = {
    sourceRaw: {
      valor_unitario_estimado: 10,
      fornecedor: 'Não se aplica',
    },
  };
  assert.equal(hasDisplayPnCpPrecoPositivo(row), true);
  assert.equal(hasValidPnCpFornecedorParaBusca(row), false);
  assert.equal(passesPnCpSearchDisplayGate(row), false);
});

test('aceita CNPJ 14 dígitos mesmo sem razão social', () => {
  const row = {
    sourceRaw: {
      valor_unitario_estimado: 10,
      cnpj_fornecedor: '12.345.678/0001-95',
      fornecedor: '',
    },
  };
  assert.equal(passesPnCpSearchDisplayGate(row), true);
});

test('em lote exige CNPJ para exibir (alinha com save)', () => {
  const row = {
    sourceRaw: {
      valor_unitario_estimado: 10,
      fornecedor: 'FORNECEDORA EXEMPLO LTDA',
    },
  };
  assert.equal(passesPnCpSearchDisplayGate(row), true);
  assert.equal(passesPnCpSearchDisplayGate(row, { requireCnpjForSave: true }), false);
});

test('em lote aceita linha com CNPJ', () => {
  const row = {
    sourceRaw: {
      valor_unitario_estimado: 10,
      cnpj_fornecedor: '12.345.678/0001-95',
      fornecedor: 'FORNECEDORA EXEMPLO LTDA',
    },
  };
  assert.equal(passesPnCpSearchDisplayGate(row, { requireCnpjForSave: true }), true);
});

test('em lote aceita CNPJ em niFornecedor (campo PNCP comum)', () => {
  const row = {
    sourceRaw: {
      valor_unitario_estimado: 10,
      niFornecedor: '12345678000195',
      fornecedor: 'FORNECEDORA EXEMPLO LTDA',
    },
  };
  assert.equal(passesPnCpSearchDisplayGate(row, { requireCnpjForSave: true }), true);
});

test('niFornecedor conta para hasCnpjFornecedorSalvar (mesma regra do save)', () => {
  const row = {
    sourceRaw: {
      valor_unitario_estimado: 10,
      niFornecedor: '12345678000195',
      fornecedor: 'FORNECEDORA EXEMPLO LTDA',
    },
  };
  assert.equal(hasCnpjFornecedorSalvar(row), true);
  assert.ok(extractCnpjFornecedorSalvar(row));
});

test('homologado com chaves PNCP pode salvar sem CNPJ no índice (enrich no backend)', () => {
  const row = {
    numeroPncp: '12345678000195-1-000001',
    anoCompra: 2024,
    sequencialCompra: 1,
    sourceRaw: {
      valor_unitario_homologado: 5,
      fornecedor: 'FORNECEDORA EXEMPLO LTDA',
      item_homologado: true,
    },
  };
  assert.equal(hasCnpjFornecedorSalvar(row), false);
  assert.equal(canSalvarCotacaoPnCp(row), true);
});

test('aceita razão social útil com preço', () => {
  const row = {
    sourceRaw: {
      valor_unitario_estimado: 10,
      fornecedor: 'FORNECEDORA EXEMPLO LTDA',
    },
  };
  assert.equal(passesPnCpSearchDisplayGate(row), true);
});

test('rejeita linha sem preço', () => {
  const row = {
    sourceRaw: {
      valor_unitario: 0,
      fornecedor: 'FORNECEDORA EXEMPLO LTDA',
    },
  };
  assert.equal(passesPnCpSearchDisplayGate(row), false);
});
