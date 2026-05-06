<template>
  <div class="ixp-page">
    <div class="ixp-wrap">
      <div class="ixp-grid">
        <section class="ixp-main">
          <div class="ixp-main-head">
            <div class="ixp-main-title">
              <div class="ixp-bot">IA</div>
              <div>
                <small>Modulo ativo</small>
                <h2>Inexigibilidade</h2>
                <p>Fornecedor Exclusivo para manutencao de veiculos (Art. 74, I)</p>
              </div>
            </div>
            <button type="button" class="ixp-btn-secondary" @click="drawerOpen = true">Dados fixos</button>
          </div>

          <div class="ixp-main-body">
            <article class="ixp-card">
              <h3>Dados basicos</h3>
              <div class="ixp-body">
                <div class="ixp-field">
                  <label>Cabecalho do documento</label>
                  <select v-model="cabecalhoDocumento">
                    <option value="">Selecione</option>
                    <option v-for="op in cabecalhoOptions" :key="op" :value="op">{{ op }}</option>
                  </select>
                </div>
                <label class="ixp-check">
                  <input v-model="processoAtivo" type="checkbox" />
                  Informar numero do processo (opcional)
                </label>
                <div class="ixp-grid-2">
                  <div v-if="processoAtivo" class="ixp-field">
                    <label>Processo</label>
                    <input v-model="processo" list="dl-processo-numero" placeholder="Ex: 123/2026" />
                  </div>
                  <div class="ixp-field">
                    <label>Orgao/Unidade responsavel pelo veiculo</label>
                    <input v-model="orgao" list="dl-orgao" placeholder="Digite o orgao" />
                  </div>
                </div>
              </div>
            </article>

            <article class="ixp-card">
              <h3>Dados do veiculo</h3>
              <div class="ixp-body ixp-grid-3">
                <div class="ixp-field"><label>Marca</label><input v-model="marca" placeholder="Ex: Chevrolet" /></div>
                <div class="ixp-field"><label>Modelo</label><input v-model="modelo" placeholder="Ex: S10" /></div>
                <div class="ixp-field"><label>Placa</label><input :value="placa" placeholder="Ex: ABC-1234" @input="placa = String($event.target.value || '').toUpperCase()" /></div>
              </div>
            </article>

            <article v-if="isDispensaManutencaoRoute" class="ixp-card">
              <h3>Tipo de manutencao</h3>
              <div class="ixp-body">
                <div class="ixp-grid-2">
                  <button type="button" :class="['ixp-choice', tipoManutencao === 'Corretiva' && 'is-active']" @click="setCorretiva">
                    <strong>Manutencao corretiva</strong>
                    <span>Reparo por falha, defeito ou necessidade imediata.</span>
                  </button>
                  <button type="button" :class="['ixp-choice', tipoManutencao === 'Preventiva' && 'is-active']" @click="tipoManutencao = 'Preventiva'">
                    <strong>Manutencao preventiva</strong>
                    <span>Revisao programada conforme quilometragem ou plano.</span>
                  </button>
                </div>
                <div v-if="tipoManutencao === 'Preventiva'" class="ixp-field ixp-mt">
                  <label>Quilometragem / Revisao preventiva</label>
                  <input v-model="revisaoKm" placeholder="Ex: Revisao de 10.000 km" />
                </div>
              </div>
            </article>

            <article class="ixp-card">
              <h3>Fornecedor exclusivo</h3>
              <div class="ixp-body ixp-grid-2">
                <div class="ixp-field"><label>Razao social / Nome do fornecedor</label><input v-model="fornecedor" list="dl-fornecedor" placeholder="Digite a razao social" /></div>
                <div class="ixp-field"><label>CNPJ</label><input :value="cnpj" placeholder="00.000.000/0001-00" @input="cnpj = formatarCNPJ(String($event.target.value || ''))" /></div>
              </div>
            </article>

            <article class="ixp-card">
              <h3>Dotacao orcamentaria</h3>
              <div class="ixp-body">
                <label class="ixp-check">
                  <input v-model="dotacaoAtiva" type="checkbox" />
                  Informar dotacao orcamentaria (opcional)
                </label>
                <div v-if="dotacaoAtiva" class="ixp-field">
                  <label>Dotacao orcamentaria</label>
                  <textarea v-model="dotacao" rows="3" :placeholder="placeholderDotacao" />
                </div>
              </div>
            </article>

            <article class="ixp-card">
              <h3>Itens e valores</h3>
              <div class="ixp-body ixp-items">
                <div v-for="(item, index) in itens" :key="index" class="ixp-item">
                  <div class="ixp-item-head">
                    <span>Item {{ index + 1 }}</span>
                    <button v-if="itens.length > 1" type="button" class="ixp-link-danger" @click="removerItem(index)">Remover</button>
                  </div>
                  <div class="ixp-grid-item">
                    <div class="ixp-field"><label>Descricao</label><input :value="item.descricao" @input="atualizarItem(index, 'descricao', $event)" /></div>
                    <div class="ixp-field"><label>Quantidade</label><input :value="item.quantidade" @input="atualizarItem(index, 'quantidade', $event)" /></div>
                    <div class="ixp-field"><label>Unidade medida</label><input :value="item.unidade" @input="atualizarItem(index, 'unidade', $event)" /></div>
                    <div class="ixp-field"><label>Valor unitario</label><input :value="item.valorUnitario" @input="atualizarItem(index, 'valorUnitario', $event)" /></div>
                    <div class="ixp-field"><label>Valor total</label><input :value="item.valorTotal" @input="atualizarItem(index, 'valorTotal', $event)" /></div>
                    <button type="button" class="ixp-btn-secondary" @click="adicionarItem">+</button>
                  </div>
                </div>
              </div>
            </article>

            <div class="ixp-field ixp-half">
              <label>Valor total do processo</label>
              <input v-model="valorGlobal" placeholder="R$ 0,00" />
            </div>

            <article class="ixp-card">
              <h3>Fiscalizacao</h3>
              <div class="ixp-body">
                <div class="ixp-field"><label>Nome do fiscal de contratos</label><input v-model="fiscal" list="dl-fiscal" /></div>
              </div>
            </article>

            <article class="ixp-card">
              <h3>Responsavel pelo Termo de Referencia</h3>
              <div class="ixp-body ixp-grid-2">
                <div class="ixp-field"><label>Nome do responsavel</label><input v-model="responsavel" list="dl-tr-nome-assinante" /></div>
                <div class="ixp-field"><label>Cargo/Funcao</label><input v-model="responsavelCargo" list="dl-tr-cargo-assinante" /></div>
              </div>
            </article>

            <article class="ixp-card">
              <h3>Data</h3>
              <div class="ixp-body ixp-grid-2">
                <div class="ixp-field">
                  <label>Modo da data</label>
                  <select v-model="modoData">
                    <option value="">Selecione</option>
                    <option v-for="op in dataOptions" :key="op" :value="op">{{ op }}</option>
                  </select>
                </div>
                <div v-if="modoData === 'Data manual'" class="ixp-field">
                  <label>Data manual</label>
                  <input :value="dataManual" placeholder="01/02/2026" @input="dataManual = formatarData(String($event.target.value || ''))" />
                </div>
              </div>
            </article>

            <article v-if="isDispensaNormalRoute" class="ixp-card">
              <h3>Gerar clausulas (IA)</h3>
              <div class="ixp-body">
                <p class="ixp-hint">
                  Gere e revise as clausulas antes do documento final. Esse fluxo vale apenas para Dispensa normal.
                </p>
                <div class="ixp-field"><label>O que sera contratado?</label><textarea v-model="clausulaContratado" rows="3" placeholder="Ex: Aquisicao de material de expediente" /></div>
                <div class="ixp-field"><label>Qual setor/secretaria sera atendido?</label><input v-model="clausulaSetor" list="dl-clausula-setor" placeholder="Ex: Secretaria de Administracao" /></div>
                <div class="ixp-field"><label>Caracteristicas minimas obrigatorias (opcional)</label><textarea v-model="clausulaCaracteristicas" rows="3" placeholder="Ex: Itens de primeira linha, entrega fracionada e suporte tecnico" /></div>
                <button class="ixp-btn-secondary" type="button" :disabled="isGeneratingClauses" @click="onGenerateClauses">
                  {{ isGeneratingClauses ? 'Gerando objeto e justificativa...' : 'Gerar objeto e justificativa' }}
                </button>
                <div class="ixp-grid-1">
                  <div class="ixp-field">
                    <label>Objeto gerado pela IA</label>
                    <textarea v-model="clausulaObjeto" rows="3" placeholder="Objeto do TR (gerado por IA ou manual)" />
                  </div>
                  <div class="ixp-field">
                    <label>Justificativa da contratacao</label>
                    <textarea v-model="clausulaJustificativa" rows="4" placeholder="Justificativa da necessidade" />
                  </div>
                </div>
              </div>
            </article>

            <div class="ixp-actions">
              <button class="ixp-btn-primary" type="button" :disabled="isSubmitting" @click="onSubmit">
                {{ isSubmitting ? 'Processando com IA...' : 'Gerar Documento com IA' }}
              </button>
              <template v-if="documentReady">
                <a v-if="documentTrUrl" :href="documentTrUrl" :download="documentTrFilename" class="ixp-btn-secondary">Download TR (DOCX)</a>
                <a v-if="documentDfdUrl" :href="documentDfdUrl" :download="documentDfdFilename" class="ixp-btn-secondary">Download DFD (DOCX)</a>
                <a v-if="documentOficioUrl" :href="documentOficioUrl" :download="documentOficioFilename" class="ixp-btn-secondary">Download Solicitacao/Oficio (DOCX)</a>
                <a v-if="documentZipUrl" :href="documentZipUrl" :download="documentZipFilename" class="ixp-btn-secondary">Download TR+DFD+Oficio (ZIP)</a>
              </template>
            </div>
            <p v-if="generateError" class="ixp-error">{{ generateError }}</p>
            <p v-if="documentReady && successMessage" class="ixp-success">{{ successMessage }}</p>
          </div>
        </section>

        <aside class="ixp-summary">
          <div class="ixp-summary-head">
            <small>Resumo em tempo real</small>
            <h3>Painel do documento</h3>
            <span>{{ progresso }}%</span>
          </div>
          <div class="ixp-progress"><div :style="{ width: `${progresso}%` }"></div></div>
          <p>{{ completos }} de {{ secoes.length }} blocos preenchidos</p>
          <div class="ixp-summary-list">
            <article v-for="sec in secoes" :key="sec.titulo" class="ixp-summary-card">
              <header>{{ sec.titulo }} <strong :class="sec.completo ? 'ok' : 'warn'">{{ sec.completo ? 'OK' : 'Pendente' }}</strong></header>
              <div v-for="linha in sec.linhas" :key="linha[0]" :class="['ixp-line', linha[2] ? 'is-ok' : 'is-warn']">
                <span>{{ linha[0] }}</span><b>{{ linha[1] }}</b>
              </div>
            </article>
          </div>
        </aside>
      </div>
    </div>

    <div v-if="drawerOpen" class="ixp-overlay" @click="drawerOpen = false"></div>
    <aside :class="['ixp-drawer', drawerOpen && 'is-open']">
      <div class="ixp-drawer-head">
        <div><small>Configuracao oculta</small><h3>Dados fixos</h3></div>
        <button type="button" class="ixp-btn-secondary" @click="drawerOpen = false">X</button>
      </div>
      <div class="ixp-drawer-body">
        <article class="ixp-card">
          <h3>1. Solicitacao / Oficio</h3>
          <div class="ixp-body">
            <div class="ixp-grid-3">
              <div class="ixp-field"><label>Tratamento</label><select v-model="fixoTratNome"><option value="">Selecione</option><option v-for="op in tratamentoNome" :key="op" :value="op">{{ op }}</option></select></div>
              <div class="ixp-field ixp-col-2"><label>1.1 A quem e direcionada a solicitacao — Nome</label><input v-model="fixoNome" list="dl-solicitacao-destinatario-nome" placeholder="Digite o nome" /></div>
            </div>
            <div class="ixp-grid-3">
              <div class="ixp-field"><label>Tratamento</label><select v-model="fixoTratCargo"><option value="">Selecione</option><option v-for="op in tratamentoCargo" :key="op" :value="op">{{ op }}</option></select></div>
              <div class="ixp-field ixp-col-2"><label>1.2 A quem e direcionada a solicitacao — Funcao / Cargo</label><input v-model="fixoCargo" list="dl-solicitacao-destinatario-cargo" placeholder="Digite a funcao ou cargo" /></div>
            </div>
            <div class="ixp-grid-2">
              <div class="ixp-field">
                <label>Nome do responsavel</label>
                <input v-model="fixoResponsavel" list="dl-solicitacao-responsavel-nome" placeholder="Digite o nome do responsavel" />
                <div class="ixp-inline-actions">
                  <button type="button" class="ixp-btn-secondary ixp-btn-xs" @click="addFieldHistory('solicitacao_responsavel_nome', fixoResponsavel)">Adicionar</button>
                  <button type="button" class="ixp-btn-secondary ixp-btn-xs" :disabled="!canDeleteFieldHistory('solicitacao_responsavel_nome', fixoResponsavel)" @click="removeFieldHistory('solicitacao_responsavel_nome', fixoResponsavel)">Excluir</button>
                </div>
              </div>
              <div class="ixp-field">
                <label>Funcao / Cargo</label>
                <input v-model="fixoResponsavelCargo" list="dl-solicitacao-responsavel-cargo" placeholder="Digite o cargo" />
                <div class="ixp-inline-actions">
                  <button type="button" class="ixp-btn-secondary ixp-btn-xs" @click="addFieldHistory('solicitacao_responsavel_cargo', fixoResponsavelCargo)">Adicionar</button>
                  <button type="button" class="ixp-btn-secondary ixp-btn-xs" :disabled="!canDeleteFieldHistory('solicitacao_responsavel_cargo', fixoResponsavelCargo)" @click="removeFieldHistory('solicitacao_responsavel_cargo', fixoResponsavelCargo)">Excluir</button>
                </div>
              </div>
            </div>
          </div>
        </article>
        <article class="ixp-card">
          <h3>2. DFD - Documento de Formalizacao da Demanda</h3>
          <div class="ixp-body ixp-grid-1">
            <div class="ixp-field">
              <label>2.1 Setor requisitante (Unidade / Setor / Departamento)</label>
              <input v-model="fixoSetor" list="dl-dfd-setor-requisitante" />
              <div class="ixp-inline-actions">
                <button type="button" class="ixp-btn-secondary ixp-btn-xs" @click="addFieldHistory('dfd_setor_requisitante', fixoSetor)">Adicionar</button>
                <button type="button" class="ixp-btn-secondary ixp-btn-xs" :disabled="!canDeleteFieldHistory('dfd_setor_requisitante', fixoSetor)" @click="removeFieldHistory('dfd_setor_requisitante', fixoSetor)">Excluir</button>
              </div>
            </div>
            <div class="ixp-field">
              <label>2.2 Responsavel pela demanda</label>
              <input v-model="fixoDemanda" list="dl-dfd-responsavel-demanda" />
              <div class="ixp-inline-actions">
                <button type="button" class="ixp-btn-secondary ixp-btn-xs" @click="addFieldHistory('dfd_responsavel_demanda', fixoDemanda)">Adicionar</button>
                <button type="button" class="ixp-btn-secondary ixp-btn-xs" :disabled="!canDeleteFieldHistory('dfd_responsavel_demanda', fixoDemanda)" @click="removeFieldHistory('dfd_responsavel_demanda', fixoDemanda)">Excluir</button>
              </div>
            </div>
            <div class="ixp-field">
              <label>2.3 E-mail</label>
              <input v-model="fixoEmail" list="dl-dfd-email" />
              <div class="ixp-inline-actions">
                <button type="button" class="ixp-btn-secondary ixp-btn-xs" @click="addFieldHistory('dfd_email', fixoEmail)">Adicionar</button>
                <button type="button" class="ixp-btn-secondary ixp-btn-xs" :disabled="!canDeleteFieldHistory('dfd_email', fixoEmail)" @click="removeFieldHistory('dfd_email', fixoEmail)">Excluir</button>
              </div>
            </div>
            <div class="ixp-field">
              <label>2.4 Nome do(a) gestor(a) de contratos</label>
              <input v-model="fixoGestor" list="dl-dfd-gestor-contratos" />
              <div class="ixp-inline-actions">
                <button type="button" class="ixp-btn-secondary ixp-btn-xs" @click="addFieldHistory('dfd_gestor_contratos', fixoGestor)">Adicionar</button>
                <button type="button" class="ixp-btn-secondary ixp-btn-xs" :disabled="!canDeleteFieldHistory('dfd_gestor_contratos', fixoGestor)" @click="removeFieldHistory('dfd_gestor_contratos', fixoGestor)">Excluir</button>
              </div>
            </div>
            <div class="ixp-field">
              <label>2.5 Nome do(a) fiscal de contratos</label>
              <input v-model="fixoFiscal" list="dl-dfd-fiscal-contratos" />
              <div class="ixp-inline-actions">
                <button type="button" class="ixp-btn-secondary ixp-btn-xs" @click="addFieldHistory('dfd_fiscal_contratos', fixoFiscal)">Adicionar</button>
                <button type="button" class="ixp-btn-secondary ixp-btn-xs" :disabled="!canDeleteFieldHistory('dfd_fiscal_contratos', fixoFiscal)" @click="removeFieldHistory('dfd_fiscal_contratos', fixoFiscal)">Excluir</button>
              </div>
            </div>
            <div class="ixp-grid-2">
              <div class="ixp-field">
                <label>Nome do responsavel</label>
                <input v-model="fixoAssinatura" list="dl-dfd-assinatura-nome" placeholder="Digite o nome do responsavel" />
                <div class="ixp-inline-actions">
                  <button type="button" class="ixp-btn-secondary ixp-btn-xs" @click="addFieldHistory('dfd_assinatura_nome', fixoAssinatura)">Adicionar</button>
                  <button type="button" class="ixp-btn-secondary ixp-btn-xs" :disabled="!canDeleteFieldHistory('dfd_assinatura_nome', fixoAssinatura)" @click="removeFieldHistory('dfd_assinatura_nome', fixoAssinatura)">Excluir</button>
                </div>
              </div>
              <div class="ixp-field">
                <label>Funcao / Cargo</label>
                <input v-model="fixoAssinaturaCargo" list="dl-dfd-assinatura-cargo" placeholder="Digite o cargo" />
                <div class="ixp-inline-actions">
                  <button type="button" class="ixp-btn-secondary ixp-btn-xs" @click="addFieldHistory('dfd_assinatura_cargo', fixoAssinaturaCargo)">Adicionar</button>
                  <button type="button" class="ixp-btn-secondary ixp-btn-xs" :disabled="!canDeleteFieldHistory('dfd_assinatura_cargo', fixoAssinaturaCargo)" @click="removeFieldHistory('dfd_assinatura_cargo', fixoAssinaturaCargo)">Excluir</button>
                </div>
              </div>
            </div>
          </div>
        </article>
      </div>
      <div class="ixp-drawer-foot">
        <button type="button" class="ixp-btn-primary" @click="onApplyFixedData">Aplicar dados fixos</button>
      </div>
    </aside>

    <datalist id="dl-processo-numero"><option v-for="v in (slotFieldOptions.processo_numero || [])" :key="`p-${v}`" :value="v" /></datalist>
    <datalist id="dl-orgao"><option v-for="v in (slotFieldOptions.orgao || [])" :key="`o-${v}`" :value="v" /></datalist>
    <datalist id="dl-fornecedor"><option v-for="v in (slotFieldOptions.fornecedor || [])" :key="`f-${v}`" :value="v" /></datalist>
    <datalist id="dl-fiscal"><option v-for="v in (slotFieldOptions.fiscal || [])" :key="`fi-${v}`" :value="v" /></datalist>
    <datalist id="dl-tr-nome-assinante"><option v-for="v in (slotFieldOptions.tr_nome_assinante || [])" :key="`na-${v}`" :value="v" /></datalist>
    <datalist id="dl-tr-cargo-assinante"><option v-for="v in (slotFieldOptions.tr_cargo_assinante || [])" :key="`ca-${v}`" :value="v" /></datalist>
    <datalist id="dl-clausula-setor"><option v-for="v in (slotFieldOptions.clausula_setor || [])" :key="`cs-${v}`" :value="v" /></datalist>
    <datalist id="dl-solicitacao-destinatario-nome"><option v-for="v in (slotFieldOptions.solicitacao_destinatario_nome || [])" :key="`sdn-${v}`" :value="v" /></datalist>
    <datalist id="dl-solicitacao-destinatario-cargo"><option v-for="v in (slotFieldOptions.solicitacao_destinatario_cargo || [])" :key="`sdc-${v}`" :value="v" /></datalist>
    <datalist id="dl-solicitacao-responsavel-nome"><option v-for="v in (slotFieldOptions.solicitacao_responsavel_nome || [])" :key="`srn-${v}`" :value="v" /></datalist>
    <datalist id="dl-solicitacao-responsavel-cargo"><option v-for="v in (slotFieldOptions.solicitacao_responsavel_cargo || [])" :key="`src-${v}`" :value="v" /></datalist>
    <datalist id="dl-dfd-setor-requisitante"><option v-for="v in (slotFieldOptions.dfd_setor_requisitante || [])" :key="`dsr-${v}`" :value="v" /></datalist>
    <datalist id="dl-dfd-responsavel-demanda"><option v-for="v in (slotFieldOptions.dfd_responsavel_demanda || [])" :key="`drd-${v}`" :value="v" /></datalist>
    <datalist id="dl-dfd-email"><option v-for="v in (slotFieldOptions.dfd_email || [])" :key="`de-${v}`" :value="v" /></datalist>
    <datalist id="dl-dfd-gestor-contratos"><option v-for="v in (slotFieldOptions.dfd_gestor_contratos || [])" :key="`dgc-${v}`" :value="v" /></datalist>
    <datalist id="dl-dfd-fiscal-contratos"><option v-for="v in (slotFieldOptions.dfd_fiscal_contratos || [])" :key="`dfc-${v}`" :value="v" /></datalist>
    <datalist id="dl-dfd-assinatura-nome"><option v-for="v in (slotFieldOptions.dfd_assinatura_nome || [])" :key="`dan-${v}`" :value="v" /></datalist>
    <datalist id="dl-dfd-assinatura-cargo"><option v-for="v in (slotFieldOptions.dfd_assinatura_cargo || [])" :key="`dac-${v}`" :value="v" /></datalist>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import { useRoute } from 'vue-router';

