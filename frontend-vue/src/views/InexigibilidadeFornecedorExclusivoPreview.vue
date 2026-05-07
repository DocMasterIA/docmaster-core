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
                    <label>Órgão/Unidade responsável pelo equipamento</label>
                    <input v-model="orgao" placeholder="Digite o órgão" />
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
              <h3>Gerar objeto e justificativa (IA)</h3>
              <div class="fe-body">
                <div class="fe-field">
                  <label>O que será contratado?</label>
                  <textarea
                    v-model="clausulaContratado"
                    rows="3"
                    placeholder="Ex: Aquisição de material de expediente para Secretaria da Administração&#10;10 canetas azul, 2 grampeadores, 10 resmas de papel A4"
                  />
                </div>
                <div class="fe-field">
                  <label>Qual setor/secretaria será atendido?</label>
                  <input v-model="clausulaSetor" placeholder="Ex: Secretaria de Administração" />
                </div>
                <div class="fe-field">
                  <label>Características mínimas obrigatórias (opcional)</label>
                  <textarea v-model="clausulaCaracteristicas" rows="3" placeholder="Ex: Para uso contínuo das unidades administrativas" />
                </div>
                <button type="button" class="fe-btn-secondary" :disabled="isGeneratingClauses" @click="onGenerateClauses">
                  {{ isGeneratingClauses ? 'Gerando objeto e justificativa...' : 'Gerar objeto e justificativa' }}
                </button>
                <div class="fe-field">
                  <label>Objeto gerado pela IA</label>
                  <textarea v-model="clausulaObjeto" rows="3" placeholder="Objeto do TR (gerado por IA ou manual)" />
                </div>
                <div class="fe-field">
                  <label>Justificativa da contratação</label>
                  <textarea v-model="clausulaJustificativa" rows="4" placeholder="Justificativa da necessidade" />
                </div>
                <p v-if="iaError" class="fe-error">{{ iaError }}</p>
              </div>
            </article>

            <article class="fe-card">
              <h3>Dados do equipamento</h3>
              <div class="fe-body fe-grid-3">
                <div class="fe-field"><label>Equipamento</label><input v-model="equipamento" placeholder="Ex: Aparelho de raio-X" /></div>
                <div class="fe-field"><label>Marca</label><input v-model="marca" placeholder="Ex: Siemens" /></div>
                <div class="fe-field"><label>Modelo</label><input v-model="modelo" placeholder="Ex: Multix Select DR" /></div>
              </div>
            </article>

            <article class="fe-card">
              <h3>Fornecedor exclusivo</h3>
              <div class="fe-body fe-grid-2">
                <div class="fe-field">
                  <label>Razão social / Nome do fornecedor</label>
                  <input v-model="fornecedor" placeholder="Digite a razão social" @input="fornecedor = iniciarComMaiuscula(fornecedor)" />
                </div>
                <div class="fe-field">
                  <label>CNPJ</label>
                  <input :value="cnpj" placeholder="00.000.000/0001-00" @input="cnpj = formatarCNPJ(String($event.target.value || ''))" />
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
                  <input v-model="valorGlobal" />
                </div>
              </div>
            </article>

            <article class="fe-card">
              <h3>Fiscalização</h3>
              <div class="fe-body"><div class="fe-field"><label>Nome do fiscal de contratos</label><input v-model="fiscal" placeholder="Digite o nome do fiscal de contratos" /></div></div>
            </article>

            <article class="fe-card">
              <h3>Responsável pelo Termo de Referência</h3>
              <div class="fe-body fe-grid-2">
                <div class="fe-field"><label>Nome do responsável</label><input v-model="responsavel" placeholder="Digite o nome" /></div>
                <div class="fe-field"><label>Cargo/Função</label><input v-model="responsavelCargo" placeholder="Digite o cargo" /></div>
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
                  {{ isSubmitting ? 'Processando com IA...' : 'Gerar Documento com IA' }}
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
          <h3>1. Solicitação / Ofício</h3>
          <div class="fe-body">
            <div class="fe-grid-3">
              <div class="fe-field">
                <label>Tratamento</label>
                <select v-model="tratNome"><option value="">Selecione</option><option v-for="o in tratamentoNome" :key="o" :value="o">{{ o }}</option></select>
              </div>
              <div class="fe-field fe-col-2">
                <label>1.1 A quem é direcionada a solicitação — Nome</label>
                <input v-model="nome" list="dl-solicitacao-destinatario-nome" />
                <div class="fe-inline-actions">
                  <button type="button" class="fe-btn-secondary fe-btn-xs" @click="addFieldHistory('solicitacao_destinatario_nome', nome)">Adicionar</button>
                </div>
              </div>
            </div>
            <div class="fe-grid-3">
              <div class="fe-field">
                <label>Tratamento</label>
                <select v-model="tratCargo"><option value="">Selecione</option><option v-for="o in tratamentoCargo" :key="o" :value="o">{{ o }}</option></select>
              </div>
              <div class="fe-field fe-col-2">
                <label>1.2 A quem é direcionada a solicitação — Função/Cargo</label>
                <input v-model="cargo" list="dl-solicitacao-destinatario-cargo" />
                <div class="fe-inline-actions">
                  <button type="button" class="fe-btn-secondary fe-btn-xs" @click="addFieldHistory('solicitacao_destinatario_cargo', cargo)">Adicionar</button>
                </div>
              </div>
            </div>
            <div class="fe-grid-2">
              <div class="fe-field">
                <label>Nome do responsável</label>
                <input v-model="fixoResponsavel" list="dl-solicitacao-responsavel-nome" placeholder="Digite o nome do responsável" />
                <div class="fe-inline-actions">
                  <button type="button" class="fe-btn-secondary fe-btn-xs" @click="addFieldHistory('solicitacao_responsavel_nome', fixoResponsavel)">Adicionar</button>
                </div>
              </div>
              <div class="fe-field">
                <label>Função / Cargo</label>
                <input v-model="fixoResponsavelCargo" list="dl-solicitacao-responsavel-cargo" placeholder="Digite a função ou cargo" />
                <div class="fe-inline-actions">
                  <button type="button" class="fe-btn-secondary fe-btn-xs" @click="addFieldHistory('solicitacao_responsavel_cargo', fixoResponsavelCargo)">Adicionar</button>
                </div>
              </div>
            </div>
          </div>
        </article>
        <article class="fe-card">
          <h3>2. DFD – Documento de Formalização da Demanda</h3>
          <div class="fe-body">
            <div class="fe-field">
              <label>2.1 Setor requisitante (Unidade / Setor / Departamento)</label>
              <input v-model="fixoSetor" list="dl-dfd-setor-requisitante" />
              <div class="fe-inline-actions">
                <button type="button" class="fe-btn-secondary fe-btn-xs" @click="addFieldHistory('dfd_setor_requisitante', fixoSetor)">Adicionar</button>
              </div>
            </div>
            <div class="fe-field">
              <label>2.2 Responsável pela demanda</label>
              <input v-model="fixoDemanda" list="dl-dfd-responsavel-demanda" />
              <div class="fe-inline-actions">
                <button type="button" class="fe-btn-secondary fe-btn-xs" @click="addFieldHistory('dfd_responsavel_demanda', fixoDemanda)">Adicionar</button>
              </div>
            </div>
            <div class="fe-field">
              <label>2.3 E-mail</label>
              <input v-model="fixoEmail" list="dl-dfd-email" />
              <div class="fe-inline-actions">
                <button type="button" class="fe-btn-secondary fe-btn-xs" @click="addFieldHistory('dfd_email', fixoEmail)">Adicionar</button>
              </div>
            </div>
            <div class="fe-field">
              <label>2.4 Nome do(a) gestor(a) de contratos</label>
              <input v-model="fixoGestor" list="dl-dfd-gestor-contratos" />
              <div class="fe-inline-actions">
                <button type="button" class="fe-btn-secondary fe-btn-xs" @click="addFieldHistory('dfd_gestor_contratos', fixoGestor)">Adicionar</button>
              </div>
            </div>
            <div class="fe-field">
              <label>2.5 Nome do(a) fiscal de contratos</label>
              <input v-model="fixoFiscal" list="dl-dfd-fiscal-contratos" />
              <div class="fe-inline-actions">
                <button type="button" class="fe-btn-secondary fe-btn-xs" @click="addFieldHistory('dfd_fiscal_contratos', fixoFiscal)">Adicionar</button>
              </div>
            </div>
            <div class="fe-grid-2">
              <div class="fe-field">
                <label>Nome do responsável</label>
                <input v-model="fixoAssinatura" list="dl-dfd-assinatura-nome" placeholder="Digite o nome do responsável" />
                <div class="fe-inline-actions">
                  <button type="button" class="fe-btn-secondary fe-btn-xs" @click="addFieldHistory('dfd_assinatura_nome', fixoAssinatura)">Adicionar</button>
                </div>
              </div>
              <div class="fe-field">
                <label>Função / Cargo</label>
                <input v-model="fixoAssinaturaCargo" list="dl-dfd-assinatura-cargo" placeholder="Digite a função ou cargo" />
                <div class="fe-inline-actions">
                  <button type="button" class="fe-btn-secondary fe-btn-xs" @click="addFieldHistory('dfd_assinatura_cargo', fixoAssinaturaCargo)">Adicionar</button>
                </div>
              </div>
            </div>
          </div>
        </article>
      </div>
      <div class="fe-drawer-foot">
        <button type="button" class="fe-btn-primary" @click="onApplyFixedData">Aplicar dados fixos</button>
      </div>
    </aside>

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

