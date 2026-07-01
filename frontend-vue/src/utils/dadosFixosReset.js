import {
  clearDeprecatedCargoPresetFields,
  TEXTO_PADRAO_ENDERECO_PROPOSTAS,
} from '@/components/dispensa-art-75-ii/dispensaArt75iiShared.js';

/**
 * Preset vazio para o drawer «Dados fixos» (dispensa Art. 75 — composable useDispensaArt75IIDadosFixos).
 * @param {{ cabecalho?: string; orgao?: string }} [opts]
 */
export function emptyDa75DadosFixosPreset(opts = {}) {
  return clearDeprecatedCargoPresetFields({
    cabecalho_documento: String(opts.cabecalho ?? ''),
    orgao: String(opts.orgao ?? ''),
    solicitacao_tratamento_nome: '',
    solicitacao_destinatario_tratamento_cargo: '',
    solicitacao_destinatario_nome: '',
    solicitacao_destinatario_cargo: '',
    solicitacao_responsavel_nome: '',
    dfd_setor_requisitante: '',
    dfd_responsavel_demanda: '',
    dfd_email: '',
    dfd_gestor_contratos: '',
    dfd_fiscal_contratos: '',
    dfd_assinatura_nome: '',
    tr_endereco_entrega_propostas: TEXTO_PADRAO_ENDERECO_PROPOSTAS,
    tr_email_recebimento_propostas: '',
    tr_termo_responsavel_nome: '',
  });
}

/**
 * Preset vazio do drawer «Dados fixos» (inexigibilidade / dispensa manutenção — preview unificado).
 * Não inclui cláusulas nem cabeçalho do formulário principal.
 */
export function emptyInexigDrawerDadosFixosPreset() {
  return clearDeprecatedCargoPresetFields({
    orgao: '',
    orgao_unidade_veiculo: '',
    orgao_responsavel_equipamento: '',
    solicitacao_destinatario_nome: '',
    solicitacao_destinatario_cargo: '',
    solicitacao_responsavel_nome: '',
    solicitacao_responsavel_cargo: '',
    dfd_setor_requisitante: '',
    dfd_responsavel_demanda: '',
    dfd_email: '',
    dfd_gestor_contratos: '',
    dfd_fiscal_contratos: '',
    dfd_assinatura_nome: '',
    dfd_assinatura_cargo: '',
    ao_senhor_genero: '',
    senhor_senhora_genero: '',
  });
}

/** Preset vazio do drawer «Dados fixos» (fornecedor exclusivo). */
export function emptyFornecedorExclusivoDrawerDadosFixosPreset() {
  return clearDeprecatedCargoPresetFields({
    orgao: '',
    solicitacao_destinatario_nome: '',
    solicitacao_destinatario_cargo: '',
    solicitacao_responsavel_nome: '',
    solicitacao_responsavel_cargo: '',
    dfd_setor_requisitante: '',
    dfd_responsavel_demanda: '',
    dfd_email: '',
    dfd_gestor_contratos: '',
    dfd_fiscal_contratos: '',
    dfd_assinatura_nome: '',
    dfd_assinatura_cargo: '',
    ao_senhor_genero: '',
    senhor_senhora_genero: '',
  });
}

/**
 * Zera seleção do cadastro de órgão (combobox + nome do cadastro).
 * @param {{ value: string }} selectedIdRef
 * @param {{ value: string }} profileNameRef
 */
export function resetOrgaoProfileSelection(selectedIdRef, profileNameRef) {
  if (selectedIdRef) selectedIdRef.value = '';
  if (profileNameRef) profileNameRef.value = '';
}