const API_BASE = import.meta.dev ? '' : (import.meta.env.VITE_API_URL || 'https://api.docmasteria.com.br');
const route = useRoute();
const dataOptions = ['Data automatica', 'Datado e assinado digitalmente', 'Data manual'];
const GLOBAL_SLOT_FORM_PRESET_KEY = 'global_slots_preset_v1';
const cabecalhoOptions = ref([]);
const userPrefeituraId = ref(null);
const tratamentoNome = ['Ao senhor', 'A senhora'];
const tratamentoCargo = ['Senhor', 'Senhora'];
const emptyItem = { descricao: '', quantidade: '', unidade: '', valorUnitario: '', valorTotal: '' };
const placeholderDotacao = ['Ex:', 'Orgao: 02', 'Unidade: 05', 'Projeto/Atividade: 2.045', 'Elemento de despesa: 3.3.90.39.00', 'Fonte: 1.500'].join('\n');
const DISPENSA_RAPIDA_TO_LOGICAL = {
  DispensaRapidaArt75IObrasEngenharia: 'DispensaArt75IObrasEngenharia',
  DispensaRapidaArt75IManutencaoVeiculos: 'DispensaArt75IManutencaoVeiculos',
  DispensaRapidaArt75IICompras: 'DispensaArt75IICompras',
  DispensaRapidaArt75IIServicos: 'DispensaArt75IIServicos',
  DispensaRapidaArt75IIComprasServicosInclusos: 'DispensaArt75IIComprasServicosInclusos',
};
const SLOT_PACKAGE_BY_ROUTE = {
  DispensaArt75IManutencaoVeiculos: 'dispensa_75_i_manutencao_veiculos',
  DispensaArt75IObrasEngenharia: 'dispensa_75_i_obras_engenharia',
  DispensaArt75IICompras: 'dispensa_75_ii_compras',
  DispensaArt75IIServicos: 'dispensa_75_ii_servicos',
  DispensaArt75IIComprasServicosInclusos: 'dispensa_75_ii_compras_servicos_inclusos',
  InexigibilidadeArt74IShowArtistico: 'inexigibilidade_74_i_show_artistico',
  InexigibilidadeArt74IFornecedorExclusivoPreview: 'inexigibilidade_74_i_fornecedor_exclusivo',
  InexigibilidadeArt74IManutencaoVeiculosPreview: 'inexigibilidade_74_i_manutencao_veiculos',
};
const SOL_OFICIO_FUNDAMENTO_LEGAL_BY_ROUTE = {
  DispensaArt75IManutencaoVeiculos: 'Art. 75, Inciso I, da Lei no 14.133/2021',
  DispensaArt75IObrasEngenharia: 'Art. 75, Inciso I, da Lei no 14.133/2021',
  DispensaArt75IICompras: 'Art. 75, Inciso II, da Lei no 14.133/2021',
  DispensaArt75IIServicos: 'Art. 75, Inciso II, da Lei no 14.133/2021',
  DispensaArt75IIComprasServicosInclusos: 'Art. 75, Inciso II, da Lei no 14.133/2021',
  InexigibilidadeArt74IShowArtistico: 'Art. 74, Inciso I, da Lei no 14.133/2021',
};

