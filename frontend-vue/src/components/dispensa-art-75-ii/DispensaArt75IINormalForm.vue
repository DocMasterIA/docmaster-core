<template>
  <div class="da75-page">
    <div class="da75-page__inner">
      <div class="da75-grid-main da75-mt">
        <section class="da75-panel">
          <div class="da75-panel__head">
            <div>
              <span class="da75-badge">Módulo ativo</span>
              <h2>Este módulo gera Solicitação/Ofício, DFD e Termo de Referência</h2>
            </div>
            <button type="button" class="da75-btn" @click="drawerAberto = true">Dados fixos</button>
          </div>

          <div class="da75-panel__body">
            <section class="da75-block da75-block--muted">
              <h3>Dados básicos</h3>
              <div class="da75-block__body">
                <div class="da75-row da75-row--basic">
                  <div class="da75-field">
                    <label class="da75-label da75-label--compact">Cabeçalho do documento</label>
                    <select v-model="cabecalho" class="da75-select da75-select--sm" :disabled="cabecalhosLoading">
                      <option value="">{{ cabecalhosLoading ? 'Carregando…' : 'Selecione' }}</option>
                      <option v-for="op in cabecalhoOptions" :key="op.id" :value="op.name">{{ op.name }}</option>
                    </select>
                    <p v-if="!cabecalhosLoading && cabecalhoOptions.length === 0" class="da75-helper da75-mt-sm">
                      Nenhum modelo na biblioteca para a sua prefeitura.
                      <router-link to="/biblioteca" class="da75-inline-link">Abrir biblioteca</router-link>
                    </p>
                  </div>
                  <div class="da75-field">
                    <label class="da75-label da75-label--compact">Órgão / unidade</label>
                    <input
                      v-model="orgao"
                      class="da75-input da75-input--sm"
                      list="da75-dl-orgao"
                      placeholder="Selecione ou digite o órgão"
                    />
                  </div>
                  <label class="da75-check da75-check--inline">
                    <input v-model="processoAtivo" type="checkbox" />
                    Processo (opcional)
                  </label>
                </div>
                <div v-if="processoAtivo" class="da75-max-xs da75-mt">
                  <label class="da75-label">Número do processo (opcional)</label>
                  <input
                    class="da75-input"
                    :value="processo"
                    list="da75-dl-processo-numero"
                    @input="processo = primeiraMaiuscula(($event.target).value)"
                  />
                </div>
              </div>
            </section>

            <section class="da75-block">
              <h3>Objeto da contratação e justificativa</h3>
              <div class="da75-block__body">
                <div class="da75-two-col">
                  <div class="da75-stack">
                    <div class="da75-field">
                      <label class="da75-label">O que será contratado?</label>
                      <textarea
                        class="da75-textarea"
                        :value="objetoContratado"
                        :placeholder="normalPhObjeto"
                        @input="objetoContratado = primeiraMaiuscula(($event.target).value)"
                      />
                    </div>
                    <div class="da75-field">
                      <label class="da75-label">Qual setor/secretaria será atendido?</label>
                      <input
                        class="da75-input"
                        :value="objetoSetor"
                        :placeholder="normalPhSetor"
                        @input="objetoSetor = primeiraMaiuscula(($event.target).value)"
                      />
                    </div>
                    <div class="da75-field">
                      <label class="da75-label">Características mínimas obrigatórias (opcional)</label>
                      <textarea
                        class="da75-textarea"
                        :value="objetoCaracteristicas"
                        :placeholder="normalPhCaracteristicas"
                        @input="objetoCaracteristicas = primeiraMaiuscula(($event.target).value)"
                      />
                    </div>
                    <button type="button" class="da75-btn da75-btn--primary da75-btn--block" :disabled="isGerandoClausulas" @click="gerar">
                      Gerar objeto e justificativa
                    </button>
                    <DocGenIaLoaderBlock
                      v-if="isGerandoClausulas"
                      compact
                      message="Gerando objeto e justificativa…"
                    />
                    <p v-if="erroGeracaoClausulas" class="da75-helper">{{ erroGeracaoClausulas }}</p>
                  </div>
                  <div class="da75-stack">
                    <div class="da75-field">
                      <label class="da75-label">Objeto gerado pela IA</label>
                      <textarea
                        class="da75-textarea"
                        rows="5"
                        :value="objetoGerado"
                        @input="objetoGerado = primeiraMaiuscula(($event.target).value)"
                      />
                    </div>
                    <div class="da75-field">
                      <label class="da75-label">Justificativa da contratação</label>
                      <textarea
                        class="da75-textarea"
                        rows="5"
                        :value="justificativa"
                        @input="justificativa = primeiraMaiuscula(($event.target).value)"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <DispensaArt75IIItensValores v-model="itens" />

            <DotacaoOrcamentariaBlock
              v-model:dotacao-ativa="dotacaoAtiva"
              v-model:dotacao="dotacao"
              :api-base="API_BASE"
              variant="da75"
              wrapper="section"
            />

            <section class="da75-block">
              <h3>Data</h3>
              <div class="da75-block__body">
                <div class="da75-row da75-row--2">
                  <div class="da75-field">
                    <label class="da75-label">Modo da data</label>
                    <select class="da75-select" :value="modoData" @change="onModoData(($event.target).value)">
                      <option value="">Selecione</option>
                      <option v-for="o in DATA_OPTIONS" :key="o" :value="o">{{ o }}</option>
                    </select>
                  </div>
                  <div v-if="modoData === 'Data manual'" class="da75-field">
                    <label class="da75-label">Data manual</label>
                    <input
                      class="da75-input"
                      :value="dataManual"
                      @input="dataManual = formatarData(($event.target).value)"
                    />
                  </div>
                </div>
              </div>
            </section>


            <div class="da75-space-y">
              <button
                type="button"
                class="da75-btn da75-btn--primary"
                :disabled="isSubmitting || !podeGerarDocumentos"
                @click="onSubmit"
              >
                Gerar documento com IA
              </button>
              <DocGenIaLoaderBlock v-if="isSubmitting" message="Gerando documentos…" />
              <p v-if="generateError" class="da75-helper">{{ generateError }}</p>
              <p v-if="successMessage" class="da75-helper">{{ successMessage }}</p>
              <div v-if="documentReady" class="da75-inline-actions">
                <a v-if="documentTrUrl" :href="documentTrUrl" :download="documentTrFilename" class="da75-btn">Download TR</a>
                <a v-if="documentDfdUrl" :href="documentDfdUrl" :download="documentDfdFilename" class="da75-btn">Download DFD</a>
                <a v-if="documentOficioUrl" :href="documentOficioUrl" :download="documentOficioFilename" class="da75-btn">Download Ofício</a>
                <a v-if="documentZipUrl" :href="documentZipUrl" :download="documentZipFilename" class="da75-btn">Download ZIP</a>
              </div>
            </div>
          </div>
        </section>

        <DispensaArt75IIDadosFixosDrawer
          :open="drawerAberto"
          :ctx="dadosFixos"
          @close="drawerAberto = false"
          @apply="onApplyDadosFixos"
        />

        <datalist id="da75-dl-orgao">
          <option v-for="v in (dadosFixos.mergedOrgaoOptions || [])" :key="`o-${v}`" :value="v" />
        </datalist>
        <datalist id="da75-dl-processo-numero">
          <option v-for="v in (dadosFixos.slotFieldOptions.processo_numero || [])" :key="`p-${v}`" :value="v" />
        </datalist>

        <aside class="da75-resumo">
          <div class="da75-resumo__head">
            <div>
              <div class="da75-resumo__kicker">Resumo em tempo real</div>
              <h3 class="da75-resumo__panel-title">Painel do documento</h3>
            </div>
            <div class="da75-resumo__pct">{{ progresso }}%</div>
          </div>
          <div class="da75-progress">
            <div class="da75-progress__bar" :style="{ width: `${progresso}%` }" />
          </div>
          <div class="da75-resumo__meta">
            {{ completos }} de {{ secoes.length }} blocos preenchidos
          </div>
          <div class="da75-resumo__secoes">
            <div v-for="secao in secoes" :key="secao.titulo" class="da75-secao">
              <div class="da75-secao__title">
                <span>{{ secao.titulo }}</span>
                <span :class="secao.completo ? 'da75-ok' : 'da75-warn'">{{ secao.completo ? '✓' : '!' }}</span>
              </div>
              <div class="da75-space-y da75-mt-sm">
                <div
                  v-for="[rotulo, valor, preenchido] in secao.linhas"
                  :key="rotulo"
                  class="da75-linha"
                  :class="preenchido ? 'da75-linha--ok' : 'da75-linha--no'"
                >
                  <span>{{ rotulo }}</span>
                  <span>{{ valor }}</span>
                </div>
              </div>
            </div>
          </div>

          <div class="da75-itens-lista">
            <div class="da75-itens-lista__title">Itens lançados</div>
            <div class="da75-mt-sm">
              <template v-if="itensValidos.length > 0">
                <div v-for="(item, index) in itensValidos" :key="index" class="da75-mini-item">
                  <strong>Item {{ index + 1 }}</strong>
                  <div>{{ item.descricao || 'Sem descrição' }}</div>
                  <div>Qtd: {{ item.quantidade || '-' }}</div>
                  <div>Unidade de medida: {{ item.unidade || '-' }}</div>
                  <div>Média de valor (opcional): {{ item.mediaValor || '-' }}</div>
                </div>
              </template>
              <div v-else class="da75-resumo__empty">Nenhum item preenchido ainda.</div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import {
  DATA_OPTIONS,
  EMPTY_ITEM,
  calcularValorTotalEstimado,
  campoPreenchido,
  formatarData,
  moedaParaNumero,
  quantidadeParaNumero,
  primeiraMaiuscula,
  stripDeprecatedCargoSlotsOverride,
  applyDfdSetorRequisitanteToSlotsOverride,
} from './dispensaArt75iiShared.js';
import './dispensaArt75ii.css';
import DispensaArt75IIDadosFixosDrawer from './DispensaArt75IIDadosFixosDrawer.vue';
import DocGenIaLoaderBlock from '@/components/DocGenIaLoaderBlock.vue';
import DispensaArt75IIItensValores from './DispensaArt75IIItensValores.vue';
import DotacaoOrcamentariaBlock from '@/components/DotacaoOrcamentariaBlock.vue';
import { fetchCabecalhosPrefeitura } from '@/utils/fetchCabecalhosPrefeitura.js';
import { buildGerarTrEDfdUrl, getApiBase } from '@/utils/apiBase.js';
import { buildClausulasObjetoJustificativaPrompt } from '@/utils/clausulasObjetoJustificativa.js';
import {
  buildFillTrSlotsUrl,
  describeFillTrSlotsNetworkFailure,
  fetchFillTrSlotsWithRetry,
} from '@/utils/fetchFillTrSlots.js';
import { describeGerarTrEDfdNetworkFailure, fetchGerarTrEDfdWithRetry } from '@/utils/fetchGerarTrEDfd.js';
import { trimMultilinePreserve } from '@/utils/itemValorCampos.js';
import {
  applyUsuarioLocalidadeToSlots,
  fetchUsuarioLocalidadeParaTr,
} from '@/utils/usuarioLocalidadeSlots.js';
import { useDispensaArt75IIDadosFixos } from '@/composables/useDispensaArt75IIDadosFixos.js';

