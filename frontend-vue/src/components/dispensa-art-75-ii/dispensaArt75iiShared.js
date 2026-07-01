import { capitalizeFirstSignificantLetter } from '../../utils/itemValorCampos.js';

export const DATA_OPTIONS = ['Data automática', 'Datado e assinado digitalmente', 'Data manual'];
export const TRATAMENTO_NOME = ['Ao senhor', 'A senhora'];
export const TRATAMENTO_CARGO = ['Senhor', 'Senhora'];

/** IDs de campos no assistente DocumentGenerator (preset global) — cargos ainda descontinuados. */
export const LEGACY_CARGO_SLOT_FORM_IDS = [
  'solicitacao_responsavel_cargo',
  'dfd_assinatura_cargo',
  'tr_cargo_assinante',
  'tr_termo_responsavel_cargo',
];

/** Preset/dados fixos — cargos descontinuados; limpar no save para não ressurgir no merge do backend. */
export const DA75_DEPRECATED_CARGO_PRESET_KEYS = [
  'solicitacao_responsavel_cargo',
  'dfd_assinatura_cargo',
  'tr_termo_responsavel_cargo',
];

/** slots_override — não enviar à geração TR/DFD/Ofício (fantasmas de presets antigos). */
export const DA75_DEPRECATED_CARGO_OVERRIDE_KEYS = [
  'sol_oficio_responsavel_cargo',
  'dfd_assinatura_cargo',
  'cargo_assinante_termo',
  'secretaria_usuario',
  'tr_cargo_assinante',
];

export function clearDeprecatedCargoPresetFields(data) {
  if (!data || typeof data !== 'object') return data;
  const out = { ...data };
  for (const key of DA75_DEPRECATED_CARGO_PRESET_KEYS) out[key] = '';
  for (const key of LEGACY_CARGO_SLOT_FORM_IDS) out[key] = '';
  return out;
}

export function stripDeprecatedCargoSlotsOverride(raw) {
  if (!raw || typeof raw !== 'object') return raw;
  const o = { ...raw };
  for (const key of DA75_DEPRECATED_CARGO_OVERRIDE_KEYS) delete o[key];
  return Object.keys(o).length ? o : null;
}
export const TEXTO_PADRAO_ENDERECO_PROPOSTAS =
  'As propostas poderão ser entregues no Setor de Compras Central da XXXXXXXXX - XX, localizado na rua XXXXXXXXXXX, Nº XXX, XXXXX, no horário das 07h00min às 11h00min e das 13h00min às 17h00min, de segunda a sexta-feira.';

export { PLACEHOLDER_DOTACAO } from '@/constants/dotacaoOrcamentaria.js';

export const EMPTY_ITEM = { descricao: '', quantidade: '', unidade: '', mediaValor: '' };

export function apenasNumeros(valor) {
  return String(valor || '').replace(/\D/g, '');
}

export function campoPreenchido(valor) {
  return String(valor || '').trim().length > 0;
}

/**
 * Setor requisitante do DFD (2.1) — somente «Dados fixos» na geração DOCX; não entra no prompt de cláusulas IA.
 * @param {{ fixoSetor?: string }} dadosFixos
 */
export function dfdSetorRequisitanteFromDadosFixos(dadosFixos) {
  return String(dadosFixos?.fixoSetor || '').trim();
}

/** Preenche dfd_setor_requisitante no override de geração TR/DFD/Ofício. */
export function applyDfdSetorRequisitanteToSlotsOverride(slotsOverride, dadosFixos) {
  const setor = dfdSetorRequisitanteFromDadosFixos(dadosFixos);
  if (setor) slotsOverride.dfd_setor_requisitante = setor;
  return slotsOverride;
}

export function primeiraMaiuscula(valor) {
  return capitalizeFirstSignificantLetter(valor);
}

export function formatarData(valor) {
  const n = apenasNumeros(valor).slice(0, 8);
  if (n.length <= 2) return n;
  if (n.length <= 4) return `${n.slice(0, 2)}/${n.slice(2)}`;
  return `${n.slice(0, 2)}/${n.slice(2, 4)}/${n.slice(4)}`;
}

export function formatarMoeda(valor) {
  const numero = Number(apenasNumeros(valor)) / 100;
  return numero.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

export function moedaParaNumero(valor) {
  const numeros = apenasNumeros(valor || '');
  return numeros ? Number(numeros) / 100 : 0;
}

export function quantidadeParaNumero(valor) {
  return Number(String(valor || '').replace(',', '.')) || 0;
}

export function calcularValorTotalEstimado(itens) {
  const total = itens.reduce(
    (acc, item) => acc + quantidadeParaNumero(item.quantidade) * moedaParaNumero(item.mediaValor),
    0,
  );
  return total.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

export function criarPerfilDadosFixos(id, nomeCadastro) {
  return {
    id,
    nomeCadastro,
    tratNome: '',
    nome: '',
    tratCargo: '',
    cargo: '',
    responsavel: '',
    responsavelCargo: '',
    setor: '',
    demanda: '',
    email: '',
    gestor: '',
    fiscal: '',
    assinatura: '',
    assinaturaCargo: '',
    responsavelTR: '',
    responsavelCargoTR: '',
    enderecoEntregaPropostas: TEXTO_PADRAO_ENDERECO_PROPOSTAS,
    emailRecebimentoPropostas: '',
  };
}

export function gerarObjetoTexto(contratado, setor, caracteristicas) {
  const c = String(contratado || '');
  const s = String(setor || '');
  const k = String(caracteristicas || '');
  const objeto = c.trim() || 'objeto não informado';
  const destino = s.trim() ? `, visando atender às demandas de ${s.trim()}` : '';
  const detalhes = k.trim() ? `, observadas as seguintes características mínimas: ${k.trim()}` : '';
  return `${primeiraMaiuscula(objeto)}${destino}${detalhes}.`;
}

export function gerarJustificativaTexto(contratado, setor, caracteristicas) {
  const c = String(contratado || '');
  const s = String(setor || '');
  const k = String(caracteristicas || '');
  const objeto = c.trim() || 'o objeto indicado';
  const destino = s.trim() ? ` do(a) ${s.trim()}` : ' da Administração Pública';
  const detalhes = k.trim()
    ? ` A contratação deverá observar as características mínimas informadas: ${k.trim()}.`
    : '';
  return `A presente contratação justifica-se pela necessidade de assegurar ${objeto} para atendimento das demandas${destino}, garantindo a continuidade, eficiência e adequada prestação dos serviços públicos.${detalhes}`;
}

/** Objeto institucional genérico (dispensa normal) — sem detalhar itens da tabela. */
export function gerarObjetoTextoDispensaNormal(contratado, setor, caracteristicas) {
  const tema = String(contratado || '').trim().toLowerCase() || 'bens e serviços';
  const s = String(setor || '').trim();
  const k = String(caracteristicas || '').trim();
  let texto = `Aquisição de ${tema}`;
  if (s) texto += `, visando atender às demandas de ${s}`;
  if (k) texto += ', observadas as características mínimas informadas';
  return `${primeiraMaiuscula(texto)}.`;
}

export function aplicarClausulasLocaisDispensaNormal(contratado, setor, caracteristicas) {
  return {
    objeto: gerarObjetoTextoDispensaNormal(contratado, setor, caracteristicas),
    justificativa: gerarJustificativaTexto(contratado, setor, caracteristicas),
  };
}
