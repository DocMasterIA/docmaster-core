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
                    <label class="da75-label da75-label--compact">Órgão / dados fixos</label>
                    <select
                      class="da75-select da75-select--sm"
                      :value="perfilSelecionadoId"
                      @change="perfilSelecionadoId = ($event.target).value"
                    >
                      <option value="">Selecione um órgão cadastrado</option>
                      <option v-for="p in perfis" :key="p.id" :value="p.id">{{ p.nomeCadastro }}</option>
                    </select>
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
                    @input="processo = primeiraMaiuscula(($event.target).value)"
                  />
                </div>
              </div>
            </section>

            <section class="da75-block">
              <h3>Objeto da contratação</h3>
              <div class="da75-block__body">
                <label class="da75-label">O que será contratado?</label>
                <textarea
                  class="da75-textarea"
                  rows="4"
                  :value="objetoContratado"
                  :placeholder="rapidaObjPlaceholder"
                  @input="objetoContratado = primeiraMaiuscula(($event.target).value)"
                />
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

            <button type="button" class="da75-btn da75-btn--primary">Gerar documento com IA</button>
          </div>
        </section>

        <DispensaArt75IIDrawer
          :open="drawerAberto"
          :perfis="perfis"
          :perfil-selecionado-id="perfilSelecionadoId"
          @close="drawerAberto = false"
          @update:perfis="perfis = $event"
          @update:perfil-selecionado-id="perfilSelecionadoId = $event"
        />

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
import { computed, onMounted, ref, watch } from 'vue';
import {
  DATA_OPTIONS,
  PLACEHOLDER_DOTACAO,
  campoPreenchido,
  formatarData,
  primeiraMaiuscula,
} from './dispensaArt75iiShared.js';
import './dispensaArt75ii.css';
import DispensaArt75IIDrawer from './DispensaArt75IIDrawer.vue';
import { fetchCabecalhosPrefeitura } from '@/utils/fetchCabecalhosPrefeitura.js';

const API_BASE = import.meta.dev ? '' : (import.meta.env.VITE_API_URL || 'https://api.docmasteria.com.br');

const drawerAberto = ref(false);
const cabecalhoOptions = ref([]);
const cabecalhosLoading = ref(false);
const perfis = ref([]);
const perfilSelecionadoId = ref('');
const cabecalho = ref('');
const processoAtivo = ref(false);
const processo = ref('');
const objetoContratado = ref('');
const dotacaoAtiva = ref(false);
const dotacao = ref('');
const modoData = ref('');
const dataManual = ref('');

const rapidaObjPlaceholder = `Ex: Aquisição de material de expediente para Secretaria da Administração
10 canetas azul, 2 grampeadores, 10 resmas de papel A4`;

watch(dotacaoAtiva, (v) => {
  if (!v) dotacao.value = '';
});

onMounted(async () => {
  cabecalhosLoading.value = true;
  try {
    const names = await fetchCabecalhosPrefeitura(API_BASE);
    cabecalhoOptions.value = names;
    if (cabecalho.value && !names.includes(cabecalho.value)) cabecalho.value = '';
  } finally {
    cabecalhosLoading.value = false;
  }
});

const perfilSelecionado = computed(() => perfis.value.find((p) => p.id === perfilSelecionadoId.value));

const dataResumo = computed(() => (modoData.value === 'Data manual' ? dataManual.value : modoData.value));

const secoes = computed(() => {
  const orgao = perfilSelecionado.value?.nomeCadastro || '';
  return [
    {
      titulo: 'Dados básicos',
      completo:
        campoPreenchido(cabecalho.value) &&
        campoPreenchido(orgao) &&
        (!processoAtivo.value || campoPreenchido(processo.value)),
      linhas: [
        ['Cabeçalho', cabecalho.value || 'Não informado', campoPreenchido(cabecalho.value)],
        ['Órgão', orgao || 'Não informado', campoPreenchido(orgao)],
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
      linhas: [['O que será contratado', objetoContratado.value || 'Não informado', campoPreenchido(objetoContratado.value)]],
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
</script>