const API_BASE = getApiBase();
const route = useRoute();

const drawerAberto = ref(false);
const cabecalhoOptions = ref([]);
const cabecalhosLoading = ref(false);
const cabecalho = ref('');
const processoAtivo = ref(false);
const processo = ref('');
const orgao = ref('');
const dadosFixos = useDispensaArt75IIDadosFixos(API_BASE, { cabecalho, processoAtivo, processo, orgao });
const objetoContratado = ref('');
const objetoSetor = ref('');
const objetoCaracteristicas = ref('');
const objetoGerado = ref('');
const justificativa = ref('');
const itens = ref([{ ...EMPTY_ITEM }]);
const dotacaoAtiva = ref(false);
const dotacao = ref('');
/** Município + UF do /api/me para linha de assinatura do TR. */
const usuarioLocalidade = ref(null);
const modoData = ref('');
const dataManual = ref('');
const isGerandoClausulas = ref(false);
const erroGeracaoClausulas = ref('');
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

const SLOT_PACKAGE_BY_ROUTE = {
  DispensaArt75IObrasEngenharia: 'dispensa_75_i_obras_engenharia',
  DispensaArt75IManutencaoVeiculos: 'dispensa_75_i_manutencao_veiculos',
  DispensaArt75IICompras: 'dispensa_75_ii_compras',
  DispensaArt75IIServicos: 'dispensa_75_ii_servicos',
  DispensaArt75IIComprasServicosInclusos: 'dispensa_75_ii_compras_servicos_inclusos',
};
/** Mesmo componente em várias rotas — ao mudar de modalidade, não manter rascunho da página anterior. */
const DISPENSA_ART75_II_NORMAL_SHARED_ROUTES = new Set(Object.keys(SLOT_PACKAGE_BY_ROUTE));
const slotPackageKey = computed(() => SLOT_PACKAGE_BY_ROUTE[String(route.name || '')] || 'tr_dfd_generico');

