<template>
  <section class="gov-page">
    <header class="gov-page__header">
      <div class="cd-head">
        <div>
          <h1 class="gov-page__title">Cotação Direta (Inciso IV)</h1>
          <p class="gov-page__subtitle">
            Cotação #{{ cotacaoId }} · Item #{{ itemId }}
          </p>
          <p v-if="isEditMode" class="cd-meta">Modo edição da cotação direta #{{ cotacaoDiretaId }}</p>
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
          <span class="cd-item-card__label">Descrição do item</span>
          <strong>{{ itemNome }}</strong>
        </section>

        <form class="cd-form" @submit.prevent="salvarCotacaoDireta">
          <div class="cd-field cd-field--full">
            <span>Fornecedor</span>
            <div class="cd-inline-row">
              <input
                v-model.trim="form.fornecedor"
                list="fornecedores-salvos-list"
                type="text"
                required
                placeholder="Nome do fornecedor"
                @change="aplicarFornecedorPorLabel"
                @blur="aplicarFornecedorPorLabel"
              />
              <datalist id="fornecedores-salvos-list">
                <option v-for="f in fornecedoresCadastrados" :key="f.id" :value="formatFornecedorLabel(f)" />
              </datalist>
              <button type="button" class="cd-btn cd-btn--ghost" @click="openFornecedorModal">
                Adicionar fornecedor
              </button>
            </div>
          </div>

          <label class="cd-field cd-field--full">
            <span>Descrição</span>
            <textarea
              v-model.trim="form.descricao"
              rows="4"
              required
              class="cd-desc-textarea"
              placeholder="Descrição principal da cotação"
            />
          </label>

          <label class="cd-field cd-field--full">
            <span>Descrição complementar</span>
            <textarea
              v-model.trim="form.descricao_complementar"
              rows="3"
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
            <span>Valor médio do item</span>
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
              {{ isSaving ? 'Salvando...' : (isEditMode ? 'Salvar edição da cotação direta' : 'Salvar cotação direta') }}
            </button>
            <RouterLink :to="backToItemUrl" class="cd-btn cd-btn--ghost">Cancelar</RouterLink>
          </div>
        </form>
      </template>
    </div>

    <div v-if="fornecedorModalOpen" class="cd-modal-backdrop" @click.self="closeFornecedorModal">
      <div class="cd-modal">
        <header class="cd-modal__header">
          <h2>Cadastro de fornecedor</h2>
          <button type="button" class="cd-modal__close" @click="closeFornecedorModal">Fechar</button>
        </header>

        <div class="cd-modal__content">
          <p class="cd-meta">Preencha manualmente ou informe CNPJ para completar automaticamente.</p>
          <div class="cd-form">
            <label class="cd-field">
              <span>Tipo (Pessoa Jurídica)</span>
              <input v-model.trim="fornecedorForm.tipo_pessoa" type="text" />
            </label>
            <label class="cd-field">
              <span>CNPJ</span>
              <div class="cd-inline-row">
                <input
                  :value="fornecedorForm.cnpj"
                  type="text"
                  inputmode="numeric"
                  maxlength="18"
                  autocomplete="off"
                  placeholder="00.000.000/0001-00"
                  @keydown="onCnpjInputKeydown"
                  @input="fornecedorForm.cnpj = formatCnpj(String(($event.target).value || ''))"
                />
                <button
                  type="button"
                  class="cd-btn"
                  :disabled="isBuscandoCnpj"
                  @click="buscarFornecedorPorCnpj"
                >
                  {{ isBuscandoCnpj ? 'Buscando...' : 'Buscar CNPJ' }}
                </button>
              </div>
            </label>

            <label class="cd-field">
              <span>Razão Social</span>
              <input v-model.trim="fornecedorForm.razao_social" type="text" />
            </label>
            <label class="cd-field">
              <span>Tipo</span>
              <input v-model.trim="fornecedorForm.tipo" type="text" />
            </label>
            <label class="cd-field">
              <span>Data de abertura</span>
              <input v-model="fornecedorForm.data_abertura" type="date" />
            </label>
            <label class="cd-field">
              <span>Porte</span>
              <input v-model.trim="fornecedorForm.porte" type="text" />
            </label>
            <label class="cd-field">
              <span>Nome fantasia</span>
              <input v-model.trim="fornecedorForm.nome_fantasia" type="text" />
            </label>
            <label class="cd-field">
              <span>Logradouro</span>
              <input v-model.trim="fornecedorForm.logradouro" type="text" />
            </label>
            <label class="cd-field">
              <span>Número</span>
              <input v-model.trim="fornecedorForm.numero" type="text" />
            </label>
            <label class="cd-field">
              <span>Complemento</span>
              <input v-model.trim="fornecedorForm.complemento" type="text" />
            </label>
            <label class="cd-field">
              <span>CEP</span>
              <input v-model.trim="fornecedorForm.cep" type="text" />
            </label>
            <label class="cd-field">
              <span>Bairro</span>
              <input v-model.trim="fornecedorForm.bairro" type="text" />
            </label>
            <label class="cd-field">
              <span>Município</span>
              <input v-model.trim="fornecedorForm.municipio" type="text" />
            </label>
            <label class="cd-field">
              <span>UF</span>
              <input v-model.trim="fornecedorForm.uf" type="text" />
            </label>
            <label class="cd-field">
              <span>E-mail</span>
              <input v-model.trim="fornecedorForm.email" type="email" />
            </label>
            <label class="cd-field">
              <span>Telefone</span>
              <input v-model.trim="fornecedorForm.telefone" type="text" />
            </label>
            <label class="cd-field">
              <span>Situação</span>
              <input v-model.trim="fornecedorForm.situacao" type="text" />
            </label>
            <label class="cd-field">
              <span>Data da situação</span>
              <input v-model="fornecedorForm.data_situacao" type="date" />
            </label>
            <label class="cd-field cd-field--full">
              <span>Motivo da situação</span>
              <input v-model.trim="fornecedorForm.motivo_situacao" type="text" />
            </label>
            <label class="cd-field">
              <span>Situação especial</span>
              <input v-model.trim="fornecedorForm.situacao_especial" type="text" />
            </label>
            <label class="cd-field">
              <span>Data da situação especial</span>
              <input v-model="fornecedorForm.data_situacao_especial" type="date" />
            </label>
          </div>

          <p v-if="fornecedorModalError" class="cd-meta cd-meta--error">{{ fornecedorModalError }}</p>
        </div>

        <footer class="cd-modal__footer">
          <button type="button" class="cd-btn cd-btn--ghost" @click="closeFornecedorModal">Cancelar</button>
          <button type="button" class="cd-btn" @click="aplicarFornecedorNoFormulario">Usar fornecedor</button>
        </footer>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  addCotacoesToItemInResearchSession,
  getItemCotacoesFromResearchSession,
  getResearchSession,
  listFornecedoresCadastrados,
  saveFornecedorCadastrado,
  updateCotacaoInItemResearchSession,
} from '../services/pncpResearch';
import { cnpjDigitsOnly as onlyDigits, formatCnpjBr as formatCnpj, onCnpjInputKeydown } from '@/utils/cnpjFormat.js';

