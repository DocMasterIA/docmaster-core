<template>
  <div class="fe-page">
    <div class="fe-wrap">
      <div class="fe-grid">
        <section class="fe-main">
          <div class="fe-main-head">
            <div class="fe-main-title">
              <div>
                <small>Módulo ativo</small>
                <h2>Inexigibilidade</h2>
                <p>Fornecedor Exclusivo Geral — Bens, Serviços e Soluções (Art. 74, I)</p>
              </div>
            </div>
            <button type="button" class="fe-btn-secondary" @click="drawerOpen = true">Dados fixos</button>
          </div>

          <div class="fe-main-body">
            <article class="fe-card">
              <h3>Dados básicos</h3>
              <div class="fe-body">
                <label class="fe-check">
                  <input v-model="processoAtivo" type="checkbox" />
                  Informar número do processo (opcional)
                </label>
                <div class="fe-grid-2">
                  <div v-if="processoAtivo" class="fe-field">
                    <label>Processo</label>
                    <input v-model="processo" placeholder="Ex: 123/2026" />
                  </div>
                  <div class="fe-field">
                    <label>{{ LABEL_ORGAO_UNIDADE_RESP_EQUIP }}</label>
                    <input
                      :value="orgao"
                      :placeholder="PLACEHOLDER_ORGAO_UNIDADE"
                      @input="onOrgaoFeInput($event)"
                    />
                  </div>
                </div>
              </div>
            </article>

            <article class="fe-card">
              <h3>Objeto específico</h3>
              <div class="fe-body">
                <div class="fe-field">
                  <label>Selecione o objeto específico da contratação</label>
                  <select v-model="objetoEspecifico">
                    <option value="">Selecione</option>
                    <option v-for="o in objetoOptions" :key="o" :value="o">{{ o }}</option>
                  </select>
                </div>
                <div v-if="objetoEspecifico === 'Outro'" class="fe-field">
                  <label>Descreva o objeto específico da contratação</label>
                  <input
                    v-model="outroObjetoEspecifico"
                    placeholder="Ex: Fornecimento de kit de manutenção original"
                  />
                </div>
              </div>
            </article>

            <article class="fe-card">
              <h3>Dados do equipamento</h3>
              <div class="fe-body fe-grid-3">
                <div class="fe-field"><label>Equipamento</label><input :value="equipamento" placeholder="Ex: Aparelho de raio-X" @input="equipamento = iniciarComMaiuscula(String(($event.target).value || ''))" /></div>
                <div class="fe-field"><label>Marca</label><input :value="marca" placeholder="Ex: Siemens" @input="marca = iniciarComMaiuscula(String(($event.target).value || ''))" /></div>
                <div class="fe-field"><label>Modelo</label><input :value="modelo" placeholder="Ex: Multix Select DR" @input="modelo = iniciarComMaiuscula(String(($event.target).value || ''))" /></div>
              </div>
            </article>

            <article class="fe-card">
              <h3>Fornecedor exclusivo</h3>
              <div class="fe-body fe-grid-2">
                <div class="fe-field">
                  <label>Razão social / Nome do fornecedor</label>
                  <input
                    :value="fornecedor"
                    placeholder="Digite a razão social"
                    @input="fornecedor = tituloNomePt(String(($event.target).value || ''))"
                  />
                </div>
                <div class="fe-field">
                  <label>CNPJ</label>
                  <input :value="cnpj" type="text" inputmode="numeric" maxlength="18" autocomplete="off" placeholder="00.000.000/0001-00" @keydown="onCnpjInputKeydown" @input="cnpj = formatCnpjBr(String(($event.target).value || ''))" />
                </div>
              </div>
            </article>

            <article class="fe-card">
              <h3>Dotação orçamentária</h3>
              <div class="fe-body">
                <label class="fe-check">
                  <input v-model="dotacaoAtiva" type="checkbox" />
                  Informar dotação orçamentária (opcional)
                </label>
                <div v-if="dotacaoAtiva" class="fe-field">
                  <label>Dotação orçamentária</label>
                  <textarea v-model="dotacao" rows="3" :placeholder="placeholderDotacao" />
                </div>
              </div>
            </article>

            <article class="fe-card">
              <h3>Itens e valores</h3>
              <div class="fe-body">
                <div v-for="(item, index) in itens" :key="index" class="fe-item">
                  <div class="fe-item-head">
                    <span>Item {{ index + 1 }}</span>
                    <button v-if="itens.length > 1" type="button" class="fe-link-danger" @click="removerItem(index)">Remover</button>
                  </div>
                  <div class="fe-grid-item">
                    <div class="fe-field"><label>Descrição</label><input :value="item.descricao" placeholder="Descreva o item" @input="atualizarItem(index, 'descricao', $event)" /></div>
                    <div class="fe-field"><label>Quantidade</label><input :value="item.quantidade" placeholder="1" @input="atualizarItem(index, 'quantidade', $event)" /></div>
                    <div class="fe-field"><label>Unidade medida</label><input :value="item.unidade" placeholder="Ex: Unidade" @input="atualizarItem(index, 'unidade', $event)" /></div>
                    <div class="fe-field"><label>Valor unitário</label><input :value="item.valorUnitario" @input="atualizarItem(index, 'valorUnitario', $event)" /></div>
                    <div class="fe-field"><label>Valor total</label><input :value="item.valorTotal" @input="atualizarItem(index, 'valorTotal', $event)" /></div>
                    <button type="button" class="fe-btn-secondary" @click="adicionarItem">+</button>
                  </div>
                </div>
                <div class="fe-field fe-half">
                  <label>Valor total do processo</label>
                  <input
                    :value="valorGlobal"
                    placeholder="R$ 0,00"
                    @input="valorGlobal = formatMoedaBRLInput(String($event.target.value || ''))"
                  />
                </div>
              </div>
            </article>

            <article class="fe-card">
              <h3>Fiscalização</h3>
              <div class="fe-body">
                <div class="fe-field">
                  <label>Nome do fiscal de contratos</label>
                  <input
                    :value="fiscal"
                    placeholder="Digite o nome do fiscal de contratos"
                    @input="fiscal = tituloNomePt(String(($event.target).value || ''))"
                  />
                </div>
              </div>
            </article>

            <article class="fe-card">
              <h3>Responsável pelo Termo de Referência</h3>
              <div class="fe-body fe-grid-2">
                <div class="fe-field">
                  <label>Nome do responsável</label>
                  <input
                    :value="responsavel"
                    placeholder="Digite o nome"
                    @input="responsavel = tituloNomePt(String(($event.target).value || ''))"
                  />
                </div>
                <div class="fe-field">
                  <label>Cargo/Função</label>
                  <input
                    :value="responsavelCargo"
                    placeholder="Digite o cargo"
                    @input="responsavelCargo = tituloNomePt(String(($event.target).value || ''))"
                  />
                </div>
              </div>
            </article>

            <article class="fe-card">
              <h3>Data</h3>
              <div class="fe-body fe-grid-2">
                <div class="fe-field">
                  <label>Modo da data</label>
                  <select v-model="modoData">
                    <option value="">Selecione</option>
                    <option v-for="o in dataOptions" :key="o" :value="o">{{ o }}</option>
                  </select>
                </div>
                <div v-if="modoData === 'Data manual'" class="fe-field">
                  <label>Data manual</label>
                  <input :value="dataManual" @input="dataManual = formatarData(String($event.target.value || ''))" />
                </div>
              </div>
            </article>

            <article class="fe-card">
              <div class="fe-actions">
                <button type="button" class="fe-btn-primary fe-btn-generate" :disabled="isSubmitting" @click="onSubmit">
                  <span v-if="!isSubmitting">Gerar Documento com IA</span>
                  <span v-else class="fe-btn-loading" aria-live="polite">
                    <i class="fa-solid fa-spinner fa-spin" aria-hidden="true"></i>
                    Processando com IA…
                  </span>
                </button>
                <template v-if="documentReady">
                  <a v-if="documentTrUrl" :href="documentTrUrl" :download="documentTrFilename" class="fe-btn-secondary">Download TR (DOCX)</a>
                  <a v-if="documentDfdUrl" :href="documentDfdUrl" :download="documentDfdFilename" class="fe-btn-secondary">Download DFD (DOCX)</a>
                  <a v-if="documentOficioUrl" :href="documentOficioUrl" :download="documentOficioFilename" class="fe-btn-secondary">Download Solicitação/Ofício (DOCX)</a>
                  <a v-if="documentZipUrl" :href="documentZipUrl" :download="documentZipFilename" class="fe-btn-secondary">Download TR+DFD+Ofício (ZIP)</a>
                </template>
                <p v-if="generateError" class="fe-error">{{ generateError }}</p>
                <p v-if="documentReady && successMessage" class="fe-success">{{ successMessage }}</p>
              </div>
            </article>
          </div>
        </section>

        <aside class="fe-summary">
          <div class="fe-summary-head">
            <small>Resumo em tempo real</small>
            <h3>Painel do documento</h3>
            <span>{{ progresso }}%</span>
          </div>
          <div class="fe-progress"><div :style="{ width: `${progresso}%` }"></div></div>
          <p>{{ completos }} de {{ secoes.length }} blocos preenchidos</p>
          <div class="fe-summary-list">
            <article v-for="sec in secoes" :key="sec.titulo" class="fe-summary-card">
              <header>{{ sec.titulo }} <strong :class="sec.completo ? 'ok' : 'warn'">{{ sec.completo ? 'OK' : 'Pendente' }}</strong></header>
              <div v-for="linha in sec.linhas" :key="linha[0]" :class="['fe-line', linha[2] ? 'is-ok' : 'is-warn']">
                <span>{{ linha[0] }}</span><b>{{ linha[1] }}</b>
              </div>
            </article>
          </div>
          <p class="fe-hint">{{ itensValidos.length ? `${itensValidos.length} item(ns) preenchido(s).` : 'Nenhum item preenchido ainda.' }}</p>
        </aside>
      </div>
    </div>

    <div v-if="drawerOpen" class="fe-overlay" @click="drawerOpen = false"></div>
    <aside :class="['fe-drawer', drawerOpen && 'is-open']">
      <div class="fe-drawer-head">
        <div><small>Configuração oculta</small><h3>Dados fixos</h3></div>
        <button type="button" class="fe-btn-secondary" @click="drawerOpen = false">X</button>
      </div>
      <div class="fe-drawer-body">
        <article class="fe-card">
          <h3>Cadastros de Órgãos</h3>
          <div class="fe-body">
            <div class="fe-field">
              <label>Órgão cadastrado</label>
              <select :value="selectedOrgaoProfileId" @change="loadOrgaoProfile(($event.target).value)">
                <option value="">Selecione um cadastro salvo</option>
                <option v-for="p in orgaoProfiles" :key="`org-${p.id}`" :value="p.id">{{ p.name }}</option>
              </select>
            </div>
            <div class="fe-field">
              <label>Nome do cadastro</label>
              <input
                :value="orgaoProfileName"
                placeholder="Ex: Fundo Municipal de Saúde"
                @input="orgaoProfileName = tituloNomePt(String(($event.target).value || ''))"
              />
            </div>
            <div class="fe-inline-actions fe-orgao-profile-actions">
              <button type="button" class="fe-btn-secondary fe-btn-xs fe-orgao-btn-new" @click="newOrgaoProfile">Novo cadastro</button>
              <button type="button" class="fe-btn-secondary fe-btn-xs fe-orgao-btn-save" @click="saveOrgaoProfile">Salvar cadastro</button>
              <button type="button" class="fe-btn-secondary fe-btn-xs fe-orgao-btn-delete" :disabled="!selectedOrgaoProfileId" @click="deleteOrgaoProfile">Excluir cadastro</button>
            </div>
          </div>
        </article>

        <article class="fe-card">
          <h3>1. Solicitação / Ofício</h3>
          <div class="fe-body">
            <div class="fe-grid-3">
              <div class="fe-field">
                <label>Tratamento</label>
                <select v-model="tratNome"><option value="">Selecione</option><option v-for="o in tratamentoNome" :key="o" :value="o">{{ o }}</option></select>
              </div>
              <div class="fe-field fe-col-2">
                <label>1.1 A quem é direcionada a solicitação — Nome</label>
                <input
                  :value="nome"
                  list="dl-solicitacao-destinatario-nome"
                  @input="nome = tituloNomePt(String(($event.target).value || ''))"
                />
              </div>
            </div>
            <div class="fe-grid-3">
              <div class="fe-field">
                <label>Tratamento</label>
                <select v-model="tratCargo"><option value="">Selecione</option><option v-for="o in tratamentoCargo" :key="o" :value="o">{{ o }}</option></select>
              </div>
              <div class="fe-field fe-col-2">
                <label>1.2 A quem é direcionada a solicitação — Função/Cargo</label>
                <input
                  :value="cargo"
                  list="dl-solicitacao-destinatario-cargo"
                  @input="cargo = tituloNomePt(String(($event.target).value || ''))"
                />
              </div>
            </div>
            <h4 class="fe-subsection-title">1.3 Responsável pela solicitação</h4>
            <div class="fe-grid-2">
              <div class="fe-field">
                <label>Nome do responsável</label>
                <input
                  :value="fixoResponsavel"
                  list="dl-solicitacao-responsavel-nome"
                  placeholder="Digite o nome do responsável"
                  @input="fixoResponsavel = tituloNomePt(String(($event.target).value || ''))"
                />
              </div>
              <div class="fe-field">
                <label>Função / Cargo</label>
                <input
                  :value="fixoResponsavelCargo"
                  list="dl-solicitacao-responsavel-cargo"
                  placeholder="Digite a função ou cargo"
                  @input="fixoResponsavelCargo = tituloNomePt(String(($event.target).value || ''))"
                />
              </div>
            </div>
          </div>
        </article>
        <article class="fe-card">
          <h3>2. DFD – Documento de Formalização da Demanda</h3>
          <div class="fe-body">
            <div class="fe-field">
              <label>2.1 Setor requisitante (Unidade / Setor / Departamento)</label>
              <input
                :value="fixoSetor"
                list="dl-dfd-setor-requisitante"
                @input="fixoSetor = tituloNomePt(String(($event.target).value || ''))"
              />
            </div>
            <div class="fe-field">
              <label>2.2 Responsável pela demanda</label>
              <input
                :value="fixoDemanda"
                list="dl-dfd-responsavel-demanda"
                @input="fixoDemanda = tituloNomePt(String(($event.target).value || ''))"
              />
            </div>
            <div class="fe-field">
              <label>2.3 E-mail</label>
              <input v-model="fixoEmail" list="dl-dfd-email" />
            </div>
            <div class="fe-field">
              <label>2.4 Nome do(a) gestor(a) de contratos</label>
              <input
                :value="fixoGestor"
                list="dl-dfd-gestor-contratos"
                @input="fixoGestor = tituloNomePt(String(($event.target).value || ''))"
              />
            </div>
            <div class="fe-field">
              <label>2.5 Nome do(a) fiscal de contratos</label>
              <input
                :value="fixoFiscal"
                list="dl-dfd-fiscal-contratos"
                @input="fixoFiscal = tituloNomePt(String(($event.target).value || ''))"
              />
            </div>
            <h4 class="fe-subsection-title">2.6 Responsável pela assinatura do DFD</h4>
            <div class="fe-grid-2">
              <div class="fe-field">
                <label>Nome do responsável</label>
                <input
                  :value="fixoAssinatura"
                  list="dl-dfd-assinatura-nome"
                  placeholder="Digite o nome do responsável"
                  @input="fixoAssinatura = tituloNomePt(String(($event.target).value || ''))"
                />
              </div>
              <div class="fe-field">
                <label>Função / Cargo</label>
                <input
                  :value="fixoAssinaturaCargo"
                  list="dl-dfd-assinatura-cargo"
                  placeholder="Digite a função ou cargo"
                  @input="fixoAssinaturaCargo = tituloNomePt(String(($event.target).value || ''))"
                />
              </div>
            </div>
          </div>
        </article>
      </div>
      <div class="fe-drawer-foot">
        <button type="button" class="fe-btn-primary" @click="onApplyFixedData">Aplicar dados fixos</button>
      </div>
    </aside>

    <datalist id="dl-processo-numero"><option v-for="v in (slotFieldOptions.processo_numero || [])" :key="`pn-${v}`" :value="v" /></datalist>
    <datalist id="dl-orgao"><option v-for="v in mergedOrgaoOptions" :key="`org-${v}`" :value="v" /></datalist>
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
import { buildGerarTrEDfdUrl, getApiBase } from '@/utils/apiBase.js';
import { describeGerarTrEDfdNetworkFailure, fetchGerarTrEDfdWithRetry } from '@/utils/fetchGerarTrEDfd.js';
import { formatCnpjBr, onCnpjInputKeydown } from '@/utils/cnpjFormat.js';
import {
  capitalizeEachWordLeadingPt,
  capitalizeFirstSignificantLetter,
  capitalizeNomeTituloPt as tituloNomePt,
  formatMoedaBRLInput,
  sanitizeQuantidadeInput,
} from '@/utils/itemValorCampos.js';