/** Exemplos por modalidade (dispensa normal — objeto / setor / características). */
const NORMAL_OBJ_EXAMPLES = {
  DispensaArt75IObrasEngenharia: {
    objeto: 'Ex: Reforma do prédio da prefeitura, incluindo fornecimento de materiais e mão de obra',
    setor: 'Ex: Secretaria Municipal de Obras e Urbanismo',
    caracteristicas: 'Ex: Cronograma físico-financeiro em anexo ao processo (opcional)',
  },
  DispensaArt75IManutencaoVeiculos: {
    objeto: 'Ex: Prestação de serviços com reparo no módulo de injeção eletrônica',
    setor: 'Ex: Frota oficial da Prefeitura',
    caracteristicas: 'Ex: Peças com garantia mínima de 90 dias (opcional)',
  },
  DispensaArt75IICompras: {
    objeto: 'Ex: Aquisição de medicamentos',
    setor: 'Ex: UBS Leontino',
    caracteristicas: 'Ex: Para doação à população carente',
  },
  DispensaArt75IIServicos: {
    objeto: 'Ex: Prestação de serviços de limpeza e conservação predial',
    setor: 'Ex: Prédios públicos municipais',
    caracteristicas: 'Ex: Com fornecimento de materiais de limpeza',
  },
  DispensaArt75IIComprasServicosInclusos: {
    objeto: 'Ex: Aquisição de playground infantil com instalação',
    setor: 'Ex: Secretaria Municipal de Assistência Social',
    caracteristicas: 'Ex: Para recreação das crianças',
  },
};

