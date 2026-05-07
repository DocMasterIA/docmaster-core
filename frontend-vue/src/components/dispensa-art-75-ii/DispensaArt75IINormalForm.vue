<template>
  <div class="da75-page">
    <div class="da75-page__inner">
      <div>
        <h1 class="da75-title">Gerador de Documentos</h1>
        <p class="da75-subtitle">Geração de Solicitação, DFD e Termo de Referência.</p>
      </div>

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
                      <option v-for="op in cabecalhoOptions" :key="op" :value="op">{{ op }}</option>
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

            <button type="button" class="da75-btn da75-btn--primary">Gerar documento com IA</button>
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
import { computed, onMounted, ref, watch } from 'vue';
import {
  DATA_OPTIONS,
  EMPTY_ITEM,
  calcularValorTotalEstimado,
  campoPreenchido,
  formatarData,
  gerarJustificativaTexto,
  gerarObjetoTexto,
  primeiraMaiuscula,
} from './dispensaArt75iiShared.js';
import './dispensaArt75ii.css';
import DispensaArt75IIDadosFixosDrawer from './DispensaArt75IIDadosFixosDrawer.vue';
import DispensaArt75IIItensValores from './DispensaArt75IIItensValores.vue';
import { fetchCabecalhosPrefeitura } from '@/utils/fetchCabecalhosPrefeitura.js';
import { useDispensaArt75IIDadosFixos } from '@/composables/useDispensaArt75IIDadosFixos.js';

const API_BASE = import.meta.dev ? '' : (import.meta.env.VITE_API_URL || 'https://api.docmasteria.com.br');

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
const isGerandoClausulas = ref(false);
const erroGeracaoClausulas = ref('');

onMounted(async () => {
  await dadosFixos.loadUserGlobalPreset();
  await dadosFixos.loadSlotCatalogSuggestions();
  cabecalhosLoading.value = true;
  try {
    const names = await fetchCabecalhosPrefeitura(API_BASE);
    cabecalhoOptions.value = names;
    if (cabecalho.value && !names.includes(cabecalho.value)) cabecalho.value = '';
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
  ];
});

const completos = computed(() => secoes.value.filter((s) => s.completo).length);
const progresso = computed(() => Math.round((completos.value / secoes.value.length) * 100));

function parseObjetoJustificativa(text) {
  const raw = String(text || '').replace(/\r/g, '').trim();
  if (!raw) return { objeto: '', justificativa: '' };
  const matchObjeto = raw.match(/Objeto:\s*([\s\S]*?)(?:\n+Justificativa:|$)/i);
  const matchJust = raw.match(/Justificativa:\s*([\s\S]*?)$/i);
  return {
    objeto: (matchObjeto?.[1] || '').trim(),
    justificativa: (matchJust?.[1] || '').trim(),
  };
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
    const prompt = [
      'Gerar APENAS duas seções em português:',
      'Objeto: <texto>',
      'Justificativa: <texto>',
      '',
      'Regras:',
      '- Não inventar dados fora do informado.',
      '- Não incluir seções extras.',
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
    if (!res.ok || !String(text || '').trim()) throw new Error(data?.error || `Erro ${res.status}`);
    const parsed = parseObjetoJustificativa(text);
    objetoGerado.value = parsed.objeto || gerarObjetoTexto(contratado, setor, caracteristicas);
    justificativa.value = parsed.justificativa || gerarJustificativaTexto(contratado, setor, caracteristicas);
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
</script>