const LABEL_ORGAO_UNIDADE_RESP_EQUIP = capitalizeEachWordLeadingPt('Órgão / unidade responsável pelo equipamento');
const PLACEHOLDER_ORGAO_UNIDADE = capitalizeEachWordLeadingPt('Digite o órgão');

const API_BASE = getApiBase();
const dataOptions = ['Data automática', 'Datado e assinado digitalmente', 'Data manual'];
const ORGAO_PROFILES_STORAGE_KEY = 'orgao_profiles_v1';
const tratamentoNome = ['Ao senhor', 'A senhora'];
const tratamentoCargo = ['Senhor', 'Senhora'];
const objetoOptions = [
  'Aquisição de bens/produtos', 'Fornecimento de peças', 'Peças originais', 'Peças de reposição',
  'Componentes e acessórios', 'Insumos e materiais', 'Prestação de serviços', 'Manutenção preventiva',
  'Manutenção corretiva', 'Manutenção preventiva e corretiva', 'Assistência técnica autorizada',
  'Suporte técnico especializado', 'Outro',
];
const placeholderDotacao = 'Ex:\nÓrgão: 02\nUnidade: 05\nProjeto/Atividade: 2.045\nElemento de despesa: 3.3.90.39.00\nFonte: 1.500';

const drawerOpen = ref(false);
const processoAtivo = ref(false);
const processo = ref('');
const orgao = ref('');