const normalPhTrio = computed(() => {
  const n = String(route.name || '');
  return (
    NORMAL_OBJ_EXAMPLES[n] || {
      objeto: 'Ex: Descreva o objeto da contratação',
      setor: 'Ex: Setor ou secretaria atendida',
      caracteristicas: 'Ex: Requisitos ou observações (opcional)',
    }
  );
});

const normalPhObjeto = computed(() => normalPhTrio.value.objeto);
const normalPhSetor = computed(() => normalPhTrio.value.setor);
const normalPhCaracteristicas = computed(() => normalPhTrio.value.caracteristicas);

function resolveSolOficioFundamentoLegal(routeName) {
  const name = String(routeName || '').trim();
  if (!name) return '';
  if (name.includes('Art75II')) return 'Art. 75, Inciso II, da Lei no 14.133/2021';
  if (name.includes('Art75I')) return 'Art. 75, Inciso I, da Lei no 14.133/2021';
  return '';
}

const cabecalhoMergeTemplateId = computed(() => {
  const n = String(cabecalho.value || '').trim();
  if (!n) return null;
  const hit = cabecalhoOptions.value.find((o) => o.name === n);
  return hit?.id ? String(hit.id) : null;
});

async function reloadPresetCabecalhosOrgao() {
  await dadosFixos.loadOrgaoProfiles();
  await dadosFixos.loadUserGlobalPreset();
  await dadosFixos.loadSlotCatalogSuggestions();
  usuarioLocalidade.value = await fetchUsuarioLocalidadeParaTr(API_BASE);
  cabecalhosLoading.value = true;
  try {
    const opts = await fetchCabecalhosPrefeitura(API_BASE);
    cabecalhoOptions.value = opts;
    if (cabecalho.value && !opts.some((o) => o.name === cabecalho.value)) cabecalho.value = '';
  } finally {
    cabecalhosLoading.value = false;
  }
}

