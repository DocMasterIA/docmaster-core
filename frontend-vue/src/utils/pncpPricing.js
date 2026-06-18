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

export function displayPnCpUnitario(row) {
  const hom = extractPnCpHomologadoUnit(row);
  if (hom != null) return hom;
  const homologado = isPnCpItemHomologado(row) || hasPnCpHomologadoPreco(row);
  if (homologado) {
    const ormUnit = pickPositiveNumber(row?.valor_unitario);
    if (ormUnit != null) return ormUnit;
  }
  const est = extractPnCpEstimadoUnit(row);
  if (est != null && !homologado) return est;
  return pickPositiveNumber(row?.valor_unitario);
}

export function displayPnCpTotal(row) {
  const hom = extractPnCpHomologadoTotal(row);
  if (hom != null) return hom;
  const src = mergedPnCpSource(row);
  const homologado = isPnCpItemHomologado(row) || hasPnCpHomologadoPreco(row);
  if (homologado) {
    const ormTotal = pickPositiveNumber(row?.valor_total);
    if (ormTotal != null) return ormTotal;
  }
  const estTotal = pickPositiveNumber(
    src.valor_total_estimado,
    src.valorTotalEstimado,
    row?.valor_total_estimado,
  );
  if (estTotal != null && !homologado) return estTotal;
  const unit = displayPnCpUnitario(row);
  const qtd = pickPositiveNumber(row?.quantidade, src.quantidade);
  if (unit != null && qtd != null) return unit * qtd;
  return pickPositiveNumber(row?.valor_total);
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
  if src.item_homologado === true) return true;
  if (src.temResultado === true) return true;
  const sit = String(
    src.situacaoCompraItemNome || src.situacao_item || src.situacao || '',
  ).toLowerCase();
  return sit.includes('homolog') || sit.includes('adjudic');
}
