/**
 * Estatística de preços por item + posição na faixa.
 */

export function stats(prices) {
  const xs = prices.filter((p) => p != null && Number.isFinite(p) && p > 0).slice().sort((a, b) => a - b);
  if (!xs.length) {
    return {
      n: 0, min: null, max: null, mean: null, median: null, stdev: null, cvPct: null,
      p25: null, p75: null, iqr: null, ratioMaxMin: null, outliers: [],
    };
  }
  const n = xs.length;
  const sum = xs.reduce((a, b) => a + b, 0);
  const mean = sum / n;
  const median = n % 2 ? xs[(n - 1) / 2] : (xs[n / 2 - 1] + xs[n / 2]) / 2;
  const variance = xs.reduce((a, b) => a + (b - mean) ** 2, 0) / n;
  const stdev = Math.sqrt(variance);
  const cvPct = mean > 0 ? (stdev / mean) * 100 : null;
  const q = (p) => {
    const i = (n - 1) * p;
    const lo = Math.floor(i);
    const hi = Math.ceil(i);
    if (lo === hi) return xs[lo];
    return xs[lo] * (hi - i) + xs[hi] * (i - lo);
  };
  const p25 = q(0.25);
  const p75 = q(0.75);
  const iqr = p75 - p25;
  const lowFence = p25 - 1.5 * iqr;
  const highFence = p75 + 1.5 * iqr;
  const outliers = xs.filter((v) => v < lowFence || v > highFence);
  return {
    n,
    min: xs[0],
    max: xs[n - 1],
    mean: round(mean, 4),
    median: round(median, 4),
    stdev: round(stdev, 4),
    cvPct: cvPct == null ? null : round(cvPct, 2),
    p25: round(p25, 4),
    p75: round(p75, 4),
    iqr: round(iqr, 4),
    ratioMaxMin: round(xs[n - 1] / Math.max(xs[0], 1e-9), 3),
    outliers,
  };
}

export function round(n, d = 2) {
  if (n == null || !Number.isFinite(n)) return null;
  const f = 10 ** d;
  return Math.round(n * f) / f;
}

/** delta% vs base; posição na faixa [0..1] (0=min, 1=max). */
export function priceVsFaixa(valor, faixa) {
  const base = faixa?.base;
  const min = faixa?.min;
  const max = faixa?.max;
  const deltaBasePct = base && valor != null && base > 0
    ? round(((valor - base) / base) * 100, 2)
    : null;
  let posFaixa = null;
  if (valor != null && min != null && max != null && max > min) {
    posFaixa = round((valor - min) / (max - min), 3);
  }
  const dentro = valor != null && min != null && max != null
    ? valor >= min - 1e-9 && valor <= max + 1e-9
    : null;
  return { deltaBasePct, posFaixa, dentro, base, min, max };
}

export function money(n) {
  if (n == null || !Number.isFinite(n)) return '—';
  return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}