async function resetFormStateForNewRoute() {
  revokeDocumentUrls();
  drawerAberto.value = false;
  cabecalho.value = '';
  processoAtivo.value = false;
  processo.value = '';
  orgao.value = '';
  objetoContratado.value = '';
  objetoSetor.value = '';
  objetoCaracteristicas.value = '';
  objetoGerado.value = '';
  justificativa.value = '';
  itens.value = [{ ...EMPTY_ITEM }];
  dotacaoAtiva.value = false;
  dotacao.value = '';
  modoData.value = '';
  dataManual.value = '';
  isGerandoClausulas.value = false;
  erroGeracaoClausulas.value = '';
  isSubmitting.value = false;
  generateError.value = '';
  successMessage.value = '';
  documentReady.value = false;
  documentTrFilename.value = 'termo_referencia.docx';
  documentDfdFilename.value = 'dfd.docx';
  documentOficioFilename.value = 'oficio.docx';
  documentZipFilename.value = 'tr_dfd_oficio.zip';
  dadosFixos.selectedOrgaoProfileId = '';
  dadosFixos.orgaoProfileName = '';
  dadosFixos.clearDadosFixosFields();
  await reloadPresetCabecalhosOrgao();
}

onMounted(async () => {
  await reloadPresetCabecalhosOrgao();
});

watch(
  () => route.name,
  async (name, prev) => {
    if (prev === undefined) return;
    const n = String(name || '');
    const p = String(prev || '');
    if (n === p) return;
    if (!DISPENSA_ART75_II_NORMAL_SHARED_ROUTES.has(n) || !DISPENSA_ART75_II_NORMAL_SHARED_ROUTES.has(p)) return;
    await resetFormStateForNewRoute();
  },
);

watch(dotacaoAtiva, (v) => {
  if (!v) dotacao.value = '';
});

async function onApplyDadosFixos() {
  drawerAberto.value = false;
  isSubmitting.value = false;
  try {
    await dadosFixos.saveUserGlobalPreset();
  } catch {
    // silencioso
  }
}

const objetoPrompt = computed(() =>
  [objetoContratado.value, objetoSetor.value, objetoCaracteristicas.value].filter(campoPreenchido).join(' | '),
);

const dataResumo = computed(() => (modoData.value === 'Data manual' ? dataManual.value : modoData.value));

const itensValidos = computed(() =>
  itens.value.filter((item) => Object.values(item).some((v) => campoPreenchido(v))),
);

const secoes = computed(() => {
  const orgaoLabel = orgao.value || '';
  return [
    {
      titulo: 'Dados básicos',
      completo:
        campoPreenchido(cabecalho.value) &&
        campoPreenchido(orgaoLabel) &&
        (!processoAtivo.value || campoPreenchido(processo.value)),
      linhas: [
        ['Cabeçalho', cabecalho.value || 'Não informado', campoPreenchido(cabecalho.value)],
        ['Órgão', orgaoLabel || 'Não informado', campoPreenchido(orgaoLabel)],
        [
          'Processo',
          processoAtivo.value ? processo.value || 'Não informado' : 'Não se aplica',
          !processoAtivo.value || campoPreenchido(processo.value),
        ],
      ],
    },
    {
      titulo: 'Objeto e justificativa',
      completo:
        campoPreenchido(objetoPrompt.value) &&
        campoPreenchido(objetoGerado.value) &&
        campoPreenchido(justificativa.value),
      linhas: [
        ['Informações base', objetoPrompt.value || 'Não informado', campoPreenchido(objetoPrompt.value)],
        ['Objeto gerado', objetoGerado.value || 'Não informado', campoPreenchido(objetoGerado.value)],
        ['Justificativa', justificativa.value || 'Não informada', campoPreenchido(justificativa.value)],
      ],
    },
    {
      titulo: 'Itens e valores',
      completo: itensValidos.value.length > 0,
      linhas: [
        ['Itens lançados', String(itensValidos.value.length), itensValidos.value.length > 0],
        ['Valor total estimado', calcularValorTotalEstimado(itens.value), itensValidos.value.length > 0],
      ],
    },
    {
      titulo: 'Dotação orçamentária',
      completo: !dotacaoAtiva.value || campoPreenchido(dotacao.value),
      linhas: [
        ['Situação', dotacaoAtiva.value ? 'Informar dotação' : 'Não informada', true],
        ['Dotação', dotacaoAtiva.value ? dotacao.value || 'Não informada' : 'Não se aplica', !dotacaoAtiva.value || campoPreenchido(dotacao.value)],
      ],
    },
    {
      titulo: 'Data',
      completo: campoPreenchido(dataResumo.value),
      linhas: [['Data / modo', dataResumo.value || 'Não informada', campoPreenchido(dataResumo.value)]],
    },
  ];
});