function onOrgaoFeInput(ev) {
  orgao.value = tituloNomePt(String(ev?.target?.value ?? ''));
}

const objetoEspecifico = ref('');
const outroObjetoEspecifico = ref('');
const equipamento = ref('');
const marca = ref('');
const modelo = ref('');
const fornecedor = ref('');
const cnpj = ref('');
const dotacaoAtiva = ref(false);
const dotacao = ref('');
const itens = ref([{ descricao: '', quantidade: '1', unidade: '', valorUnitario: 'R$ 0,00', valorTotal: 'R$ 0,00' }]);
const valorGlobal = ref('R$ 0,00');
const fiscal = ref('');
const responsavel = ref('');
const responsavelCargo = ref('');
const modoData = ref('');
const dataManual = ref('');
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

const tratNome = ref('');
const nome = ref('');
const tratCargo = ref('');
const cargo = ref('');
const fixoResponsavel = ref('');
const fixoResponsavelCargo = ref('');
const fixoSetor = ref('');
const fixoDemanda = ref('');
const fixoEmail = ref('');
const fixoGestor = ref('');
const fixoFiscal = ref('');
const fixoAssinatura = ref('');
const fixoAssinaturaCargo = ref('');
const slotFieldOptions = reactive({});
const orgaoProfiles = ref([]);
const selectedOrgaoProfileId = ref('');
const orgaoProfileName = ref('');
const orgaoOptionsFromProfiles = computed(() => {
  const values = orgaoProfiles.value
    .map((p) => String(p?.name || '').trim())
    .filter(Boolean);
  return [...new Set(values)];
});
const mergedOrgaoOptions = computed(() => orgaoOptionsFromProfiles.value);
const GLOBAL_SLOT_FORM_PRESET_KEY = 'global_slots_preset_v1';
const SLOT_PACKAGE_KEY = 'inexigibilidade_74_i_fornecedor_exclusivo';
const CATALOG_KEYS = [
  'orgao',
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
];

function apenasNumeros(valor) { return String(valor || '').replace(/\D/g, ''); }
function campoPreenchido(valor) { return String(valor || '').trim().length > 0; }
function formatarData(valor) {
  const n = apenasNumeros(valor).slice(0, 8);
  if (n.length <= 2) return n;
  if (n.length <= 4) return `${n.slice(0, 2)}/${n.slice(2)}`;
  return `${n.slice(0, 2)}/${n.slice(2, 4)}/${n.slice(4)}`;
}
function iniciarComMaiuscula(v) {
  return capitalizeFirstSignificantLetter(v);
}
function moedaParaNumero(v) {
  const n = apenasNumeros(v || '');
  return n ? Number(n) / 100 : 0;
}
function calcularTotalItem(quantidade, unitario) {
  const q = Number(String(quantidade || '').replace(',', '.')) || 0;
  const val = moedaParaNumero(unitario);
  return (q * val).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}
function calcularValorGlobal() {
  const total = itens.value.reduce((acc, item) => acc + moedaParaNumero(item.valorTotal), 0);
  return total.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}
