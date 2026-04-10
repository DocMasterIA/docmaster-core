<template>
  <section class="gov-page">
    <div v-if="tituloSalvo" class="cot-page-toast">
      <i class="fa-solid fa-circle-check" aria-hidden="true"></i>
      Título salvo com sucesso
    </div>

    <header class="gov-page__header">
      <div class="cot-header-row">
        <div>
          <h1 class="gov-page__title">Detalhes da Cotação</h1>
          <p class="gov-page__subtitle">
            Cotações › Cotação #{{ cotacaoId }}
          </p>
        </div>
        <RouterLink to="/pesquisador-pncp" class="cot-back-btn">
          <i class="fa-solid fa-arrow-left" aria-hidden="true"></i>
          Voltar para lista
        </RouterLink>
      </div>
      <p v-if="loadError" class="cot-meta cot-meta--error">{{ loadError }}</p>
      <p v-else-if="isLoading" class="cot-meta">Carregando itens da cotação no backend...</p>
    </header>

    <div class="gov-surface gov-page__content">
      <section class="cot-title-editor">
        <label class="cot-title-editor__field">
          <span>Título da cotação</span>
          <input
            v-model.trim="tituloCotacao"
            type="text"
            placeholder="Ex.: Cotação de medicamentos - abril/2026"
          />
        </label>
        <button type="button" class="cot-btn cot-btn--primary" @click="salvarTituloCotacao">
          <i class="fa-solid fa-floppy-disk" aria-hidden="true"></i>
          Salvar título
        </button>
      </section>

      <section class="cot-head">
        <div class="cot-head__summary">
          <div class="cot-card">
            <span class="cot-card__label">Modelo</span>
            <strong>{{ sessaoModeloLabel }}</strong>
          </div>
          <div class="cot-card">
            <span class="cot-card__label">Termo PNCP</span>
            <strong class="cot-card__truncate" :title="sessaoTermoBusca">{{ sessaoTermoBusca }}</strong>
          </div>
          <div class="cot-card">
            <span class="cot-card__label">Criado por</span>
            <strong>{{ sessaoCriadoPor }}</strong>
            <span v-if="sessaoCriadoPorEmail" class="cot-card__email">{{ sessaoCriadoPorEmail }}</span>
          </div>
          <div class="cot-card">
            <span class="cot-card__label">Criado em</span>
            <strong>{{ sessaoCreatedAt }}</strong>
          </div>
          <div class="cot-card cot-card--highlight">
            <span class="cot-card__label">Soma dos itens (estimado)</span>
            <strong>{{ valorTotalItensFmt }}</strong>
          </div>
        </div>
      </section>

      <section class="cot-formula">
        <div class="cot-formula__icon">∑</div>
        <div class="cot-formula__text">
          <div class="cot-formula__title">Fórmula de Cálculo</div>
          <div class="cot-formula__subtitle">Aplicada para consolidação</div>
        </div>
        <button type="button" class="cot-formula__select">
          Média aritmética dos preços obtidos
          <span aria-hidden="true">▾</span>
        </button>
      </section>

      <section class="cot-actions">
        <button type="button" class="cot-btn">
          <i class="fa-solid fa-file-arrow-up" aria-hidden="true"></i>
          Importar Planilha Preenchida
        </button>
        <button type="button" class="cot-btn">
          <i class="fa-solid fa-file-excel" aria-hidden="true"></i>
          Baixar Planilha Modelo
        </button>
        <button type="button" class="cot-btn">
          <i class="fa-solid fa-paperclip" aria-hidden="true"></i>
          Anexar Cotação do Fornecedor
        </button>
        <button type="button" class="cot-btn">
          <i class="fa-solid fa-file-lines" aria-hidden="true"></i>
          Gerar Relatório
        </button>
      </section>

      <section class="cot-new-item-block">
        <div class="cot-new-item-block__text">
          <h2>Novo item</h2>
          <p>Escolha como deseja iniciar a pesquisa para adicionar novos itens à cotação.</p>
        </div>
        <div class="cot-new-item-block__actions">
          <RouterLink :to="`/pesquisador-pncp/cotacoes/${cotacaoId}/busca-inteligente`" class="cot-btn cot-btn--primary">
            <i class="fa-solid fa-robot" aria-hidden="true"></i>
            Iniciar busca com I.A
          </RouterLink>
          <RouterLink :to="`/pesquisador-pncp/cotacoes/${cotacaoId}/busca-manual`" class="cot-btn">
            <i class="fa-solid fa-magnifying-glass" aria-hidden="true"></i>
            Iniciar busca manual
          </RouterLink>
        </div>
      </section>

      <section class="cot-sheet-shell">
        <div class="cot-sheet-toolbar">
          <label class="cot-sheet-search">
            <i class="fa-solid fa-magnifying-glass" aria-hidden="true"></i>
            <input
              type="text"
              placeholder="Buscar itens"
              aria-label="Buscar itens na planilha"
            />
          </label>
          <button
            type="button"
            class="cot-sheet-bulk-delete"
            :disabled="selectedIds.size === 0"
            @click="openBulkDeleteModal"
          >
            <i class="fa-solid fa-trash-can" aria-hidden="true"></i>
            Excluir selecionados
          </button>
        </div>
        <div class="cot-sheet-scroll">
          <table class="cot-sheet-table" aria-label="Estrutura base da planilha de cotacao">
            <colgroup class="cot-sheet-columns">
              <col style="width: 56px" />
              <col style="width: 260px" />
              <col style="width: 110px" />
              <col style="width: 110px" />
              <col style="width: 110px" />
              <col style="width: 110px" />
              <col style="width: 110px" />
              <col style="width: 70px" />
              <col style="width: 70px" />
              <col style="width: 120px" />
              <col style="width: 170px" />
              <col style="width: 110px" />
              <col style="width: 170px" />
            </colgroup>
            <thead>
              <tr>
                <th rowspan="2" class="cot-sheet-center">
                  <input
                    type="checkbox"
                    class="cot-sheet-checkbox"
                    :checked="allSelected"
                    :indeterminate.prop="isPartiallySelected"
                    @change="toggleSelectAll"
                    aria-label="Selecionar todos os itens"
                  />
                </th>
                <th rowspan="2">Nome do Item</th>
                <th colspan="5" class="cot-sheet-group">Fontes de Preco (Art. 5º)</th>
                <th rowspan="2" class="cot-sheet-center">Qtd.</th>
                <th rowspan="2" class="cot-sheet-center">Und.</th>
                <th rowspan="2" class="cot-sheet-center">Preco Total</th>
                <th rowspan="2">Faixa Regional do Item</th>
                <th rowspan="2" class="cot-sheet-center">Status</th>
                <th rowspan="2" class="cot-sheet-center">Acoes</th>
              </tr>
              <tr>
                <th class="cot-sheet-source">
                  <span class="cot-sheet-source__icon"><i class="fa-solid fa-building-columns" aria-hidden="true"></i></span>
                  <span class="cot-sheet-source__title">Precos Governamentais</span>
                  <span class="cot-sheet-source__sub">(Inciso I)</span>
                </th>
                <th class="cot-sheet-source">
                  <span class="cot-sheet-source__icon"><i class="fa-solid fa-building" aria-hidden="true"></i></span>
                  <span class="cot-sheet-source__title">Outros Entes Publicos</span>
                  <span class="cot-sheet-source__sub">(Inciso II)</span>
                </th>
                <th class="cot-sheet-source">
                  <span class="cot-sheet-source__icon"><i class="fa-solid fa-globe" aria-hidden="true"></i></span>
                  <span class="cot-sheet-source__title">Dominio Amplo</span>
                  <span class="cot-sheet-source__sub">(Inciso III)</span>
                </th>
                <th class="cot-sheet-source">
                  <span class="cot-sheet-source__icon"><i class="fa-solid fa-money-bill-wave" aria-hidden="true"></i></span>
                  <span class="cot-sheet-source__title">Cotacao Direta</span>
                  <span class="cot-sheet-source__sub">(Inciso IV)</span>
                </th>
                <th class="cot-sheet-source">
                  <span class="cot-sheet-source__icon"><i class="fa-solid fa-file-lines" aria-hidden="true"></i></span>
                  <span class="cot-sheet-source__title">Notas Fiscais</span>
                  <span class="cot-sheet-source__sub">(Inciso V)</span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="linha in linhasMock" :key="linha.id">
                <td class="cot-sheet-center">
                  <input
                    type="checkbox"
                    class="cot-sheet-checkbox"
                    :checked="selectedIds.has(linha.id)"
                    @change="toggleSelectRow(linha.id)"
                    :aria-label="`Selecionar item ${linha.id}`"
                  />
                </td>
                <td>{{ linha.nomeItem }}</td>
                <td class="cot-sheet-center">
                  <button
                    type="button"
                    class="cot-sheet-source-cell"
                    :class="linha.id % 2 === 0 ? 'cot-sheet-source-cell--green' : 'cot-sheet-source-cell--gray'"
                  >
                    {{ linha.fontes.governamentais }}
                  </button>
                </td>
                <td class="cot-sheet-center">
                  <button
                    type="button"
                    class="cot-sheet-source-cell"
                    :class="linha.id % 2 === 0 ? 'cot-sheet-source-cell--gray' : 'cot-sheet-source-cell--green'"
                  >
                    {{ linha.fontes.entesPublicos }}
                  </button>
                </td>
                <td class="cot-sheet-center">
                  <button
                    type="button"
                    class="cot-sheet-source-cell"
                    :class="linha.id % 2 === 0 ? 'cot-sheet-source-cell--green' : 'cot-sheet-source-cell--gray'"
                  >
                    {{ linha.fontes.dominioAmplo }}
                  </button>
                </td>
                <td class="cot-sheet-center">
                  <button
                    type="button"
                    class="cot-sheet-source-cell"
                    :class="linha.id % 2 === 0 ? 'cot-sheet-source-cell--gray' : 'cot-sheet-source-cell--green'"
                  >
                    {{ linha.fontes.cotacaoDireta }}
                  </button>
                </td>
                <td class="cot-sheet-center">
                  <button
                    type="button"
                    class="cot-sheet-source-cell"
                    :class="linha.id % 2 === 0 ? 'cot-sheet-source-cell--green' : 'cot-sheet-source-cell--gray'"
                  >
                    {{ linha.fontes.notasFiscais }}
                  </button>
                </td>
                <td class="cot-sheet-center">{{ linha.qtd }}</td>
                <td class="cot-sheet-center">{{ linha.und }}</td>
                <td class="cot-sheet-center">{{ linha.precoTotal }}</td>
                <td>
                  <div class="cot-faixa-block">
                    <span class="cot-faixa-block__label">BASE</span>
                    <strong class="cot-faixa-block__value">{{ faixaRegionalBase }}</strong>
                    <span class="cot-faixa-block__dot" aria-hidden="true">·</span>
                    <span class="cot-faixa-block__label">VAR</span>
                    <strong class="cot-faixa-block__value">{{ faixaRegionalVariacao }}</strong>
                  </div>
                </td>
                <td class="cot-sheet-center">
                  <span class="cot-sheet-status">{{ linha.status }}</span>
                </td>
                <td>
                  <div class="cot-sheet-actions">
                    <button type="button" class="cot-sheet-action-btn">Abrir</button>
                    <button type="button" class="cot-sheet-action-btn">Editar</button>
                    <button
                      type="button"
                      class="cot-sheet-action-btn cot-sheet-action-btn--danger"
                      @click="openRowDeleteModal(linha)"
                    >
                      Excluir
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>

    <Teleport to="body">
      <div
        v-if="pendingDelete"
        class="pncp-modal-backdrop"
        role="presentation"
        @click.self="cancelDelete"
      >
        <div
          class="pncp-modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="cot-pncp-delete-title"
        >
          <h2 id="cot-pncp-delete-title" class="pncp-modal__title">{{ deleteModalTitle }}</h2>
          <p class="pncp-modal__text">{{ deleteModalText }}</p>
          <p v-if="deleteModalQuote" class="pncp-modal__quote">{{ deleteModalQuote }}</p>
          <div class="pncp-modal__actions">
            <button type="button" class="pncp-modal__btn pncp-modal__btn--ghost" @click="cancelDelete">
              Cancelar
            </button>
            <button type="button" class="pncp-modal__btn pncp-modal__btn--danger" @click="confirmDelete">
              Excluir
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { getResearchSession, updateResearchSession } from '../services/pncpResearch';

