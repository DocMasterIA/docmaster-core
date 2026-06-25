/** Extrai preços estimado vs homologado de linhas PNCP (cotação / busca). */

export function pickPositiveNumber(...vals) {
  for (const v of vals) {
    const n = Number(v);
    if (Number.isFinite(n) && n > 0) return n;
  }
  return null;
}

/** Mescla source externo (ORM) com source aninhado (payload salvo na criação). */
export function mergedPnCpSource(row) {
  const raw = row?.sourceRaw && typeof row.sourceRaw === 'object' ? row.sourceRaw : {};
  const outer = row?.source && typeof row.source === 'object' ? row.source : {};
  const inner = outer?.source && typeof outer.source === 'object' ? outer.source : {};
  return { ...inner, ...raw, ...outer };
}

export function extractPnCpHomologadoUnit(row) {
  const src = mergedPnCpSource(row);
  return pickPositiveNumber(
    src.valor_unitario_homologado,
    src.valorUnitarioHomologado,
    row?.valor_unitario_homologado,
  );
}

export function extractPnCpEstimadoUnit(row) {
  const src = mergedPnCpSource(row);
  return pickPositiveNumber(
    src.valor_unitario_estimado,
    src.valorUnitarioEstimado,
    row?.valor_unitario_estimado,
  );
}

export function hasPnCpHomologadoPreco(row) {
  const src = mergedPnCpSource(row);
  return (
    extractPnCpHomologadoUnit(row) != null
    || pickPositiveNumber(
      src.valor_total_homologado,
      src.valorTotalHomologado,
      row?.valor_total_homologado,
    ) != null
  );
}

export function extractPnCpHomologadoTotal(row) {
  const src = mergedPnCpSource(row);
  const direct = pickPositiveNumber(
    src.valor_total_homologado,
    src.valorTotalHomologado,
    row?.valor_total_homologado,
  );
  if (direct) return direct;
  const unit = extractPnCpHomologadoUnit(row);
  const qtd = pickPositiveNumber(
    src.quantidade_homologada,
    src.quantidadeHomologada,
    row?.quantidade,
    src.quantidade,
  );
  if (unit && qtd) return unit * qtd;
  return null;
}

export function extractPnCpEstimadoTotal(row) {
  const src = mergedPnCpSource(row);
  const direct = pickPositiveNumber(
    src.valor_total_estimado,
    src.valorTotalEstimado,
    row?.valor_total_estimado,
  );
  if (direct) return direct;
  const unit = extractPnCpEstimadoUnit(row);
  const qtd = pickPositiveNumber(
    src.quantidade_estimada,
    src.quantidadeEstimada,
    row?.quantidade,
    src.quantidade,
  );
  if (unit && qtd) return unit * qtd;
  return null;
}

function deriveUnitFromTotal(row) {
  const src = mergedPnCpSource(row);
  const pairs = [
    [extractPnCpHomologadoTotal(row), pickPositiveNumber(
      src.quantidade_homologada,
      src.quantidadeHomologada,
      row?.quantidade,
      src.quantidade,
    )],
    [pickPositiveNumber(src.valor_total, row?.valor_total), pickPositiveNumber(row?.quantidade, src.quantidade)],
    [extractPnCpEstimadoTotal(row), pickPositiveNumber(
      src.quantidade_estimada,
      src.quantidadeEstimada,
      row?.quantidade,
      src.quantidade,
    )],
  ];
  for (const [total, qtd] of pairs) {
    if (total != null && qtd != null && qtd > 0) return total / qtd;
  }
  return null;
}

export function displayPnCpUnitario(row) {
  const src = mergedPnCpSource(row);
  const hom = extractPnCpHomologadoUnit(row);
  if (hom != null) return hom;
  const homologado = isPnCpItemHomologado(row) || hasPnCpHomologadoPreco(row);
  const ormUnit = pickPositiveNumber(src.valor_unitario, row?.valor_unitario);
  if (homologado && ormUnit != null) return ormUnit;
  const est = extractPnCpEstimadoUnit(row);
  if (est != null) return est;
  if (ormUnit != null) return ormUnit;
  return deriveUnitFromTotal(row);
}

export function hasDisplayPnCpPrecoPositivo(row) {
  const unit = displayPnCpUnitario(row);
  return unit != null && unit > 0;
}

const FORNECEDOR_PLACEHOLDER = new Set([
  'demais',
  'nao informado',
  'não informado',
  'nao informada',
  'não informada',
  'epp',
  'me',
  'mei',
  'outros',
  'n/a',
  'na',
  'n.a',
  'n.a.',
  'nao se aplica',
  'não se aplica',
  'nao aplicavel',
  'não aplicavel',
  'não aplicável',
  'sem fornecedor',
  'nao consta',
  'não consta',
  'inexistente',
  '-',
  '—',
]);