const drawerOpen = ref(false);
const cabecalhoDocumento = ref('');
const processoAtivo = ref(false);
const processo = ref('');
const orgao = ref('');
const marca = ref('');
const modelo = ref('');
const placa = ref('');
const tipoManutencao = ref('');
const revisaoKm = ref('');
const fornecedor = ref('');
const cnpj = ref('');
const dotacaoAtiva = ref(false);
const dotacao = ref('');
const itens = ref([{ ...emptyItem }]);
const valorGlobal = ref('');
const fiscal = ref('');
const responsavel = ref('');
const responsavelCargo = ref('');
const modoData = ref('');
const dataManual = ref('');

const fixoTratNome = ref('');
const fixoNome = ref('');
const fixoTratCargo = ref('');
const fixoCargo = ref('');
const fixoResponsavel = ref('');
const fixoResponsavelCargo = ref('');
const fixoSetor = ref('');
const fixoDemanda = ref('');
const fixoEmail = ref('');
const fixoGestor = ref('');
const fixoFiscal = ref('');
const fixoAssinatura = ref('');
const fixoAssinaturaCargo = ref('');
const isSubmitting = ref(false);
const generateError = ref('');
const successMessage = ref('');
const documentReady = ref(false);
const documentTrUrl = ref('');
const documentDfdUrl = ref('');
const documentOficioUrl = ref('');
const documentZipUrl = ref('');
const documentTrFilename = ref('termo_referencia.docx');
const documentDfdFilename = ref('dfd.docx');
const documentOficioFilename = ref('oficio.docx');
const documentZipFilename = ref('tr_dfd_oficio.zip');
const isGeneratingClauses = ref(false);
const clausulaContratado = ref('');
const clausulaSetor = ref('');
const clausulaCaracteristicas = ref('');
const clausulaObjeto = ref('');
const clausulaJustificativa = ref('');