const route = useRoute();
const cotacaoId = computed(() => route.params.cotacaoId || 'CT-2026-00421');

const MODELO_COTACAO_LABELS = {
  pesquisa_precos_padrao: 'Pesquisa de preços (padrão)',
  referencia_mercado: 'Referência de mercado',
};

const linhasMock = ref([]);

const selectedIds = ref(new Set());
const tituloCotacao = ref('');
const sessaoModeloLabel = ref('—');
const sessaoTermoBusca = ref('—');
const sessaoCreatedAt = ref('—');
const sessaoCriadoPor = ref('—');
const sessaoCriadoPorEmail = ref('');
const valorTotalItensFmt = ref('R$ —');
const tituloSalvo = ref(false);
const isLoading = ref(false);
const loadError = ref('');
const faixaRegionalBase = 'R$ 15,00';
const faixaRegionalVariacao = '20%';

const allSelected = computed(() => {
  const rows = linhasMock.value;
  return rows.length > 0 && selectedIds.value.size === rows.length;
});

const isPartiallySelected = computed(() => {
  const rows = linhasMock.value;
  return selectedIds.value.size > 0 && selectedIds.value.size < rows.length;
});

function toggleSelectRow(id) {
  const next = new Set(selectedIds.value);
  if (next.has(id)) {
    next.delete(id);
  } else {
    next.add(id);
  }
  selectedIds.value = next;
}

