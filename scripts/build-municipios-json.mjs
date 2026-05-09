/**
 * Gera frontend-vue/src/data/municipios-por-uf.json a partir de cidades/*Cities.jsx
 * (export const XX_CITIES = [ ... ];). Executar após alterar listas: node scripts/build-municipios-json.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, '..');
const cidadesDir = path.join(root, 'cidades');
const outPath = path.join(root, 'frontend-vue', 'src', 'data', 'municipios-por-uf.json');

function ufKeyFromFile(fname) {
  const base = fname.replace(/\.jsx$/i, '');
  const prefix = base.replace(/Cities$/i, '');
  if (prefix === 'parana') return 'PR';
  if (prefix.length !== 2) throw new Error(`Ficheiro não mapeado para UF: ${fname} (prefix=${prefix})`);
  return prefix.toUpperCase();
}

function extractCityArray(content) {
  const m = content.match(/export\s+const\s+\w+\s*=\s*(\[[\s\S]*?\])\s*;\s*(?:\n|$)/);
  if (!m) throw new Error('Array export const ... = [ não encontrado');
  let jsonish = m[1].trim();
  jsonish = jsonish.replace(/,(\s*)\]/g, '$1]');
  return JSON.parse(jsonish);
}

const DROP_EXACT = new Set(['Wikimedia', 'Commons', '↑', 'a']);

function limparNomesMunicipios(lista) {
  return lista.filter((nome) => {
    if (typeof nome !== 'string') return false;
    const t = nome.trim();
    if (!t) return false;
    if (DROP_EXACT.has(t)) return false;
    if (/^Lista de municípios/i.test(t)) return false;
    if (t === 'Municípios' || /^Municípios do /i.test(t)) return false;
    return true;
  });
}

const files = fs.readdirSync(cidadesDir).filter((f) => /Cities\.jsx$/i.test(f));
if (!files.length) throw new Error(`Nenhum *Cities.jsx em ${cidadesDir}`);

/** @type {Record<string, string[]>} */
const out = {};
for (const f of files.sort()) {
  const uf = ufKeyFromFile(f);
  const raw = fs.readFileSync(path.join(cidadesDir, f), 'utf8');
  out[uf] = limparNomesMunicipios(extractCityArray(raw));
}

const orderedKeys = Object.keys(out).sort();
const ordered = {};
for (const k of orderedKeys) ordered[k] = out[k];

fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, `${JSON.stringify(ordered, null, 0)}\n`, 'utf8');
console.log(`Escrito ${outPath} (${orderedKeys.length} UFs, ${orderedKeys.map((k) => `${k}:${ordered[k].length}`).join(', ')})`);