const logicalRouteName = computed(() => DISPENSA_RAPIDA_TO_LOGICAL[route.name] || route.name);
const slotPackageKey = computed(() => SLOT_PACKAGE_BY_ROUTE[logicalRouteName.value] || 'tr_dfd_generico');
const isDispensaNormalRoute = computed(() => String(route.name || '').startsWith('DispensaArt75'));
const isDispensaManutencaoRoute = computed(() => logicalRouteName.value === 'DispensaArt75IManutencaoVeiculos');
const slotFieldOptions = reactive({});
const CATALOG_KEYS = [
  'cabecalho_documento',
  'processo_numero',
  'orgao',
  'fornecedor',
  'fiscal',
  'tr_nome_assinante',
  'tr_cargo_assinante',
  'solicitacao_destinatario_nome',
  'solicitacao_destinatario_cargo',
  'solicitacao_responsavel_nome',
  'solicitacao_responsavel_cargo',
  'dfd_setor_requisitante',
  'dfd_responsavel_demanda',
  'dfd_email',
  'dfd_gestor_contratos',
  'dfd_fiscal_contratos',
  'dfd_assinatura_nome',
  'dfd_assinatura_cargo',
  'clausula_contratado',
  'clausula_setor',
  'clausula_caracteristicas',
];

function collectGlobalFormStatePayload() {
  return {
    cabecalho_documento: cabecalhoDocumento.value,
    processo_ativo: !!processoAtivo.value,
    processo_numero: processo.value,
    orgao: orgao.value,
    solicitacao_destinatario_nome: fixoNome.value,
    solicitacao_destinatario_cargo: fixoCargo.value,
    solicitacao_responsavel_nome: fixoResponsavel.value,
    solicitacao_responsavel_cargo: fixoResponsavelCargo.value,
    dfd_setor_requisitante: fixoSetor.value,
    dfd_responsavel_demanda: fixoDemanda.value,
    dfd_email: fixoEmail.value,
    dfd_gestor_contratos: fixoGestor.value,
    dfd_fiscal_contratos: fixoFiscal.value,
    dfd_assinatura_nome: fixoAssinatura.value,
    dfd_assinatura_cargo: fixoAssinaturaCargo.value,
    tr_nome_assinante: responsavel.value,
    tr_cargo_assinante: responsavelCargo.value,
    clausula_contratado: clausulaContratado.value,
    clausula_setor: clausulaSetor.value,
    clausula_caracteristicas: clausulaCaracteristicas.value,
    clausula_objeto: clausulaObjeto.value,
    clausula_justificativa: clausulaJustificativa.value,
  };
}

function applyGlobalFormStatePayload(data) {
  if (!data || typeof data !== 'object') return;
  if ('cabecalho_documento' in data) cabecalhoDocumento.value = String(data.cabecalho_documento || '');
  if ('processo_ativo' in data) processoAtivo.value = !!data.processo_ativo;
  if ('processo_numero' in data) processo.value = String(data.processo_numero || '');
  if ('orgao' in data) orgao.value = String(data.orgao || '');
  if ('solicitacao_destinatario_nome' in data) fixoNome.value = String(data.solicitacao_destinatario_nome || '');
  if ('solicitacao_destinatario_cargo' in data) fixoCargo.value = String(data.solicitacao_destinatario_cargo || '');
  if ('solicitacao_responsavel_nome' in data) fixoResponsavel.value = String(data.solicitacao_responsavel_nome || '');
  if ('solicitacao_responsavel_cargo' in data) fixoResponsavelCargo.value = String(data.solicitacao_responsavel_cargo || '');
  if ('dfd_setor_requisitante' in data) fixoSetor.value = String(data.dfd_setor_requisitante || '');
  if ('dfd_responsavel_demanda' in data) fixoDemanda.value = String(data.dfd_responsavel_demanda || '');
  if ('dfd_email' in data) fixoEmail.value = String(data.dfd_email || '');
  if ('dfd_gestor_contratos' in data) fixoGestor.value = String(data.dfd_gestor_contratos || '');
  if ('dfd_fiscal_contratos' in data) fixoFiscal.value = String(data.dfd_fiscal_contratos || '');
  if ('dfd_assinatura_nome' in data) fixoAssinatura.value = String(data.dfd_assinatura_nome || '');
  if ('dfd_assinatura_cargo' in data) fixoAssinaturaCargo.value = String(data.dfd_assinatura_cargo || '');
  if ('tr_nome_assinante' in data) responsavel.value = String(data.tr_nome_assinante || '');
  if ('tr_cargo_assinante' in data) responsavelCargo.value = String(data.tr_cargo_assinante || '');
  if ('clausula_contratado' in data) clausulaContratado.value = String(data.clausula_contratado || '');
  if ('clausula_setor' in data) clausulaSetor.value = String(data.clausula_setor || '');
  if ('clausula_caracteristicas' in data) clausulaCaracteristicas.value = String(data.clausula_caracteristicas || '');
  if ('clausula_objeto' in data) clausulaObjeto.value = String(data.clausula_objeto || '');
  if ('clausula_justificativa' in data) clausulaJustificativa.value = String(data.clausula_justificativa || '');
}

async function saveUserGlobalPreset() {
  try {
    await fetch(`${API_BASE}/api/slots/form-state/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        slot_package_key: GLOBAL_SLOT_FORM_PRESET_KEY,
        data: collectGlobalFormStatePayload(),
      }),
    });
    await persistSlotEntries(buildCatalogEntries());
  } catch (_e) {
    // silencioso
  }
}

function buildCatalogEntries() {
  const pairs = [
    ['cabecalho_documento', cabecalhoDocumento.value],
    ['processo_numero', processo.value],
    ['orgao', orgao.value],
    ['fornecedor', fornecedor.value],
    ['fiscal', fiscal.value],
    ['tr_nome_assinante', responsavel.value],
    ['tr_cargo_assinante', responsavelCargo.value],
    ['solicitacao_destinatario_nome', fixoNome.value],
    ['solicitacao_destinatario_cargo', fixoCargo.value],
    ['solicitacao_responsavel_nome', fixoResponsavel.value],
    ['solicitacao_responsavel_cargo', fixoResponsavelCargo.value],
    ['dfd_setor_requisitante', fixoSetor.value],
    ['dfd_responsavel_demanda', fixoDemanda.value],
    ['dfd_email', fixoEmail.value],
    ['dfd_gestor_contratos', fixoGestor.value],
    ['dfd_fiscal_contratos', fixoFiscal.value],
    ['dfd_assinatura_nome', fixoAssinatura.value],
    ['dfd_assinatura_cargo', fixoAssinaturaCargo.value],
    ['clausula_contratado', clausulaContratado.value],
    ['clausula_setor', clausulaSetor.value],
    ['clausula_caracteristicas', clausulaCaracteristicas.value],
  ];
  return pairs
    .map(([field_key, value]) => ({ field_key, value: String(value || '').trim() }))
    .filter((e) => e.value);
}

async function persistSlotEntries(entries) {
  if (!Array.isArray(entries) || entries.length === 0) return;
  try {
    await fetch(`${API_BASE}/api/slots/catalog/upsert`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ entries }),
    });
  } catch (_e) {
    // silencioso
  }
}

async function removeCatalogEntry(fieldKey, value) {
  const v = String(value || '').trim();
  if (!v) return;
  try {
    await fetch(`${API_BASE}/api/slots/catalog/delete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ field_key: fieldKey, value: v }),
    });
  } catch (_e) {
    // silencioso
  }
}

async function addFieldHistory(fieldKey, rawValue) {
  const value = String(rawValue || '').trim();
  if (!value) return;
  const current = Array.isArray(slotFieldOptions[fieldKey]) ? slotFieldOptions[fieldKey] : [];
  if (!current.includes(value)) slotFieldOptions[fieldKey] = [...current, value];
  await persistSlotEntries([{ field_key: fieldKey, value }]);
}

function canDeleteFieldHistory(fieldKey, rawValue) {
  const value = String(rawValue || '').trim();
  if (!value) return false;
  const current = Array.isArray(slotFieldOptions[fieldKey]) ? slotFieldOptions[fieldKey] : [];
  return current.includes(value);
}

async function removeFieldHistory(fieldKey, rawValue) {
  const value = String(rawValue || '').trim();
  if (!value) return;
  const current = Array.isArray(slotFieldOptions[fieldKey]) ? slotFieldOptions[fieldKey] : [];
  slotFieldOptions[fieldKey] = current.filter((v) => v !== value);
  await removeCatalogEntry(fieldKey, value);
}

