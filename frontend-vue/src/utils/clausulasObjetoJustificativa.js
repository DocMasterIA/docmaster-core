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

const OBJETO_JUSTIFICATIVA_BLEED = [
  'a presente contratação justifica-se',
  'justifica-se pela necessidade',
  'caso não seja realizada',
  'em caso de não contratação',
];

/** Remove fechamento normativo do TR e frases de justificativa no campo objeto. */
export function sanitizeObjetoClausePura(text) {
  let t = String(text || '').trim();
  if (!t) return '';
  const sentences = t.split(/(?<=[.!?])\s+/).filter(Boolean);
  const kept = sentences.filter((sent) => {
    const low = sent.toLowerCase().trim();
    if (/^a execução obedecer/.test(low)) return false;
    if (/^obedecerá rigorosamente/.test(low)) return false;
    if (/^conforme (especifica|quantidades|requisitos)/.test(low)) return false;
    if (OBJETO_JUSTIFICATIVA_BLEED.some((m) => low.includes(m))) return false;
    return true;
  });
  t = kept.join(' ').trim();
  t = t
    .replace(/[,;]?\s*a execução obedecerá[^.]*\.?/gi, '')
    .replace(/[,;]?\s*conforme especificações técnicas[^.]*termo de referência[^.]*\.?/gi, '')
    .replace(/[,;]?\s*conforme quantidades e demais condições estabelecidas neste termo de referência\.?/gi, '')
    .replace(/\s{2,}/g, ' ')
    .trim();
  if (t && !/[.!?]$/.test(t)) t = `${t}.`;
  return t;
}

/** Extrai objeto/justificativa/dfd_objeto_referencia de JSON (Qwen) ou fallback para seções. */
export function parseClausulasResponseText(text) {
  const raw = String(text || '').trim();
  if (!raw) return { objeto: '', justificativa: '', dfd_objeto_referencia: '' };
  const cleaned = raw.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/i, '').trim();
  if (cleaned.startsWith('{')) {
    try {
      const parsed = JSON.parse(cleaned);
      return {
        objeto: sanitizeObjetoClausePura(parsed.objeto || ''),
        justificativa: String(parsed.justificativa || '').trim(),
        dfd_objeto_referencia: String(parsed.dfd_objeto_referencia || parsed.dfdObjetoReferencia || '').trim(),
      };
    } catch {
      /* fallback abaixo */
    }
  }
  const sections = parseClauseSections(raw);
  return {
    objeto: sanitizeObjetoClausePura(sections.objeto || ''),
    justificativa: sections.justificativa || '',
    dfd_objeto_referencia: '',
  };
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
    objeto: sanitizeObjetoClausePura(get('objeto', 'objeto_licitacao', 'do_objeto')),
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
export const INEXIG_CLAUSULAS_CLOUD_MAX_TOKENS = 1200;

/**
 * Aplica cláusulas aprofundadas (Qwen) nos slots de inexigibilidade.
 * @param {Record<string, unknown>} slots
 * @param {{ objeto?: string, justificativa?: string, dfd_objeto_referencia?: string } | null} ia
 */
export function applyInexigibilidadeDeepenedClauses(slots, ia) {
  if (!ia || !slots) return;
  const objeto = String(ia.objeto || '').trim();
  const justificativa = String(ia.justificativa || '').trim();
  const dfdObjRef = String(ia.dfd_objeto_referencia || '').trim();
  if (objeto) {
    slots.objeto = objeto;
    slots.sol_oficio_objeto = objeto;
  }
  if (justificativa) {
    slots.justificativa = justificativa;
    slots.dfd_justificativa = justificativa;
    slots.sol_oficio_justificativa = justificativa;
  }
  if (dfdObjRef) {
    slots.dfd_objeto_referencia = dfdObjRef;
  }
}

export function buildInexigibilidadeManutencaoPrompt(fields) {
  const lines = [
    'Modalidade: inexigibilidade art. 74, inciso I — manutenção veicular com fornecedor exclusivo.',
    fields.orgao ? `Órgão: ${fields.orgao}` : '',
    fields.orgaoUnidadeVeiculo ? `Unidade de lotação/uso do veículo: ${fields.orgaoUnidadeVeiculo}` : '',
    fields.marca ? `Marca: ${fields.marca}` : '',
    fields.modelo ? `Modelo: ${fields.modelo}` : '',
    fields.placa ? `Placa: ${fields.placa}` : '',
    fields.tipoManutencao ? `Tipo de manutenção: ${fields.tipoManutencao}` : '',
    fields.revisaoKm ? `Revisão/KM: ${fields.revisaoKm}` : '',
    fields.fornecedor ? `Fornecedor exclusivo: ${fields.fornecedor}` : '',
    fields.cnpj ? `CNPJ do fornecedor: ${fields.cnpj}` : '',
    fields.valorGlobal ? `Valor global estimado: ${fields.valorGlobal}` : '',
    fields.itensResumo ? `Itens da contratação: ${fields.itensResumo}` : '',
  ];
  return lines.filter(Boolean).join('\n');
}