function toggleSelectAll(event) {
  if (event.target.checked) {
    selectedIds.value = new Set(linhasMock.value.map((linha) => linha.id));
    return;
  }
  selectedIds.value = new Set();
}

/** Mesmo padrão de modal que em `PncpResearcher.vue`: exclusão em lote ou uma linha. */
const pendingDelete = ref(null);

const deleteModalTitle = computed(() => {
  const p = pendingDelete.value;
  if (!p) return '';
  return p.kind === 'bulk' ? 'Excluir itens' : 'Excluir item';
});

const deleteModalText = computed(() => {
  const p = pendingDelete.value;
  if (!p) return '';
  return p.kind === 'bulk'
    ? 'Tem certeza que deseja excluir os itens selecionados? Esta ação não pode ser desfeita.'
    : 'Tem certeza que deseja excluir este item? Esta ação não pode ser desfeita.';
});

const deleteModalQuote = computed(() => {
  const p = pendingDelete.value;
  if (!p) return '';
  if (p.kind === 'row') return p.row.nomeItem;
  const idSet = new Set(p.ids);
  const names = linhasMock.value.filter((l) => idSet.has(l.id)).map((l) => l.nomeItem);
  if (names.length === 0) return '';
  if (names.length <= 2) return names.join(' · ');
  return `${names.length} itens selecionados`;
});

