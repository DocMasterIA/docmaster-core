/**
 * Valor monetário por extenso (pt-BR) — espelho do backend `valor_extenso_pt.py`.
 * Uso previsto: UI de cotação, formulários e integrações futuras.
 */

const UNIDADES = [
  'zero', 'um', 'dois', 'três', 'quatro', 'cinco', 'seis', 'sete', 'oito', 'nove',
  'dez', 'onze', 'doze', 'treze', 'catorze', 'quinze', 'dezesseis', 'dezessete', 'dezoito', 'dezenove',
];

const DEZENAS = ['', '', 'vinte', 'trinta', 'quarenta', 'cinquenta', 'sessenta', 'setenta', 'oitenta', 'noventa'];

const CENTENAS = [
  '', 'cento', 'duzentos', 'trezentos', 'quatrocentos', 'quinhentos',
  'seiscentos', 'setecentos', 'oitocentos', 'novecentos',
];

const ESCALAS = [
  [1_000_000_000_000_000, 'quadrilhão', 'quadrilhões'],
  [1_000_000_000_000, 'trilhão', 'trilhões'],
  [1_000_000_000, 'bilhão', 'bilhões'],
  [1_000_000, 'milhão', 'milhões'],
];

export function parseValorMonetarioBr(value) {
  if (value === null || value === undefined) return null;
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) return null;
    return value;
  }
  const raw = String(value).trim();
  if (!raw) return null;
  let cleaned = raw.replace(/^\s*R\$\s*/i, '').replace(/\s/g, '');
  if (!cleaned) return null;
  if (cleaned.includes(',')) {
    cleaned = cleaned.replace(/\./g, '').replace(',', '.');
  }
  const n = Number.parseFloat(cleaned);
  return Number.isFinite(n) ? n : null;
}

function extenso0a999(n) {
  if (n === 0) return '';
  if (n === 100) return 'cem';
  if (n < 20) return UNIDADES[n];
  if (n < 100) {
    const dezena = Math.floor(n / 10);
    const unidade = n % 10;
    if (unidade === 0) return DEZENAS[dezena];
    return `${DEZENAS[dezena]} e ${UNIDADES[unidade]}`;
  }
  const centena = Math.floor(n / 100);
  const resto = n % 100;
  const prefixo = CENTENAS[centena];
  if (resto === 0) return prefixo;
  return `${prefixo} e ${extenso0a999(resto)}`;
}

function extensoMilhar(n) {
  if (n < 1000) return extenso0a999(n);
  const mil = Math.floor(n / 1000);
  const resto = n % 1000;
  const esquerda = mil === 1 ? 'mil' : `${extenso0a999(mil)} mil`;
  if (resto === 0) return esquerda;
  if (resto < 100) return `${esquerda} e ${extenso0a999(resto)}`;
  return `${esquerda} ${extenso0a999(resto)}`;
}

function extensoEscala(n, divisor, singular, plural) {
  if (n < divisor) return extensoMilhar(n);
  const quociente = Math.floor(n / divisor);
  const resto = n % divisor;
  const esquerda = quociente === 1 ? `um ${singular}` : `${extenso0a999(quociente)} ${plural}`;
  if (resto === 0) return esquerda;
  const direita = extensoMilhar(resto);
  if (resto < 1000) return `${esquerda} e ${direita}`;
  return `${esquerda} ${direita}`;
}

export function inteiroPorExtenso(n) {
  const valor = Math.trunc(Number(n));
  if (!Number.isFinite(valor) || valor < 0) {
    throw new Error('inteiroPorExtenso aceita apenas valores >= 0');
  }
  if (valor === 0) return 'zero';
  for (const [divisor, singular, plural] of ESCALAS) {
    if (valor >= divisor) return extensoEscala(valor, divisor, singular, plural);
  }
  return extensoMilhar(valor);
}

export function valorMonetarioPorExtenso(value, { incluirMoeda = true } = {}) {
  const parsed = parseValorMonetarioBr(value);
  if (parsed === null) throw new Error('valor monetário inválido');
  if (parsed < 0) throw new Error('valor monetário não pode ser negativo');

  const quantizado = Math.round(parsed * 100) / 100;
  const reais = Math.trunc(quantizado);
  const centavos = Math.round((quantizado - reais) * 100);

  if (reais === 0 && centavos === 0) {
    return incluirMoeda ? 'zero reais' : 'zero';
  }

  const partes = [];
  if (reais > 0) {
    const textoReais = inteiroPorExtenso(reais);
    partes.push(incluirMoeda ? `${textoReais} ${reais === 1 ? 'real' : 'reais'}` : textoReais);
  }
  if (centavos > 0) {
    const textoCentavos = inteiroPorExtenso(centavos);
    const frag = incluirMoeda
      ? `${textoCentavos} ${centavos === 1 ? 'centavo' : 'centavos'}`
      : textoCentavos;
    partes.push(partes.length ? `e ${frag}` : frag);
  }
  return partes.join(' ');
}

export function valorMonetarioExtensoPayload(value) {
  const parsed = parseValorMonetarioBr(value);
  if (parsed === null) throw new Error('valor monetário inválido');
  if (parsed < 0) throw new Error('valor monetário não pode ser negativo');

  const quantizado = Math.round(parsed * 100) / 100;
  const reais = Math.trunc(quantizado);
  const centavos = Math.round((quantizado - reais) * 100);
  return {
    valor: quantizado,
    valor_fmt: quantizado.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }),
    reais,
    centavos,
    extenso: valorMonetarioPorExtenso(quantizado),
  };
}

/**
 * Soma totais de itens de cotação (mesma prioridade da tela de detalhe).
 * @param {Array<object>} itens
 */
export function somarValorTotalEstimadoItens(itens) {
  if (!Array.isArray(itens) || !itens.length) return null;
  let soma = 0;
  let temValor = false;
  for (const it of itens) {
    const vt = Number(it?.valor_total_refletido ?? it?.valor_total ?? it?.valor_unitario);
    if (Number.isFinite(vt) && vt >= 0) {
      soma += vt;
      temValor = true;
    }
  }
  return temValor ? Math.round(soma * 100) / 100 : null;
}
