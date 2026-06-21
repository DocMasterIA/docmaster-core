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
 * @param {{ contratado: string, setor: string, caracteristicas?: string, variant?: 'dispensa_normal'|'generic' }} fields
 */
export function buildClausulasObjetoJustificativaPrompt(fields) {
  const contratado = String(fields.contratado || '').trim();
  const setor = String(fields.setor || '').trim();
  const caracteristicas = String(fields.caracteristicas || '').trim();
  const variant = fields.variant || 'generic';
  const compact = !!fields.compact;

  if (compact && variant === 'dispensa_normal') {
    return [
      'Redija em pt-BR, formal, só duas linhas rotuladas:',
      'Objeto: cláusula declarativa com o núcleo material informado e o setor atendido.',
      'Justificativa: parágrafo argumentativo (5 a 8 frases).',
      `Contratação: ${contratado}`,
      `Setor: ${setor}`,
      caracteristicas ? `Características: ${caracteristicas}` : '',
    ]
      .filter(Boolean)
      .join('\n');
  }

  const lines = [
    'Com base EXCLUSIVAMENTE nos dados abaixo, gere APENAS duas seções:',
    'Objeto:',
    'Justificativa:',
    '',
    'REGRAS OBRIGATÓRIAS:',
    '- Não inventar órgão, secretaria, produto, quantidade, valor ou localidade além do informado.',
    '- Não reutilizar contexto de mensagens anteriores.',
    '- Usar apenas os campos fornecidos pelo usuário.',
    '- Se faltar informação, redija de forma genérica sem adicionar fatos novos.',
  ];

  if (variant === 'dispensa_normal') {
    lines.push(
      '- Na cláusula de objeto: declare o núcleo material informado e vincule ao setor/secretaria.',
      '- Justificativa: parágrafo argumentativo completo (5 a 8 frases), linguagem formal.',
      '- Não enumere itens de tabela com quantidades, valores ou marcas — detalhe na tabela do TR.',
    );
  }

  lines.push(
    '',
    `O que será contratado: ${contratado}`,
    `Setor/secretaria atendido: ${setor}`,
    `Características mínimas (opcional): ${caracteristicas || 'não informado'}`,
    '',
    'Formato obrigatório de resposta:',
    'Objeto: <texto>',
    'Justificativa: <texto>',
    '',
    'Não inclua nenhuma seção extra.',
  );

  return lines.join('\n');
}

/** Limites Ollama para cláusulas curtas (objeto + justificativa) — alvo ~3s. */
export const CLAUSULAS_LLM_OPTIONS = {
  num_predict: 220,
  temperature: 0.2,
  top_p: 0.85,
};

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
    variant: options.variant || 'generic',
    compact: options.compact !== false,
  });

  const body = {
    prompt,
    stream: false,
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
  const text = data.generated_text || data.text || data.content || data?.data?.response || data?.data?.text || data?.response || data?.text || '';
  const parsed = bySections.objeto || bySections.justificativa ? bySections : parseClauseSections(text);

  return {
    ok: true,
    objeto: String(parsed.objeto || '').trim(),
    justificativa: String(parsed.justificativa || '').trim(),
    status: res.status,
    errorMessage: '',
  };
}
