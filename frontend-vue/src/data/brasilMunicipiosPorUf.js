/**
 * Listas oficiais por UF (nomes de município).
 * Fonte: `municipios-por-uf.json` (gerado a partir de `cidades/*Cities.jsx` no repositório;
 * para regenerar: `node scripts/build-municipios-json.mjs` na raiz do repo).
 */
import municipiosPorUf from './municipios-por-uf.json';

/** @type {Record<string, string[]>} */
export const MUNICIPIOS_POR_UF = municipiosPorUf;