const API_BASE = import.meta.dev ? '' : (import.meta.env.VITE_API_URL || 'https://api.docmasteria.com.br');
const dataOptions = ['Data automática', 'Datado e assinado digitalmente', 'Data manual'];
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
const isGeneratingClauses = ref(false);
const iaError = ref('');
const clausulaContratado = ref('');
const clausulaSetor = ref('');
const clausulaCaracteristicas = ref('');
const clausulaObjeto = ref('');
const clausulaJustificativa = ref('');

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
const GLOBAL_SLOT_FORM_PRESET_KEY = 'global_slots_preset_v1';
const SLOT_PACKAGE_KEY = 'inexigibilidade_74_i_fornecedor_exclusivo';
const CATALOG_KEYS = [
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
  const txt = String(v || '');
  const idx = txt.search(/[A-Za-zÀ-ÿ]/);
  if (idx < 0) return txt;
  return txt.slice(0, idx) + txt[idx].toUpperCase() + txt.slice(idx + 1);
}
function formatarMoeda(v) {
  const n = Number(apenasNumeros(v)) / 100;
  return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
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
function formatarCNPJ(v) {
  const n = apenasNumeros(v).slice(0, 14);
  if (n.length <= 2) return n;
  if (n.length <= 5) return `${n.slice(0, 2)}.${n.slice(2)}`;
  if (n.length <= 8) return `${n.slice(0, 2)}.${n.slice(2, 5)}.${n.slice(5)}`;
  if (n.length <= 12) return `${n.slice(0, 2)}.${n.slice(2, 5)}.${n.slice(5, 8)}/${n.slice(8)}`;
  return `${n.slice(0, 2)}.${n.slice(2, 5)}.${n.slice(5, 8)}/${n.slice(8, 12)}-${n.slice(12)}`;
}

function atualizarItem(index, campo, ev) {
  const valorRaw = String(ev.target?.value || '');
  const valor = campo === 'valorUnitario' || campo === 'valorTotal'
    ? formatarMoeda(valorRaw)
    : (campo === 'quantidade' ? valorRaw : iniciarComMaiuscula(valorRaw));
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
function gerarObjetoTexto(contratado, setor, caracteristicas) {
  const objeto = String(contratado || '').trim() || 'objeto não informado';
  const destino = String(setor || '').trim() ? `, visando atender as demandas de ${String(setor).trim()}` : '';
  const detalhes = String(caracteristicas || '').trim() ? `, observadas as seguintes características mínimas: ${String(caracteristicas).trim()}` : '';
  return `${iniciarComMaiuscula(objeto)}${destino}${detalhes}.`;
}
function gerarJustificativaTexto(contratado, setor, caracteristicas) {
  const objeto = String(contratado || '').trim() || 'o objeto indicado';
  const destino = String(setor || '').trim() ? ` do(a) ${String(setor).trim()}` : ' da Administração Pública';
  const detalhes = String(caracteristicas || '').trim() ? ` A contratação deverá observar as características mínimas informadas: ${String(caracteristicas).trim()}.` : '';
  return `A presente contratação justifica-se pela necessidade de assegurar ${objeto} para atendimento das demandas${destino}, garantindo a continuidade e a eficiência dos serviços públicos.${detalhes}`;
}
function parseClauseSections(text) {
  const normalized = String(text || '').replace(/\r/g, '');
  const sections = { objeto: '', justificativa: '' };
  const lines = normalized.split('\n');
  let current = '';
  lines.forEach((line) => {
    const trimmed = line.trim();
    const low = trimmed.toLowerCase().replace(/[*:#-]/g, '').trim();
    if (low.startsWith('objeto')) {
      current = 'objeto';
      const content = trimmed.replace(/^.*?:\s*/, '');
      if (content && content !== trimmed) sections.objeto += (sections.objeto ? '\n' : '') + content;
      return;
    }
    if (low.startsWith('justificativa')) {
      current = 'justificativa';
      const content = trimmed.replace(/^.*?:\s*/, '');
      if (content && content !== trimmed) sections.justificativa += (sections.justificativa ? '\n' : '') + content;
      return;
    }
    if (current) sections[current] += (sections[current] ? '\n' : '') + trimmed;
  });
  return sections;
}
async function onGenerateClauses() {
  isGeneratingClauses.value = true;
  iaError.value = '';
  try {
    const contratado = String(clausulaContratado.value || '').trim();
    const setor = String(clausulaSetor.value || '').trim();
    const caracteristicas = String(clausulaCaracteristicas.value || '').trim();
    if (!contratado || !setor) {
      iaError.value = 'Preencha "O que será contratado?" e "Qual setor/secretaria será atendido?".';
      return;
    }
    const prompt = [
      'Com base EXCLUSIVAMENTE nos dados abaixo, gere APENAS duas seções:',
      'Objeto:',
      'Justificativa:',
      '',
      `O que será contratado: ${contratado}`,
      `Setor/secretaria atendido: ${setor}`,
      `Características mínimas (opcional): ${caracteristicas || 'não informado'}`,
    ].join('\n');
    const res = await fetch(`${API_BASE}/api/llm/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ prompt, stream: false }),
    });
    const data = await res.json().catch(() => ({}));
    const text = data?.data?.response || data?.data?.text || data?.response || data?.text || '';
    if (!res.ok || !data?.ok) {
      iaError.value = data?.error || data?.detail || `Erro ${res.status} ao gerar objeto e justificativa.`;
      clausulaObjeto.value = gerarObjetoTexto(contratado, setor, caracteristicas);
      clausulaJustificativa.value = gerarJustificativaTexto(contratado, setor, caracteristicas);
      return;
    }
    const parsed = parseClauseSections(text);
    clausulaObjeto.value = parsed.objeto || gerarObjetoTexto(contratado, setor, caracteristicas);
    clausulaJustificativa.value = parsed.justificativa || gerarJustificativaTexto(contratado, setor, caracteristicas);
  } catch (e) {
    clausulaObjeto.value = gerarObjetoTexto(clausulaContratado.value, clausulaSetor.value, clausulaCaracteristicas.value);
    clausulaJustificativa.value = gerarJustificativaTexto(clausulaContratado.value, clausulaSetor.value, clausulaCaracteristicas.value);
    iaError.value = e?.message || 'Não foi possível gerar via IA; aplicamos texto base.';
  } finally {
    isGeneratingClauses.value = false;
  }
}
function collectGlobalFormStatePayload() {
  return {
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
  if ('solicitacao_destinatario_nome' in data) nome.value = String(data.solicitacao_destinatario_nome || '');
  if ('solicitacao_destinatario_cargo' in data) cargo.value = String(data.solicitacao_destinatario_cargo || '');
  if ('solicitacao_responsavel_nome' in data) fixoResponsavel.value = String(data.solicitacao_responsavel_nome || '');
  if ('solicitacao_responsavel_cargo' in data) fixoResponsavelCargo.value = String(data.solicitacao_responsavel_cargo || '');
  if ('dfd_setor_requisitante' in data) fixoSetor.value = String(data.dfd_setor_requisitante || '');
  if ('dfd_responsavel_demanda' in data) fixoDemanda.value = String(data.dfd_responsavel_demanda || '');
  if ('dfd_email' in data) fixoEmail.value = String(data.dfd_email || '');
  if ('dfd_gestor_contratos' in data) fixoGestor.value = String(data.dfd_gestor_contratos || '');
  if ('dfd_fiscal_contratos' in data) fixoFiscal.value = String(data.dfd_fiscal_contratos || '');
  if ('dfd_assinatura_nome' in data) fixoAssinatura.value = String(data.dfd_assinatura_nome || '');
  if ('dfd_assinatura_cargo' in data) fixoAssinaturaCargo.value = String(data.dfd_assinatura_cargo || '');
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
    secretaria_usuario: String((fixoSetor.value || orgao.value || '').trim()),
    dfd_setor_requisitante: String((fixoSetor.value || orgao.value || '').trim()),
    dfd_responsavel_demanda: String(fixoDemanda.value || '').trim(),
    dfd_email: String(fixoEmail.value || '').trim(),
    dfd_gestor_contratos: String(fixoGestor.value || '').trim(),
    dfd_fiscal_contratos: String((fixoFiscal.value || fiscal.value || '').trim()),
    dfd_assinatura_nome: String(fixoAssinatura.value || '').trim(),
    dfd_assinatura_cargo: String(fixoAssinaturaCargo.value || '').trim(),
  };
  if (clausulaObjeto.value.trim()) {
    o.objeto = clausulaObjeto.value.trim();
    o.sol_oficio_objeto = clausulaObjeto.value.trim();
  }
  if (clausulaJustificativa.value.trim()) {
    o.justificativa = clausulaJustificativa.value.trim();
    o.sol_oficio_justificativa = clausulaJustificativa.value.trim();
  }
  if (dotacaoAtiva.value && String(dotacao.value || '').trim()) o.dotacao_numero = String(dotacao.value || '').trim();
  const modo = String(modoData.value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
  if (modo === 'data automatica') {
    const now = new Date();
    o.data_termo = `${String(now.getDate()).padStart(2, '0')}/${String(now.getMonth() + 1).padStart(2, '0')}/${now.getFullYear()}`;
  } else if (modo === 'data manual' && dataManual.value.trim()) {
    o.data_termo = dataManual.value.trim();
  } else if (modo === 'datado e assinado digitalmente') {
    o.data_termo = 'datado e assinado digitalmente';
  }
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
    const res = await fetch(`${API_BASE}/api/documentos/gerar-tr-e-dfd`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.ok) {
      generateError.value = data.error || data.detail || `Erro ${res.status} ao gerar documento.`;
      return;
    }
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
.fe-actions { display: grid; gap: 8px; }
.fe-btn-generate { font-weight: 700; letter-spacing: .2px; }
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
