<template>
  <section class="gov-page">
    <header class="gov-page__header">
      <h1 class="gov-page__title">Pesquisador de Dados PNCP</h1>
      <p class="gov-page__subtitle">
        Base estrutural inicial da lista de cotações (mock no frontend-vue).
      </p>
    </header>

    <div class="gov-surface gov-page__content">
      <section class="pncp-mock">
        <div class="pncp-mock__head">
          <div>
            <h2 class="pncp-mock__title">Pesquisa de Preços Inteligente</h2>
            <p class="pncp-mock__subtitle">Dados iniciais mockados da página de cotações.</p>
          </div>
          <RouterLink to="/pesquisador-pncp/cotacoes/CT-2026-00421" class="pncp-new-btn">+ Fazer nova cotação</RouterLink>
        </div>

        <div class="pncp-mock__filters">
          <div class="pncp-mock__chips">
            <button type="button" class="pncp-chip" :class="{ 'pncp-chip--active': mockStatusFilter === 'todos' }" @click="mockStatusFilter = 'todos'">Todos</button>
            <button type="button" class="pncp-chip" :class="{ 'pncp-chip--active': mockStatusFilter === 'Em andamento' }" @click="mockStatusFilter = 'Em andamento'">Em andamento</button>
            <button type="button" class="pncp-chip" :class="{ 'pncp-chip--active': mockStatusFilter === 'Finalizada' }" @click="mockStatusFilter = 'Finalizada'">Finalizadas</button>
          </div>
          <input v-model.trim="mockQuery" type="text" class="gov-input pncp-mock__search" placeholder="Filtrar cotações..." />
        </div>

        <div class="pncp-mock__summary">
          <div class="pncp-mock__summary-card"><span class="pncp-mock__summary-label">Total</span><strong>{{ mockRows.length }}</strong></div>
          <div class="pncp-mock__summary-card"><span class="pncp-mock__summary-label">Em andamento</span><strong>{{ mockInProgressCount }}</strong></div>
          <div class="pncp-mock__summary-card"><span class="pncp-mock__summary-label">Finalizadas</span><strong>{{ mockFinishedCount }}</strong></div>
          <div class="pncp-mock__summary-card pncp-mock__summary-card--highlight"><span class="pncp-mock__summary-label">Eficiência</span><strong>Alta</strong></div>
        </div>

        <div class="pncp-mock__table-wrap">
          <table class="pncp-mock__table">
            <thead>
              <tr>
                <th>Data</th>
                <th>Descrição</th>
                <th>Itens</th>
                <th>Responsável</th>
                <th>Status</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in filteredMockRows" :key="row.id">
                <td>{{ row.data }}</td>
                <td>
                  <div class="pncp-mock__desc">{{ row.descricao }}</div>
                  <div class="pncp-mock__desc-sub">Gerenciado pela IA DocMaster</div>
                </td>
                <td>{{ row.itens }}</td>
                <td>{{ row.usuario }}</td>
                <td>
                  <span class="pncp-status" :class="row.status === 'Finalizada' ? 'pncp-status--ok' : 'pncp-status--run'">{{ row.status }}</span>
                </td>
                <td>
                  <div class="pncp-actions">
                    <RouterLink :to="`/pesquisador-pncp/cotacoes/${row.cotacaoId}`" class="pncp-action-btn">Abrir</RouterLink>
                    <button type="button" class="pncp-action-btn" @click="openDeleteModal(row)">Excluir</button>
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
          aria-labelledby="pncp-delete-title"
        >
          <h2 id="pncp-delete-title" class="pncp-modal__title">Excluir cotação</h2>
          <p class="pncp-modal__text">
            Tem certeza que deseja excluir esta cotação? Esta ação não pode ser desfeita.
          </p>
          <p v-if="pendingDelete?.descricao" class="pncp-modal__quote">{{ pendingDelete.descricao }}</p>
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
import { computed, onUnmounted, ref, watch } from 'vue';

const mockQuery = ref('');
const mockStatusFilter = ref('todos');
const mockRows = ref([
  {
    id: 1,
    cotacaoId: 'CT-2026-00421',
    data: '01/04/2026 14:49',
    descricao: 'Contratação de empresa para manutenção de ar-condicionado',
    itens: 4,
    usuario: 'Diniz Luiz Martins Neto',
    status: 'Em andamento',
  },
  {
    id: 2,
    cotacaoId: 'CT-2026-00422',
    data: '01/04/2026 13:40',
    descricao: 'Aquisição de gêneros alimentícios',
    itens: 4,
    usuario: 'Diniz Luiz Martins Neto',
    status: 'Finalizada',
  },
  {
    id: 3,
    cotacaoId: 'CT-2026-00423',
    data: '01/04/2026 03:50',
    descricao: 'Aquisição de medicamentos',
    itens: 10,
    usuario: 'Edislene Ferreira da Silva',
    status: 'Finalizada',
  },
]);