function cnpjDigits14(row) {
  const src = mergedPnCpSource(row);
  const raw = row?.cnpjFornecedor || src.cnpj_fornecedor || src.cnpjFornecedor || src.niFornecedor || src.cnpj || '';
  const digits = String(raw).replace(/\D/g, '');
  return digits.length === 14 ? digits : '';
}

function fornecedorNomeUtil(nome) {
  const n = String(nome || '').trim();
  if (n.length < 3) return false;
  const low = n.replace(/\s+/g, ' ').toLowerCase();
  if (FORNECEDOR_PLACEHOLDER.has(low)) return false;
  if (low.startsWith('pncp_')) return false;
  if (/^\d{2}\.?\d{3}\.?\d{3}\/?\d{4}-?\d{2}$/.test(n.replace(/\s/g, ''))) return false;
  if (low.replace(/\D/g, '').length === 14) return false;
  return true;
}

/** CNPJ 14 dígitos ou razão social útil (exclui «Não se aplica» e similares). */
export function hasValidPnCpFornecedorParaBusca(row) {
  if (cnpjDigits14(row)) return true;
  const src = mergedPnCpSource(row);
  const names = [
    row?.fornecedor,
    src.fornecedor,
    src.nomeRazaoSocialFornecedor,
    src.fornecedor_nome,
    src.nome_fornecedor,
    src.fornecedor_cadastro?.razao_social,
    src.fornecedor_cadastro?.nome_fantasia,
  ]
    .map((v) => String(v || '').trim())
    .filter(Boolean);
  return names.some(fornecedorNomeUtil);
}

/** Preço positivo + fornecedor válido para exibir na pesquisa. */
export function passesPnCpSearchDisplayGate(row) {
  return hasDisplayPnCpPrecoPositivo(row) && hasValidPnCpFornecedorParaBusca(row);
}

/** Calcula min/max da faixa regional (espelha backend pricing_faixa). */
export function computeFaixaRegional(valorBase, variacaoPct, sentido = 'ambos') {
  const base = Number(valorBase);
  const pct = Math.max(0, Number(variacaoPct));
  if (!Number.isFinite(base) || base <= 0 || !Number.isFinite(pct)) {
    return { min: null, max: null, sentido: 'ambos' };
  }
  const s = ['cima', 'baixo', 'ambos'].includes(String(sentido || '').toLowerCase())
    ? String(sentido).toLowerCase()
    : 'ambos';
  const f = pct / 100;
  if (s === 'baixo') return { min: Math.max(0, base * (1 - f)), max: base, sentido: s };
  if (s === 'cima') return { min: base, max: base * (1 + f), sentido: s };
  return { min: Math.max(0, base * (1 - f)), max: base * (1 + f), sentido: s };
}

/** Texto curto da faixa para mensagens de UI. */
export function formatFaixaResumo(valorBase, variacaoPct, sentido = 'ambos') {
  const { min, max, sentido: s } = computeFaixaRegional(valorBase, variacaoPct, sentido);
  if (min == null || max == null) return '';
  const baseFmt = Number(valorBase).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  const minFmt = min.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  const maxFmt = max.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  const pct = Math.round(Number(variacaoPct));
  if (s === 'baixo') return `base ${baseFmt}, até ${pct}% abaixo (${minFmt} – ${maxFmt})`;
  if (s === 'cima') return `base ${baseFmt}, até ${pct}% acima (${minFmt} – ${maxFmt})`;
  return `base ${baseFmt}, ±${pct}% (${minFmt} – ${maxFmt})`;
}

export function displayPnCpTotal(row) {
  const hom = extractPnCpHomologadoTotal(row);
  if (hom != null) return hom;
  const src = mergedPnCpSource(row);
  const homologado = isPnCpItemHomologado(row) || hasPnCpHomologadoPreco(row);
  const ormTotal = pickPositiveNumber(src.valor_total, row?.valor_total);
  if (homologado && ormTotal != null) return ormTotal;
  const estTotal = extractPnCpEstimadoTotal(row);
  if (estTotal != null) return estTotal;
  const unit = displayPnCpUnitario(row);
  const qtd = pickPositiveNumber(row?.quantidade, src.quantidade);
  if (unit != null && qtd != null) return unit * qtd;
  return ormTotal;
}

/** Item homologado na PNCP mas preço vencedor ainda não veio de /resultados. */
export function isPnCpHomologadoSemPrecoVencedor(row) {
  return isPnCpItemHomologado(row) && !hasPnCpHomologadoPreco(row);
}

export function hasPnCpEstimadoDistinto(row) {
  const est = extractPnCpEstimadoUnit(row);
  const hom = extractPnCpHomologadoUnit(row);
  if (!est || !hom) return false;
  return Math.abs(est - hom) > 0.001;
}

export function isPnCpItemHomologado(row) {
  const src = mergedPnCpSource(row);
  if (src.item_homologado === true) return true;
  if (src.temResultado === true) return true;
  const sit = String(
    src.situacaoCompraItemNome || src.situacao_item || src.situacao || '',
  ).toLowerCase();
  return sit.includes('homolog') || sit.includes('adjudic');
}
