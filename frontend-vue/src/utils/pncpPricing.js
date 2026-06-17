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
  const outer = row?.source && typeof row.source === 'object' ? row.source : {};
  const inner = outer?.source && typeof outer.source === 'object' ? outer.source : {};
  return { ...inner, ...outer };
}

export function extractPnCpHomologadoUnit(row) {
  const src = mergedPnCpSource(row);
  const explicit = pickPositiveNumber(
    src.valor_unitario_homologado,
    src.valorUnitarioHomologado,
    row?.valor_unitario_homologado,
  );
  if (explicit) return explicit;
  if (isPnCpItemHomologado(row)) {
    return pickPositiveNumber(row?.valor_unitario);
  }
  return null;
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
  return extractPnCpHomologadoUnit(row) != null;
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
  const qtd = pickPositiveNumber(row?.quantidade, src.quantidade);
  if (unit && qtd) return unit * qtd;
  if (isPnCpItemHomologado(row)) {
    return pickPositiveNumber(row?.valor_total);
  }
  return null;
}

export function displayPnCpUnitario(row) {
  return extractPnCpHomologadoUnit(row) ?? pickPositiveNumber(row?.valor_unitario);
}

export function displayPnCpTotal(row) {
  return extractPnCpHomologadoTotal(row) ?? pickPositiveNumber(row?.valor_total);
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
  const sit = String(
    src.situacaoCompraItemNome || src.situacao_item || src.situacao || '',
  ).toLowerCase();
  return sit.includes('homolog') || sit.includes('adjudic');
}