function openBulkDeleteModal() {
  if (selectedIds.value.size === 0) return;
  pendingDelete.value = { kind: 'bulk', ids: [...selectedIds.value] };
}

function openRowDeleteModal(row) {
  pendingDelete.value = { kind: 'row', row };
}

function cancelDelete() {
  pendingDelete.value = null;
}

function confirmDelete() {
  const p = pendingDelete.value;
  if (!p) return;
  if (p.kind === 'bulk') {
    const remover = new Set(p.ids);
    linhasMock.value = linhasMock.value.filter((linha) => !remover.has(linha.id));
    selectedIds.value = new Set();
  } else {
    const id = p.row.id;
    linhasMock.value = linhasMock.value.filter((linha) => linha.id !== id);
    const next = new Set(selectedIds.value);
    next.delete(id);
    selectedIds.value = next;
  }
  pendingDelete.value = null;
}

let escHandler = null;
watch(pendingDelete, (open) => {
  if (escHandler) {
    window.removeEventListener('keydown', escHandler);
    escHandler = null;
  }
  if (open) {
    escHandler = (e) => {
      if (e.key === 'Escape') cancelDelete();
    };
    window.addEventListener('keydown', escHandler);
  }
});
onUnmounted(() => {
  if (escHandler) window.removeEventListener('keydown', escHandler);
});