async function loadSlotCatalogSuggestions() {
  try {
    const url = `${API_BASE}/api/slots/catalog/batch?fields=${encodeURIComponent(CATALOG_KEYS.join(','))}&limit=25`;
    const res = await fetch(url, { credentials: 'include' });
    if (!res.ok) return;
    const payload = await res.json().catch(() => ({}));
    const map = payload?.items || {};
    CATALOG_KEYS.forEach((key) => {
      const incoming = Array.isArray(map[key]) ? map[key] : [];
      slotFieldOptions[key] = [...new Set(incoming.map((x) => String(x || '').trim()).filter(Boolean))];
    });
  } catch (_e) {
    // silencioso
  }
}
async function loadCabecalhoOptions() {
  try {
    try {
      const meRes = await fetch(`${API_BASE}/api/me/`, { credentials: 'include' });
      if (meRes.ok) {
        const me = await meRes.json().catch(() => ({}));
        userPrefeituraId.value = me?.prefeitura_id ? String(me.prefeitura_id) : null;
      } else {
        userPrefeituraId.value = null;
      }
    } catch (_e) {
      userPrefeituraId.value = null;
    }

    const res = await fetch(`${API_BASE}/api/documentos_modelos/`, { credentials: 'include' });
    if (!res.ok) return;
    const payload = await res.json().catch(() => ({}));
    const templates = Array.isArray(payload?.templates) ? payload.templates : [];
    const filtered = templates.filter((t) => {
      const tplPrefId = t?.prefeitura?.id != null ? String(t.prefeitura.id) : null;
      // Regra solicitada: apenas cabeçalhos vinculados à prefeitura do usuário.
      return !!userPrefeituraId.value && !!tplPrefId && tplPrefId === userPrefeituraId.value;
    });
    const names = [...new Set(filtered.map((t) => String(t?.name || '').trim()).filter(Boolean))];
    cabecalhoOptions.value = names;
    if (cabecalhoDocumento.value && !names.includes(cabecalhoDocumento.value)) {
      cabecalhoDocumento.value = '';
    }
  } catch (_e) {
    // silencioso
  }
}

async function loadUserGlobalPreset() {
  try {
    const url = `${API_BASE}/api/slots/form-state?slot_package_key=${encodeURIComponent(GLOBAL_SLOT_FORM_PRESET_KEY)}`;
    const res = await fetch(url, { credentials: 'include' });
    if (!res.ok) return;
    const payload = await res.json().catch(() => ({}));
    applyGlobalFormStatePayload(payload?.data || {});
  } catch (_e) {
    // silencioso
  }
}

function apenasNumeros(v) {
  return String(v || '').replace(/\D/g, '');
}
function formatarCNPJ(v) {
  const n = apenasNumeros(v).slice(0, 14);
  if (n.length <= 2) return n;
  if (n.length <= 5) return `${n.slice(0, 2)}.${n.slice(2)}`;
  if (n.length <= 8) return `${n.slice(0, 2)}.${n.slice(2, 5)}.${n.slice(5)}`;
  if (n.length <= 12) return `${n.slice(0, 2)}.${n.slice(2, 5)}.${n.slice(5, 8)}/${n.slice(8)}`;
  return `${n.slice(0, 2)}.${n.slice(2, 5)}.${n.slice(5, 8)}/${n.slice(8, 12)}-${n.slice(12)}`;
}
function formatarData(v) {
  const n = apenasNumeros(v).slice(0, 8);
  if (n.length <= 2) return n;
  if (n.length <= 4) return `${n.slice(0, 2)}/${n.slice(2)}`;
  return `${n.slice(0, 2)}/${n.slice(2, 4)}/${n.slice(4)}`;
}
function moedaParaNumero(v) {
  const n = apenasNumeros(v);
  if (!n) return 0;
  return Number(n) / 100;
}
function formatarMoeda(v) {
  const numero = Number(apenasNumeros(v)) / 100;
  return numero.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}
function calcularTotalItem(qtd, unitario) {
  const q = Number(String(qtd || '').replace(',', '.')) || 0;
  const v = moedaParaNumero(unitario);
  return (q * v).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}
function calcularValorGlobal(lista) {
  const total = lista.reduce((acc, item) => acc + moedaParaNumero(item.valorTotal), 0);
  return total.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}
