<template>
  <Teleport to="body">
    <div v-if="open" class="da75-backdrop" role="presentation" @click="$emit('close')" />
    <aside class="da75-drawer" :class="{ 'da75-drawer--open': open }" :aria-hidden="!open">
      <div class="da75-drawer__head">
        <div>
          <div class="da75-drawer__kicker">Configuração oculta</div>
          <h3>Dados fixos</h3>
          <p class="da75-drawer__hint">Cadastre e reutilize informações fixas por órgão ou unidade.</p>
        </div>
        <button type="button" class="da75-drawer__close" aria-label="Fechar" @click="$emit('close')">×</button>
      </div>

      <div class="da75-drawer__scroll">
        <section class="da75-block">
          <h3>Cadastros de órgãos</h3>
          <div class="da75-block__body da75-stack">
            <div class="da75-field">
              <label class="da75-label">Órgão cadastrado</label>
              <select
                class="da75-select"
                :value="perfilSelecionadoId"
                @change="carregarPerfil(($event.target).value)"
              >
                <option value="">Selecione um cadastro salvo</option>
                <option v-for="p in perfis" :key="p.id" :value="p.id">{{ p.nomeCadastro }}</option>
              </select>
            </div>
            <div class="da75-field">
              <label class="da75-label">Nome do cadastro</label>
              <input
                class="da75-input"
                :value="form.nomeCadastro"
                placeholder="Ex: Fundo Municipal de Saúde"
                @input="setCampo('nomeCadastro', primeiraMaiuscula(($event.target).value))"
              />
            </div>
            <div class="da75-row da75-row--3">
              <button type="button" class="da75-btn" @click="novoCadastro">Novo cadastro</button>
              <button type="button" class="da75-btn da75-btn--primary" @click="salvarCadastro">Salvar cadastro</button>
              <button
                type="button"
                class="da75-btn da75-btn--danger"
                :disabled="!perfilSelecionadoId"
                @click="excluirCadastro"
              >
                Excluir cadastro
              </button>
            </div>
          </div>
        </section>

        <section class="da75-block">
          <h3>1. Solicitação / Ofício</h3>
          <div class="da75-block__body">
            <div class="da75-row da75-row--3">
              <div class="da75-field">
                <label class="da75-label">Tratamento</label>
                <select class="da75-select" :value="form.tratNome" @change="setCampo('tratNome', ($event.target).value)">
                  <option value="">Selecione</option>
                  <option v-for="o in TRATAMENTO_NOME" :key="o" :value="o">{{ o }}</option>
                </select>
              </div>
              <div class="da75-field da75-span-2">
                <label class="da75-label">1.1 A quem é direcionada a solicitação — Nome</label>
                <input
                  class="da75-input"
                  :value="form.nome"
                  @input="setCampo('nome', primeiraMaiuscula(($event.target).value))"
                />
              </div>
            </div>
            <div class="da75-row da75-row--3 da75-mt">
              <div class="da75-field">
                <label class="da75-label">Tratamento</label>
                <select class="da75-select" :value="form.tratCargo" @change="setCampo('tratCargo', ($event.target).value)">
                  <option value="">Selecione</option>
                  <option v-for="o in TRATAMENTO_CARGO" :key="o" :value="o">{{ o }}</option>
                </select>
              </div>
              <div class="da75-field da75-span-2">
                <label class="da75-label">1.2 A quem é direcionada a solicitação — Função / Cargo</label>
                <input
                  class="da75-input"
                  :value="form.cargo"
                  @input="setCampo('cargo', primeiraMaiuscula(($event.target).value))"
                />
              </div>
            </div>
            <div class="da75-mt">
              <div class="da75-subblock-title">1.3 Responsável pela solicitação</div>
              <div class="da75-row da75-row--2">
                <div class="da75-field">
                  <label class="da75-label">Nome do responsável</label>
                  <input
                    class="da75-input"
                    :value="form.responsavel"
                    @input="setCampo('responsavel', primeiraMaiuscula(($event.target).value))"
                  />
                </div>
                <div class="da75-field">
                  <label class="da75-label">Função / Cargo</label>
                  <input
                    class="da75-input"
                    :value="form.responsavelCargo"
                    @input="setCampo('responsavelCargo', primeiraMaiuscula(($event.target).value))"
                  />
                </div>
              </div>
            </div>
          </div>
        </section>

        <section class="da75-block">
          <h3>2. DFD – Documento de Formalização da Demanda</h3>
          <div class="da75-block__body da75-stack">
            <div class="da75-field">
              <label class="da75-label">2.1 Setor requisitante (Unidade / Setor / Departamento)</label>
              <input
                class="da75-input"
                :value="form.setor"
                @input="setCampo('setor', primeiraMaiuscula(($event.target).value))"
              />
            </div>
            <div class="da75-field">
              <label class="da75-label">2.2 Responsável pela demanda</label>
              <input
                class="da75-input"
                :value="form.demanda"
                @input="setCampo('demanda', primeiraMaiuscula(($event.target).value))"
              />
            </div>
            <div class="da75-field">
              <label class="da75-label">2.3 E-mail</label>
              <input
                class="da75-input"
                :value="form.email"
                @input="setCampo('email', primeiraMaiuscula(($event.target).value))"
              />
            </div>
            <div class="da75-field">
              <label class="da75-label">2.4 Nome do(a) gestor(a) de contratos</label>
              <input
                class="da75-input"
                :value="form.gestor"
                @input="setCampo('gestor', primeiraMaiuscula(($event.target).value))"
              />
            </div>
            <div class="da75-field">
              <label class="da75-label">2.5 Nome do(a) fiscal de contratos</label>
              <input
                class="da75-input"
                :value="form.fiscal"
                @input="setCampo('fiscal', primeiraMaiuscula(($event.target).value))"
              />
            </div>
            <div>
              <div class="da75-subblock-title">2.6 Responsável pela assinatura da DFD</div>
              <div class="da75-row da75-row--2">
                <div class="da75-field">
                  <label class="da75-label">Nome do responsável</label>
                  <input
                    class="da75-input"
                    :value="form.assinatura"
                    @input="setCampo('assinatura', primeiraMaiuscula(($event.target).value))"
                  />
                </div>
                <div class="da75-field">
                  <label class="da75-label">Função / Cargo</label>
                  <input
                    class="da75-input"
                    :value="form.assinaturaCargo"
                    @input="setCampo('assinaturaCargo', primeiraMaiuscula(($event.target).value))"
                  />
                </div>
              </div>
            </div>
          </div>
        </section>

        <section class="da75-block">
          <h3>3. Termo de Referência</h3>
          <div class="da75-block__body da75-stack">
            <div class="da75-field">
              <label class="da75-label">Endereço presencial para envio ou entrega de propostas</label>
              <p class="da75-helper">
                Texto pré-preenchido e editável. Ajuste o município, UF, endereço, número, bairro e horário conforme o
                órgão.
              </p>
              <textarea
                class="da75-textarea"
                rows="3"
                :value="form.enderecoEntregaPropostas"
                @input="setCampo('enderecoEntregaPropostas', primeiraMaiuscula(($event.target).value))"
              />
            </div>
            <div class="da75-field">
              <label class="da75-label">E-mail para recebimento de propostas</label>
              <input
                class="da75-input"
                :value="form.emailRecebimentoPropostas"
                placeholder="Ex: propostas@municipio.go.gov.br"
                @input="setCampo('emailRecebimentoPropostas', primeiraMaiuscula(($event.target).value))"
              />
            </div>
            <div>
              <div class="da75-subblock-title">Responsável pelo Termo de Referência</div>
              <div class="da75-row da75-row--2">
                <div class="da75-field">
                  <label class="da75-label">Nome do responsável</label>
                  <input
                    class="da75-input"
                    :value="form.responsavelTR"
                    @input="setCampo('responsavelTR', primeiraMaiuscula(($event.target).value))"
                  />
                </div>
                <div class="da75-field">
                  <label class="da75-label">Cargo/Função</label>
                  <input
                    class="da75-input"
                    :value="form.responsavelCargoTR"
                    @input="setCampo('responsavelCargoTR', primeiraMaiuscula(($event.target).value))"
                  />
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </aside>
  </Teleport>
