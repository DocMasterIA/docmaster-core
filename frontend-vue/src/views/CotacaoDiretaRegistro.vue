<template>
  <section class="gov-page">
    <header class="gov-page__header">
      <div class="cd-head">
        <div>
          <h1 class="gov-page__title">Cotação Direta (Inciso IV)</h1>
          <p class="gov-page__subtitle">
            Cotação #{{ cotacaoId }} · Item #{{ itemId }}
          </p>
        </div>
        <RouterLink :to="backToItemUrl" class="cd-back-btn">
          <i class="fa-solid fa-arrow-left" aria-hidden="true"></i>
          Voltar para item
        </RouterLink>
      </div>
    </header>

    <div class="gov-surface gov-page__content">
      <p v-if="isLoading" class="cd-meta">Carregando dados do item...</p>
      <p v-else-if="loadError" class="cd-meta cd-meta--error">{{ loadError }}</p>

      <template v-else>
        <section class="cd-item-card">
          <span class="cd-item-card__label">Nome do item</span>
          <strong>{{ itemNome }}</strong>
        </section>

        <form class="cd-form" @submit.prevent="salvarCotacaoDireta">
          <label class="cd-field">
            <span>Fornecedor</span>
            <input v-model.trim="form.fornecedor" type="text" required placeholder="Nome do fornecedor" />
          </label>

          <label class="cd-field">
            <span>Descrição</span>
            <input v-model.trim="form.descricao" type="text" required placeholder="Descrição principal da cotação" />
          </label>

          <label class="cd-field cd-field--full">
            <span>Descrição complementar</span>
            <textarea
              v-model.trim="form.descricao_complementar"
              rows="2"
              placeholder="Especificações adicionais, marca, modelo, validade etc."
            />
          </label>

          <label class="cd-field">
            <span>Quantidade</span>
            <input v-model.trim="form.quantidade" type="text" inputmode="decimal" placeholder="Ex.: 300" />
          </label>

          <label class="cd-field">
            <span>Unidade de medida</span>
            <input v-model.trim="form.unidade_medida" type="text" placeholder="Ex.: UN, KG, TON" />
          </label>

          <label class="cd-field">
            <span>Valor unitário</span>
            <input v-model.trim="form.valor_unitario" type="text" inputmode="decimal" placeholder="Ex.: 145,00" />
          </label>

          <label class="cd-field">
            <span>Data de cotação</span>
            <input v-model="form.data_cotacao" type="date" />
          </label>

          <label class="cd-field">
            <span>Hora de cotação</span>
            <input v-model="form.hora_cotacao" type="time" />
          </label>

          <label class="cd-field">
            <span>Ajuste de frete</span>
            <select v-model="form.ajuste_frete">
              <option value="">Não informado</option>
              <option value="com_frete">Com frete</option>
              <option value="sem_frete">Sem frete</option>
            </select>
          </label>

          <label class="cd-field">
            <span>Valor de frete</span>
            <input v-model.trim="form.valor_frete" type="text" inputmode="decimal" placeholder="Ex.: 500,00" />
          </label>

          <label class="cd-field cd-field--full">
            <span>Observações</span>
            <textarea v-model.trim="form.observacoes" rows="3" placeholder="Observações gerais da negociação." />
          </label>

          <p v-if="saveError" class="cd-meta cd-meta--error">{{ saveError }}</p>
          <p v-if="saveSuccess" class="cd-meta cd-meta--ok">{{ saveSuccess }}</p>

          <div class="cd-actions">
            <button type="submit" class="cd-btn" :disabled="isSaving">
              {{ isSaving ? 'Salvando...' : 'Salvar cotação direta' }}
            </button>
            <RouterLink :to="backToItemUrl" class="cd-btn cd-btn--ghost">Cancelar</RouterLink>
          </div>
        </form>
      </template>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { addCotacoesToItemInResearchSession, getResearchSession } from '../services/pncpResearch';

const route = useRoute();
const router = useRouter();

const cotacaoId = computed(() => Number(route.params.cotacaoId));
const itemId = computed(() => Number(route.params.itemId));

const isLoading = ref(false);
const loadError = ref('');
const isSaving = ref(false);
const saveError = ref('');
const saveSuccess = ref('');
const itemNome = ref('—');