function atualizarItem(index, campo, ev) {
  const valorRaw = String(ev.target?.value || '');
  let valor = valorRaw;
  if (campo === 'descricao' || campo === 'unidade') {
    valor = capitalizeFirstSignificantLetter(valorRaw);
  } else if (campo === 'quantidade') {
    valor = sanitizeQuantidadeInput(valorRaw);
  } else if (campo === 'valorUnitario' || campo === 'valorTotal') {
    valor = formatMoedaBRLInput(valorRaw);
  }
  itens.value = itens.value.map((it, i) => {
    if (i !== index) return it;
    const next = { ...it, [campo]: valor };
    if (campo === 'quantidade' || campo === 'valorUnitario') next.valorTotal = calcularTotalItem(next.quantidade, next.valorUnitario);
    return next;
  });
  valorGlobal.value = calcularValorGlobal();
}
function adicionarItem() { itens.value.push({ descricao: '', quantidade: '1', unidade: '', valorUnitario: 'R$ 0,00', valorTotal: 'R$ 0,00' }); }
function removerItem(index) {
  itens.value = itens.value.filter((_, i) => i !== index);
  if (!itens.value.length) itens.value = [{ descricao: '', quantidade: '1', unidade: '', valorUnitario: 'R$ 0,00', valorTotal: 'R$ 0,00' }];
  valorGlobal.value = calcularValorGlobal();
}
function collectGlobalFormStatePayload() {
  return {
    processo_ativo: false,
    processo_numero: '',
    orgao: orgao.value,
    solicitacao_destinatario_nome: nome.value,
    solicitacao_destinatario_cargo: cargo.value,
    solicitacao_responsavel_nome: fixoResponsavel.value,
    solicitacao_responsavel_cargo: fixoResponsavelCargo.value,
    dfd_setor_requisitante: fixoSetor.value,
    dfd_responsavel_demanda: fixoDemanda.value,
    dfd_email: fixoEmail.value,
    dfd_gestor_contratos: fixoGestor.value,
    dfd_fiscal_contratos: fixoFiscal.value,
    dfd_assinatura_nome: fixoAssinatura.value,
    dfd_assinatura_cargo: fixoAssinaturaCargo.value,
    ao_senhor_genero: tratNome.value,
    senhor_senhora_genero: tratCargo.value,
  };
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
  } catch (_e) {
    // silencioso
  }
}
function applyGlobalFormStatePayload(data) {
  if (!data || typeof data !== 'object') return;
  if ('orgao' in data) {
    const t = String(data.orgao || '').trim();
    orgao.value = t ? tituloNomePt(t) : '';
  }
  if ('solicitacao_destinatario_nome' in data) {
    const v = String(data.solicitacao_destinatario_nome || '').trim();
    nome.value = v ? tituloNomePt(v) : '';
  }
  if ('solicitacao_destinatario_cargo' in data) {
    const v = String(data.solicitacao_destinatario_cargo || '').trim();
    cargo.value = v ? tituloNomePt(v) : '';
  }
  if ('solicitacao_responsavel_nome' in data) {
    const v = String(data.solicitacao_responsavel_nome || '').trim();
    fixoResponsavel.value = v ? tituloNomePt(v) : '';
  }
  if ('solicitacao_responsavel_cargo' in data) {
    const v = String(data.solicitacao_responsavel_cargo || '').trim();
    fixoResponsavelCargo.value = v ? tituloNomePt(v) : '';
  }
  if ('dfd_setor_requisitante' in data) {
    const v = String(data.dfd_setor_requisitante || '').trim();
    fixoSetor.value = v ? tituloNomePt(v) : '';
  }
  if ('dfd_responsavel_demanda' in data) {
    const v = String(data.dfd_responsavel_demanda || '').trim();
    fixoDemanda.value = v ? tituloNomePt(v) : '';
  }
  if ('dfd_email' in data) fixoEmail.value = String(data.dfd_email || '');
  if ('dfd_gestor_contratos' in data) {
    const v = String(data.dfd_gestor_contratos || '').trim();
    fixoGestor.value = v ? tituloNomePt(v) : '';
  }
  if ('dfd_fiscal_contratos' in data) {
    const v = String(data.dfd_fiscal_contratos || '').trim();
    fixoFiscal.value = v ? tituloNomePt(v) : '';
  }
  if ('dfd_assinatura_nome' in data) {
    const v = String(data.dfd_assinatura_nome || '').trim();
    fixoAssinatura.value = v ? tituloNomePt(v) : '';
  }
  if ('dfd_assinatura_cargo' in data) {
    const v = String(data.dfd_assinatura_cargo || '').trim();
    fixoAssinaturaCargo.value = v ? tituloNomePt(v) : '';
  }
  if ('ao_senhor_genero' in data) tratNome.value = String(data.ao_senhor_genero || '');
  if ('senhor_senhora_genero' in data) tratCargo.value = String(data.senhor_senhora_genero || '');
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

function loadOrgaoProfiles() {
  try {
    const raw = localStorage.getItem(ORGAO_PROFILES_STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    const list = Array.isArray(parsed) ? parsed : [];
    let dirty = false;
    orgaoProfiles.value = list.map((p) => {
      const trimmed = String(p?.name ?? '').trim();
      const n = trimmed ? tituloNomePt(trimmed) : '';
      if (n !== trimmed) dirty = true;
      return { ...p, name: n };
    });
    if (dirty) persistOrgaoProfiles();
  } catch {
    orgaoProfiles.value = [];
  }
}

function persistOrgaoProfiles() {
  try {
    localStorage.setItem(ORGAO_PROFILES_STORAGE_KEY, JSON.stringify(orgaoProfiles.value));
  } catch {
    // silencioso
  }
}

function loadOrgaoProfile(profileId) {
  const id = String(profileId || '');
  selectedOrgaoProfileId.value = id;
  const hit = orgaoProfiles.value.find((p) => String(p.id) === id);
  if (!hit) return;
  const trimmed = String(hit.name || '').trim();
  orgaoProfileName.value = trimmed ? tituloNomePt(trimmed) : '';
  applyGlobalFormStatePayload(hit.data || {});
}

function newOrgaoProfile() {
  selectedOrgaoProfileId.value = '';
  orgaoProfileName.value = '';
}

function saveOrgaoProfile() {
  const nameRaw = String(orgaoProfileName.value || '').trim();
  const name = nameRaw ? tituloNomePt(nameRaw) : '';
  if (!name) return false;
  orgaoProfileName.value = name;
  const data = collectGlobalFormStatePayload();
  data.orgao = name;
  const orgaoValue = String(data?.orgao || '').trim();
  const idx = orgaoProfiles.value.findIndex((p) => String(p.id) === String(selectedOrgaoProfileId.value || ''));
  if (idx >= 0) {
    orgaoProfiles.value[idx] = { ...orgaoProfiles.value[idx], name, data };
  } else {
    const id = String(Date.now());
    orgaoProfiles.value.push({ id, name, data });
    selectedOrgaoProfileId.value = id;
  }
  persistOrgaoProfiles();
  if (orgaoValue) {
    const current = Array.isArray(slotFieldOptions.orgao) ? slotFieldOptions.orgao : [];
    if (!current.includes(orgaoValue)) slotFieldOptions.orgao = [...current, orgaoValue];
    void persistSlotEntries([{ field_key: 'orgao', value: orgaoValue }]);
  }
  return true;
}

function deleteOrgaoProfile() {
  const id = String(selectedOrgaoProfileId.value || '');
  if (!id) return;
  orgaoProfiles.value = orgaoProfiles.value.filter((p) => String(p.id) !== id);
  persistOrgaoProfiles();
  selectedOrgaoProfileId.value = '';
  orgaoProfileName.value = '';
}
function toBlobUrl(base64, mimeType) {
  if (!base64) return '';
  const binary = atob(base64);
  const len = binary.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i += 1) bytes[i] = binary.charCodeAt(i);
  return URL.createObjectURL(new Blob([bytes], { type: mimeType }));
}
function revokeDocumentUrls() {
  [documentTrUrl, documentDfdUrl, documentOficioUrl, documentZipUrl].forEach((urlRef) => {
    if (urlRef.value) URL.revokeObjectURL(urlRef.value);
    urlRef.value = '';
  });
}

function objetoEspecificoContratacaoFe() {
  if (objetoEspecifico.value === 'Outro') return String(outroObjetoEspecifico.value || '').trim();
  return String(objetoEspecifico.value || '').trim();
}

/** Encaixa o objeto específico na frase "A necessidade consiste …" com artigo natural. */
function necessidadeConsisteComObjeto(obRaw) {
  const t = String(obRaw || '').trim();
  if (!t) return '';
  const low = t.toLowerCase();
  const lowAscii = low.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  if (/^(prestacao|aquisicao|fornecimento|manutencao|assistencia|implementacao)\b/.test(lowAscii)) {
    return `na ${low}`;
  }
  return `em assegurar ${low}`;
}

/** Texto para (DFD_OBJETO_REFERENCIA) — redação em prosa; inexigibilidade Art. 74.I fornecedor exclusivo. */
function buildFornecedorExclusivo74DfdObjetoReferencia() {
  const eq = String(equipamento.value || '').trim();
  const m = String(marca.value || '').trim();
  const mod = String(modelo.value || '').trim();
  const ob = objetoEspecificoContratacaoFe();
  const org = String(orgao.value || '').trim();
  const temEquip = !!(eq || m || mod);
  const fichaEquip = [eq, m && `marca ${m}`, mod && `modelo ${mod}`].filter(Boolean).join(', ');
  const obFrase = ob
    ? (ob.charAt(0).toUpperCase() + ob.slice(1))
    : '';

  const paragrafos = [];
  if (obFrase && temEquip) {
    const nucleo = necessidadeConsisteComObjeto(ob);
    paragrafos.push(
      `A necessidade a ser atendida consiste ${nucleo} `
      + `no âmbito do equipamento identificado (${fichaEquip}), de forma a preservar a continuidade operacional, a rastreabilidade técnica e condições seguras de uso do bem, `
      + 'evitando paralisações ou degradação do serviço público que depende dessa infraestrutura.',
    );
  } else if (obFrase) {
    paragrafos.push(
      `A necessidade administrativa consiste em formalizar a contratação referente a ${obFrase.charAt(0).toLowerCase() + obFrase.slice(1)}, `
      + 'alinhada à hipótese de inexigibilidade por fornecedor exclusivo e à continuidade adequada das atividades do órgão.',
    );
  } else if (temEquip) {
    paragrafos.push(
      `A necessidade reporta-se ao equipamento (${fichaEquip}), cuja manutenção da condição de uso e do desempenho técnico é imprescindível à rotina administrativa ou assistencial, `
      + 'devendo a contratação observar a singularidade do fornecimento e os requisitos legais aplicáveis.',
    );
  }
  if (org && paragrafos.length) {
    paragrafos.push(
      `A demanda é apresentada em nome do órgão ou unidade ${org}, responsável pela guarda, operação ou manutenção do equipamento.`,
    );
  }
  return paragrafos.join('\n\n');
}

/** Justificativa para TR, DFD e ofício — mesma redação (TR tem campo de justificativa). */
function buildFornecedorExclusivo74JustificativaTrDfd() {
  const org = String(orgao.value || '').trim();
  const ob = objetoEspecificoContratacaoFe();
  const partesEq = [String(equipamento.value || '').trim(), String(marca.value || '').trim(), String(modelo.value || '').trim()].filter(Boolean);
  const eqRef = partesEq.length ? partesEq.join(', ') : '';
  const forn = String(fornecedor.value || '').trim();
  const cnpjStr = String(cnpj.value || '').trim();
  const obTxt = ob ? ob.charAt(0).toLowerCase() + ob.slice(1) : '';

  const partes = [
    'A contratação direta enquadra-se na hipótese de inexigibilidade de licitação prevista no art. 74, inciso I, da Lei nº 14.133/2021, em razão da exclusividade do fornecimento ou da prestação técnica especializada e da imprescindibilidade de compatibilidade com solução já existente no âmbito do órgão.',
  ];
  if (obTxt && eqRef) {
    partes.push(
      `Do ponto de vista fático, a medida decorre da necessidade de ${obTxt} em relação ao equipamento ${eqRef}${org ? `, sob a responsabilidade da unidade ${org}` : ''}, `
      + 'de modo a restabelecer ou manter o padrão técnico exigido para o uso regular do bem.',
    );
  } else if (obTxt) {
    partes.push(
      `A medida atende à necessidade de ${obTxt}${org ? `, conforme demanda apresentada pelo órgão ou unidade ${org}` : ''}, nos limites da legislação aplicável.`,
    );
  } else if (eqRef) {
    partes.push(
      `A medida atende à necessidade vinculada ao equipamento ${eqRef}${org ? `, sob a responsabilidade da unidade ${org}` : ''}, preservando a continuidade operacional e a segurança de uso.`,
    );
  }
  if (forn) {
    partes.push(
      `Para fins de instrução do processo, o fornecedor exclusivo indicado é ${forn}${cnpjStr ? `, inscrito no CNPJ ${cnpjStr}` : ''}, observados os requisitos de idoneidade e a compatibilidade técnica exigidos para a espécie.`,
    );
  }
  partes.push(
    'Por conseguinte, a justificativa demonstra a singularidade do fornecimento e a adequação da contratação direta à continuidade do serviço público, com observância dos demais requisitos legais.',
  );
  return partes.join('\n\n');
}

/** Objeto resumido para o TR e ofício — uma frase em prosa. */
function buildFornecedorExclusivo74ObjetoTrResumo() {
  const ob = objetoEspecificoContratacaoFe().trim();
  const eq = String(equipamento.value || '').trim();
  const m = String(marca.value || '').trim();
  const mod = String(modelo.value || '').trim();
  const nomeEq = [eq, m, mod].filter(Boolean).join(', ');
  if (ob && nomeEq) {
    return `Contratação de ${ob.charAt(0).toLowerCase() + ob.slice(1)} vinculada ao equipamento ${nomeEq}, na hipótese de fornecedor exclusivo (art. 74, inciso I, da Lei nº 14.133/2021).`;
  }
  if (ob) {
    return `Contratação de ${ob.charAt(0).toLowerCase() + ob.slice(1)}, na hipótese de fornecedor exclusivo (art. 74, inciso I, da Lei nº 14.133/2021).`;
  }
  if (nomeEq) {
    return `Contratação vinculada ao equipamento ${nomeEq}, na hipótese de fornecedor exclusivo (art. 74, inciso I, da Lei nº 14.133/2021).`;
  }
  return '';
}

function buildSlotsOverride() {
  const o = {
    numero_processo: processoAtivo.value ? String(processo.value || '').trim() : '',
    orgao: String(orgao.value || '').trim(),
    objeto_especifico: objetoEspecifico.value === 'Outro' ? String(outroObjetoEspecifico.value || '').trim() : String(objetoEspecifico.value || '').trim(),
    equipamento: String(equipamento.value || '').trim(),
    marca: String(marca.value || '').trim(),
    modelo: String(modelo.value || '').trim(),
    fornecedor: String(fornecedor.value || '').trim(),
    cnpj_fornecedor: String(cnpj.value || '').trim(),
    valor_total: String(valorGlobal.value || '').trim(),
    ao_senhor_genero: String(tratNome.value || '').trim(),
    senhor_senhora_genero: String(tratCargo.value || '').trim(),
    sol_oficio_destinatario_nome: String(nome.value || '').trim(),
    sol_oficio_destinatario_cargo: String(cargo.value || '').trim(),
    sol_oficio_responsavel_nome: String(fixoResponsavel.value || '').trim(),
    sol_oficio_responsavel_cargo: String(fixoResponsavelCargo.value || '').trim(),
    secretaria_usuario: String((responsavelCargo.value || '').trim()),
    dfd_setor_requisitante: String((fixoSetor.value || orgao.value || '').trim()),
    dfd_responsavel_demanda: String(fixoDemanda.value || '').trim(),
    dfd_email: String(fixoEmail.value || '').trim(),
    dfd_gestor_contratos: String(fixoGestor.value || '').trim(),
    dfd_fiscal_contratos: String((fixoFiscal.value || fiscal.value || '').trim()),
    dfd_assinatura_nome: String(fixoAssinatura.value || '').trim(),
    dfd_assinatura_cargo: String(fixoAssinaturaCargo.value || '').trim(),
    sol_oficio_artigo_inciso: 'Art. 74, Inciso I, da Lei no 14.133/2021',
  };
  if (dotacaoAtiva.value && String(dotacao.value || '').trim()) {
    const dotacaoTexto = String(dotacao.value || '').trim();
    o.dotacao = dotacaoTexto;
    o.dotacao_numero = dotacaoTexto;
    o.objeto_resultados = `Dotação orçamentária: ${dotacaoTexto}`;
  }
  const modo = String(modoData.value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
  let dataTermoFornecedor = '';
  if (modo === 'data automatica') {
    const now = new Date();
    dataTermoFornecedor = `${String(now.getDate()).padStart(2, '0')}/${String(now.getMonth() + 1).padStart(2, '0')}/${now.getFullYear()}`;
  } else if (modo === 'data manual' && dataManual.value.trim()) {
    dataTermoFornecedor = dataManual.value.trim();
  }
  if (modo === 'datado e assinado digitalmente') {
    dataTermoFornecedor = 'datado e assinado digitalmente';
  }
  if (dataTermoFornecedor) o.data_termo = dataTermoFornecedor;
  o.itens = itens.value.filter((x) => Object.values(x).some((v) => String(v || '').trim())).map((item) => ({
    descricao: String(item.descricao || '').trim(),
    quantidade: String(item.quantidade || '').trim(),
    unidade: String(item.unidade || '').trim(),
    valor_unitario: String(item.valorUnitario || '').trim(),
    valor_total: String(item.valorTotal || '').trim(),
  }));
  const fiscalNome = String((fixoFiscal.value || fiscal.value || '')).trim();
  o.fiscal = fiscalNome ? { nome: fiscalNome } : undefined;
  o.nome_assinante_termo = String(responsavel.value || '').trim();
  o.cargo_assinante_termo = String(responsavelCargo.value || '').trim();

  const dfdObjRef = buildFornecedorExclusivo74DfdObjetoReferencia().trim();
  const justTrDfd = buildFornecedorExclusivo74JustificativaTrDfd().trim();
  const objetoTr = buildFornecedorExclusivo74ObjetoTrResumo().trim();
  if (dfdObjRef) o.dfd_objeto_referencia = dfdObjRef;
  if (justTrDfd) {
    o.justificativa = justTrDfd;
    o.dfd_justificativa = justTrDfd;
    o.sol_oficio_justificativa = justTrDfd;
  }
  if (objetoTr) {
    o.objeto = objetoTr;
    o.sol_oficio_objeto = objetoTr;
  }

  return o;
}
function buildUserPrompt() {
  return [
    'Inexigibilidade Art. 74 I - Fornecedor Exclusivo.',
    `Objeto específico: ${objetoEspecifico.value || 'não informado'}`,
    `Órgão: ${orgao.value || 'não informado'}`,
    `Fornecedor: ${fornecedor.value || 'não informado'}`,
  ].join('\n');
}
async function onSubmit() {
  isSubmitting.value = true;
  generateError.value = '';
  successMessage.value = '';
  documentReady.value = false;
  revokeDocumentUrls();
  try {
    const payload = {
      user_prompt: buildUserPrompt(),
      slots_override: buildSlotsOverride(),
      slot_package_key: SLOT_PACKAGE_KEY,
    };
    const gerarUrl = buildGerarTrEDfdUrl(API_BASE);
    const result = await fetchGerarTrEDfdWithRetry(API_BASE, payload);
    if (!result.ok) {
      if (result.kind === 'network') {
        const msg = String(result.errorMessage || '');
        const looksNetwork = /fetch|network|failed|load|aborted|timed out|timeout/i.test(msg);
        generateError.value = looksNetwork ? describeGerarTrEDfdNetworkFailure(gerarUrl) : msg;
      } else {
        generateError.value = `${result.errorMessage}${result.status ? ` (${result.status})` : ''}`;
      }
      return;
    }
    const { data } = result;
    if (!data.tr?.docx_base64 || !data.dfd?.docx_base64 || !data.oficio?.docx_base64) {
      generateError.value = data.error || 'TR, DFD ou Solicitação/Ofício não vieram na resposta.';
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
    successMessage.value = 'Termo de Referência, DFD e Solicitação/Ofício gerados com sucesso.';
    await saveUserGlobalPreset();
  } catch (e) {
    generateError.value = e?.message || 'Erro ao gerar documento.';
  } finally {
    isSubmitting.value = false;
  }
}
async function onApplyFixedData() {
  await saveUserGlobalPreset();
  drawerOpen.value = false;
}
onMounted(async () => {
  loadOrgaoProfiles();
  await loadUserGlobalPreset();
  await loadSlotCatalogSuggestions();
});
onBeforeUnmount(() => {
  revokeDocumentUrls();
});

const itensValidos = computed(() => itens.value.filter((it) => Object.values(it).some(campoPreenchido)));
const secoes = computed(() => [
  {
    titulo: 'Dados básicos',
    completo: (!processoAtivo.value || campoPreenchido(processo.value)) && campoPreenchido(orgao.value),
    linhas: [
      ['Processo', processoAtivo.value ? processo.value || 'Não informado' : 'Não se aplica', !processoAtivo.value || campoPreenchido(processo.value)],
      ['Órgão', orgao.value || 'Não informado', campoPreenchido(orgao.value)],
    ],
  },
  {
    titulo: 'Objeto específico',
    completo: campoPreenchido(objetoEspecifico.value) && (objetoEspecifico.value !== 'Outro' || campoPreenchido(outroObjetoEspecifico.value)),
    linhas: [
      ['Objeto específico', objetoEspecifico.value || 'Não informado', campoPreenchido(objetoEspecifico.value)],
      ['Descrição', objetoEspecifico.value === 'Outro' ? (outroObjetoEspecifico.value || 'Não informada') : 'Não se aplica', objetoEspecifico.value !== 'Outro' || campoPreenchido(outroObjetoEspecifico.value)],
    ],
  },
  {
    titulo: 'Equipamento',
    completo: campoPreenchido(equipamento.value) && campoPreenchido(marca.value) && campoPreenchido(modelo.value),
    linhas: [
      ['Equipamento', equipamento.value || 'Não informado', campoPreenchido(equipamento.value)],
      ['Marca', marca.value || 'Não informado', campoPreenchido(marca.value)],
      ['Modelo', modelo.value || 'Não informado', campoPreenchido(modelo.value)],
    ],
  },
  {
    titulo: 'Fornecedor',
    completo: campoPreenchido(fornecedor.value) && campoPreenchido(cnpj.value),
    linhas: [
      ['Razão social', fornecedor.value || 'Não informado', campoPreenchido(fornecedor.value)],
      ['CNPJ', cnpj.value || 'Não informado', campoPreenchido(cnpj.value)],
    ],
  },
  {
    titulo: 'Dotação orçamentária',
    completo: !dotacaoAtiva.value || campoPreenchido(dotacao.value),
    linhas: [
      ['Situação', dotacaoAtiva.value ? 'Informada' : 'Não informada', !dotacaoAtiva.value || campoPreenchido(dotacao.value)],
      ['Dotação', dotacaoAtiva.value ? (dotacao.value || 'Não informada') : 'Não se aplica', !dotacaoAtiva.value || campoPreenchido(dotacao.value)],
    ],
  },
  {
    titulo: 'Itens',
    completo: itensValidos.value.length > 0 && campoPreenchido(valorGlobal.value),
    linhas: [
      ['Itens lançados', String(itensValidos.value.length), itensValidos.value.length > 0],
      ['Valor global', valorGlobal.value || 'Não informado', campoPreenchido(valorGlobal.value)],
    ],
  },
  {
    titulo: 'Fiscalização',
    completo: campoPreenchido(fiscal.value),
    linhas: [['Fiscal', fiscal.value || 'Não informado', campoPreenchido(fiscal.value)]],
  },
  {
    titulo: 'Responsável pelo TR',
    completo: campoPreenchido(responsavel.value) && campoPreenchido(responsavelCargo.value),
    linhas: [
      ['Responsável', responsavel.value || 'Não informado', campoPreenchido(responsavel.value)],
      ['Cargo/Função', responsavelCargo.value || 'Não informado', campoPreenchido(responsavelCargo.value)],
    ],
  },
  {
    titulo: 'Data',
    completo: campoPreenchido(modoData.value) && (modoData.value !== 'Data manual' || campoPreenchido(dataManual.value)),
    linhas: [
      ['Modo', modoData.value || 'Não informado', campoPreenchido(modoData.value)],
      ['Data', modoData.value === 'Data manual' ? (dataManual.value || 'Não informada') : (modoData.value ? 'Não se aplica' : 'Não se aplica'), modoData.value !== 'Data manual' || campoPreenchido(dataManual.value)],
    ],
  },
]);
const completos = computed(() => secoes.value.filter((s) => s.completo).length);
const progresso = computed(() => Math.round((completos.value / secoes.value.length) * 100));
</script>

<style scoped>
.fe-page { min-height: 100vh; background: #f1f5f9; padding: 16px; }
.fe-wrap { max-width: 1280px; margin: 0 auto; }
.fe-grid { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 14px; }
.fe-main, .fe-summary, .fe-drawer, .fe-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; }
.fe-main-head { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0; padding: 14px; }
.fe-main-title small { font-size: 11px; text-transform: uppercase; color: #64748b; }
.fe-main-title h2 { margin: 4px 0 0; font-size: 18px; }
.fe-main-title p { margin: 2px 0 0; color: #64748b; font-size: 13px; }
.fe-main-body { padding: 14px; display: grid; gap: 12px; }
.fe-card { padding: 12px; }
.fe-card h3 { margin: 0 0 8px; font-size: 14px; }
.fe-subsection-title {
  margin: 6px 0 0;
  font-size: 13px;
  font-weight: 600;
  color: #334155;
}
.fe-body { display: grid; gap: 8px; }
.fe-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.fe-grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; }
.fe-grid-item { display: grid; grid-template-columns: repeat(6, 1fr); gap: 8px; align-items: end; }
.fe-field label { font-size: 12px; color: #475569; display: block; margin-bottom: 3px; }
.fe-field input, .fe-field select, .fe-field textarea { width: 100%; box-sizing: border-box; border: 1px solid #cbd5e1; border-radius: 8px; padding: 8px 10px; }
.fe-check { font-size: 13px; color: #334155; }
.fe-item { border: 1px solid #e2e8f0; border-radius: 10px; padding: 10px; }
.fe-item-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-size: 12px; color: #64748b; }
.fe-link-danger { border: 0; background: transparent; color: #dc2626; cursor: pointer; }
.fe-half { max-width: 360px; }
.fe-hint { margin-top: 10px; font-size: 12px; color: #64748b; }
.fe-summary { padding: 12px; position: sticky; top: 10px; height: fit-content; }
.fe-summary-head small { color: #64748b; text-transform: uppercase; font-size: 11px; }
.fe-summary-head h3 { margin: 4px 0; font-size: 15px; }
.fe-summary-head span { font-size: 12px; font-weight: 700; color: #0369a1; }
.fe-progress { margin: 8px 0; height: 8px; border-radius: 8px; background: #e2e8f0; overflow: hidden; }
.fe-progress > div { height: 100%; background: #0ea5e9; }
.fe-summary-list { display: grid; gap: 8px; margin-top: 8px; }
.fe-summary-card { border: 1px solid #e2e8f0; border-radius: 10px; padding: 8px; }
.fe-summary-card header { font-size: 13px; display: flex; justify-content: space-between; margin-bottom: 6px; }
.fe-summary-card .ok { color: #15803d; }
.fe-summary-card .warn { color: #d97706; }
.fe-line { display: flex; justify-content: space-between; gap: 8px; font-size: 12px; padding: 4px 6px; border-radius: 6px; margin-bottom: 4px; }
.fe-line.is-ok { background: #ecfdf5; border-left: 3px solid #22c55e; }
.fe-line.is-warn { background: #fff7ed; border-left: 3px solid #f59e0b; }
.fe-overlay { position: fixed; inset: 0; background: rgba(2, 6, 23, 0.25); z-index: 40; }
.fe-drawer { position: fixed; right: 0; top: 0; height: 100%; width: min(880px, 100%); transform: translateX(100%); transition: transform .2s; z-index: 50; display: grid; grid-template-rows: auto 1fr auto; }
.fe-drawer.is-open { transform: translateX(0); }
.fe-drawer-head { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0; padding: 12px; }
.fe-drawer-head small { font-size: 11px; color: #64748b; text-transform: uppercase; }
.fe-drawer-head h3 { margin: 2px 0 0; font-size: 16px; }
.fe-drawer-body { padding: 12px; overflow: auto; display: grid; gap: 10px; }
.fe-drawer-foot { border-top: 1px solid #e2e8f0; padding: 12px; }
.fe-col-2 { grid-column: span 2; }
.fe-btn-primary, .fe-btn-secondary { border-radius: 8px; border: 1px solid #cbd5e1; padding: 8px 12px; cursor: pointer; }
.fe-btn-primary { background: #0f172a; color: #fff; border-color: #0f172a; width: 100%; }
.fe-btn-secondary { background: #fff; color: #334155; }
.fe-btn-xs { padding: 6px 10px; font-size: 12px; border-radius: 8px; }
.fe-inline-actions { display: flex; gap: 6px; margin-top: 6px; flex-wrap: wrap; }
.fe-orgao-profile-actions { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; width: 100%; }
.fe-orgao-profile-actions > button { width: 100%; padding: 10px 12px; font-size: 13px; border-radius: 8px; }
.fe-orgao-btn-save { background: #2563eb; border-color: #2563eb; color: #fff; }
.fe-orgao-btn-delete { background: #dc2626; border-color: #dc2626; color: #fff; }
.fe-orgao-profile-actions > button:disabled { opacity: 0.6; }
.fe-actions { display: grid; gap: 8px; }
.fe-btn-generate { font-weight: 700; letter-spacing: .2px; }
.fe-btn-loading {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
}
.fe-btn-loading .fa-spinner {
  flex-shrink: 0;
}
.fe-error { margin: 0; border: 1px solid #fecaca; background: #fff1f2; color: #b91c1c; border-radius: 8px; padding: 9px 11px; font-size: 13px; }
.fe-success { margin: 0; border: 1px solid #bbf7d0; background: #f0fdf4; color: #166534; border-radius: 8px; padding: 9px 11px; font-size: 13px; }

.dm-dark .fe-page,
.dm-dark-theme .fe-page { background: #020617; }

.dm-dark .fe-main,
.dm-dark .fe-summary,
.dm-dark .fe-drawer,
.dm-dark .fe-card,
.dm-dark .fe-item,
.dm-dark .fe-summary-card,
.dm-dark-theme .fe-main,
.dm-dark-theme .fe-summary,
.dm-dark-theme .fe-drawer,
.dm-dark-theme .fe-card,
.dm-dark-theme .fe-item,
.dm-dark-theme .fe-summary-card {
  background: #0f172a;
  border-color: #334155;
}

.dm-dark .fe-main-head,
.dm-dark .fe-drawer-head,
.dm-dark .fe-drawer-foot,
.dm-dark-theme .fe-main-head,
.dm-dark-theme .fe-drawer-head,
.dm-dark-theme .fe-drawer-foot { border-color: #334155; }

.dm-dark .fe-main-title h2,
.dm-dark .fe-main-title p,
.dm-dark .fe-card h3,
.dm-dark .fe-summary-head h3,
.dm-dark .fe-summary-card header,
.dm-dark .fe-line b,
.dm-dark-theme .fe-main-title h2,
.dm-dark-theme .fe-main-title p,
.dm-dark-theme .fe-card h3,
.dm-dark-theme .fe-summary-head h3,
.dm-dark-theme .fe-summary-card header,
.dm-dark-theme .fe-line b { color: #e2e8f0; }

.dm-dark .fe-subsection-title,
.dm-dark-theme .fe-subsection-title { color: #cbd5e1; }

.dm-dark .fe-main-title small,
.dm-dark .fe-field label,
.dm-dark .fe-check,
.dm-dark .fe-item-head span,
.dm-dark .fe-summary > p,
.dm-dark .fe-summary-head small,
.dm-dark .fe-drawer-head small,
.dm-dark-theme .fe-main-title small,
.dm-dark-theme .fe-field label,
.dm-dark-theme .fe-check,
.dm-dark-theme .fe-item-head span,
.dm-dark-theme .fe-summary > p,
.dm-dark-theme .fe-summary-head small,
.dm-dark-theme .fe-drawer-head small { color: #94a3b8; }

.dm-dark .fe-field input,
.dm-dark .fe-field textarea,
.dm-dark .fe-field select,
.dm-dark .fe-btn-secondary,
.dm-dark-theme .fe-field input,
.dm-dark-theme .fe-field textarea,
.dm-dark-theme .fe-field select,
.dm-dark-theme .fe-btn-secondary {
  background: #0b1222;
  border-color: #334155;
  color: #e2e8f0;
}

.dm-dark .fe-field input::placeholder,
.dm-dark .fe-field textarea::placeholder,
.dm-dark-theme .fe-field input::placeholder,
.dm-dark-theme .fe-field textarea::placeholder { color: #64748b; }

.dm-dark .fe-field input:focus,
.dm-dark .fe-field textarea:focus,
.dm-dark .fe-field select:focus,
.dm-dark-theme .fe-field input:focus,
.dm-dark-theme .fe-field textarea:focus,
.dm-dark-theme .fe-field select:focus { border-color: #0ea5e9; outline: none; }

.dm-dark .fe-btn-secondary,
.dm-dark-theme .fe-btn-secondary { color: #cbd5e1; }
.dm-dark .fe-orgao-btn-save,
.dm-dark-theme .fe-orgao-btn-save { background: #2563eb; border-color: #2563eb; color: #fff; }
.dm-dark .fe-orgao-btn-delete,
.dm-dark-theme .fe-orgao-btn-delete { background: #dc2626; border-color: #dc2626; color: #fff; }

.dm-dark .fe-progress,
.dm-dark-theme .fe-progress { background: #1e293b; }

.dm-dark .fe-summary-head span,
.dm-dark-theme .fe-summary-head span { color: #7dd3fc; }

.dm-dark .fe-line.is-ok,
.dm-dark-theme .fe-line.is-ok { background: #052e16; border-color: #166534; }

.dm-dark .fe-line.is-warn,
.dm-dark-theme .fe-line.is-warn { background: #3f1d2e; border-color: #9f1239; }

.dm-dark .fe-overlay,
.dm-dark-theme .fe-overlay { background: rgba(2, 6, 23, 0.72); }

.dm-dark .fe-link-danger,
.dm-dark-theme .fe-link-danger { color: #fb7185; }

.dm-dark .fe-hint,
.dm-dark-theme .fe-hint { color: #94a3b8; }
.dm-dark .fe-error,
.dm-dark-theme .fe-error { border-color: #9f1239; background: #3f1d2e; color: #fecdd3; }
.dm-dark .fe-success,
.dm-dark-theme .fe-success { border-color: #166534; background: #052e16; color: #bbf7d0; }
@media (max-width: 1180px) { .fe-grid { grid-template-columns: 1fr; } .fe-summary { position: static; } }
</style>
