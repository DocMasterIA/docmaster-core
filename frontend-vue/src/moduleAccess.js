export const MODULE_KEYS = [
  'dispensa',
  'dispensa_eletronica',
  'pregao',
  'pregao_eletronico',
  'inexigibilidade',
  'etp',
  'analisador',
  'pesquisa',
  'contratos',
  'controle_interno',
  'impugnacao',
  'recurso',
  'usuario',
];

export function normalizeAllowedModules(raw, isSuperuser = false) {
  if (isSuperuser) return [...MODULE_KEYS];
  // Perfil ainda não carregado (ex.: /api/me/ pendente): não assumir «todos os módulos» no UI.
  if (raw === undefined || raw === null) return [];
  if (!Array.isArray(raw)) return [];
  const valid = raw.map((x) => String(x || '').trim()).filter((x) => MODULE_KEYS.includes(x));
  const unique = Array.from(new Set(valid));
  if (!unique.length) {
    // Alinhado a User.get_allowed_modules: lista vazia ou só chaves inválidas = acesso implícito
    // a todos os módulos (legado / mesma semântica que a API já devolve após normalização).
    return [...MODULE_KEYS];
  }
  return unique;
}

export function resolveModuleKey(to) {
  const name = String(to?.name || '');
  const path = String(to?.path || '');

  if (name === 'AreaDoUsuario' || path.startsWith('/area-do-usuario')) return 'usuario';
  if (name === 'DocumentAnalyzer' || path.startsWith('/analisador')) return 'analisador';
  if (name === 'PncpResearcher' || path.startsWith('/pesquisador-pncp')) return 'pesquisa';
  if (name === 'ModuleContratos' || path.startsWith('/contratos')) return 'contratos';
  if (name === 'ModuleControleInterno' || path.startsWith('/controle-interno')) return 'controle_interno';
  if (name === 'ModuleImpugnacao' || path.startsWith('/impugnacao')) return 'impugnacao';
  if (name === 'ModuleRecursoLicitatorio' || path.startsWith('/recurso-processo-licitatorio')) return 'recurso';
  if (name === 'ModuleDispensaEletronica' || path.startsWith('/dispensa-eletronica')) return 'dispensa_eletronica';
  if (name === 'ModulePregao' || path === '/pregao') return 'pregao';
  if (name === 'ModulePregaoEletronico' || path.startsWith('/pregao-eletronico')) return 'pregao_eletronico';
  if (name === 'DispensaGeracaoHub' || path === '/geracao/dispensa') return 'dispensa';
  if (
    name.startsWith('DispensaArt75')
    || name.startsWith('DispensaRapida')
    || path.startsWith('/geracao/dispensa-art-75')
    || path.startsWith('/geracao/dispensa-rapida')
  ) {
    return 'dispensa';
  }
  if (name === 'InexigibilidadeGeracaoHub' || path === '/geracao/inexigibilidade') return 'inexigibilidade';
  if (name.startsWith('InexigibilidadeArt74') || path.startsWith('/geracao/inexigibilidade-art-74')) return 'inexigibilidade';
  if (name === 'EtpLivre' || path.startsWith('/geracao/etp-livre')) return 'etp';
  return null;
}

export function firstAllowedPath(allowedSet) {
  if (!allowedSet || allowedSet.size === 0) {
    return '/area-do-usuario';
  }
  const order = [
    ['dispensa', '/geracao/dispensa'],
    ['dispensa_eletronica', '/dispensa-eletronica'],
    ['pregao', '/pregao'],
    ['pregao_eletronico', '/pregao-eletronico'],
    ['inexigibilidade', '/geracao/inexigibilidade'],
    ['etp', '/geracao/etp-livre'],
    ['analisador', '/analisador'],
    ['pesquisa', '/pesquisador-pncp'],
    ['contratos', '/contratos'],
    ['controle_interno', '/controle-interno'],
    ['impugnacao', '/impugnacao'],
    ['recurso', '/recurso-processo-licitatorio'],
    ['usuario', '/area-do-usuario'],
  ];
  for (const [key, path] of order) {
    if (allowedSet.has(key)) return path;
  }
  return '/area-do-usuario';
}