const form = ref({
  fornecedor: '',
  descricao: '',
  descricao_complementar: '',
  quantidade: '',
  unidade_medida: '',
  valor_unitario: '',
  data_cotacao: '',
  hora_cotacao: '',
  ajuste_frete: '',
  valor_frete: '',
  observacoes: '',
});

const backToItemUrl = computed(
  () => `/pesquisador-pncp/cotacoes/${cotacaoId.value}/itens/${itemId.value}?fonte=cotacao_direta`,
);

function toNumberBR(value) {
  const s = String(value || '').trim();
  if (!s) return null;
  const normalized = s.replace(/\s+/g, '').replace(/\./g, '').replace(',', '.');
  const n = Number(normalized);
  return Number.isFinite(n) ? n : null;
}

function buildDataPublicacaoIso(dataCotacao, horaCotacao) {
  const d = String(dataCotacao || '').trim();
  if (!d) return null;
  const t = String(horaCotacao || '').trim() || '00:00';
  const iso = `${d}T${t}:00`;
  const dt = new Date(iso);
  return Number.isFinite(dt.getTime()) ? dt.toISOString() : null;
}

async function carregarItem() {
  const sessaoId = cotacaoId.value;
  const iid = itemId.value;
  if (!Number.isFinite(sessaoId) || !Number.isFinite(iid)) {
    loadError.value = 'Parâmetros inválidos para registrar cotação direta.';
    return;
  }
  isLoading.value = true;
  loadError.value = '';
  try {
    const data = await getResearchSession(sessaoId);
    const itens = Array.isArray(data?.itens) ? data.itens : [];
    const item = itens.find((x) => Number(x?.id) === iid);
    if (!item) {
      loadError.value = 'Item não encontrado nesta cotação.';
      return;
    }
    itemNome.value = String(item?.descricao_item || item?.descricao || '').trim() || '—';
    if (!form.value.quantidade && Number.isFinite(Number(item?.quantidade))) {
      form.value.quantidade = String(item.quantidade);
    }
    if (!form.value.unidade_medida) {
      form.value.unidade_medida = String(item?.unidade_medida || '').trim();
    }
    if (!form.value.descricao) {
      form.value.descricao = itemNome.value;
    }
  } catch (err) {
    loadError.value = `Falha ao carregar item (${err?.message || 'erro desconhecido'}).`;
  } finally {
    isLoading.value = false;
  }
}

