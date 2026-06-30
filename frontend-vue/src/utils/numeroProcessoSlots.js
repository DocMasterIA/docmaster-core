/**
 * Número de processo nos slots TR/DFD (placeholder `( NUMERO_PROCESSO )` no Word).
 */

export function trimNumeroProcesso(value) {
  return String(value ?? '').trim();
}

/**
 * Preenche `numero_processo` e `dfd_numero_processo` quando o usuário informou valor.
 * @param {Record<string, unknown>} slotsOverride
 * @param {string} numeroProcesso
 */
export function applyNumeroProcessoToSlotsOverride(slotsOverride, numeroProcesso) {
  const np = trimNumeroProcesso(numeroProcesso);
  if (!np) return slotsOverride;
  slotsOverride.numero_processo = np;
  slotsOverride.dfd_numero_processo = np;
  return slotsOverride;
}

/**
 * Fluxos com checkbox «Informar processo» + campo de texto.
 * @param {Record<string, unknown>} slotsOverride
 * @param {boolean} processoAtivo
 * @param {string} processo
 */
export function applyProcessoAtivoToSlotsOverride(slotsOverride, processoAtivo, processo) {
  if (!processoAtivo) return slotsOverride;
  return applyNumeroProcessoToSlotsOverride(slotsOverride, processo);
}
