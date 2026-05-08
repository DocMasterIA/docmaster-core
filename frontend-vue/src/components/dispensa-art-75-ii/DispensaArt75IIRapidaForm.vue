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
              <h3>O que será contratado?</h3>
              <div class="da75-block__body">
                <div class="da75-field">
                  <textarea
                    class="da75-textarea"
                    :value="objetoContratado"
                    :placeholder="rapidaObjPlaceholder"
                    @input="objetoContratado = primeiraMaiuscula(($event.target).value)"
                  />
                </div>
              </div>
            </section>

            <section class="da75-block">
              <h3>Dotação orçamentária</h3>
              <div class="da75-block__body">
                <label class="da75-check">
                  <input v-model="dotacaoAtiva" type="checkbox" />
                  Informar dotação orçamentária (opcional)
                </label>
                <div v-if="dotacaoAtiva" class="da75-mt">
                  <label class="da75-label">Dotação orçamentária</label>
                  <textarea
                    class="da75-textarea"
                    :value="dotacao"
                    :placeholder="PLACEHOLDER_DOTACAO"
                    @input="dotacao = primeiraMaiuscula(($event.target).value)"
                  />
                </div>
              </div>
            </section>

            <section class="da75-block">
              <h3>Cotação</h3>
              <div class="da75-block__body">
                <label class="da75-check">
                  <input v-model="cotacaoAtiva" type="checkbox" />
                  Incluir número de cotação (opcional)
                </label>
                <div v-if="cotacaoAtiva" class="da75-max-xs da75-mt">
                  <label class="da75-label">Número da cotação</label>
                  <input
                    class="da75-input"
                    :value="numeroCotacao"
                    placeholder="Ex: COT-2026-00123"
                    @input="numeroCotacao = primeiraMaiuscula(($event.target).value)"
                  />
                </div>
              </div>
            </section>

            <section class="da75-block">
              <h3>Data</h3>
              <div class="da75-block__body">
                <div class="da75-row da75-row--2">
                  <div class="da75-field">
                    <label class="da75-label">Modo da data</label>
                    <select
                      class="da75-select"
                      :value="modoData"
                      @change="onModoData(($event.target).value)"
                    >
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
              <button type="button" class="da75-btn da75-btn--primary" :disabled="isSubmitting" @click="onSubmit">
                {{ isSubmitting ? 'Gerando documentos...' : 'Gerar documento com IA' }}
              </button>
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
  PLACEHOLDER_DOTACAO,
  campoPreenchido,
  formatarData,
  gerarJustificativaTexto,
  gerarObjetoTexto,
  primeiraMaiuscula,
} from './dispensaArt75iiShared.js';
import './dispensaArt75ii.css';
import DispensaArt75IIDadosFixosDrawer from './DispensaArt75IIDadosFixosDrawer.vue';
import { fetchCabecalhosPrefeitura } from '@/utils/fetchCabecalhosPrefeitura.js';
import { getApiBase } from '@/utils/apiBase.js';
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
const objetoGerado = ref('');
const justificativa = ref('');
const dotacaoAtiva = ref(false);
const dotacao = ref('');
const modoData = ref('');
const dataManual = ref('');
const cotacaoAtiva = ref(false);
const numeroCotacao = ref('');
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

const rapidaObjPlaceholder = `Ex: Aquisição de material de expediente para Secretaria da Administração
10 canetas azul, 2 grampeadores, 10 resmas de papel A4`;

const SLOT_PACKAGE_BY_ROUTE = {
  DispensaRapidaArt75IObrasEngenharia: 'dispensa_75_i_obras_engenharia',
  DispensaRapidaArt75IManutencaoVeiculos: 'dispensa_75_i_manutencao_veiculos',
  DispensaRapidaArt75IICompras: 'dispensa_75_ii_compras',
  DispensaRapidaArt75IIServicos: 'dispensa_75_ii_servicos',
  DispensaRapidaArt75IIComprasServicosInclusos: 'dispensa_75_ii_compras_servicos_inclusos',
};

watch(dotacaoAtiva, (v) => {
  if (!v) dotacao.value = '';
});

onMounted(async () => {
  await dadosFixos.loadUserGlobalPreset();
  await dadosFixos.loadSlotCatalogSuggestions();
  numeroCotacao.value = String(dadosFixos.fixoCotacaoNumero || '').trim();
  cotacaoAtiva.value = !!numeroCotacao.value;
  cabecalhosLoading.value = true;
  try {
    const opts = await fetchCabecalhosPrefeitura(API_BASE);
    cabecalhoOptions.value = opts;
    if (cabecalho.value && !opts.some((o) => o.name === cabecalho.value)) cabecalho.value = '';
  } finally {
    cabecalhosLoading.value = false;
  }
});

function onApplyDadosFixos() {
  void dadosFixos.saveUserGlobalPreset();
  numeroCotacao.value = String(dadosFixos.fixoCotacaoNumero || '').trim();
  cotacaoAtiva.value = !!numeroCotacao.value;
  drawerAberto.value = false;
}