async function salvarCotacaoDireta() {
  const sessaoId = cotacaoId.value;
  const iid = itemId.value;
  if (!Number.isFinite(sessaoId) || !Number.isFinite(iid)) return;

  saveError.value = '';
  saveSuccess.value = '';

  const fornecedor = String(form.value.fornecedor || '').trim();
  const descricao = String(form.value.descricao || '').trim();
  if (!fornecedor || !descricao) {
    saveError.value = 'Fornecedor e descrição são obrigatórios.';
    return;
  }

  const quantidade = toNumberBR(form.value.quantidade);
  if (form.value.quantidade && !Number.isFinite(quantidade)) {
    saveError.value = 'Quantidade inválida.';
    return;
  }
  if (Number.isFinite(quantidade) && quantidade <= 0) {
    saveError.value = 'Quantidade deve ser maior que zero.';
    return;
  }

  const valorUnitario = toNumberBR(form.value.valor_unitario);
  if (form.value.valor_unitario && !Number.isFinite(valorUnitario)) {
    saveError.value = 'Valor unitário inválido.';
    return;
  }
  if (Number.isFinite(valorUnitario) && valorUnitario <= 0) {
    saveError.value = 'Valor unitário deve ser maior que zero.';
    return;
  }

  const valorFrete = toNumberBR(form.value.valor_frete);
  if (form.value.valor_frete && !Number.isFinite(valorFrete)) {
    saveError.value = 'Valor de frete inválido.';
    return;
  }
  if (Number.isFinite(valorFrete) && valorFrete < 0) {
    saveError.value = 'Valor de frete não pode ser negativo.';
    return;
  }

  const ajusteFrete = String(form.value.ajuste_frete || '').trim();
  const valorTotalBase = Number.isFinite(valorUnitario) && Number.isFinite(quantidade)
    ? valorUnitario * quantidade
    : null;
  const valorTotal = ajusteFrete === 'com_frete' && Number.isFinite(valorTotalBase) && Number.isFinite(valorFrete)
    ? valorTotalBase + valorFrete
    : valorTotalBase;

  const dataPublicacao = buildDataPublicacaoIso(form.value.data_cotacao, form.value.hora_cotacao);
  const descricaoComplementar = String(form.value.descricao_complementar || '').trim();
  const observacoes = String(form.value.observacoes || '').trim();

  const payload = {
    numero_pncp: '',
    numero_item: '',
    descricao_item: descricao,
    quantidade: Number.isFinite(quantidade) ? quantidade : null,
    unidade_medida: String(form.value.unidade_medida || '').trim(),
    valor_unitario: Number.isFinite(valorUnitario) ? valorUnitario : null,
    valor_total: Number.isFinite(valorTotal) ? valorTotal : null,
    orgao: fornecedor,
    municipio: '',
    uf: '',
    modalidade: 'Cotação direta',
    data_publicacao: dataPublicacao,
    score_aprovacao: 100,
    confiabilidade: 'Alta',
    risco: 'Baixo',
    status: 'Aprovado',
    fonte: 'cotacao_direta',
    inciso_classificacao: 'inciso_iv',
    tipo_fonte: 'cotacao_direta',
    source: {
      fornecedor,
      descricao_complementar: descricaoComplementar || null,
      ajuste_frete: ajusteFrete || null,
      valor_frete: Number.isFinite(valorFrete) ? valorFrete : null,
      observacoes: observacoes || null,
      origem: 'cotacao_direta_manual',
      fonte: 'cotacao_direta',
      inciso_classificacao: 'inciso_iv',
      tipo_fonte: 'cotacao_direta',
    },
  };

  isSaving.value = true;
  try {
    await addCotacoesToItemInResearchSession(sessaoId, iid, [payload]);
    saveSuccess.value = 'Cotação direta registrada com sucesso.';
    setTimeout(() => {
      router.push(backToItemUrl.value);
    }, 450);
  } catch (err) {
    saveError.value = `Falha ao salvar cotação direta (${err?.message || 'erro desconhecido'}).`;
  } finally {
    isSaving.value = false;
  }
}

onMounted(() => {
  const now = new Date();
  form.value.data_cotacao = now.toISOString().slice(0, 10);
  form.value.hora_cotacao = now.toTimeString().slice(0, 5);
  carregarItem();
});
</script>

<style scoped>
.gov-page { display: flex; flex-direction: column; gap: 16px; width: 100%; min-width: 0; }
.gov-page__title { margin: 0; font-size: 24px; }
.gov-page__subtitle { margin: 6px 0 0; color: var(--color-text-soft); }
.gov-page__content { padding: 16px; display: flex; flex-direction: column; gap: 12px; min-width: 0; }
.cd-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
.cd-back-btn { border: 1px solid #cfd8e3; border-radius: 10px; background: #fff; color: #1f2937; padding: 7px 12px; font-size: 12px; text-decoration: none; display: inline-flex; align-items: center; gap: 7px; }
.cd-meta { margin: 0; font-size: 12px; color: #64748b; }
.cd-meta--error { color: #b91c1c; }
.cd-meta--ok { color: #065f46; }
.cd-item-card { border: 1px solid #d6dde8; border-radius: 10px; background: #fff; padding: 10px; display: flex; flex-direction: column; gap: 4px; }
.cd-item-card__label { font-size: 10px; text-transform: uppercase; color: #64748b; }
.cd-form { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; }
.cd-field { display: flex; flex-direction: column; gap: 4px; }
.cd-field--full { grid-column: 1 / -1; }
.cd-field > span { font-size: 11px; color: #475569; font-weight: 600; }
.cd-field input, .cd-field select, .cd-field textarea {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 13px;
  background: #fff;
}
.cd-field textarea { resize: vertical; min-height: 74px; }
.cd-actions { display: flex; gap: 8px; align-items: center; grid-column: 1 / -1; }
.cd-btn {
  border: 1px solid #1f4e79;
  border-radius: 8px;
  background: #1f4e79;
  color: #fff;
  padding: 8px 12px;
  font-size: 12px;
  cursor: pointer;
  text-decoration: none;
}
.cd-btn:disabled { opacity: 0.65; cursor: not-allowed; }
.cd-btn--ghost { background: #fff; color: #1f4e79; }
</style>