const mockInProgressCount = computed(
  () => mockRows.value.filter((x) => x.status === 'Em andamento').length,
);
const mockFinishedCount = computed(
  () => mockRows.value.filter((x) => x.status === 'Finalizada').length,
);

const filteredMockRows = computed(() => {
  const q = mockQuery.value.toLowerCase();
  return mockRows.value.filter((row) => {
    const statusOk =
      mockStatusFilter.value === 'todos' || row.status === mockStatusFilter.value;
    if (!statusOk) return false;
    if (!q) return true;
    return (
      row.descricao.toLowerCase().includes(q) ||
      row.usuario.toLowerCase().includes(q) ||
      row.status.toLowerCase().includes(q)
    );
  });
});

/** Linha selecionada para exclusão (modal de confirmação). */
const pendingDelete = ref(null);

function openDeleteModal(row) {
  pendingDelete.value = row;
}

function cancelDelete() {
  pendingDelete.value = null;
}

function confirmDelete() {
  if (!pendingDelete.value) return;
  const id = pendingDelete.value.id;
  mockRows.value = mockRows.value.filter((r) => r.id !== id);
  pendingDelete.value = null;
}

let escHandler = null;
watch(pendingDelete, (row) => {
  if (escHandler) {
    window.removeEventListener('keydown', escHandler);
    escHandler = null;
  }
  if (row) {
    escHandler = (e) => {
      if (e.key === 'Escape') cancelDelete();
    };
    window.addEventListener('keydown', escHandler);
  }
});
onUnmounted(() => {
  if (escHandler) window.removeEventListener('keydown', escHandler);
});
</script>

<style scoped>
.gov-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
}

.gov-page__title {
  margin: 0;
  font-size: 24px;
}

.gov-page__subtitle {
  margin: 6px 0 0;
  color: var(--color-text-soft);
}

.gov-page__content {
  padding: 16px;
}

.pncp-mock {
  border: 1px solid #d6dde8;
  border-radius: var(--radius-md);
  background: #fff;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pncp-mock__title {
  margin: 0;
  font-size: 18px;
}

.pncp-mock__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
  flex-wrap: wrap;
}

.pncp-new-btn {
  border: 1px solid #1f4e79;
  background: #1f4e79;
  color: #fff;
  border-radius: 10px;
  padding: 7px 12px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.pncp-new-btn:hover {
  filter: brightness(0.95);
}

.pncp-mock__subtitle {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--color-text-soft);
}

.pncp-mock__filters {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.pncp-mock__chips {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.pncp-chip {
  border: 1px solid #cfd8e3;
  background: #fff;
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
  cursor: pointer;
}

.pncp-chip--active {
  background: #1f4e79;
  border-color: #1f4e79;
  color: #fff;
}

.pncp-mock__search {
  width: 260px;
  max-width: 100%;
}

.pncp-mock__summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 8px;
}

.pncp-mock__summary-card {
  border: 1px solid #d6dde8;
  border-radius: 10px;
  padding: 8px 10px;
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.pncp-mock__summary-card--highlight strong {
  color: #0f5e3a;
}

.pncp-mock__summary-label {
  font-size: 11px;
  color: var(--color-text-soft);
  text-transform: uppercase;
}

.pncp-mock__table-wrap {
  overflow-x: auto;
}

.pncp-mock__table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.pncp-mock__table th,
.pncp-mock__table td {
  border-bottom: 1px solid #e8edf4;
  padding: 10px 8px;
  text-align: left;
}

.pncp-mock__table th {
  color: var(--color-text-soft);
  font-size: 11px;
  text-transform: uppercase;
}

.pncp-mock__desc {
  font-weight: 600;
}

.pncp-mock__desc-sub {
  color: var(--color-text-soft);
  font-size: 11px;
  margin-top: 2px;
}

.pncp-status {
  border: 1px solid #cfd8e3;
  border-radius: 999px;
  padding: 3px 8px;
  font-size: 11px;
  font-weight: 600;
}

.pncp-status--ok {
  background: #e8f7ee;
  border-color: #b7e2c5;
  color: #0f5e3a;
}

.pncp-status--run {
  background: #e8f1fb;
  border-color: #b7d2ef;
  color: #1f4e79;
}

.pncp-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.pncp-action-btn {
  border: 1px solid #cfd8e3;
  background: #fff;
  border-radius: 8px;
  padding: 4px 8px;
  font-size: 11px;
  cursor: pointer;
}

.pncp-action-btn:hover {
  background: #f6f9fc;
}

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