const dataResumo = computed(() => (modoData.value === 'Data manual' ? dataManual.value : modoData.value));
const slotPackageKey = computed(() => SLOT_PACKAGE_BY_ROUTE[String(route.name || '')] || 'tr_dfd_generico');

const cabecalhoMergeTemplateId = computed(() => {
  const n = String(cabecalho.value || '').trim();
  if (!n) return null;
  const hit = cabecalhoOptions.value.find((o) => o.name === n);
  return hit?.id ? String(hit.id) : null;
});

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
      titulo: 'Objeto da contratação',
      completo: campoPreenchido(objetoContratado.value),
      linhas: [
        ['Resumo do objeto', objetoContratado.value || 'Não informado', campoPreenchido(objetoContratado.value)],
      ],
    },
    {
      titulo: 'Dotação orçamentária',
      completo: !dotacaoAtiva.value || campoPreenchido(dotacao.value),
      linhas: [
        ['Situação', dotacaoAtiva.value ? 'Informar dotação' : 'Não informada', true],
        [
          'Dotação',
          dotacaoAtiva.value ? dotacao.value || 'Não informada' : 'Não se aplica',
          !dotacaoAtiva.value || campoPreenchido(dotacao.value),
        ],
      ],
    },
    {
      titulo: 'Cotação',
      completo: !cotacaoAtiva.value || campoPreenchido(numeroCotacao.value),
      linhas: [
        ['Situação', cotacaoAtiva.value ? 'Informada' : 'Não informada', true],
        ['Número da cotação', cotacaoAtiva.value ? (numeroCotacao.value || 'Não informado') : 'Não se aplica', !cotacaoAtiva.value || campoPreenchido(numeroCotacao.value)],
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

function onModoData(valor) {
  modoData.value = valor;
  if (valor !== 'Data manual') dataManual.value = '';
}

function slotsOverrideWithoutClauseDraft(raw) {
  if (!raw || typeof raw !== 'object') return raw;
  const o = { ...raw };
  delete o.objeto;
  delete o.justificativa;
  delete o.sol_oficio_objeto;
  delete o.sol_oficio_justificativa;
  return Object.keys(o).length ? o : null;
}

/** Preenche objeto e justificativa (RAG + fallback) só em memória, para o merge nos DOCX. */
async function preencherObjetoEJustificativaInterno() {
  const contratado = String(objetoContratado.value || '').trim();
  objetoGerado.value = '';
  justificativa.value = '';
  try {
    const res = await fetch(`${API_BASE}/api/documentos/fill-tr-slots`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        user_prompt: buildUserPrompt(),
        slots_override: slotsOverrideWithoutClauseDraft(buildSlotsOverride()),
        slot_package_key: slotPackageKey.value,
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.ok) {
      throw new Error(data?.error || data?.detail || `Erro ${res.status}`);
    }
    const slots = data.slots && typeof data.slots === 'object' ? data.slots : {};
    const obj = String(slots.objeto || '').trim();
    const jus = String(slots.justificativa || '').trim();
    objetoGerado.value = obj || gerarObjetoTexto(contratado, '', '');
    justificativa.value = jus || gerarJustificativaTexto(contratado, '', '');
  } catch (_e) {
    objetoGerado.value = gerarObjetoTexto(contratado, '', '');
    justificativa.value = gerarJustificativaTexto(contratado, '', '');
  }
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
  if (documentTrUrl.value) URL.revokeObjectURL(documentTrUrl.value);
  if (documentDfdUrl.value) URL.revokeObjectURL(documentDfdUrl.value);
  if (documentOficioUrl.value) URL.revokeObjectURL(documentOficioUrl.value);
  if (documentZipUrl.value) URL.revokeObjectURL(documentZipUrl.value);
  documentTrUrl.value = '';
  documentDfdUrl.value = '';
  documentOficioUrl.value = '';
  documentZipUrl.value = '';
}

function buildSlotsOverride() {
  const o = {};
  const destNome = String(dadosFixos.fixoNome || '').trim();
  const destCargo = String(dadosFixos.fixoCargo || '').trim();
  const respNome = String(dadosFixos.fixoResponsavel || '').trim();
  const respCargo = String(dadosFixos.fixoResponsavelCargo || '').trim();
  const tratNome = String(dadosFixos.fixoTratNome || '').trim();
  const tratCargo = String(dadosFixos.fixoTratCargo || '').trim();
  if (destNome) o.sol_oficio_destinatario_nome = destNome;
  if (destCargo) o.sol_oficio_destinatario_cargo = destCargo;
  if (respNome) o.sol_oficio_responsavel_nome = respNome;
  if (respCargo) o.sol_oficio_responsavel_cargo = respCargo;
  if (tratNome) o.ao_senhor_genero = tratNome;
  if (tratCargo) o.senhor_senhora_genero = tratCargo;
  if (String(dadosFixos.fixoSetor || '').trim()) o.dfd_setor_requisitante = String(dadosFixos.fixoSetor).trim();
  if (String(dadosFixos.fixoDemanda || '').trim()) o.dfd_responsavel_demanda = String(dadosFixos.fixoDemanda).trim();
  if (String(dadosFixos.fixoEmail || '').trim()) o.dfd_email = String(dadosFixos.fixoEmail).trim();
  if (String(dadosFixos.fixoGestor || '').trim()) o.dfd_gestor_contratos = String(dadosFixos.fixoGestor).trim();
  if (String(dadosFixos.fixoFiscal || '').trim()) o.dfd_fiscal_contratos = String(dadosFixos.fixoFiscal).trim();
  if (String(dadosFixos.fixoAssinatura || '').trim()) o.dfd_assinatura_nome = String(dadosFixos.fixoAssinatura).trim();
  if (String(dadosFixos.fixoAssinaturaCargo || '').trim()) o.dfd_assinatura_cargo = String(dadosFixos.fixoAssinaturaCargo).trim();
  if (processoAtivo.value && String(processo.value || '').trim()) {
    const np = String(processo.value).trim();
    o.numero_processo = np;
    o.dfd_numero_processo = np;
  }
  if (String(dadosFixos.fixoEnderecoEntrega || '').trim()) o.endereco_entrega = String(dadosFixos.fixoEnderecoEntrega).trim();
  if (String(dadosFixos.fixoEmailPropostas || '').trim()) o.email_envio_propostas = String(dadosFixos.fixoEmailPropostas).trim();
  if (String(dadosFixos.fixoTrResponsavelNome || '').trim()) o.nome_assinante_termo = String(dadosFixos.fixoTrResponsavelNome).trim();
  if (String(dadosFixos.fixoTrResponsavelCargo || '').trim()) o.cargo_assinante_termo = String(dadosFixos.fixoTrResponsavelCargo).trim();
  if (cotacaoAtiva.value && String(numeroCotacao.value || '').trim()) o.dotacao = String(numeroCotacao.value || '').trim();
  const modoNormalizado = String(modoData.value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
  let dataTermo = '';
  if (modoNormalizado === 'data automatica') {
    const now = new Date();
    dataTermo = `${String(now.getDate()).padStart(2, '0')}/${String(now.getMonth() + 1).padStart(2, '0')}/${now.getFullYear()}`;
  } else if (modoNormalizado === 'data manual') {
    dataTermo = String(dataManual.value || '').trim();
  }
  if (modoNormalizado === 'datado e assinado digitalmente') {
    dataTermo = 'datado e assinado digitalmente';
  }
  if (dataTermo) o.data_termo = dataTermo;
  const objetoFinal = String(objetoGerado.value || objetoContratado.value || '').trim();
  if (objetoFinal) o.objeto = objetoFinal;
  if (String(justificativa.value || '').trim()) o.justificativa = String(justificativa.value).trim();
  if (objetoFinal) o.sol_oficio_objeto = objetoFinal;
  if (String(justificativa.value || '').trim()) o.sol_oficio_justificativa = String(justificativa.value).trim();
  if (dotacaoAtiva.value && String(dotacao.value || '').trim()) {
    const dotacaoTexto = String(dotacao.value).trim();
    o.dotacao = dotacaoTexto;
    o.objeto_resultados = `Dotação orçamentária: ${dotacaoTexto}`;
  }
  return Object.keys(o).length ? o : null;
}

function buildUserPrompt() {
  return [
    `Gerar documento com base nos dados preenchidos para ${String(route.meta?.title || 'dispensa rapida')}.`,
    `Cabeçalho do documento: ${cabecalho.value || 'Não informado'}`,
    `Órgão: ${orgao.value || 'Não informado'}`,
    `Processo: ${processoAtivo.value ? (processo.value || 'Não informado') : 'Não se aplica'}`,
    `Objeto (o que será contratado): ${objetoContratado.value || 'Não informado'}`,
    `Cotação: ${cotacaoAtiva.value ? (numeroCotacao.value || 'Não informada') : 'Não se aplica'}`,
  ].join('\n');
}

async function onSubmit() {
  isSubmitting.value = true;
  generateError.value = '';
  successMessage.value = '';
  documentReady.value = false;
  revokeDocumentUrls();
  try {
    if (!String(objetoContratado.value || '').trim()) {
      generateError.value = 'Preencha o campo «O que será contratado?» antes de gerar o documento.';
      return;
    }
    await preencherObjetoEJustificativaInterno();
    const payload = {
      user_prompt: buildUserPrompt(),
      slots_override: buildSlotsOverride(),
      slot_package_key: slotPackageKey.value,
    };
    if (cabecalhoMergeTemplateId.value) payload.template_id = cabecalhoMergeTemplateId.value;
    const res = await fetch(`${API_BASE}/api/documentos/gerar-tr-e-dfd`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.ok) {
      generateError.value = data.error || data.detail || `Erro ${res.status}`;
      return;
    }
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
    await dadosFixos.saveUserGlobalPreset();
  } catch (e) {
    generateError.value = e?.message || 'Erro ao gerar documento';
  } finally {
    isSubmitting.value = false;
  }
}

onBeforeUnmount(() => {
  revokeDocumentUrls();
});
</script>
