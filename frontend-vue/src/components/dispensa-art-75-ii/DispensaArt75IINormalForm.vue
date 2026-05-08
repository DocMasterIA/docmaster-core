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
                      placeholder="Digite o órgão (use Dados fixos para sugestões)"
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
                        placeholder="Ex: Aquisição de medicamentos"
                        @input="objetoContratado = primeiraMaiuscula(($event.target).value)"
                      />
                    </div>
                    <div class="da75-field">
                      <label class="da75-label">Qual setor/secretaria será atendido?</label>
                      <input
                        class="da75-input"
                        :value="objetoSetor"
                        placeholder="Ex: UBS Leontino"
                        @input="objetoSetor = primeiraMaiuscula(($event.target).value)"
                      />
                    </div>
                    <div class="da75-field">
                      <label class="da75-label">Características mínimas obrigatórias (opcional)</label>
                      <textarea
                        class="da75-textarea"
                        :value="objetoCaracteristicas"
                        placeholder="Ex: Para doação à população carente"
                        @input="objetoCaracteristicas = primeiraMaiuscula(($event.target).value)"
                      />
                    </div>
                    <button type="button" class="da75-btn da75-btn--primary da75-btn--block" :disabled="isGerandoClausulas" @click="gerar">
                      {{ isGerandoClausulas ? 'Gerando objeto e justificativa...' : 'Gerar objeto e justificativa' }}
                    </button>
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

            <div class="da75-space-y">
              <button type="button" class="da75-btn da75-btn--primary" :disabled="isSubmitting" @click="onSubmit">
                {{ isSubmitting ? 'Gerando...' : 'Gerar documento com IA' }}
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
          <option v-for="v in (dadosFixos.slotFieldOptions.orgao || [])" :key="`o-${v}`" :value="v" />
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
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import {
  DATA_OPTIONS,
  EMPTY_ITEM,
  calcularValorTotalEstimado,
  campoPreenchido,
  formatarData,
  gerarJustificativaTexto,
  gerarObjetoTexto,
  moedaParaNumero,
  quantidadeParaNumero,
  primeiraMaiuscula,
} from './dispensaArt75iiShared.js';
import './dispensaArt75ii.css';
import DispensaArt75IIDadosFixosDrawer from './DispensaArt75IIDadosFixosDrawer.vue';
import DispensaArt75IIItensValores from './DispensaArt75IIItensValores.vue';
import { fetchCabecalhosPrefeitura } from '@/utils/fetchCabecalhosPrefeitura.js';
import { useDispensaArt75IIDadosFixos } from '@/composables/useDispensaArt75IIDadosFixos.js';

const API_BASE = (() => {
  const t = String(import.meta.env.VITE_API_URL || '').trim();
  if (t) return t.replace(/\/$/, '');
  if (import.meta.env.DEV) return '';
  return 'https://api.docmasteria.com.br';
})();
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
const modoData = ref('');
const dataManual = ref('');
const cotacaoAtiva = ref(false);
const numeroCotacao = ref('');
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
const slotPackageKey = computed(() => SLOT_PACKAGE_BY_ROUTE[String(route.name || '')] || 'tr_dfd_generico');

const cabecalhoMergeTemplateId = computed(() => {
  const n = String(cabecalho.value || '').trim();
  if (!n) return null;
  const hit = cabecalhoOptions.value.find((o) => o.name === n);
  return hit?.id ? String(hit.id) : null;
});

onMounted(async () => {
  await dadosFixos.loadUserGlobalPreset();
  await dadosFixos.loadSlotCatalogSuggestions();
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
  drawerAberto.value = false;
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
      titulo: 'Data',
      completo: campoPreenchido(dataResumo.value),
      linhas: [['Data / modo', dataResumo.value || 'Não informada', campoPreenchido(dataResumo.value)]],
    },
    {
      titulo: 'Cotação',
      completo: !cotacaoAtiva.value || campoPreenchido(numeroCotacao.value),
      linhas: [
        ['Situação', cotacaoAtiva.value ? 'Informada' : 'Não informada', true],
        ['Número da cotação', cotacaoAtiva.value ? (numeroCotacao.value || 'Não informado') : 'Não se aplica', !cotacaoAtiva.value || campoPreenchido(numeroCotacao.value)],
      ],
    },
  ];
});

const completos = computed(() => secoes.value.filter((s) => s.completo).length);
const progresso = computed(() => Math.round((completos.value / secoes.value.length) * 100));

/** Remove rascunho de objeto/justificativa para fill_tr_slots_with_llm (rag_service). */
function slotsOverrideWithoutClauseDraft(raw) {
  if (!raw || typeof raw !== 'object') return raw;
  const o = { ...raw };
  delete o.objeto;
  delete o.justificativa;
  delete o.sol_oficio_objeto;
  delete o.sol_oficio_justificativa;
  return Object.keys(o).length ? o : null;
}

