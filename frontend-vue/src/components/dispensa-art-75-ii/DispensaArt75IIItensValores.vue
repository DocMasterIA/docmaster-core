<template>
  <section class="da75-block">
    <h3>Itens e valores</h3>
    <div class="da75-block__body">
      <div class="da75-stack">
        <div v-for="(item, index) in modelValue" :key="index" class="da75-item-card">
          <div class="da75-item-head">
            <span>Item {{ index + 1 }}</span>
            <button
              v-if="modelValue.length > 1"
              type="button"
              class="da75-link-remove"
              @click="remover(index)"
            >
              Remover
            </button>
          </div>
          <div class="da75-items-grid">
            <div class="da75-field da75-col-5">
              <label class="da75-label">Descrição</label>
              <input
                class="da75-input"
                :value="item.descricao"
                @input="atualizar(index, 'descricao', primeiraMaiuscula(($event.target).value))"
              />
            </div>
            <div class="da75-field da75-col-2">
              <label class="da75-label">Qtd.</label>
              <input
                class="da75-input"
                :value="item.quantidade"
                @input="atualizar(index, 'quantidade', sanitizeQuantidadeInput(($event.target).value))"
              />
            </div>
            <div class="da75-field da75-col-2">
              <label class="da75-label">Unidade de medida</label>
              <input
                class="da75-input"
                :value="item.unidade"
                @input="atualizar(index, 'unidade', primeiraMaiuscula(($event.target).value))"
              />
            </div>
            <div class="da75-field da75-col-3">
              <label class="da75-label">Média de valor (opcional)</label>
              <input
                class="da75-input"
                :value="item.mediaValor"
                @input="atualizar(index, 'mediaValor', String(($event.target).value || ''))"
              />
            </div>
          </div>
        </div>
      </div>
      <div class="da75-items-footer">
        <button type="button" class="da75-btn" @click="adicionar">Adicionar item</button>
        <div class="da75-total-box">
          <span class="da75-total-label">Valor total estimado: </span>
          <span class="da75-total-value">{{ total }}</span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue';
import {
  EMPTY_ITEM,
  calcularValorTotalEstimado,
  primeiraMaiuscula,
} from './dispensaArt75iiShared.js';
import { formatMoedaBRLInput, sanitizeQuantidadeInput } from '../../utils/itemValorCampos.js';
import './dispensaArt75ii.css';

const modelValue = defineModel({ type: Array });

const total = computed(() => calcularValorTotalEstimado(modelValue.value));

function emitNext(next) {
  modelValue.value = next;
}

function atualizar(index, campo, valor) {
  const v = campo === 'mediaValor' ? formatMoedaBRLInput(valor) : valor;
  emitNext(
    modelValue.value.map((row, i) => (i === index ? { ...row, [campo]: v } : row)),
  );
}

function remover(index) {
  emitNext(modelValue.value.filter((_, i) => i !== index));
}

function adicionar() {
  emitNext([...modelValue.value, { ...EMPTY_ITEM }]);
}
</script>