const completos = computed(() => secoes.value.filter((s) => s.completo).length);
const progresso = computed(() => Math.round((completos.value / secoes.value.length) * 100));
const podeGerarDocumentos = computed(() => secoes.value.every((s) => s.completo));

/** Igual à rápida: tira rascunho de cláusulas e itens da tabela (itens só vão no gerar-tr-e-dfd). */
function slotsOverrideWithoutClauseDraft(raw) {
  if (!raw || typeof raw !== 'object') return raw;
  const o = { ...raw };
  delete o.objeto;
  delete o.justificativa;
  delete o.sol_oficio_objeto;
  delete o.sol_oficio_justificativa;
  delete o.itens;
  delete o.valor_total;
  return stripDeprecatedCargoSlotsOverride(o);
}

/** Só os campos do bloco «Objeto da contratação» — sem Dados básicos, dados fixos ou tabela de itens. */
function buildSlotsOverrideForGerarClausulas() {
  const setor = String(objetoSetor.value || '').trim();
  const o = { dispensa_fluxo_ui: 'normal' };
  if (setor) o.dfd_setor_requisitante = setor;
  return o;
}

function buildUserPromptGerarClausulas() {
  const car = String(objetoCaracteristicas.value || '').trim();
  return [
    `O que será contratado: ${objetoContratado.value}`,
    `Setor/secretaria atendido: ${objetoSetor.value}`,
    car ? `Características mínimas: ${car}` : '',
  ]
    .filter(Boolean)
    .join('\n');
}

async function gerar() {
  erroGeracaoClausulas.value = '';
  const contratado = String(objetoContratado.value || '').trim();
  const setor = String(objetoSetor.value || '').trim();
  if (!contratado || !setor) {
    erroGeracaoClausulas.value = 'Preencha "O que será contratado?" e "Qual setor/secretaria será atendido?".';
    return;
  }

  objetoGerado.value = '';
  justificativa.value = '';
  isGerandoClausulas.value = true;
  const fillUrl = buildFillTrSlotsUrl(API_BASE);
  try {
    const result = await fetchFillTrSlotsWithRetry(
      API_BASE,
      {
        user_prompt: buildUserPromptGerarClausulas(),
        slots_override: buildSlotsOverrideForGerarClausulas(),
        slot_package_key: slotPackageKey.value,
      },
      { maxAttempts: 1 },
    );
    if (!result.ok) {
      if (result.kind === 'network') {
        const m = String(result.errorMessage || '');
        const looksNetwork = /fetch|network|failed|load|aborted|timed out|timeout/i.test(m);
        throw new Error(
          looksNetwork ? describeFillTrSlotsNetworkFailure(fillUrl) : m || describeFillTrSlotsNetworkFailure(fillUrl),
        );
      }
      throw new Error(result.errorMessage || 'Erro ao preencher objeto/justificativa.');
    }
    const slots = result.data.slots && typeof result.data.slots === 'object' ? result.data.slots : {};
    const obj = String(slots.objeto || '').trim();
    const jus = String(slots.justificativa || '').trim();
    if (!obj || !jus) {
      throw new Error('IA não retornou objeto/justificativa completos.');
    }
    objetoGerado.value = obj;
    justificativa.value = jus;
  } catch (err) {
    const msg = String(err?.message || '');
    const looksNet =
      err?.name === 'TypeError' || /failed to fetch|load failed|networkerror|err_failed/i.test(msg);
    erroGeracaoClausulas.value = looksNet ? describeFillTrSlotsNetworkFailure(fillUrl) : msg || 'Falha ao gerar cláusulas.';
  } finally {
    isGerandoClausulas.value = false;
  }
}

function onModoData(valor) {
  modoData.value = valor;
  if (valor !== 'Data manual') dataManual.value = '';
}

function toBlobUrl(base64, mimeType) {
  if (!base64) return '';
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return URL.createObjectURL(new Blob([bytes], { type: mimeType }));
}

