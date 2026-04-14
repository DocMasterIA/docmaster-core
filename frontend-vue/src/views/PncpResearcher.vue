<template>
  <section class="gov-page">
    <header class="gov-page__header">
      <h1 class="gov-page__title">Pesquisador de Dados PNCP</h1>
      <p class="gov-page__subtitle">Pesquisas/cotações PNCP salvas no backend.</p>
      <p v-if="loadError" class="gov-page__meta gov-page__meta--error">{{ loadError }}</p>
      <p v-else-if="isLoading" class="gov-page__meta">Carregando cotações do backend...</p>
      <p v-else class="gov-page__meta gov-page__meta--ok">Conectado ao backend PNCP.</p>
    </header>

    <div class="gov-surface gov-page__content">
      <section class="pncp-mock">
        <div class="pncp-mock__head">
          <div>
            <h2 class="pncp-mock__title">Pesquisa de Preços Inteligente</h2>
            <p class="pncp-mock__subtitle">Cotações salvas no backend; nova cotação só precisa de um título.</p>
          </div>
          <button type="button" class="pncp-new-btn" :disabled="isCreating" @click="openCreateModal">
            + Fazer nova cotação
          </button>
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
                <th>Criada em</th>
                <th>Descrição</th>
                <th>Itens</th>
                <th>Responsável</th>
                <th>Status</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody v-if="filteredMockRows.length">
              <tr v-for="row in filteredMockRows" :key="row.id">
                <td>{{ row.data }}</td>
                <td>
                  <div class="pncp-mock__desc">{{ row.descricao }}</div>
                </td>
                <td>{{ row.itens }}</td>
                <td>
                  <div class="pncp-mock__usuario">{{ row.usuario }}</div>
                  <div v-if="row.usuarioEmail" class="pncp-mock__desc-sub">{{ row.usuarioEmail }}</div>
                </td>
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
            <tbody v-else>
              <tr>
                <td colspan="6" class="pncp-empty">Nenhuma cotação encontrada no backend.</td>
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
            <button type="button" class="pncp-modal__btn pncp-modal__btn--danger" :disabled="isDeleting" @click="confirmDelete">
              {{ isDeleting ? 'Excluindo...' : 'Excluir' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div
        v-if="showCreateModal"
        class="pncp-modal-backdrop"
        role="presentation"
        @click.self="closeCreateModal"
      >
        <div
          class="pncp-modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="pncp-create-title"
          @click.stop
        >
          <h2 id="pncp-create-title" class="pncp-modal__title">Nova cotação</h2>
          <p class="pncp-modal__text">
            O título sugerido inclui seu nome cadastrado e a data/hora. Ao criar, o sistema grava também seu e-mail e o vínculo com seu usuário; o termo inicial de busca no PNCP será o mesmo título.
          </p>
          <div class="pncp-modal__form">
            <label class="pncp-modal__field">
              <span>Título <abbr title="obrigatório">*</abbr></span>
              <input
                v-model.trim="createForm.titulo"
                type="text"
                class="gov-input"
                placeholder="Ex.: Cotação de material de expediente — abril/2026"
                autocomplete="off"
              />
            </label>
          </div>
          <p v-if="createFormError" class="pncp-modal__error">{{ createFormError }}</p>
          <div class="pncp-modal__actions">
            <button type="button" class="pncp-modal__btn pncp-modal__btn--ghost" @click="closeCreateModal">
              Cancelar
            </button>
            <button
              type="button"
              class="pncp-modal__btn pncp-modal__btn--primary"
              :disabled="isCreating"
              @click="submitCreateCotacao"
            >
              {{ isCreating ? 'Criando...' : 'Criar cotação' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import {
  createResearchSession,
  deleteResearchSession,
  fetchCurrentUser,
  listResearchSessions,
} from '../services/pncpResearch';

const router = useRouter();
const mockQuery = ref('');
const mockStatusFilter = ref('todos');
const isLoading = ref(false);
const isCreating = ref(false);
const isDeleting = ref(false);
const loadError = ref('');
const mockRows = ref([]);

const showCreateModal = ref(false);
const createFormError = ref('');
const createForm = ref({
  titulo: '',
});

async function openCreateModal() {
  createFormError.value = '';
  const now = new Date();
  let titulo = `Cotação ${now.toLocaleDateString('pt-BR')} ${now.toLocaleTimeString('pt-BR')}`;
  try {
    const me = await fetchCurrentUser();
    if (me?.full_name) {
      const dataLonga = now.toLocaleDateString('pt-BR', {
        weekday: 'long',
        day: 'numeric',
        month: 'long',
        year: 'numeric',
      });
      const hora = now.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
      titulo = `Cotação — ${me.full_name} — ${dataLonga} · ${hora}`;
    }
  } catch {
    /* mantém titulo com data simples */
  }
  createForm.value = { titulo };
  showCreateModal.value = true;
}

function closeCreateModal() {
  if (isCreating.value) return;
  showCreateModal.value = false;
}

async function loadSessionsFromBackend() {
  isLoading.value = true;
  loadError.value = '';
  try {
    const data = await listResearchSessions(100);
    if (data?.ok && Array.isArray(data.sessoes)) {
      mockRows.value = data.sessoes.map((s) => ({
        id: s.id,
        cotacaoId: String(s.id),
        data: formatDateTime(s.created_at || s.updated_at),
        descricao: s.titulo || s.termo_busca || `Cotação ${s.id}`,
        itens: Number(s.total_itens || 0),
        usuario: s.criado_por || '—',
        usuarioEmail: (s.criado_por_email || '').trim(),
        status: s.status === 'aberta' ? 'Em andamento' : 'Finalizada',
      }));
    }
  } catch (err) {
    loadError.value = `Backend PNCP indisponível (${err.message || 'erro desconhecido'}).`;
  } finally {
    isLoading.value = false;
  }
}

async function submitCreateCotacao() {
  const titulo = (createForm.value.titulo || '').trim();
  if (!titulo) {
    createFormError.value = 'Informe um título para a cotação.';
    return;
  }
  createFormError.value = '';
  isCreating.value = true;
  loadError.value = '';
  try {
    const payload = { titulo, filtros: {} };
    const data = await createResearchSession(payload);
    const newId = data?.sessao_id ?? data?.cotacao_id;
    if (data?.ok && newId != null) {
      showCreateModal.value = false;
      router.push(`/pesquisador-pncp/cotacoes/${newId}`);
    }
  } catch (err) {
    createFormError.value = err.message || 'Erro desconhecido ao criar cotação.';
  } finally {
    isCreating.value = false;
  }
}

function formatDateTime(iso) {
  if (!iso) return '--';
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return String(iso);
  return dt.toLocaleString('pt-BR');
}

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
      (row.usuarioEmail && row.usuarioEmail.toLowerCase().includes(q)) ||
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

async function confirmDelete() {
  if (!pendingDelete.value) return;
  const row = pendingDelete.value;
  isDeleting.value = true;
  loadError.value = '';
  try {
    await deleteResearchSession(row.id);
    mockRows.value = mockRows.value.filter((r) => r.id !== row.id);
    pendingDelete.value = null;
  } catch (err) {
    loadError.value = `Falha ao excluir cotação (${err.message || 'erro desconhecido'}).`;
  } finally {
    isDeleting.value = false;
  }
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

let escCreateHandler = null;
watch(showCreateModal, (open) => {
  if (escCreateHandler) {
    window.removeEventListener('keydown', escCreateHandler);
    escCreateHandler = null;
  }
  if (open) {
    escCreateHandler = (e) => {
      if (e.key === 'Escape') closeCreateModal();
    };
    window.addEventListener('keydown', escCreateHandler);
  }
});

onUnmounted(() => {
  if (escHandler) window.removeEventListener('keydown', escHandler);
  if (escCreateHandler) window.removeEventListener('keydown', escCreateHandler);
});
onMounted(() => {
  loadSessionsFromBackend();
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

.gov-page__meta {
  margin: 6px 0 0;
  font-size: 12px;
  color: #64748b;
}

.gov-page__meta--error {
  color: #b91c1c;
}

.gov-page__meta--ok {
  color: #0f5e3a;
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

.pncp-empty {
  text-align: center !important;
  color: #64748b;
}

.pncp-mock__table th {
  color: var(--color-text-soft);
  font-size: 11px;
  text-transform: uppercase;
}

.pncp-mock__desc {
  font-weight: 600;
}

.pncp-mock__usuario {
  font-weight: 600;
  font-size: 12px;
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

.pncp-modal__form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin: 12px 0 16px;
}

.pncp-modal__field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: var(--color-text-soft);
}

.pncp-modal__field span abbr {
  text-decoration: none;
  color: #b91c1c;
}

.pncp-modal__error {
  margin: 0 0 12px;
  font-size: 13px;
  color: #b91c1c;
}

.pncp-modal__btn--primary {
  background: #1f4e79;
  border-color: #1f4e79;
  color: #fff;
}

.pncp-modal__btn--primary:hover:not(:disabled) {
  filter: brightness(0.95);
}

.pncp-modal__btn--primary:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}
</style>
