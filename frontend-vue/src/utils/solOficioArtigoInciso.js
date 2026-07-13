/**
 * Valor do slot sol_oficio_artigo_inciso / (SOL_OFICIO_ARTIGO_INCISO).
 * Apenas artigo + inciso — a Lei 14.133/2021 já consta no corpo do ofício.
 */

const SOL_OFICIO_ARTIGO_INCISO_BY_ROUTE = {
  DispensaArt75I: 'Art. 75, Inciso I',
  DispensaArt75IManutencaoVeiculos: 'Art. 75, Inciso I',
  DispensaArt75IObrasEngenharia: 'Art. 75, Inciso I',
  DispensaArt75II: 'Art. 75, Inciso II',
  DispensaArt75IICompras: 'Art. 75, Inciso II',
  DispensaArt75IIServicos: 'Art. 75, Inciso II',
  DispensaArt75IIComprasServicosInclusos: 'Art. 75, Inciso II',
  DispensaRapidaArt75IICompras: 'Art. 75, Inciso II',
  DispensaRapidaArt75IIServicos: 'Art. 75, Inciso II',
  DispensaRapidaArt75IIComprasServicosInclusos: 'Art. 75, Inciso II',
  DispensaRapidaArt75IManutencaoVeiculos: 'Art. 75, Inciso I',
  DispensaRapidaArt75IObrasEngenharia: 'Art. 75, Inciso I',
  InexigibilidadeArt74I: 'Art. 74, Inciso I',
  InexigibilidadeArt74IManutencaoVeiculos: 'Art. 74, Inciso I',
  InexigibilidadeArt74IManutencaoVeiculosPreview: 'Art. 74, Inciso I',
  InexigibilidadeArt74IFornecedorExclusivo: 'Art. 74, Inciso I',
  InexigibilidadeArt74IFornecedorExclusivoPreview: 'Art. 74, Inciso I',
};

const LEI_SUFFIX_RE =
  /,?\s*da\s+Lei\s+n[oº°.]?\s*\.?\s*14[\./]?133(?:\/\d{4})?\s*$/i;

/** Remove sufixo «, da Lei nº 14.133/2021» (ou variantes) de valores legados. */
export function stripLeiFromSolOficioArtigoInciso(value) {
  const text = String(value || '').trim();
  if (!text) return '';
  return text.replace(LEI_SUFFIX_RE, '').replace(/,\s*$/, '').trim();
}

/** Resolve artigo + inciso para o slot do ofício a partir do nome da rota Vue. */
export function resolveSolOficioArtigoInciso(routeName) {
  const name = String(routeName || '').trim();
  if (!name) return '';
  if (SOL_OFICIO_ARTIGO_INCISO_BY_ROUTE[name]) {
    return SOL_OFICIO_ARTIGO_INCISO_BY_ROUTE[name];
  }
  if (name.startsWith('InexigibilidadeArt74I')) return 'Art. 74, Inciso I';
  if (name.includes('Art75II')) return 'Art. 75, Inciso II';
  if (name.includes('Art75I')) return 'Art. 75, Inciso I';
  return '';
}

/** @deprecated use resolveSolOficioArtigoInciso */
export function resolveSolOficioFundamentoLegal(routeName) {
  return resolveSolOficioArtigoInciso(routeName);
}