const route = useRoute();
const router = useRouter();

const cotacaoId = computed(() => Number(route.params.cotacaoId));
const itemId = computed(() => Number(route.params.itemId));
const cotacaoDiretaId = computed(() => Number(route.query.cotacaoDiretaId));

const isLoading = ref(false);
const loadError = ref('');
const isSaving = ref(false);
const saveError = ref('');
const saveSuccess = ref('');
const itemNome = ref('—');
const fornecedorModalOpen = ref(false);
const fornecedorModalError = ref('');
const isBuscandoCnpj = ref(false);
const fornecedoresCadastrados = ref([]);

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

const fornecedorForm = ref({
  tipo_pessoa: 'Pessoa Jurídica',
  cnpj: '',
  razao_social: '',
  tipo: '',
  data_abertura: '',
  porte: '',
  nome_fantasia: '',
  logradouro: '',
  numero: '',
  complemento: '',
  cep: '',
  bairro: '',
  municipio: '',
  uf: '',
  email: '',
  telefone: '',
  situacao: '',
  data_situacao: '',
  motivo_situacao: '',
  situacao_especial: '',
  data_situacao_especial: '',
});

const backToItemUrl = computed(
  () => `/pesquisador-pncp/cotacoes/${cotacaoId.value}/itens/${itemId.value}?fonte=cotacao_direta`,
);
const isEditMode = computed(() => Number.isFinite(cotacaoDiretaId.value) && cotacaoDiretaId.value > 0);

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