onMounted(() => {
  loadSessionFromBackend();
});

async function loadSessionFromBackend() {
  const sessionId = Number(cotacaoId.value);
  if (Number.isNaN(sessionId)) {
    loadError.value = 'ID de cotação inválido para backend PNCP.';
    return;
  }
  isLoading.value = true;
  loadError.value = '';
  try {
    const data = await getResearchSession(sessionId);
    if (data?.ok && data.sessao) {
      const s = data.sessao;
      tituloCotacao.value = s.titulo || `Cotação ${cotacaoId.value}`;
      const mk = s.modelo_cotacao || 'pesquisa_precos_padrao';
      sessaoModeloLabel.value = MODELO_COTACAO_LABELS[mk] || mk;
      sessaoTermoBusca.value = s.termo_busca || '—';
      sessaoCreatedAt.value = formatDateTimePt(s.created_at);
      sessaoCriadoPor.value = s.criado_por || '—';
      sessaoCriadoPorEmail.value = (s.criado_por_email || '').trim();
    }
    if (data?.ok && Array.isArray(data.itens)) {
      let soma = 0;
      let temValor = false;
      linhasMock.value = data.itens.map((it, idx) => {
        const vt = Number(it.valor_total ?? it.valor_unitario);
        if (!Number.isNaN(vt) && vt > 0) {
          soma += vt;
          temValor = true;
        }
        return {
          id: it.id || idx + 1,
          nomeItem: it.descricao_item || `Item ${idx + 1}`,
          fontes: { governamentais: 1, entesPublicos: 0, dominioAmplo: 0, cotacaoDireta: 0, notasFiscais: 0 },
          qtd: it.quantidade ?? '-',
          und: it.unidade_medida || '-',
          precoTotal: formatCurrency(it.valor_total ?? it.valor_unitario ?? 0),
          faixaRegional: '',
          status: 'Importado',
        };
      });
      valorTotalItensFmt.value = temValor ? formatCurrency(soma) : 'R$ —';
    } else if (data?.ok) {
      linhasMock.value = [];
      valorTotalItensFmt.value = 'R$ —';
    }
  } catch (err) {
    loadError.value = `Não foi possível carregar a sessão no backend (${err.message || 'erro desconhecido'}).`;
    linhasMock.value = [];
    valorTotalItensFmt.value = 'R$ —';
    sessaoCriadoPor.value = '—';
    sessaoCriadoPorEmail.value = '';
  } finally {
    isLoading.value = false;
  }
}