</template>

<script setup>
import { reactive, watch } from 'vue';
import {
  TRATAMENTO_NOME,
  TRATAMENTO_CARGO,
  criarPerfilDadosFixos,
  primeiraMaiuscula,
} from './dispensaArt75iiShared.js';
import './dispensaArt75ii.css';

const props = defineProps({
  open: { type: Boolean, default: false },
  perfis: { type: Array, default: () => [] },
  perfilSelecionadoId: { type: String, default: '' },
});

const emit = defineEmits(['close', 'update:perfis', 'update:perfilSelecionadoId']);

const form = reactive(criarPerfilDadosFixos('', ''));

function assignForm(perfil) {
  const base = perfil || criarPerfilDadosFixos('', '');
  Object.keys(form).forEach((k) => {
    if (k in base) form[k] = base[k];
  });
}

function syncFromParent() {
  const p = props.perfis.find((item) => item.id === props.perfilSelecionadoId);
  assignForm(p || null);
}

watch(
  () => props.open,
  (aberto) => {
    if (aberto) syncFromParent();
  },
);

watch(
  () => props.perfilSelecionadoId,
  () => {
    if (props.open) syncFromParent();
  },
);

watch(
  () => props.perfis,
  () => {
    if (props.open) syncFromParent();
  },
  { deep: true },
);

function setCampo(campo, valor) {
  form[campo] = valor;
}

function carregarPerfil(id) {
  emit('update:perfilSelecionadoId', id);
  const perfil = props.perfis.find((item) => item.id === id);
  assignForm(perfil || null);
}

function novoCadastro() {
  emit('update:perfilSelecionadoId', '');
  assignForm(null);
}

function salvarCadastro() {
  const id = props.perfilSelecionadoId || `perfil-${Date.now()}`;
  const perfil = {
    ...form,
    id,
    nomeCadastro: String(form.nomeCadastro || '').trim() || 'Cadastro sem nome',
  };
  const atuais = props.perfis;
  const next = props.perfilSelecionadoId
    ? atuais.map((item) => (item.id === id ? perfil : item))
    : [...atuais, perfil];
  emit('update:perfis', next);
  emit('update:perfilSelecionadoId', id);
  assignForm(perfil);
}

function excluirCadastro() {
  if (!props.perfilSelecionadoId) return;
  emit(
    'update:perfis',
    props.perfis.filter((item) => item.id !== props.perfilSelecionadoId),
  );
  novoCadastro();
}
</script>