function normalizeDateToInput(value) {
  const s = String(value || '').trim();
  if (!s) return '';
  const iso = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (iso) return `${iso[1]}-${iso[2]}-${iso[3]}`;
  const br = s.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (br) return `${br[3]}-${br[2]}-${br[1]}`;
  return '';
}

function formatFornecedorLabel(f) {
  const cnpj = formatCnpj(f?.cnpj);
  const nome = String(f?.razao_social || f?.nome_fantasia || 'Fornecedor sem nome').trim();
  return cnpj ? `${cnpj} - ${nome}` : nome;
}

function openFornecedorModal() {
  fornecedorModalOpen.value = true;
  fornecedorModalError.value = '';
}

function closeFornecedorModal() {
  fornecedorModalOpen.value = false;
  fornecedorModalError.value = '';
}

function aplicarFornecedorSelecionado(pick) {
  if (!pick) return;
  fornecedorForm.value = {
    ...fornecedorForm.value,
    ...pick,
    cnpj: formatCnpj(pick?.cnpj),
  };
  const label = formatFornecedorLabel(pick);
  if (label) form.value.fornecedor = label;
}

function aplicarFornecedorPorLabel() {
  const label = String(form.value.fornecedor || '').trim();
  if (!label) return;
  const pick = fornecedoresCadastrados.value.find((x) => formatFornecedorLabel(x) === label);
  if (pick) aplicarFornecedorSelecionado(pick);
}

async function aplicarFornecedorNoFormulario() {
  const razao = String(fornecedorForm.value.razao_social || '').trim();
  const fantasia = String(fornecedorForm.value.nome_fantasia || '').trim();
  const nome = razao || fantasia;
  if (nome) form.value.fornecedor = nome;
  try {
    const saveRes = await saveFornecedorCadastrado({
      ...fornecedorForm.value,
      cnpj: formatCnpj(fornecedorForm.value.cnpj),
    });
    if (saveRes?.fornecedor?.id) {
      fornecedorForm.value = { ...fornecedorForm.value, ...saveRes.fornecedor };
      await carregarFornecedoresCadastrados();
    }
  } catch (_) {
    // Não interrompe o uso do formulário.
  }
  closeFornecedorModal();
}