export function buildInexigibilidadeFornecedorExclusivoPrompt(fields) {
  const lines = [
    'Modalidade: inexigibilidade art. 74, inciso I — fornecedor exclusivo.',
    fields.orgao ? `Órgão: ${fields.orgao}` : '',
    fields.orgaoResponsavel ? `Unidade responsável pelo equipamento: ${fields.orgaoResponsavel}` : '',
    fields.objetoEspecifico ? `Objeto específico: ${fields.objetoEspecifico}` : '',
    fields.equipamento ? `Equipamento: ${fields.equipamento}` : '',
    fields.marca ? `Marca: ${fields.marca}` : '',
    fields.modelo ? `Modelo: ${fields.modelo}` : '',
    fields.fornecedor ? `Fornecedor exclusivo: ${fields.fornecedor}` : '',
    fields.cnpj ? `CNPJ do fornecedor: ${fields.cnpj}` : '',
    fields.valorGlobal ? `Valor global estimado: ${fields.valorGlobal}` : '',
    fields.itensResumo ? `Itens da contratação: ${fields.itensResumo}` : '',
  ];
  return lines.filter(Boolean).join('\n');
}

/**
 * Aprofunda cláusulas de inexigibilidade via Qwen (POST /api/llm/generate).
 * @returns {Promise<{ ok: boolean, objeto: string, justificativa: string, dfd_objeto_referencia: string, status: number, errorMessage: string }>}
 */
export async function requestInexigibilidadeClausulasDeepen(apiBase, options = {}) {
  const variant = String(options.variant || 'manutencao').trim().toLowerCase();
  const prompt =
    variant === 'fornecedor_exclusivo'
      ? buildInexigibilidadeFornecedorExclusivoPrompt(options)
      : buildInexigibilidadeManutencaoPrompt(options);

  const base = String(apiBase ?? getApiBase()).replace(/\/$/, '');
  const url = base ? `${base}/api/llm/generate` : '/api/llm/generate';
  const body = {
    prompt,
    stream: false,
    max_tokens: options.maxTokens ?? INEXIG_CLAUSULAS_CLOUD_MAX_TOKENS,
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
      return { ok: false, objeto: '', justificativa: '', dfd_objeto_referencia: '', status: 0, errorMessage: 'Pedido cancelado.' };
    }
    return {
      ok: false,
      objeto: '',
      justificativa: '',
      dfd_objeto_referencia: '',
      status: 0,
      errorMessage: String(netErr?.message || netErr || 'Erro de rede'),
    };
  }

  const data = await res.json().catch(() => ({}));
  if (!res.ok || !data?.ok) {
    const err =
      res.status === 504
        ? 'A IA demorou para responder (504). Tente novamente em instantes.'
        : data?.error || data?.detail || `Erro ${res.status} ao aprofundar cláusulas`;
    return {
      ok: false,
      objeto: '',
      justificativa: '',
      dfd_objeto_referencia: '',
      status: res.status,
      errorMessage: String(err),
    };
  }

  const bySections = extractClausesFromSectionTexts(data.section_texts || {});
  const text =
    data.generated_text ||
    data.text ||
    data.content ||
    data?.data?.response ||
    data?.data?.text ||
    data?.response ||
    '';
  const parsed =
    bySections.objeto || bySections.justificativa
      ? {
          objeto: bySections.objeto,
          justificativa: bySections.justificativa,
          dfd_objeto_referencia: '',
        }
      : parseClausulasResponseText(text);

  return {
    ok: Boolean(parsed.objeto || parsed.justificativa || parsed.dfd_objeto_referencia),
    objeto: String(parsed.objeto || '').trim(),
    justificativa: String(parsed.justificativa || '').trim(),
    dfd_objeto_referencia: String(parsed.dfd_objeto_referencia || '').trim(),
    status: res.status,
    errorMessage: '',
  };
}

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
