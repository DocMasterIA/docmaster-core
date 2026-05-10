/**
 * Utilitários compartilhados para campos de item (descrição, quantidade, unidade, valores em R$).
 */

/**
 * Primeira letra significativa (A-Z / acentos) em maiúsculas; restante inalterado.
 * @param {string} value
 */
export function capitalizeFirstSignificantLetter(value) {
  const v = String(value ?? '');
  const indice = v.search(/[A-Za-zÀ-ÿ]/u);
  if (indice < 0) return v;
  const ch = v[indice];
  const up = ch.toLocaleUpperCase('pt-BR');
  if (ch === up) return v;
  return v.slice(0, indice) + up + v.slice(indice + 1);
}

/**
 * Maiúscula na primeira letra de cada sequência de letras Unicode (inclui acentos em pt-BR).
 * Ex.: "órgão / unidade do veículo" -> "Órgão / Unidade Do Veículo"
 * @param {string} value
 */
export function capitalizeEachWordLeadingPt(value) {
  return String(value ?? '').replace(/\p{L}[\p{L}\p{Mn}]*/gu, (w) => {
    if (!w) return w;
    return w.charAt(0).toLocaleUpperCase('pt-BR') + w.slice(1);
  });
}

/** Partículas comuns em nomes próprios e títulos (permanecem em minúsculas após a primeira palavra). */
const PT_NOME_TITULO_PARTICULAS = new Set([
  'de', 'da', 'do', 'dos', 'das', 'e', 'del', 'y', 'em', 'na', 'no', 'nas', 'nos',
]);

/**
 * Formata texto livre como nome ou título em pt-BR: cada palavra com inicial maiúscula,
 * exceto partículas (de, da, do…) quando não são a primeira palavra.
 * Ex.: "ariane do nascimento martins" → "Ariane do Nascimento Martins"
 * @param {string} value
 */
export function capitalizeNomeTituloPt(value) {
  const raw = String(value ?? '');
  if (!raw.trim()) return raw;
  const parts = raw.split(/(\s+)/);
  let seenWord = false;
  return parts
    .map((segment) => {
      if (/^\s+$/.test(segment)) return segment;
      const lower = segment.toLocaleLowerCase('pt-BR');
      const letters = lower.match(/\p{L}/u);
      if (!letters) return segment;
      const isParticle = seenWord && PT_NOME_TITULO_PARTICULAS.has(lower);
      seenWord = true;
      if (isParticle) return lower;
      return lower.charAt(0).toLocaleUpperCase('pt-BR') + lower.slice(1);
    })
    .join('');
}

/**
 * Quantidade: só dígitos e um separador decimal (`,` ou `.`). Sem milhares.
 * @param {string} value
 */
export function sanitizeQuantidadeInput(value) {
  const t = String(value ?? '').replace(/[^\d,.]/g, '');
  if (!t) return '';
  let sepIdx = -1;
  let sepChar = '';
  for (let i = 0; i < t.length; i += 1) {
    if (t[i] === ',' || t[i] === '.') {
      if (sepIdx < 0) {
        sepIdx = i;
        sepChar = t[i];
      }
    }
  }
  if (sepIdx < 0) return t.replace(/\D/g, '');
  const intPart = t.slice(0, sepIdx).replace(/\D/g, '');
  let fracPart = t.slice(sepIdx + 1).replace(/\D/g, '');
  fracPart = fracPart.slice(0, 8);
  if (fracPart.length > 0) return `${intPart || '0'}${sepChar}${fracPart}`;
  return `${intPart}${sepChar}`;
}

/**
 * Converte string "apenas dígitos" para exibição R$ (centavos implicitamente, como em caixa).
 * @param {string} digits (apenas 0-9)
 */
export function formatMoedaBRLFromDigitString(digits) {
  const d = String(digits ?? '').replace(/\D/g, '');
  if (!d) return '';
  const cents = Number.parseInt(d, 10);
  if (!Number.isFinite(cents)) return '';
  const value = cents / 100;
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

/**
 * Normaliza entrada de moeda BRL (híbrido digit string) para o display pt-BR.
 * @param {string} raw valor do input
 */
export function formatMoedaBRLInput(raw) {
  const digits = String(raw ?? '').replace(/\D/g, '');
  return formatMoedaBRLFromDigitString(digits);
}