async function buscarFornecedorPorCnpj() {
  fornecedorModalError.value = '';
  const cnpjDigits = onlyDigits(fornecedorForm.value.cnpj);
  if (cnpjDigits.length !== 14) {
    fornecedorModalError.value = 'Informe um CNPJ válido com 14 dígitos.';
    return;
  }
  isBuscandoCnpj.value = true;
  try {
    const res = await fetch(`https://brasilapi.com.br/api/cnpj/v1/${cnpjDigits}`);
    const payload = await res.json();
    if (!res.ok) {
      throw new Error(String(payload?.message || payload?.error || 'falha na consulta do CNPJ'));
    }

    fornecedorForm.value.cnpj = formatCnpj(cnpjDigits);
    fornecedorForm.value.razao_social = String(payload?.razao_social || '').trim();
    fornecedorForm.value.tipo = String(payload?.descricao_identificador_matriz_filial || '').trim();
    fornecedorForm.value.data_abertura = normalizeDateToInput(payload?.data_inicio_atividade);
    fornecedorForm.value.porte = String(payload?.porte?.descricao || payload?.porte || '').trim();
    fornecedorForm.value.nome_fantasia = String(payload?.nome_fantasia || '').trim();
    fornecedorForm.value.logradouro = String(payload?.logradouro || '').trim();
    fornecedorForm.value.numero = String(payload?.numero || '').trim();
    fornecedorForm.value.complemento = String(payload?.complemento || '').trim();
    fornecedorForm.value.cep = String(payload?.cep || '').trim();
    fornecedorForm.value.bairro = String(payload?.bairro || '').trim();
    fornecedorForm.value.municipio = String(payload?.municipio || '').trim();
    fornecedorForm.value.uf = String(payload?.uf || '').trim();
    fornecedorForm.value.email = String(payload?.email || '').trim();
    fornecedorForm.value.telefone = String(payload?.ddd_telefone_1 || payload?.ddd_telefone_2 || '').trim();
    fornecedorForm.value.situacao = String(payload?.descricao_situacao_cadastral || '').trim();
    fornecedorForm.value.data_situacao = normalizeDateToInput(payload?.data_situacao_cadastral);
    fornecedorForm.value.motivo_situacao = String(payload?.motivo_situacao_cadastral || '').trim();
    fornecedorForm.value.situacao_especial = String(payload?.situacao_especial || '').trim();
    fornecedorForm.value.data_situacao_especial = normalizeDateToInput(payload?.data_situacao_especial);

    const nome = String(fornecedorForm.value.razao_social || fornecedorForm.value.nome_fantasia || '').trim();
    if (nome) form.value.fornecedor = nome;
  } catch (err) {
    fornecedorModalError.value = `Não foi possível consultar o CNPJ (${err?.message || 'erro desconhecido'}).`;
  } finally {
    isBuscandoCnpj.value = false;
  }
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
    if (isEditMode.value) {
      await carregarCotacaoDiretaParaEdicao(sessaoId, iid, cotacaoDiretaId.value);
    }
  } catch (err) {
    loadError.value = `Falha ao carregar item (${err?.message || 'erro desconhecido'}).`;
  } finally {
    isLoading.value = false;
  }
}

async function carregarCotacaoDiretaParaEdicao(sessaoId, iid, cotId) {
  const data = await getItemCotacoesFromResearchSession(sessaoId, iid);
  const rows = Array.isArray(data?.cotacoes) ? data.cotacoes : [];
  const row = rows.find((x) => Number(x?.id) === Number(cotId));
  if (!row) return;

  const src = row?.source || {};
  form.value.fornecedor = diretaFornecedorLabelFromRow(row);
  form.value.descricao = String(row?.descricao_item || '').trim() || form.value.descricao;
  form.value.descricao_complementar = String(src?.descricao_complementar || src?.descricaoComplementar || '').trim();
  form.value.quantidade = Number.isFinite(Number(row?.quantidade)) ? String(row.quantidade) : '';
  form.value.unidade_medida = String(row?.unidade_medida || '').trim();
  form.value.valor_unitario = Number.isFinite(Number(row?.valor_unitario)) ? String(row.valor_unitario).replace('.', ',') : '';
  form.value.ajuste_frete = String(src?.ajuste_frete || '').trim();
  form.value.valor_frete = Number.isFinite(Number(src?.valor_frete)) ? String(src.valor_frete).replace('.', ',') : '';
  form.value.observacoes = String(src?.observacoes || '').trim();

  const dt = String(row?.data_publicacao || '').trim();
  if (dt) {
    const d = new Date(dt);
    if (Number.isFinite(d.getTime())) {
      form.value.data_cotacao = d.toISOString().slice(0, 10);
      form.value.hora_cotacao = d.toTimeString().slice(0, 5);
    }
  }

  if (src?.fornecedor_cadastro && typeof src.fornecedor_cadastro === 'object') {
    fornecedorForm.value = { ...fornecedorForm.value, ...src.fornecedor_cadastro };
  }
}