function revokeDocumentUrls() {
  if (documentTrUrl.value) URL.revokeObjectURL(documentTrUrl.value);
  if (documentDfdUrl.value) URL.revokeObjectURL(documentDfdUrl.value);
  if (documentOficioUrl.value) URL.revokeObjectURL(documentOficioUrl.value);
  if (documentZipUrl.value) URL.revokeObjectURL(documentZipUrl.value);
  documentTrUrl.value = '';
  documentDfdUrl.value = '';
  documentOficioUrl.value = '';
  documentZipUrl.value = '';
}

function formatCurrencyBr(value) {
  const n = Number(value || 0);
  return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function buildSlotsOverride() {
  const o = {};
  applyUsuarioLocalidadeToSlots(o, usuarioLocalidade.value);
  o.dispensa_fluxo_ui = 'normal';
  const destNome = trimMultilinePreserve(dadosFixos.fixoNome || '');
  const respNome = trimMultilinePreserve(dadosFixos.fixoResponsavel || '');
  const tratNome = String(dadosFixos.fixoTratNome || '').trim();
  if (destNome) o.sol_oficio_destinatario_nome = destNome;
  if (respNome) o.sol_oficio_responsavel_nome = respNome;
  if (tratNome) o.ao_senhor_genero = tratNome;
  const setorFormulario = String(objetoSetor.value || '').trim();
  if (setorFormulario) {
    o.dfd_setor_requisitante = setorFormulario;
  } else {
    applyDfdSetorRequisitanteToSlotsOverride(o, dadosFixos);
  }
  if (String(dadosFixos.fixoDemanda || '').trim()) o.dfd_responsavel_demanda = String(dadosFixos.fixoDemanda).trim();
  if (String(dadosFixos.fixoEmail || '').trim()) o.dfd_email = String(dadosFixos.fixoEmail).trim();
  if (String(dadosFixos.fixoGestor || '').trim()) o.dfd_gestor_contratos = String(dadosFixos.fixoGestor).trim();
  if (String(dadosFixos.fixoFiscal || '').trim()) {
    const fn = String(dadosFixos.fixoFiscal).trim();
    o.dfd_fiscal_contratos = fn;
    o.fiscal = { nome: fn };
  }
  if (trimMultilinePreserve(dadosFixos.fixoAssinatura || '')) {
    o.dfd_assinatura_nome = trimMultilinePreserve(dadosFixos.fixoAssinatura);
  }
  if (processoAtivo.value && String(processo.value || '').trim()) {
    const np = String(processo.value).trim();
    o.numero_processo = np;
    o.dfd_numero_processo = np;
  }
  if (String(dadosFixos.fixoEnderecoEntrega || '').trim()) o.endereco_entrega = String(dadosFixos.fixoEnderecoEntrega).trim();
  if (String(dadosFixos.fixoEmailPropostas || '').trim()) o.email_envio_propostas = String(dadosFixos.fixoEmailPropostas).trim();
  const trRespNome = trimMultilinePreserve(dadosFixos.fixoTrResponsavelNome || '');
  if (trRespNome) o.nome_assinante_termo = trRespNome;
  if (dotacaoAtiva.value && String(dotacao.value || '').trim()) {
    const dotacaoTexto = String(dotacao.value).trim();
    o.dotacao = dotacaoTexto;
    o.objeto_resultados = `Dotação orçamentária: ${dotacaoTexto}`;
  }
  const modoNormalizado = String(modoData.value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
  let dataTermo = '';
  if (modoNormalizado === 'data automatica') {
    const now = new Date();
    dataTermo = `${String(now.getDate()).padStart(2, '0')}/${String(now.getMonth() + 1).padStart(2, '0')}/${now.getFullYear()}`;
  } else if (modoNormalizado === 'data manual') {
    const manual = String(dataManual.value || '').trim();
    if (manual) dataTermo = manual;
  }
  if (modoNormalizado === 'datado e assinado digitalmente') {
    dataTermo = 'datado e assinado digitalmente';
  }
  if (dataTermo) o.data_termo = dataTermo;
  const objetoFinal = String(objetoGerado.value || objetoContratado.value || '').trim();
  if (objetoFinal) o.objeto = objetoFinal;
  const brutoContratado = String(objetoContratado.value || '').trim();
  if (brutoContratado) o.objeto_contratado_bruto = brutoContratado;
  if (String(justificativa.value || '').trim()) o.justificativa = String(justificativa.value).trim();
  const itensOverride = itens.value
    .filter((item) => Object.values(item).some((v) => campoPreenchido(v)))
    .map((item) => {
      const qtd = quantidadeParaNumero(item.quantidade);
      const unit = moedaParaNumero(item.mediaValor);
      return {
        descricao: String(item.descricao || '').trim(),
        quantidade: String(item.quantidade || '').trim(),
        unidade: String(item.unidade || '').trim(),
        valor_unitario: String(item.mediaValor || '').trim(),
        valor_total: formatCurrencyBr(qtd * unit),
      };
    });
  if (itensOverride.length) {
    o.itens = itensOverride;
    const total = itensOverride.reduce((acc, item) => acc + moedaParaNumero(item.valor_total), 0);
    o.valor_total = formatCurrencyBr(total);
  }
  const fundamentoLegal = resolveSolOficioFundamentoLegal(String(route.name || ''));
  if (fundamentoLegal) o.sol_oficio_artigo_inciso = fundamentoLegal;
  return stripDeprecatedCargoSlotsOverride(o);
}

function buildUserPrompt() {
  const contratadoBlock = buildClausulasObjetoJustificativaPrompt({
    contratado: objetoContratado.value,
    caracteristicas: objetoCaracteristicas.value,
    variant: 'dispensa_normal',
  });
  return [
    `Gerar documento com base nos dados preenchidos para ${String(route.meta?.title || 'dispensa normal')}.`,
    contratadoBlock,
    objetoSetor.value.trim() ? `Setor/secretaria atendido: ${objetoSetor.value.trim()}` : '',
    'Em objeto e justificativa não liste nem discuta itens da tabela (descrições, quantidades, valores); mantenha texto genérico.',
  ]
    .filter(Boolean)
    .join('\n');
}

function sanitizeJsonBody(obj) {
  try {
    return JSON.parse(JSON.stringify(obj));
  } catch {
    return null;
  }
}

async function onSubmit() {
  if (isSubmitting.value) return;
  generateError.value = '';
  successMessage.value = '';
  documentReady.value = false;
  revokeDocumentUrls();
  const pendente = secoes.value.find((s) => !s.completo);
  if (pendente) {
    generateError.value = `Preencha todos os campos obrigatórios em «${pendente.titulo}» antes de gerar os documentos.`;
    return;
  }
  const payload = {
    user_prompt: buildUserPrompt(),
    slots_override: buildSlotsOverride(),
    slot_package_key: slotPackageKey.value,
  };
  if (cabecalhoMergeTemplateId.value) payload.template_id = cabecalhoMergeTemplateId.value;
  const bodyObj = sanitizeJsonBody(payload);
  if (!bodyObj) {
    generateError.value = 'Não foi possível preparar os dados para envio. Verifique os campos (especialmente itens e valores).';
    return;
  }
  isSubmitting.value = true;
  let presetSaveAfterSuccess = false;
  try {
    const gerarUrl = buildGerarTrEDfdUrl(API_BASE);
    const result = await fetchGerarTrEDfdWithRetry(API_BASE, bodyObj);
    if (!result.ok) {
      if (result.kind === 'network') {
        const msg = String(result.errorMessage || '');
        generateError.value =
          /fetch|network|failed|load|aborted|timed out|timeout/i.test(msg)
            ? describeGerarTrEDfdNetworkFailure(gerarUrl)
            : msg || describeGerarTrEDfdNetworkFailure(gerarUrl);
      } else {
        generateError.value = result.errorMessage;
      }
      return;
    }
    const { data } = result;
    if (!data.tr?.docx_base64 || !data.dfd?.docx_base64 || !data.oficio?.docx_base64) {
      generateError.value = data.error || 'TR, DFD ou Ofício não vieram na resposta.';
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
    successMessage.value = 'Documentos gerados com sucesso.';
    presetSaveAfterSuccess = true;
  } catch (e) {
    generateError.value = e?.message || 'Erro ao gerar documento';
  } finally {
    isSubmitting.value = false;
  }
  if (presetSaveAfterSuccess) void dadosFixos.saveUserGlobalPreset();
}

onBeforeUnmount(() => {
  revokeDocumentUrls();
});
</script>
