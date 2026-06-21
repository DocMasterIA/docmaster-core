import { getApiBase } from './apiBase.js';

/**
 * Geração rápida de cláusulas de objeto/justificativa (dispensa normal, inexigibilidade).
 * Usa POST /api/llm/generate — mais leve que fill-tr-slots (rag + pipeline TR completo).
 */

export function parseClauseSections(text) {
  const normalized = String(text || '').replace(/\r/g, '');
  const sections = {
    objeto: '',
    justificativa: '',
    escopo: '',
    entregas: '',
    resultados: '',
  };
  const lines = normalized.split('\n');
  let current = '';
  const keyByHeader = {
    objeto: 'objeto',
    justificativa: 'justificativa',
    escopo: 'escopo',
    entregas: 'entregas',
    'resultados esperados': 'resultados',
    resultados: 'resultados',
  };
  lines.forEach((line) => {
    const trimmed = line.trim();
    const low = trimmed.toLowerCase().replace(/[*:#-]/g, '').trim();
    const headerMatch = Object.keys(keyByHeader).find((k) => low.startsWith(k));
    if (headerMatch) {
      current = keyByHeader[headerMatch];
      const content = trimmed.replace(/^.*?:\s*/, '');
      if (content && content !== trimmed) sections[current] += (sections[current] ? '\n' : '') + content;
      return;
    }
    if (current) sections[current] += (sections[current] ? '\n' : '') + trimmed;
  });
  return sections;
}

/** Extrai objeto/justificativa de JSON (Qwen) ou fallback para seções Objeto:/Justificativa:. */
export function parseClausulasResponseText(text) {
  const raw = String(text || '').trim();
  if (!raw) return { objeto: '', justificativa: '' };
  const cleaned = raw.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/i, '').trim();
  if (cleaned.startsWith('{')) {
    try {
      const parsed = JSON.parse(cleaned);
      return {
        objeto: String(parsed.objeto || '').trim(),
        justificativa: String(parsed.justificativa || '').trim(),
      };
    } catch {
      /* fallback abaixo */
    }
  }
  const sections = parseClauseSections(raw);
  return { objeto: sections.objeto || '', justificativa: sections.justificativa || '' };
}

export function extractClausesFromSectionTexts(sectionTexts) {
  const get = (...keys) => {
    for (const key of keys) {
      const value = sectionTexts?.[key];
      if (typeof value === 'string' && value.trim()) return value.trim();
    }
    return '';
  };
  return {
    objeto: get('objeto', 'objeto_licitacao', 'do_objeto'),
    justificativa: get('justificativa', 'necessidade', 'fundamentacao', 'da_necessidade'),
    escopo: get('escopo', 'objeto_escopo'),
    entregas: get('entregas', 'objeto_entregas'),
    resultados: get('resultados', 'objeto_resultados', 'resultados_esperados'),
  };
}

/**
 * @param {{
 *   contratado: string,
 *   setor: string,
 *   caracteristicas?: string,
 *   tipoManutencao?: string,
 *   revisaoKm?: string,
 *   variant?: 'dispensa_normal'|'generic'
 * }} fields
 */
export function buildClausulasObjetoJustificativaPrompt(fields) {
  const contratado = String(fields.contratado || '').trim();
  const setor = String(fields.setor || '').trim();
  const caracteristicas = String(fields.caracteristicas || '').trim();
  const tipoManutencao = String(fields.tipoManutencao || '').trim();
  const revisaoKm = String(fields.revisaoKm || '').trim();

  return [
    `O que será contratado: ${contratado}`,
    `Setor/secretaria atendido: ${setor}`,
    caracteristicas ? `Características mínimas: ${caracteristicas}` : '',
    tipoManutencao ? `Tipo de manutenção: ${tipoManutencao}` : '',
    revisaoKm ? `Revisão/KM: ${revisaoKm}` : '',
  ]
    .filter(Boolean)
    .join('\n');
}

/** Limites Ollama para cláusulas curtas (objeto + justificativa) — alvo ~3s. */
export const CLAUSULAS_LLM_OPTIONS = {
  num_predict: 220,
  temperature: 0.2,
  top_p: 0.85,
};

export const CLAUSULAS_CLOUD_MAX_TOKENS = 2048;

/**
 * @returns {Promise<{ ok: boolean, objeto: string, justificativa: string, status: number, errorMessage: string }>}
 */
export async function requestClausulasObjetoJustificativaFast(apiBase, options = {}) {
  const base = String(apiBase ?? getApiBase()).replace(/\/$/, '');
  const url = base ? `${base}/api/llm/generate` : '/api/llm/generate';
  const prompt = buildClausulasObjetoJustificativaPrompt({
    contratado: options.contratado,
    setor: options.setor,
    caracteristicas: options.caracteristicas,
    tipoManutencao: options.tipoManutencao,
    revisaoKm: options.revisaoKm,
    variant: options.variant || 'generic',
    compact: options.compact !== false,
  });

  const body = {
    prompt,
    stream: false,
    max_tokens: options.maxTokens ?? CLAUSULAS_CLOUD_MAX_TOKENS,
  };
  const pkg = String(options.slotPackageKey || '').trim();
  if (pkg) body.slot_package_key = pkg;

  let res;
  try {
    res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(body),
      signal: options.signal,
    });
  } catch (netErr) {
    if (netErr?.name === 'AbortError') {
      return { ok: false, objeto: '', justificativa: '', status: 0, errorMessage: 'Pedido cancelado.' };
    }
    return {
      ok: false,
      objeto: '',
      justificativa: '',
      status: 0,
      errorMessage: String(netErr?.message || netErr || 'Erro de rede'),
    };
  }

  const data = await res.json().catch(() => ({}));
  if (!res.ok || !data?.ok) {
    const err =
      res.status === 504
        ? 'A IA demorou para responder (504). Tente novamente em instantes.'
        : data?.error || data?.detail || `Erro ${res.status} ao gerar cláusulas`;
    return { ok: false, objeto: '', justificativa: '', status: res.status, errorMessage: String(err) };
  }

  const bySections = extractClausesFromSectionTexts(data.section_texts || {});
  const text =
    data.generated_text ||
    data.text ||
    data.content ||
    data?.data?.response ||
    data?.data?.text ||
    data?.response ||
    data?.text ||
    '';
  const parsed =
    bySections.objeto || bySections.justificativa
      ? { objeto: bySections.objeto, justificativa: bySections.justificativa }
      : parseClausulasResponseText(text);

  return {
    ok: true,
    objeto: String(parsed.objeto || '').trim(),
    justificativa: String(parsed.justificativa || '').trim(),
    status: res.status,
    errorMessage: '',
  };
}