function formatCurrency(v) {
  const n = Number(v);
  if (Number.isNaN(n)) return 'R$ -';
  return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function formatDateTimePt(iso) {
  if (!iso) return '—';
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return String(iso);
  return dt.toLocaleString('pt-BR', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function salvarTituloCotacao() {
  saveTituloNoBackend();
}

async function saveTituloNoBackend() {
  const sessionId = Number(cotacaoId.value);
  if (Number.isNaN(sessionId)) {
    loadError.value = 'Não foi possível salvar: cotação sem ID numérico.';
    return;
  }
  loadError.value = '';
  try {
    await updateResearchSession(sessionId, {
      titulo: tituloCotacao.value || `Cotação ${sessionId}`,
    });
    tituloSalvo.value = true;
    setTimeout(() => {
      tituloSalvo.value = false;
    }, 1500);
  } catch (err) {
    loadError.value = `Falha ao salvar título (${err.message || 'erro desconhecido'}).`;
  }
}
</script>

<style scoped>
.gov-page { display: flex; flex-direction: column; gap: 16px; width: 100%; min-width: 0; }
.gov-page__title { margin: 0; font-size: 24px; }
.gov-page__subtitle { margin: 6px 0 0; color: var(--color-text-soft); }
.cot-meta { margin: 8px 0 0; font-size: 12px; color: #64748b; }
.cot-meta--error { color: #b91c1c; }
.gov-page__content { padding: 16px; display: flex; flex-direction: column; gap: 12px; min-width: 0; }
.cot-header-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
.cot-back-btn { border: 1px solid #cfd8e3; border-radius: 10px; background: #fff; color: #1f2937; padding: 7px 12px; font-size: 12px; text-decoration: none; display: inline-flex; align-items: center; gap: 7px; }

.cot-head__summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 8px; }
.cot-card { border: 1px solid #d6dde8; border-radius: 10px; background: #fff; padding: 10px; display: flex; flex-direction: column; gap: 2px; }
.cot-card--highlight strong { color: #1f4e79; }
.cot-card__label { font-size: 11px; text-transform: uppercase; color: var(--color-text-soft); }
.cot-card__email {
  display: block;
  margin-top: 4px;
  font-size: 11px;
  color: var(--color-text-soft);
  word-break: break-all;
}
.cot-card__truncate {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-word;
  font-weight: 600;
}

.cot-title-editor {
  border: 1px solid #d6dde8;
  border-radius: 10px;
  background: #fff;
  padding: 10px;
  display: flex;
  align-items: end;
  gap: 8px;
  flex-wrap: wrap;
}

.cot-title-editor__field {
  flex: 1 1 320px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.cot-title-editor__field span {
  font-size: 10px;
  text-transform: uppercase;
  color: var(--color-text-soft);
}

.cot-title-editor__field input {
  border: 1px solid #cfd8e3;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 13px;
  outline: none;
}

.cot-page-toast {
  position: fixed;
  top: 14px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 999;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border: 1px solid #b7d2ef;
  background: #e8f1fb;
  color: #1f4e79;
  border-radius: 999px;
  padding: 7px 12px;
  font-size: 12px;
  font-weight: 600;
}

.cot-formula {
  border: 1px solid #d6dde8;
  border-radius: 10px;
  background: #fff;
  padding: 10px;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.cot-formula__icon {
  width: 36px;
  height: 36px;
  border-radius: 999px;
  background: #e8f1fb;
  color: #1f4e79;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
}

.cot-formula__text { display: flex; flex-direction: column; gap: 2px; }
.cot-formula__title { font-size: 13px; font-weight: 600; }
.cot-formula__subtitle { font-size: 12px; color: var(--color-text-soft); }

.cot-formula__select {
  margin-left: auto;
  border: 1px solid #cfd8e3;
  border-radius: 8px;
  background: #fff;
  padding: 7px 10px;
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.cot-actions { display: flex; flex-wrap: wrap; gap: 8px; }
.cot-btn { border: 1px solid #cfd8e3; border-radius: 10px; background: #fff; color: #1f2937; padding: 7px 12px; font-size: 12px; text-decoration: none; cursor: pointer; display: inline-flex; align-items: center; gap: 7px; }
.cot-btn--primary { background: #1f4e79; color: #fff; border-color: #1f4e79; }

.cot-new-item-block {
  border: 1px solid #d6dde8;
  border-radius: 10px;
  background: #fff;
  padding: 10px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.cot-new-item-block__text h2 {
  margin: 0;
  font-size: 16px;
}

.cot-new-item-block__text p {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--color-text-soft);
}

.cot-new-item-block__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.cot-sheet-shell {
  width: 100%;
  border: 1px solid #d6dde8;
  border-radius: 10px;
  background: #fff;
  padding: 12px;
  min-width: 0;
  max-width: 100%;
}

.cot-sheet-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.cot-sheet-search {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid #cfd8e3;
  border-radius: 10px;
  background: #fff;
  color: #64748b;
  padding: 7px 10px;
  min-width: 260px;
  flex: 1 1 320px;
}

.cot-sheet-search input {
  border: 0;
  outline: none;
  width: 100%;
  min-width: 0;
  font-size: 12px;
  color: #1f2937;
  background: transparent;
}

.cot-sheet-bulk-delete {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  flex-shrink: 0;
  border: 1px solid #e5c9c9;
  border-radius: 10px;
  background: #fff;
  color: #b05d5d;
  padding: 7px 12px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}

.cot-sheet-bulk-delete:hover:not(:disabled) {
  background: #fff5f5;
}

.cot-sheet-bulk-delete:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.cot-sheet-scroll {
  width: 100%;
  max-width: 100%;
  overflow-x: auto;
  overflow-y: hidden;
  min-width: 0;
}

.cot-sheet-table {
  width: 100%;
  min-width: 1100px;
  border-collapse: collapse;
  table-layout: fixed;
}

.cot-sheet-table th,
.cot-sheet-table td {
  border: 1px solid #e5eaf3;
  padding: 8px;
  font-size: 11px;
  line-height: 1.25;
}

.cot-sheet-table thead th {
  background: #f8fafc;
  color: #334155;
  font-weight: 700;
  text-transform: uppercase;
}

.cot-sheet-group {
  text-align: center;
  background: #edf4ff !important;
}

.cot-sheet-source {
  background: #edf4ff !important;
}

.cot-sheet-source__icon {
  display: block;
  text-align: center;
  font-size: 13px;
  margin-bottom: 3px;
  color: #334155;
}

.cot-sheet-source__title {
  display: block;
  font-size: 10px;
  line-height: 1.15;
}

.cot-sheet-source__sub {
  display: block;
  font-size: 10px;
  line-height: 1.15;
  color: #64748b;
  text-transform: none;
}

.cot-sheet-center {
  text-align: center;
}

.cot-sheet-checkbox {
  width: 15px;
  height: 15px;
  cursor: pointer;
}

.cot-sheet-source-cell {
  min-width: 32px;
  border-radius: 7px;
  border: 1px solid #d4dbe6;
  padding: 4px 7px;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
}

.cot-sheet-source-cell--gray {
  background: #eef2f7;
  color: #475569;
  border-color: #d5dde9;
}

.cot-sheet-source-cell--green {
  background: #e4efff;
  color: #1f4e79;
  border-color: #b7d2ef;
}

.cot-sheet-source-cell:hover {
  filter: brightness(0.97);
}

.cot-sheet-status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #b7d2ef;
  background: #e8f1ff;
  color: #1f4e79;
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 10px;
  white-space: nowrap;
}

.cot-faixa-block {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 1px solid #d6dde8;
  border-radius: 8px;
  background: #f8fafc;
  padding: 4px 6px;
  white-space: nowrap;
}

.cot-faixa-block__label {
  font-size: 10px;
  font-weight: 700;
  color: #64748b;
}

.cot-faixa-block__value {
  font-size: 11px;
  color: #1f2937;
}

.cot-faixa-block__dot {
  color: #64748b;
}

.cot-sheet-actions {
  display: flex;
  gap: 6px;
  flex-wrap: nowrap;
}

.cot-sheet-action-btn {
  border: 1px solid #cfd8e3;
  border-radius: 8px;
  background: #fff;
  color: #1f2937;
  padding: 4px 8px;
  font-size: 11px;
  white-space: nowrap;
  cursor: pointer;
}

.cot-sheet-action-btn--danger {
  border-color: #e5c9c9;
  color: #b05d5d;
}

/* Alinhado ao modal de exclusão em `PncpResearcher.vue` */
.pncp-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: rgba(15, 23, 42, 0.45);
}

.pncp-modal {
  width: 100%;
  max-width: 420px;
  border-radius: var(--radius-md);
  background: #fff;
  border: 1px solid #d6dde8;
  box-shadow: 0 16px 48px rgba(15, 23, 42, 0.18);
  padding: 20px;
}

.pncp-modal__title {
  margin: 0 0 10px;
  font-size: 18px;
  color: #0f172a;
}

.pncp-modal__text {
  margin: 0 0 10px;
  font-size: 14px;
  line-height: 1.45;
  color: var(--color-text-soft);
}

.pncp-modal__quote {
  margin: 0 0 16px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #f6f9fc;
  border: 1px solid #e8edf4;
  font-size: 12px;
  line-height: 1.4;
  color: #334155;
}

.pncp-modal__actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

.pncp-modal__btn {
  border-radius: 10px;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
}

.pncp-modal__btn--ghost {
  background: #fff;
  border-color: #cfd8e3;
  color: #334155;
}

.pncp-modal__btn--ghost:hover {
  background: #f6f9fc;
}

.pncp-modal__btn--danger {
  background: #b91c1c;
  border-color: #b91c1c;
  color: #fff;
}

.pncp-modal__btn--danger:hover {
  filter: brightness(0.95);
}
</style>
