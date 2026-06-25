import test from 'node:test';
import assert from 'node:assert/strict';

import {
  hasValidPnCpFornecedorParaBusca,
  passesPnCpSearchDisplayGate,
  hasDisplayPnCpPrecoPositivo,
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