function isFilled(v) {
  return String(v || '').trim().length > 0;
}
function setCorretiva() {
  tipoManutencao.value = 'Corretiva';
  revisaoKm.value = '';
}
function adicionarItem() {
  itens.value.push({ ...emptyItem });
}
function removerItem(index) {
  itens.value.splice(index, 1);
  if (!itens.value.length) itens.value = [{ ...emptyItem }];
  valorGlobal.value = calcularValorGlobal(itens.value);
}
function atualizarItem(index, campo, event) {
  const raw = String(event.target.value || '');
  const next = [...itens.value];
  const item = { ...next[index] };
  item[campo] = campo === 'valorUnitario' ? formatarMoeda(raw) : raw;
  if (campo === 'quantidade' || campo === 'valorUnitario') {
    item.valorTotal = calcularTotalItem(item.quantidade, item.valorUnitario);
  }
  next[index] = item;
  itens.value = next;
  valorGlobal.value = calcularValorGlobal(next);
}
function revokeDocumentUrls() {
  [documentTrUrl, documentDfdUrl, documentOficioUrl, documentZipUrl].forEach((urlRef) => {
    if (urlRef.value) URL.revokeObjectURL(urlRef.value);
    urlRef.value = '';
  });
}
function toBlobUrl(base64, mimeType) {
  if (!base64) return '';
  const binary = atob(base64);
  const len = binary.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i += 1) bytes[i] = binary.charCodeAt(i);
  return URL.createObjectURL(new Blob([bytes], { type: mimeType }));
}
function toBrDate(iso) {
  const v = String(iso || '').trim();
  if (!v) return '';
  const m = v.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!m) return v;
  return `${m[3]}/${m[2]}/${m[1]}`;
}
function primeiraMaiuscula(valor) {
  const v = String(valor || '');
  const idx = v.search(/[A-Za-zÀ-ÿ]/);
  if (idx < 0) return v;
  return v.slice(0, idx) + v[idx].toUpperCase() + v.slice(idx + 1);
}
function gerarObjetoTexto(contratado, setor, caracteristicas, tipoManutencaoValue = '', revisaoKmValue = '') {
  const objeto = String(contratado || '').trim() || 'objeto nao informado';
  const destino = String(setor || '').trim() ? `, visando atender as demandas de ${String(setor).trim()}` : '';
  const manutencao = String(tipoManutencaoValue || '').trim()
    ? `, no escopo de manutencao ${String(tipoManutencaoValue).trim().toLowerCase()}`
    : '';
  const revisao = String(revisaoKmValue || '').trim() ? ` (referencia: ${String(revisaoKmValue).trim()})` : '';
  const detalhes = String(caracteristicas || '').trim() ? `, observadas as seguintes caracteristicas minimas: ${String(caracteristicas).trim()}` : '';
  return `${primeiraMaiuscula(objeto)}${destino}${manutencao}${revisao}${detalhes}.`;
}
function gerarJustificativaTexto(contratado, setor, caracteristicas, tipoManutencaoValue = '', revisaoKmValue = '') {
  const objeto = String(contratado || '').trim() || 'o objeto indicado';
  const destino = String(setor || '').trim() ? ` do(a) ${String(setor).trim()}` : ' da Administracao Publica';
  const manutencao = String(tipoManutencaoValue || '').trim()
    ? ` Considera-se a manutencao ${String(tipoManutencaoValue).trim().toLowerCase()} como eixo da contratacao.`
    : '';
  const revisao = String(revisaoKmValue || '').trim() ? ` Foi indicada a referencia de revisao/quilometragem: ${String(revisaoKmValue).trim()}.` : '';
  const detalhes = String(caracteristicas || '').trim() ? ` A contratacao devera observar as caracteristicas minimas informadas: ${String(caracteristicas).trim()}.` : '';
  return `A presente contratacao justifica-se pela necessidade de assegurar ${objeto} para atendimento das demandas${destino}, garantindo a continuidade, eficiencia e adequada prestacao dos servicos publicos.${manutencao}${revisao}${detalhes}`;
}
function buildSlotsOverride() {
  const o = {};
  const solDestNome = fixoNome.value.trim();
  const solDestCargo = fixoCargo.value.trim();
  const solRespNome = fixoResponsavel.value.trim();
  const solRespCargo = fixoResponsavelCargo.value.trim();
  if (solDestNome) o.sol_oficio_destinatario_nome = solDestNome;
  if (solDestCargo) o.sol_oficio_destinatario_cargo = solDestCargo;
  if (solRespNome) o.sol_oficio_responsavel_nome = solRespNome;
  if (solRespCargo) o.sol_oficio_responsavel_cargo = solRespCargo;

  const setor = (fixoSetor.value || orgao.value).trim();
  if (setor) {
    o.secretaria_usuario = setor;
    o.dfd_setor_requisitante = setor;
  }
  const demanda = fixoDemanda.value.trim();
  if (demanda) {
    o.nome_usuario = demanda;
    o.dfd_responsavel_demanda = demanda;
  }
  if (fixoEmail.value.trim()) o.dfd_email = fixoEmail.value.trim();
  if (fixoGestor.value.trim()) o.dfd_gestor_contratos = fixoGestor.value.trim();
  const fiscalNome = (fixoFiscal.value || fiscal.value).trim();
  if (fiscalNome) {
    o.fiscal = { nome: fiscalNome };
    o.dfd_fiscal_contratos = fiscalNome;
  }
  if (fixoAssinatura.value.trim()) o.dfd_assinatura_nome = fixoAssinatura.value.trim();
  if (fixoAssinaturaCargo.value.trim()) o.dfd_assinatura_cargo = fixoAssinaturaCargo.value.trim();

  const dataManualFmt = toBrDate(dataManual.value);
  let dataTermo = '';
  if (modoData.value === 'Data automatica') {
    const now = new Date();
    dataTermo = `${String(now.getDate()).padStart(2, '0')}/${String(now.getMonth() + 1).padStart(2, '0')}/${now.getFullYear()}`;
  } else if (modoData.value === 'Data manual' && dataManualFmt) {
    dataTermo = dataManualFmt;
  }
  if (modoData.value === 'Datado e assinado digitalmente') {
    dataTermo = dataTermo ? `${dataTermo}, datado e assinado digitalmente` : 'datado e assinado digitalmente';
  }
  if (dataTermo) o.data_termo = dataTermo;

  if (responsavel.value.trim()) o.nome_assinante_termo = responsavel.value.trim();
  if (responsavelCargo.value.trim()) o.cargo_assinante_termo = responsavelCargo.value.trim();

  const objetoFallback = [
    tipoManutencao.value ? `Tipo: ${tipoManutencao.value}` : '',
    marca.value ? `Marca: ${marca.value}` : '',
    modelo.value ? `Modelo: ${modelo.value}` : '',
    placa.value ? `Placa: ${placa.value}` : '',
    revisaoKm.value ? `Revisao/KM: ${revisaoKm.value}` : '',
  ].filter(Boolean).join(' | ');
  const justificativaFallback = fornecedor.value.trim()
    ? `Fornecedor exclusivo: ${fornecedor.value.trim()} (CNPJ: ${cnpj.value.trim() || 'nao informado'})`
    : '';
  const entregasFallback = valorGlobal.value.trim() ? `Valor total estimado: ${valorGlobal.value.trim()}` : '';
  const resultadosFallback = dotacaoAtiva.value && dotacao.value.trim() ? `Dotacao orcamentaria: ${dotacao.value.trim()}` : '';
  o.objeto = clausulaObjeto.value.trim() || objetoFallback;
  if (clausulaJustificativa.value.trim() || justificativaFallback) o.justificativa = clausulaJustificativa.value.trim() || justificativaFallback;
  if (entregasFallback) o.objeto_entregas = entregasFallback;
  if (resultadosFallback) o.objeto_resultados = resultadosFallback;

  const fundamentoLegal = SOL_OFICIO_FUNDAMENTO_LEGAL_BY_ROUTE[logicalRouteName.value];
  if (fundamentoLegal) o.sol_oficio_artigo_inciso = fundamentoLegal;
  return Object.keys(o).length ? o : null;
}
function parseClauseSections(text) {
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
function extractClausesFromSectionTexts(sectionTexts) {
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
  };
}
async function onGenerateClauses() {
  isGeneratingClauses.value = true;
  generateError.value = '';
  try {
    const contratado = String(clausulaContratado.value || '').trim();
    const setor = String(clausulaSetor.value || '').trim();
    const caracteristicas = String(clausulaCaracteristicas.value || '').trim();
    if (!contratado || !setor) {
      generateError.value = 'Preencha "O que sera contratado?" e "Qual setor/secretaria sera atendido?" para gerar objeto e justificativa.';
      return;
    }
    const prompt = [
      'Com base EXCLUSIVAMENTE nos dados abaixo, gere APENAS duas secoes:',
      'Objeto:',
      'Justificativa:',
      '',
      'REGRAS OBRIGATORIAS:',
      '- Nao inventar orgao, secretaria, tipo de objeto, localidade, frota, veiculos, alunos ou professores se nao estiver explicitamente informado.',
      '- Nao reutilizar contexto de mensagens anteriores.',
      '- Usar apenas os tres campos fornecidos pelo usuario.',
      '- Se faltar informacao, escrever de forma generica sem adicionar fatos novos.',
      '',
      `O que sera contratado: ${contratado}`,
      `Setor/secretaria atendido: ${setor}`,
      `Caracteristicas minimas (opcional): ${caracteristicas || 'nao informado'}`,
      `Tipo de manutencao: ${isDispensaManutencaoRoute.value ? (tipoManutencao.value || 'nao informado') : 'nao se aplica'}`,
      `Revisao/KM: ${isDispensaManutencaoRoute.value ? (revisaoKm.value || 'nao informado') : 'nao se aplica'}`,
    ].join('\n');
    async function requestClausesFast(promptText) {
      const fastPrompt = [
        promptText,
        '',
        'Formato obrigatorio de resposta:',
        'Objeto: <texto>',
        'Justificativa: <texto>',
        '',
        'Nao inclua nenhuma secao extra.',
      ].join('\n');
      const res = await fetch(`${API_BASE}/api/llm/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ prompt: fastPrompt, stream: false }),
      });
      const data = await res.json().catch(() => ({}));
      // Normaliza para o mesmo contrato usado abaixo.
      const text = data?.data?.response || data?.data?.text || data?.response || data?.text || '';
      return { res, data: { ok: !!data?.ok, response: text } };
    }
    const { res, data } = await requestClausesFast(prompt);
    if (!res.ok || !data.ok) {
      generateError.value = res.status === 504
        ? 'A IA demorou para responder (504 Gateway Timeout). Tente um prompt mais objetivo ou gere novamente em alguns instantes.'
        : (data.error || data.detail || `Erro ${res.status} ao gerar clausulas`);
      return;
    }
    const bySections = extractClausesFromSectionTexts(data.section_texts || {});
    const text = data.generated_text || data.text || data.content || data.response || '';
    const parsed = (bySections.objeto || bySections.justificativa)
      ? bySections
      : parseClauseSections(text);
    if (!parsed.objeto && !parsed.justificativa && !String(text).trim()) {
      clausulaObjeto.value = gerarObjetoTexto(contratado, setor, caracteristicas, tipoManutencao.value, revisaoKm.value);
      clausulaJustificativa.value = gerarJustificativaTexto(contratado, setor, caracteristicas, tipoManutencao.value, revisaoKm.value);
      return;
    }
    clausulaObjeto.value = parsed.objeto || gerarObjetoTexto(contratado, setor, caracteristicas, tipoManutencao.value, revisaoKm.value);
    clausulaJustificativa.value = parsed.justificativa || gerarJustificativaTexto(contratado, setor, caracteristicas, tipoManutencao.value, revisaoKm.value);
    await saveUserGlobalPreset();
  } catch (e) {
    clausulaObjeto.value = gerarObjetoTexto(clausulaContratado.value, clausulaSetor.value, clausulaCaracteristicas.value, tipoManutencao.value, revisaoKm.value);
    clausulaJustificativa.value = gerarJustificativaTexto(clausulaContratado.value, clausulaSetor.value, clausulaCaracteristicas.value, tipoManutencao.value, revisaoKm.value);
    generateError.value = e?.message || 'Nao foi possivel gerar via IA; aplicamos a versao padrao local.';
    await saveUserGlobalPreset();
  } finally {
    isGeneratingClauses.value = false;
  }
}
function buildUserPrompt() {
  const lines = [
    `Gerar documento com base nos dados preenchidos para ${String(route.meta?.title || 'a rota atual')}.`,
    `Cabecalho do documento: ${cabecalhoDocumento.value || 'Nao informado'}`,
    `Processo: ${processoAtivo.value ? (processo.value || 'Nao informado') : 'Nao se aplica'}`,
    `Orgao: ${orgao.value || 'Nao informado'}`,
    `Veiculo: ${marca.value || '-'} ${modelo.value || '-'} / Placa ${placa.value || '-'}`,
    `Fornecedor: ${fornecedor.value || 'Nao informado'} / CNPJ: ${cnpj.value || 'Nao informado'}`,
    `Valor global: ${valorGlobal.value || 'Nao informado'}`,
  ];
  if (isDispensaManutencaoRoute.value) {
    lines.splice(5, 0, `Tipo manutencao: ${tipoManutencao.value || 'Nao informado'}`);
  }
  return lines.join('\n');
}
async function onSubmit() {
  isSubmitting.value = true;
  generateError.value = '';
  successMessage.value = '';
  documentReady.value = false;
  revokeDocumentUrls();
  try {
    if (isDispensaNormalRoute.value) {
      const hasObjeto = !!clausulaObjeto.value.trim();
      const hasJustificativa = !!clausulaJustificativa.value.trim();
      if (!hasObjeto || !hasJustificativa) {
        generateError.value = 'Para Dispensa normal, gere as clausulas com IA (ou preencha Objeto e Justificativa manualmente) antes de gerar o documento.';
        return;
      }
    }
    const payload = {
      user_prompt: buildUserPrompt(),
      slots_override: buildSlotsOverride(),
      slot_package_key: slotPackageKey.value,
    };
    const res = await fetch(`${API_BASE}/api/documentos/gerar-tr-e-dfd`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(payload),
    });
    const rawText = await res.text();
    let data = {};
    try {
      data = rawText ? JSON.parse(rawText) : {};
    } catch (_e) {
      generateError.value = `Resposta invalida do servidor (nao e JSON). Status: ${res.status}.`;
      return;
    }
    if (!res.ok || !data.ok) {
      generateError.value = res.status === 500
        ? (data.error || data.detail || 'Erro 500 no servidor. Veja logs do backend.')
        : (data.error || data.detail || `Erro ${res.status}`);
      return;
    }
    if (!data.tr?.docx_base64 || !data.dfd?.docx_base64 || !data.oficio?.docx_base64) {
      generateError.value = data.error || 'TR, DFD ou Solicitacao/Oficio nao vieram na resposta.';
      return;
    }
    documentTrUrl.value = toBlobUrl(data.tr.docx_base64, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document');
    documentDfdUrl.value = toBlobUrl(data.dfd.docx_base64, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document');
    documentOficioUrl.value = toBlobUrl(data.oficio.docx_base64, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document');
    documentZipUrl.value = data.zip?.zip_base64 ? toBlobUrl(data.zip.zip_base64, 'application/zip') : '';
    documentTrFilename.value = data.tr?.filename || 'termo_referencia.docx';
    documentDfdFilename.value = data.dfd?.filename || 'dfd.docx';
    documentOficioFilename.value = data.oficio?.filename || 'oficio.docx';
    documentZipFilename.value = data.zip?.filename || 'tr_dfd_oficio.zip';
    documentReady.value = true;
    successMessage.value = 'Termo de Referencia, DFD e Solicitacao/Oficio gerados com sucesso. Baixe os arquivos abaixo.';
    await saveUserGlobalPreset();
  } catch (e) {
    generateError.value = e?.message || 'Erro ao gerar documento';
  } finally {
    isSubmitting.value = false;
  }
}
async function onApplyFixedData() {
  await saveUserGlobalPreset();
  drawerOpen.value = false;
}
onMounted(async () => {
  await loadUserGlobalPreset();
  await loadCabecalhoOptions();
  await loadSlotCatalogSuggestions();
});
onBeforeUnmount(() => {
  revokeDocumentUrls();
});

const secoes = computed(() => {
  const itensValidos = itens.value.filter((i) => Object.values(i).some(isFilled));
  return [
    { titulo: 'Dados basicos', completo: isFilled(cabecalhoDocumento.value) && (!processoAtivo.value || isFilled(processo.value)) && isFilled(orgao.value), linhas: [['Cabecalho', cabecalhoDocumento.value || 'Nao informado', isFilled(cabecalhoDocumento.value)], ['Processo', processoAtivo.value ? processo.value || 'Nao informado' : 'Nao se aplica', !processoAtivo.value || isFilled(processo.value)], ['Orgao', orgao.value || 'Nao informado', isFilled(orgao.value)]] },
    { titulo: 'Veiculo', completo: isFilled(marca.value) && isFilled(modelo.value) && isFilled(placa.value), linhas: [['Marca', marca.value || 'Nao informado', isFilled(marca.value)], ['Modelo', modelo.value || 'Nao informado', isFilled(modelo.value)], ['Placa', placa.value || 'Nao informado', isFilled(placa.value)]] },
    ...(isDispensaManutencaoRoute.value ? [{
      titulo: 'Manutencao',
      completo: isFilled(tipoManutencao.value) && (tipoManutencao.value !== 'Preventiva' || isFilled(revisaoKm.value)),
      linhas: [
        ['Tipo', tipoManutencao.value || 'Nao informado', isFilled(tipoManutencao.value)],
        ['Revisao/KM', tipoManutencao.value === 'Preventiva' ? revisaoKm.value || 'Nao informado' : 'Nao se aplica', tipoManutencao.value !== 'Preventiva' || isFilled(revisaoKm.value)],
      ],
    }] : []),
    { titulo: 'Fornecedor', completo: isFilled(fornecedor.value) && isFilled(cnpj.value), linhas: [['Razao social', fornecedor.value || 'Nao informado', isFilled(fornecedor.value)], ['CNPJ', cnpj.value || 'Nao informado', isFilled(cnpj.value)]] },
    { titulo: 'Dotacao orcamentaria', completo: !dotacaoAtiva.value || isFilled(dotacao.value), linhas: [['Situacao', dotacaoAtiva.value ? 'Informar dotacao' : 'Nao informada', true], ['Dotacao', dotacaoAtiva.value ? dotacao.value || 'Nao informada' : 'Nao se aplica', !dotacaoAtiva.value || isFilled(dotacao.value)]] },
    { titulo: 'Itens', completo: itensValidos.length > 0 && isFilled(valorGlobal.value), linhas: [['Itens lancados', String(itensValidos.length), itensValidos.length > 0], ['Valor global', valorGlobal.value || 'Nao informado', isFilled(valorGlobal.value)]] },
    { titulo: 'Fiscalizacao', completo: isFilled(fiscal.value), linhas: [['Fiscal', fiscal.value || 'Nao informado', isFilled(fiscal.value)]] },
    { titulo: 'Responsavel pelo TR', completo: isFilled(responsavel.value) && isFilled(responsavelCargo.value), linhas: [['Responsavel', responsavel.value || 'Nao informado', isFilled(responsavel.value)], ['Cargo/Funcao', responsavelCargo.value || 'Nao informado', isFilled(responsavelCargo.value)]] },
    { titulo: 'Data', completo: isFilled(modoData.value) && (modoData.value !== 'Data manual' || isFilled(dataManual.value)), linhas: [['Modo', modoData.value || 'Nao informado', isFilled(modoData.value)], ['Data', modoData.value === 'Data manual' ? dataManual.value || 'Nao informada' : 'Nao se aplica', modoData.value !== 'Data manual' || isFilled(dataManual.value)]] },
  ];
});

const completos = computed(() => secoes.value.filter((s) => s.completo).length);
const progresso = computed(() => Math.round((completos.value / secoes.value.length) * 100));
</script>

<style>
.ixp-page { min-height: 100vh; background: #f1f5f9; padding: 16px; }
.ixp-wrap { max-width: 1280px; margin: 0 auto; }
.ixp-header h1 { margin: 0; font-size: 20px; color: #0f172a; }
.ixp-header p { margin: 4px 0 0; font-size: 13px; color: #64748b; }
.ixp-grid { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 16px; }
.ixp-main { border: 1px solid #e2e8f0; border-radius: 14px; background: #fff; overflow: hidden; }
.ixp-main-head { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; border-bottom: 1px solid #e2e8f0; padding: 16px; }
.ixp-main-title { display: flex; gap: 12px; }
.ixp-main-title small { display: block; font-size: 11px; text-transform: uppercase; color: #64748b; letter-spacing: .08em; }
.ixp-main-title h2 { margin: 4px 0 0; font-size: 18px; color: #0f172a; }
.ixp-main-title p { margin: 4px 0 0; font-size: 14px; font-weight: 600; color: #020617; }
.ixp-bot { width: 40px; height: 40px; border-radius: 12px; background: #dbeafe; color: #2563eb; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; }
.ixp-main-body { padding: 16px; display: grid; gap: 14px; }
.ixp-card { border: 1px solid #e2e8f0; border-radius: 16px; background: #fff; padding: 14px; }
.ixp-card h3 { margin: 0; font-size: 14px; color: #1e293b; }
.ixp-body { margin-top: 10px; display: grid; gap: 10px; }
.ixp-grid-1 { display: grid; gap: 10px; }
.ixp-grid-2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.ixp-grid-3 { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
.ixp-col-2 { grid-column: span 2; }
.ixp-grid-item { display: grid; grid-template-columns: 2fr 1fr 1fr 1fr 1fr 44px; gap: 10px; }
.ixp-field { display: grid; gap: 4px; }
.ixp-field label { font-size: 12px; color: #475569; font-weight: 500; }
.ixp-field input, .ixp-field textarea, .ixp-field select { width: 100%; border: 1px solid #cbd5e1; border-radius: 12px; padding: 10px 11px; font-size: 14px; color: #1e293b; outline: none; }
.ixp-field input:focus, .ixp-field textarea:focus, .ixp-field select:focus { border-color: #38bdf8; }
.ixp-check { display: flex; align-items: center; gap: 8px; font-size: 14px; color: #334155; }
.ixp-choice { border: 1px solid #e2e8f0; border-radius: 14px; background: #fff; padding: 12px; text-align: left; }
.ixp-choice strong { display: block; font-size: 14px; color: #1e293b; }
.ixp-choice span { display: block; margin-top: 4px; font-size: 12px; color: #64748b; }
.ixp-choice.is-active { border-color: #3b82f6; background: #eff6ff; }
.ixp-mt { margin-top: 4px; }
.ixp-items { gap: 12px; }
.ixp-item { border: 1px solid #e2e8f0; border-radius: 12px; padding: 12px; }
.ixp-item-head { display: flex; justify-content: space-between; margin-bottom: 8px; }
.ixp-item-head span { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; color: #64748b; }
.ixp-link-danger { border: 0; background: transparent; color: #dc2626; font-size: 12px; font-weight: 600; }
.ixp-half { max-width: 400px; }
.ixp-btn-secondary { border: 1px solid #cbd5e1; background: #fff; color: #334155; border-radius: 12px; padding: 9px 12px; font-size: 13px; font-weight: 600; }
.ixp-btn-xs { padding: 6px 10px; font-size: 12px; border-radius: 10px; }
.ixp-inline-actions { display: flex; gap: 6px; margin-top: 6px; flex-wrap: wrap; }
.ixp-btn-primary { border: 0; background: #2563eb; color: #fff; border-radius: 12px; padding: 10px 14px; font-size: 13px; font-weight: 700; width: fit-content; }
.ixp-actions { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.ixp-hint { margin: 0; font-size: 12px; color: #64748b; }
.ixp-error { margin: 0; border: 1px solid #fecaca; background: #fff1f2; color: #b91c1c; border-radius: 12px; padding: 9px 11px; font-size: 13px; }
.ixp-success { margin: 0; border: 1px solid #bbf7d0; background: #f0fdf4; color: #166534; border-radius: 12px; padding: 9px 11px; font-size: 13px; }
.ixp-summary { position: sticky; top: 16px; align-self: start; border: 1px solid #e2e8f0; border-radius: 14px; background: #fff; padding: 14px; }
.ixp-summary-head small { font-size: 11px; text-transform: uppercase; color: #64748b; letter-spacing: .08em; }
.ixp-summary-head h3 { margin: 4px 0 0; font-size: 16px; color: #0f172a; }
.ixp-summary-head span { display: inline-block; margin-top: 8px; border-radius: 999px; background: #e0f2fe; color: #0369a1; padding: 4px 10px; font-size: 12px; font-weight: 700; }
.ixp-progress { margin-top: 10px; height: 8px; background: #e2e8f0; border-radius: 999px; overflow: hidden; }
.ixp-progress > div { height: 100%; background: #0ea5e9; }
.ixp-summary > p { font-size: 12px; color: #64748b; margin: 8px 0 0; }
.ixp-summary-list { margin-top: 10px; display: grid; gap: 8px; }
.ixp-summary-card { border: 1px solid #e2e8f0; border-radius: 10px; padding: 8px; }
.ixp-summary-card header { display: flex; justify-content: space-between; font-size: 13px; font-weight: 700; color: #1e293b; margin-bottom: 6px; }
.ixp-summary-card .ok { color: #16a34a; }
.ixp-summary-card .warn { color: #d97706; }
.ixp-line { display: flex; justify-content: space-between; gap: 8px; border-radius: 8px; padding: 6px; font-size: 11px; margin-bottom: 5px; }
.ixp-line b { text-align: right; max-width: 65%; white-space: pre-wrap; color: #0f172a; }
.ixp-line.is-ok { border: 1px solid #86efac; background: #f0fdf4; }
.ixp-line.is-warn { border: 1px solid #fda4af; background: #fff1f2; }
.ixp-overlay { position: fixed; inset: 0; background: rgba(15, 23, 42, .2); z-index: 40; }
.ixp-drawer { position: fixed; right: 0; top: 0; height: 100%; width: 100%; max-width: 880px; transform: translateX(100%); transition: transform .25s ease; background: #fff; border-left: 1px solid #e2e8f0; z-index: 50; display: grid; grid-template-rows: auto 1fr auto; }
.ixp-drawer.is-open { transform: translateX(0); }
.ixp-drawer-head { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0; padding: 14px 16px; }
.ixp-drawer-head small { font-size: 11px; text-transform: uppercase; color: #64748b; letter-spacing: .08em; }
.ixp-drawer-head h3 { margin: 3px 0 0; font-size: 16px; color: #0f172a; }
.ixp-drawer-body { overflow: auto; padding: 16px; display: grid; gap: 12px; }
.ixp-drawer-foot { border-top: 1px solid #e2e8f0; padding: 14px 16px; }
.ixp-drawer-foot .ixp-btn-primary { width: 100%; }
@media (max-width: 1200px) { .ixp-grid { grid-template-columns: 1fr; } .ixp-summary { position: static; } }
@media (max-width: 900px) { .ixp-grid-2, .ixp-grid-3, .ixp-grid-item { grid-template-columns: 1fr; } .ixp-col-2 { grid-column: auto; } }
.dm-dark .ixp-page,
.dm-dark-theme .ixp-page { background: #020617; }
.dm-dark .ixp-main, .dm-dark .ixp-card, .dm-dark .ixp-summary, .dm-dark .ixp-drawer, .dm-dark .ixp-item, .dm-dark .ixp-summary-card,
.dm-dark-theme .ixp-main, .dm-dark-theme .ixp-card, .dm-dark-theme .ixp-summary, .dm-dark-theme .ixp-drawer, .dm-dark-theme .ixp-item, .dm-dark-theme .ixp-summary-card { background: #0f172a; border-color: #334155; }
.dm-dark .ixp-main-head, .dm-dark .ixp-drawer-head, .dm-dark .ixp-drawer-foot,
.dm-dark-theme .ixp-main-head, .dm-dark-theme .ixp-drawer-head, .dm-dark-theme .ixp-drawer-foot { border-color: #334155; }
.dm-dark .ixp-main-title h2, .dm-dark .ixp-main-title p, .dm-dark .ixp-card h3, .dm-dark .ixp-summary-head h3, .dm-dark .ixp-summary-card header, .dm-dark .ixp-line b, .dm-dark .ixp-choice strong,
.dm-dark-theme .ixp-main-title h2, .dm-dark-theme .ixp-main-title p, .dm-dark-theme .ixp-card h3, .dm-dark-theme .ixp-summary-head h3, .dm-dark-theme .ixp-summary-card header, .dm-dark-theme .ixp-line b, .dm-dark-theme .ixp-choice strong { color: #e2e8f0; }
.dm-dark .ixp-main-title small, .dm-dark .ixp-field label, .dm-dark .ixp-check, .dm-dark .ixp-item-head span, .dm-dark .ixp-summary > p, .dm-dark .ixp-choice span, .dm-dark .ixp-summary-head small, .dm-dark .ixp-drawer-head small,
.dm-dark-theme .ixp-main-title small, .dm-dark-theme .ixp-field label, .dm-dark-theme .ixp-check, .dm-dark-theme .ixp-item-head span, .dm-dark-theme .ixp-summary > p, .dm-dark-theme .ixp-choice span, .dm-dark-theme .ixp-summary-head small, .dm-dark-theme .ixp-drawer-head small { color: #94a3b8; }
.dm-dark .ixp-field input, .dm-dark .ixp-field textarea, .dm-dark .ixp-field select, .dm-dark .ixp-btn-secondary, .dm-dark .ixp-choice,
.dm-dark-theme .ixp-field input, .dm-dark-theme .ixp-field textarea, .dm-dark-theme .ixp-field select, .dm-dark-theme .ixp-btn-secondary, .dm-dark-theme .ixp-choice { background: #0b1222; border-color: #334155; color: #e2e8f0; }
.dm-dark .ixp-field input::placeholder, .dm-dark .ixp-field textarea::placeholder,
.dm-dark-theme .ixp-field input::placeholder, .dm-dark-theme .ixp-field textarea::placeholder { color: #64748b; }
.dm-dark .ixp-field input:focus, .dm-dark .ixp-field textarea:focus, .dm-dark .ixp-field select:focus,
.dm-dark-theme .ixp-field input:focus, .dm-dark-theme .ixp-field textarea:focus, .dm-dark-theme .ixp-field select:focus { border-color: #0ea5e9; }
.dm-dark .ixp-btn-secondary,
.dm-dark-theme .ixp-btn-secondary { color: #cbd5e1; }
.dm-dark .ixp-choice.is-active,
.dm-dark-theme .ixp-choice.is-active { border-color: #38bdf8; background: #082f49; }
.dm-dark .ixp-progress,
.dm-dark-theme .ixp-progress { background: #1e293b; }
.dm-dark .ixp-summary-head span,
.dm-dark-theme .ixp-summary-head span { background: #082f49; color: #7dd3fc; }
.dm-dark .ixp-line.is-ok,
.dm-dark-theme .ixp-line.is-ok { background: #052e16; border-color: #166534; }
.dm-dark .ixp-line.is-warn,
.dm-dark-theme .ixp-line.is-warn { background: #3f1d2e; border-color: #9f1239; }
.dm-dark .ixp-overlay,
.dm-dark-theme .ixp-overlay { background: rgba(2, 6, 23, 0.72); }
.dm-dark .ixp-error,
.dm-dark-theme .ixp-error { border-color: #9f1239; background: #3f1d2e; color: #fecdd3; }
.dm-dark .ixp-success,
.dm-dark-theme .ixp-success { border-color: #166534; background: #052e16; color: #bbf7d0; }
.dm-dark .ixp-hint,
.dm-dark-theme .ixp-hint { color: #94a3b8; }
</style>