function diretaFornecedorLabelFromRow(row) {
  const src = row?.source || {};
  const cad = src?.fornecedor_cadastro || {};
  const cnpj = String(cad?.cnpj || src?.cnpj_fornecedor || src?.cnpj || '').trim();
  const nome = String(cad?.razao_social || cad?.nome_fantasia || src?.fornecedor || row?.orgao || '').trim();
  if (cnpj && nome) return `${cnpj} - ${nome}`;
  return nome || cnpj || '';
}

async function carregarFornecedoresCadastrados() {
  try {
    const res = await listFornecedoresCadastrados(200);
    fornecedoresCadastrados.value = Array.isArray(res?.fornecedores) ? res.fornecedores : [];
  } catch (_) {
    fornecedoresCadastrados.value = [];
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
    saveError.value = 'Valor médio do item inválido.';
    return;
  }
  if (Number.isFinite(valorUnitario) && valorUnitario <= 0) {
    saveError.value = 'Valor médio do item deve ser maior que zero.';
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
      fornecedor_cadastro: {
        ...fornecedorForm.value,
        cnpj: formatCnpj(fornecedorForm.value.cnpj),
      },
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
    const fornecedorCadastroPayload = {
      ...fornecedorForm.value,
      cnpj: formatCnpj(fornecedorForm.value.cnpj),
      razao_social: String(fornecedorForm.value.razao_social || fornecedor || '').trim(),
      nome_fantasia: String(fornecedorForm.value.nome_fantasia || '').trim(),
    };
    try {
      const saveRes = await saveFornecedorCadastrado(fornecedorCadastroPayload);
      if (saveRes?.fornecedor?.id) {
        fornecedorForm.value = { ...fornecedorForm.value, ...saveRes.fornecedor };
      }
    } catch (_) {
      // Não bloqueia gravação da cotação direta se o cadastro falhar.
    }
    if (isEditMode.value) {
      await updateCotacaoInItemResearchSession(sessaoId, iid, cotacaoDiretaId.value, payload);
      saveSuccess.value = 'Cotação direta atualizada com sucesso.';
    } else {
      await addCotacoesToItemInResearchSession(sessaoId, iid, [payload]);
      saveSuccess.value = 'Cotação direta registrada com sucesso.';
    }
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
  carregarFornecedoresCadastrados();
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
.cd-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(260px, 1fr));
  gap: 12px;
  align-items: start;
}
.cd-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.cd-field--full { grid-column: 1 / -1; }
.cd-field > span { font-size: 11px; color: #475569; font-weight: 600; }
.cd-field input, .cd-field select, .cd-field textarea {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 9px 11px;
  font-size: 13px;
  background: #fff;
}
.cd-field textarea { resize: vertical; min-height: 86px; }
.cd-desc-textarea {
  min-height: 128px !important;
  font-size: 14px;
  line-height: 1.45;
}
.cd-inline-row { display: flex; gap: 8px; align-items: center; }
.cd-inline-row > input { flex: 1; min-width: 0; }
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
.cd-modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 70;
  padding: 16px;
}
.cd-modal {
  width: min(960px, 100%);
  max-height: calc(100vh - 32px);
  background: #fff;
  border-radius: 12px;
  border: 1px solid #cfd8e3;
  display: flex;
  flex-direction: column;
}
.cd-modal__header,
.cd-modal__footer {
  padding: 12px 14px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.cd-modal__footer {
  border-top: 1px solid #e2e8f0;
  border-bottom: 0;
  justify-content: flex-end;
}
.cd-modal__header h2 {
  margin: 0;
  font-size: 18px;
}
.cd-modal__close {
  border: 1px solid #cbd5e1;
  background: #fff;
  border-radius: 8px;
  padding: 6px 10px;
  cursor: pointer;
}
.cd-modal__content {
  padding: 14px;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
@media (max-width: 900px) {
  .cd-form {
    grid-template-columns: 1fr;
  }
}
</style>
