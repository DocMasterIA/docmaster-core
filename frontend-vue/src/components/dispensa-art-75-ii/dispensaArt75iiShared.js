export const DATA_OPTIONS = ['Data automática', 'Datado e assinado digitalmente', 'Data manual'];
export const TRATAMENTO_NOME = ['Ao senhor', 'A senhora'];
export const TRATAMENTO_CARGO = ['Senhor', 'Senhora'];
export const CABECALHOS_DOCUMENTO = [
  'Cabeçalho padrão do município',
  'Cabeçalho do Fundo Municipal de Saúde',
  'Cabeçalho da Assistência Social',
  'Cabeçalho da Secretaria de Educação',
  'Cabeçalho sem brasão',
];

export const TEXTO_PADRAO_ENDERECO_PROPOSTAS =
  'Nome Município - UF, localizado na rua xxxxxxxxxxxxx, Nº xx, bairro xxx, no horário das 07h00min às 11h00min e das 13h00min às 17h00min, de segunda a sexta-feira.';

export const PLACEHOLDER_DOTACAO =
  'Ex:\nÓrgão: 02\nUnidade: 05\nProjeto/Atividade: 2.045\nElemento de despesa: 3.3.90.39.00\nFonte: 1.500';

export const EMPTY_ITEM = { descricao: '', quantidade: '', unidade: '', mediaValor: '' };

export function apenasNumeros(valor) {
  return String(valor || '').replace(/\D/g, '');
}

export function campoPreenchido(valor) {
  return String(valor || '').trim().length > 0;
}

export function primeiraMaiuscula(valor) {
  const v = String(valor || '');
  const indice = v.search(/[A-Za-zÀ-ÿ]/);
  if (indice < 0) return v;
  return v.slice(0, indice) + v[indice].toUpperCase() + v.slice(indice + 1);
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