async function gerar() {
  erroGeracaoClausulas.value = '';
  const contratado = String(objetoContratado.value || '').trim();
  const setor = String(objetoSetor.value || '').trim();
  const caracteristicas = String(objetoCaracteristicas.value || '').trim();
  if (!contratado || !setor) {
    erroGeracaoClausulas.value = 'Preencha "O que será contratado?" e "Qual setor/secretaria será atendido?".';
    return;
  }
  isGerandoClausulas.value = true;
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
    objetoGerado.value = obj || gerarObjetoTexto(contratado, setor, caracteristicas);
    justificativa.value = jus || gerarJustificativaTexto(contratado, setor, caracteristicas);
  } catch (_e) {
    objetoGerado.value = gerarObjetoTexto(contratado, setor, caracteristicas);
    justificativa.value = gerarJustificativaTexto(contratado, setor, caracteristicas);
    erroGeracaoClausulas.value = 'Falha na IA; aplicamos versão padrão local.';
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
  if (String(dadosFixos.fixoEnderecoEntrega || '').trim()) o.endereco_entrega = String(dadosFixos.fixoEnderecoEntrega).trim();
  if (String(dadosFixos.fixoEmailPropostas || '').trim()) o.email_envio_propostas = String(dadosFixos.fixoEmailPropostas).trim();
  if (String(dadosFixos.fixoTrResponsavelNome || '').trim()) o.nome_assinante_termo = String(dadosFixos.fixoTrResponsavelNome).trim();
  if (String(dadosFixos.fixoTrResponsavelCargo || '').trim()) o.cargo_assinante_termo = String(dadosFixos.fixoTrResponsavelCargo).trim();
  if (cotacaoAtiva.value && String(numeroCotacao.value || '').trim()) o.dotacao = String(numeroCotacao.value || '').trim();
  const modoNormalizado = String(modoData.value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
  if (modoNormalizado === 'data automatica') {
    const now = new Date();
    o.data_termo = `${String(now.getDate()).padStart(2, '0')}/${String(now.getMonth() + 1).padStart(2, '0')}/${now.getFullYear()}`;
  } else if (modoNormalizado === 'data manual') {
    const manual = String(dataManual.value || '').trim();
    if (manual) o.data_termo = manual;
  } else if (modoNormalizado === 'datado e assinado digitalmente') {
    o.data_termo = 'datado e assinado digitalmente';
  }
  const objetoFinal = String(objetoGerado.value || objetoContratado.value || '').trim();
  if (objetoFinal) o.objeto = objetoFinal;
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
    o.force_manual_items = true;
    const total = itensOverride.reduce((acc, item) => acc + moedaParaNumero(item.valor_total), 0);
    o.valor_total = formatCurrencyBr(total);
  }
  return Object.keys(o).length ? o : null;
}

function buildUserPrompt() {
  return [
    `Gerar documento com base nos dados preenchidos para ${String(route.meta?.title || 'dispensa normal')}.`,
    `Cabeçalho do documento: ${cabecalho.value || 'Não informado'}`,
    `Órgão: ${orgao.value || 'Não informado'}`,
    `Processo: ${processoAtivo.value ? (processo.value || 'Não informado') : 'Não se aplica'}`,
    `Objeto base: ${objetoContratado.value || 'Não informado'}`,
    `Setor atendido: ${objetoSetor.value || 'Não informado'}`,
    `Características mínimas: ${objetoCaracteristicas.value || 'Não informado'}`,
    `Cotação: ${cotacaoAtiva.value ? (numeroCotacao.value || 'Não informada') : 'Não se aplica'}`,
  ].join('\n');
}

function sanitizeJsonBody(obj) {
  try {
    return JSON.parse(JSON.stringify(obj));
  } catch {
    return null;
  }
}

async function onSubmit() {
  isSubmitting.value = true;
  generateError.value = '';
  successMessage.value = '';
  documentReady.value = false;
  revokeDocumentUrls();
  try {
    if (!objetoGerado.value.trim() || !justificativa.value.trim()) {
      generateError.value = 'Gere (ou preencha) Objeto e Justificativa antes de gerar o documento.';
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
    let res;
    try {
      res = await fetch(`${API_BASE}/api/documentos/gerar-tr-e-dfd`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(bodyObj),
      });
    } catch (netErr) {
      const msg = String(netErr?.message || netErr || '');
      generateError.value =
        /fetch|network|failed|load|aborted|timed out|timeout/i.test(msg) || netErr?.name === 'TypeError'
          ? 'Falha de rede ao gerar o documento (ligação interrompida, firewall ou tempo limite no servidor). Com muitos itens na tabela o pedido pode ser maior e demorar mais; tente novamente ou reduza linhas vazias.'
          : msg || 'Erro de rede ao gerar documento.';
      return;
    }
    const rawText = await res.text();
    let data = {};
    try {
      data = rawText ? JSON.parse(rawText) : {};
    } catch {
      generateError.value = rawText && /^</.test(rawText.trim())
        ? `Servidor devolveu HTML em vez de JSON (proxy ou erro ${res.status}).`
        : `Resposta inválida do servidor (não é JSON). HTTP ${res.status}.`;
      return;
    }
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
